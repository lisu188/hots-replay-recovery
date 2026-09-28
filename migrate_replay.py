from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from decoders import BitPackedDecoder, VersionedDecoder
from encoders import BitPackedEncoder, encode_header
from mpq_reader import MPQArchive
from mpq_rebuild import rebuild_replay, verify_container

SOURCE_SHA256 = 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
UPSTREAM_COMMIT = '9af3ea7150f1a8acb53464c92519a9bbcc7a3594'
DEFAULTS = {
    'm_ammId': None, 'm_vector': None,
    'm_banner': b'', 'm_spray': b'', 'm_announcerPack': b'', 'm_voiceLine': b'',
    'm_heroMasteryTiers': [], 'm_disabledHeroList': [],
    'm_hasVoiceSilencePenalty': False, 'm_isBlizzardStaff': False,
    'm_hasActiveBoost': False, 'm_isRandomTestValue': False,
}


@dataclass(frozen=True)
class BitVector:
    length: int
    value: int


class SemanticDecoder(BitPackedDecoder):
    def _bitarray(self, bounds):
        length = self._int(bounds)
        return BitVector(length, sum(self._buffer.read_bits(1) << i for i in range(length)))


class SemanticEncoder(BitPackedEncoder):
    def _bitarray(self, bounds, value):
        if not isinstance(value, BitVector):
            raise TypeError('Expected a physical-order BitVector')
        if value.value < 0 or value.value >= 1 << value.length:
            raise ValueError('Invalid bit vector')
        self._int(bounds, value.length)
        for i in range(value.length):
            self._buffer.write_bits((value.value >> i) & 1, 1)


def json_value(value):
    if isinstance(value, BitVector):
        return {'$bitvector': {'length': value.length, 'lsb0': hex(value.value)}}
    if isinstance(value, bytes):
        return {'$bytes_base64': base64.b64encode(value).decode('ascii')}
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items() if k != '_bits'}
    if isinstance(value, (list, tuple)):
        return [json_value(x) for x in value]
    return value


def dump(value):
    return json.dumps(json_value(value), sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(value), sort_keys=True, indent=2) + '\n', encoding='utf-8')


def protocol(build, local=False):
    name = f'protocol{build}' if local else f'heroprotocol.versions.protocol{build}'
    return importlib.import_module(name)


def decode_events(raw, p, kind):
    decoder = VersionedDecoder(raw, p.typeinfos) if kind == 'tracker' else SemanticDecoder(raw, p.typeinfos)
    event_types = getattr(p, f'{kind}_event_types')
    event_id_type = getattr(p, f'{kind}_eventid_typeid')
    loop = 0
    while not decoder.done():
        delta = decoder.instance(p.svaruint32_typeid)
        loop += next(iter(delta.values()))
        user = decoder.instance(p.replay_userid_typeid) if kind != 'tracker' else None
        event_id = decoder.instance(event_id_type)
        if event_id not in event_types:
            raise ValueError(f'Unknown {kind} event id {event_id}')
        type_id, name = event_types[event_id]
        event = decoder.instance(type_id)
        event.update(_event=name, _eventid=event_id, _gameloop=loop)
        if kind != 'tracker':
            event['_userid'] = user
        decoder.byte_align()
        yield event


def encode_events(events, p, kind):
    if kind == 'tracker':
        raise ValueError('Tracker bytes must be preserved')
    encoder = SemanticEncoder(p.typeinfos)
    previous = 0
    for event in events:
        delta = event['_gameloop'] - previous
        if not 0 <= delta < 1 << 32:
            raise ValueError('Invalid event time delta')
        previous = event['_gameloop']
        widths = (6, 14, 22, 32)
        width = next(n for n in widths if delta < 1 << n)
        encoder.instance(p.svaruint32_typeid, {f'm_uint{width}': delta})
        encoder.instance(p.replay_userid_typeid, event['_userid'])
        event_id = event['_eventid']
        encoder.instance(getattr(p, f'{kind}_eventid_typeid'), event_id)
        type_id, name = getattr(p, f'{kind}_event_types')[event_id]
        if name != event['_event']:
            raise ValueError('Event name/id mismatch')
        encoder.instance(type_id, event)
        encoder.byte_align()
    return encoder.getvalue()


def note(audit, path, operation, before, after):
    audit.append({'path': path, 'operation': operation, 'before': before, 'after': after})


