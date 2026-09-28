from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import struct
from collections import Counter
from pathlib import Path

from encoders import VersionedEncoder, encode_header, encode_tracker_events
from migrate_replay import BitVector, SemanticDecoder, SemanticEncoder, decode_events, encode_events, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_EVENTS = 500000
TARGET_FIELDS = ('m_version', 'm_dataBuildNum', 'm_ngdpRootKey', 'm_replayCompatibilityHash')


def checked_archive(path: Path) -> MPQArchive:
    path = Path(path)
    size = path.stat().st_size
    if not 48 <= size <= MAX_FILE_BYTES:
        raise ValueError('Reference replay is outside the supported file-size limits')
    with path.open('rb') as handle:
        magic, capacity, offset, length = struct.unpack('<4sIII', handle.read(16))
        if magic != b'MPQ\x1b' or not 16 <= offset <= size - 32 or length > offset - 16:
            raise ValueError('Invalid replay user-data header')
        handle.seek(offset)
        h = struct.unpack('<4sIIHHIIII', handle.read(32))
        if h[0] != b'MPQ\x1a' or h[1] < 32 or h[3] > 3:
            raise ValueError('Unsupported replay archive header')
        for start, count in ((h[5], h[7]), (h[6], h[8])):
            if count > 100000 or offset + start + count * 16 > size:
                raise ValueError('Invalid replay table bounds')
    archive = MPQArchive(path)
    try:
        if sum(b.size for b in archive.block_table) > 4 * MAX_MEMBER_BYTES:
            raise ValueError('Reference replay exceeds the decoded-size limit')
        for block in archive.block_table:
            if block.size > MAX_MEMBER_BYTES or offset + block.offset + block.archived_size > size:
                raise ValueError('Invalid replay member bounds')
        return archive
    except BaseException:
        archive.close()
        raise


class SortedVersionedEncoder(VersionedEncoder):
    def _struct(self, fields, value):
        super()._struct(sorted(fields, key=lambda field: field[2]), value)


def native(value):
    if isinstance(value, BitVector):
        return [value.length, value.value]
    if isinstance(value, dict):
        return {k: native(v) for k, v in value.items() if k != '_bits'}
    if isinstance(value, (tuple, list)):
        return [native(v) for v in value]
    return value


def metadata(header: dict) -> dict:
    version = header.get('m_version', {})
    for key in ('m_flags', 'm_major', 'm_minor', 'm_revision', 'm_build', 'm_baseBuild'):
        value = version.get(key)
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError(f'Invalid reference version field: {key}')
    if version['m_build'] <= 0 or version['m_baseBuild'] <= 0:
        raise ValueError('Reference build numbers must be positive')
    fields = dict(header)
    if 'm_replayCompatibilityHash' not in fields and 'm_fixedFileHash' in fields:
        fields['m_replayCompatibilityHash'] = fields['m_fixedFileHash']
    for key in ('m_ngdpRootKey', 'm_replayCompatibilityHash'):
        raw = fields.get(key, {}).get('m_data')
        if not isinstance(raw, bytes) or len(raw) != 16 or (key == 'm_ngdpRootKey' and not any(raw)):
            raise ValueError(f'Missing or invalid reference identifier: {key}')
    data_build = fields.get('m_dataBuildNum')
    if type(data_build) is not int or not 0 < data_build < 2**32:
        raise ValueError('Invalid reference data build')
    return {key: fields[key] for key in TARGET_FIELDS}


def peek(path: Path) -> dict:
    import protocol41810
    archive = checked_archive(path)
    try:
        header = protocol41810.decode_replay_header(archive.header['user_data_header']['content'])
        target = metadata(header)
        return {'file_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                'file_bytes': Path(path).stat().st_size, 'target': target,
                'header_only': True, 'client_playback_validated': False}
    finally:
        archive.close()