def adapt(value, p, tid, path, audit):
    kind, args = p.typeinfos[tid]
    if kind == '_struct':
        if not isinstance(value, dict):
            raise TypeError(f'{path}: expected object')
        names = {name for name, _, _ in args[0]}
        if '__parent' in names:
            raise ValueError('Parent-flattened structures are not migrated by this adapter')
        result = {}
        renamed = set()
        for name, child, _ in args[0]:
            key = f'{path}/{name}'
            if name in value:
                old = value[name]
            elif name == 'm_replayCompatibilityHash' and 'm_fixedFileHash' in value:
                old = value['m_fixedFileHash']
                renamed.add('m_fixedFileHash')
                note(audit, key, 'reinterpret-unverified-hash', old, old)
            elif path.startswith('/header') and p.typeinfos[child][0] == '_optional':
                continue
            elif name in DEFAULTS:
                old = copy.deepcopy(DEFAULTS[name])
                note(audit, key, 'default', {'$absent': True}, old)
            else:
                raise ValueError(f'{key}: no explicit migration rule')
            result[name] = adapt(old, p, child, key, audit)
        for name in sorted(value.keys() - names - renamed):
            if name not in ('m_licenses', 'm_artifacts') or any(value[name]):
                raise ValueError(f'{path}/{name}: refusing to discard data')
            note(audit, f'{path}/{name}', 'remove-empty-legacy-field', value[name], {'$absent': True})
        return result
    if kind == '_array':
        check_bound(len(value), args[0], path)
        return [adapt(x, p, args[1], f'{path}/{i}', audit) for i, x in enumerate(value)]
    if kind == '_optional':
        return None if value is None else adapt(value, p, args[0], path, audit)
    if kind == '_choice':
        if len(value) != 1:
            raise ValueError(f'{path}: invalid choice')
        name = next(iter(value))
        choices = {n: child for n, child in args[1].values()}
        if name == 'MouseButton' and 'MouseEvent' in choices:
            new = {'MouseEvent': {'m_button': value[name], 'm_metaKeyFlags': 0}}
            note(audit, path, 'mouse-event-upgrade', value, new)
            value, name = new, 'MouseEvent'
        if name not in choices:
            raise ValueError(f'{path}: unmapped choice {name}')
        return {name: adapt(value[name], p, choices[name], f'{path}/{name}', audit)}
    if kind == '_bitarray':
        if not isinstance(value, BitVector):
            raise TypeError(f'{path}: expected logical bit vector')
        minimum, bits = args[0]
        maximum = minimum + (1 << bits) - 1
        if value.length > maximum:
            if not path.endswith('/m_allowedControls'):
                raise ValueError(f'{path}: cannot narrow bit vector')
            if value.value != (1 << value.length) - 1 and value.value >> maximum:
                raise ValueError(f'{path}: nonzero unrepresentable control flags')
            new = BitVector(maximum, value.value & ((1 << maximum) - 1))
            op = 'restrict-all-controls-to-target-domain' if value.value >> maximum else 'remove-zero-control-tail'
            note(audit, path, op, value, new)
            value = new
        check_bound(value.length, args[0], path)
        return value
    if kind == '_int':
        check_bound(value, args[0], path)
    elif kind == '_blob':
        if not isinstance(value, bytes):
            raise TypeError(f'{path}: expected bytes')
        check_bound(len(value), args[0], path)
    elif kind == '_fourcc':
        if not isinstance(value, bytes) or len(value) != 4:
            raise ValueError(f'{path}: invalid fourcc')
    elif kind == '_bool':
        if not isinstance(value, bool):
            raise TypeError(f'{path}: expected bool')
    elif kind == '_null':
        if value is not None:
            raise ValueError(f'{path}: expected null')
    elif kind not in ('_real32', '_real64'):
        raise ValueError(f'Unsupported type {kind}')
    return value


def check_bound(value, bounds, path):
    low, width = bounds
    if not isinstance(value, int) or not low <= value < low + (1 << width):
        raise ValueError(f'{path}: {value} outside {bounds}')


def migrate(source: Path, target_build: int, root: Path, local=False) -> dict:
    source, root = Path(source), Path(root)
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('This experiment is scoped to the preserved TEN_GREYMANE source')
    sp, tp = protocol(41810, local), protocol(target_build, local)
    folder = root / 'checkpoints' / str(target_build)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f'TEN_GREYMANE_protocol{target_build}.StormReplay'
    temporary = out.with_suffix('.tmp')
    archive = MPQArchive(source)
    checked = None
    try:
        audit = []
        header = sp.decode_replay_header(archive.header['user_data_header']['content'])
        intended_header = adapt(copy.deepcopy(header), tp, tp.replay_header_typeid, '/header', audit)
        for name in ('m_build', 'm_baseBuild'):
            note(audit, f'/header/m_version/{name}', 'target-protocol', intended_header['m_version'][name], target_build)
            intended_header['m_version'][name] = target_build
        initial = SemanticDecoder(archive.read_file('replay.initData'), sp.typeinfos).instance(sp.replay_initdata_typeid)
        intended_initial = adapt(initial, tp, tp.replay_initdata_typeid, '/initData', audit)
        encoder = SemanticEncoder(tp.typeinfos)
        encoder.instance(tp.replay_initdata_typeid, intended_initial)
        replacements = {'replay.initData': encoder.getvalue()}
        intended_streams, source_streams, stream_hashes, changed_counts = {}, {}, {}, {}
        for kind in ('game', 'message', 'tracker'):
            raw = archive.read_file(f'replay.{kind}.events')
            before = list(decode_events(raw, sp, kind))
            source_streams[kind] = before
            if kind == 'tracker':
                after = before
            else:
                mapping = {name: (eid, tid) for eid, (tid, name) in getattr(tp, f'{kind}_event_types').items()}
                after = []
                for i, event in enumerate(before):
                    event_id, tid = mapping[event['_event']]
                    fields = {k: v for k, v in event.items() if not k.startswith('_')}
                    fields = adapt(fields, tp, tid, f'/{kind}/{i}', audit)
                    if event['_event'] == 'NNet.Game.SUserOptionsEvent':
                        for name in ('m_buildNum', 'm_baseBuildNum'):
                            note(audit, f'/{kind}/{i}/{name}', 'target-protocol', fields[name], target_build)
                            fields[name] = target_build
                    fields.update({k: v for k, v in event.items() if k.startswith('_')})
                    fields['_eventid'] = event_id
                    after.append(fields)
                encoded = encode_events(after, tp, kind)
                if encoded != raw:
                    replacements[f'replay.{kind}.events'] = encoded
            intended_streams[kind] = after
            delta_path = folder / f'{kind}.changes.jsonl'
            changed = 0
            with delta_path.open('w', encoding='utf-8') as handle:
                for i, (old, new) in enumerate(zip(before, after)):
                    if old != new:
                        handle.write(dump({'index': i, 'before': old, 'after': new}) + '\n')
                        changed += 1
            changed_counts[kind] = changed
            stream_hashes[kind] = hashlib.sha256((''.join(dump(x) + '\n' for x in after)).encode()).hexdigest()
        container_report = rebuild_replay(source, temporary, encode_header(intended_header, tp), replacements)
        container_checks = verify_container(temporary)
        checked = MPQArchive(temporary)
        actual_header = tp.decode_replay_header(checked.header['user_data_header']['content'])
        actual_initial = SemanticDecoder(checked.read_file('replay.initData'), tp.typeinfos).instance(tp.replay_initdata_typeid)
        if actual_header != intended_header or actual_initial != intended_initial:
            raise AssertionError('Header or lobby round-trip mismatch')
        for kind, intended in intended_streams.items():
            actual = list(decode_events(checked.read_file(f'replay.{kind}.events'), tp, kind))
            if actual != intended:
                raise AssertionError(f'{kind} stream round-trip mismatch')
        for name in archive.read_file('(listfile)').decode('utf-8').splitlines() + ['(listfile)']:
            if name not in replacements and archive.read_file(name) != checked.read_file(name):
                raise AssertionError(f'Untouched MPQ member changed: {name}')
        checked.close()
        checked = None
        os.replace(temporary, out)
        raw = out.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        artifact_base = folder / (out.name + '.base64')
        text = base64.encodebytes(raw).decode('ascii').splitlines(keepends=True)
        for old in folder.glob(out.name + '.base64.part*'):
            old.unlink()
        for number, start in enumerate(range(0, len(text), 1000)):
            artifact_base.with_name(artifact_base.name + f'.part{number:03d}').write_text(''.join(text[start:start + 1000]), encoding='ascii', newline='\n')
        out.with_name(out.name + '.sha256').write_text(f'{digest}  {out.name}\n', encoding='ascii')
        reconstructed = base64.b64decode(''.join(p.read_text(encoding='ascii') for p in sorted(folder.glob(out.name + '.base64.part*'))), validate=False)
        if reconstructed != raw:
            raise AssertionError('Base64 reconstruction mismatch')
        write_json(folder / 'header.json', intended_header)
        write_json(folder / 'initData.json', intended_initial)
        with (folder / 'semantic-audit.jsonl').open('w', encoding='utf-8') as handle:
            for entry in audit:
                handle.write(dump(entry) + '\n')
        report = {
            'source_build': 41810, 'source_sha256': SOURCE_SHA256, 'target_protocol': target_build,
            'output_sha256': digest, 'output_bytes': len(raw),
            'roundtrip_validated': True, 'base64_roundtrip_validated': True,
            'client_playback_validated': False, 'simulation_compatibility_validated': False,
            'protocol_provider': 'local' if local else 'Blizzard/heroprotocol',
            'upstream_commit': None if local else UPSTREAM_COMMIT,
            'events': {k: len(v) for k, v in intended_streams.items()},
            'changed_events': changed_counts, 'stream_jsonl_sha256': stream_hashes,
            'semantic_audit_entries': len(audit), 'container': container_report, 'container_checks': container_checks,
            'projection': 'hots-replay-json-v2-physical-bitvectors',
            'known_limitations': [
                'Source dataBuildNum, root key and version tuple are preserved; target metadata is unverified.',
                'The renamed compatibility hash retains original opaque bytes, not a verified target hash.',
                'All-controls vectors are restricted to the target representable domain; no catalog equivalence is proven.',
                'Opaque sync, resumable and battlelobby members remain unchanged.',
                'Encoding command flags at a new width does not prove their engine semantics are unchanged.',
                'No HotS client or deterministic replay simulation was executed.',
            ],
        }
        write_json(folder / 'report.json', report)
        return report
    finally:
        if checked is not None:
            checked.close()
        archive.close()
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--target', type=int, required=True)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--local-protocols', action='store_true')
    args = parser.parse_args()
    print(json.dumps(migrate(args.source, args.target, args.root, args.local_protocols), indent=2))


if __name__ == '__main__':
    main()