def inspect_reference(path: Path, schema_build: int, expected_build: int | None = None,
                      local: bool = False) -> dict:
    path = Path(path)
    archive = checked_archive(path)
    try:
        initial_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        p = load_protocol(schema_build, local)
        header_raw = archive.header['user_data_header']['content']
        header = p.decode_replay_header(header_raw)
        target = metadata(header)
        build = target['m_version']['m_build']
        if expected_build is not None and build != expected_build:
            raise ValueError(f'Reference declares {build}, expected {expected_build}')
        if encode_header(header, p) != header_raw:
            raise ValueError('Reference header contains unsupported or noncanonical serialized data')
        details_raw = archive.read_file('replay.details')
        details = p.decode_replay_details(details_raw)
        details_encoder = SortedVersionedEncoder(p.typeinfos)
        details_encoder.instance(p.game_details_typeid, details)
        if details_encoder.getvalue() != details_raw:
            raise ValueError('Reference details do not round-trip through the selected schema')
        initial_raw = archive.read_file('replay.initData')
        initial = SemanticDecoder(initial_raw, p.typeinfos).instance(p.replay_initdata_typeid)
        encoder = SemanticEncoder(p.typeinfos)
        encoder.instance(p.replay_initdata_typeid, initial)
        if encoder.getvalue() != initial_raw:
            raise ValueError('Reference lobby does not round-trip through the selected schema')
        if native(initial) != native(p.decode_replay_initdata(initial_raw)):
            raise ValueError('Official and semantic lobby decoders disagree')
        streams, options = {}, []
        for kind in ('game', 'message', 'tracker'):
            raw = archive.read_file(f'replay.{kind}.events')
            if raw is None:
                raise ValueError(f'Reference lacks its {kind} event stream')
            events = list(itertools.islice(decode_events(raw, p, kind), MAX_EVENTS + 1))
            if len(events) > MAX_EVENTS:
                raise ValueError(f'Reference {kind} stream exceeds the event limit')
            sentinel = object()
            official = getattr(p, f'decode_replay_{kind}_events')(raw)
            for a, b in itertools.zip_longest(events, official, fillvalue=sentinel):
                if a is sentinel or b is sentinel or native(a) != native(b):
                    raise ValueError(f'Official and semantic {kind} decoders disagree')
            encoded = encode_tracker_events(events, p) if kind == 'tracker' else encode_events(events, p, kind)
            if encoded != raw:
                raise ValueError(f'Reference {kind} stream does not round-trip byte-for-byte')
            streams[kind] = {'count': len(events), 'sha256': hashlib.sha256(raw).hexdigest(),
                             'event_types': dict(sorted(Counter(e['_event'] for e in events).items())),
                             'binary_roundtrip': True}
            if kind == 'game':
                options = [{k: e[k] for k in ('m_buildNum', 'm_baseBuildNum', 'm_versionFlags')}
                           for e in events if e['_event'] == 'NNet.Game.SUserOptionsEvent']
        if not options or any(o != options[0] for o in options):
            raise ValueError('Reference client-version options are absent or inconsistent')
        if (options[0]['m_buildNum'] != build or
                options[0]['m_baseBuildNum'] != target['m_version']['m_baseBuild']):
            raise ValueError('Reference header and client-version options disagree')
        if initial_digest != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Reference changed while it was being inspected')
        return {'format': 'hots-reference-profile-v1', 'file_sha256': initial_digest,
                'file_bytes': path.stat().st_size, 'target': target, 'user_options': options[0],
                'schema_build': schema_build,
                'schema_file_sha256': hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest(),
                'protocol_provider': 'local' if local else 'Blizzard/heroprotocol',
                'declared_base_matches_schema': target['m_version']['m_baseBuild'] == schema_build,
                'observed_payload_roundtrip': True, 'all_target_event_types_proven': False,
                'proven_authentic_by_signature': False, 'client_playback_validated': False,
                'compatibility_hash_is_zero': not any(target['m_replayCompatibilityHash']['m_data']),
                'streams': streams,
                'limitations': ['Successful decoding covers only the event types present in this reference.',
                                'A replay header is self-declared metadata, not an authenticity signature.',
                                'Matching serialization does not establish identical simulation or catalogs.']}
    finally:
        archive.close()


def scan(root: Path, minimum_build: int, limit: int = 5000) -> dict:
    if not Path(root).is_dir():
        raise NotADirectoryError(root)
    if not 1 <= limit <= 100000:
        raise ValueError('Invalid scan limit')
    matches, errors, seen = [], 0, 0
    candidates = itertools.islice(Path(root).rglob('*.StormReplay'), limit + 1)
    for path in candidates:
        seen += 1
        if seen > limit:
            break
        try:
            result = peek(path)
            if result['target']['m_version']['m_build'] >= minimum_build:
                matches.append({'local_path': str(path.resolve()), **result})
        except Exception:
            errors += 1
    return {'matches': matches, 'scanned': min(seen, limit), 'errors': errors,
            'truncated': seen > limit, 'local_paths_are_private': True}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('replay', type=Path)
    inspect.add_argument('--schema-build', type=int, required=True)
    inspect.add_argument('--expected-build', type=int)
    inspect.add_argument('--output', type=Path, required=True)
    discover = sub.add_parser('scan')
    discover.add_argument('root', type=Path)
    discover.add_argument('--minimum-build', type=int, default=96477)
    discover.add_argument('--limit', type=int, default=5000)
    discover.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inspect':
        result = inspect_reference(args.replay, args.schema_build, args.expected_build)
    else:
        result = scan(args.root, args.minimum_build, args.limit)
    write_json(args.output, result)
    print(json.dumps({'report': str(args.output), 'command': args.command}))


if __name__ == '__main__':
    main()
