from __future__ import annotations

import argparse
import hashlib
import json
import struct
import tempfile
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

R7_SHA256 = '3cedf89c901c98e43201542dba901797c222e9ce36215f4d234bd43dfc66581e'
OUTPUT_NAME = 'TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay'
MEMBER = 'replay.resumable.events'
SOURCE_STREAM_SHA256 = '149a6dc6b02f74b04801c2830ed5c0416c6204ab8e5760e758c102f21c7a7aa7'
MIGRATED_STREAM_SHA256 = '2d439945492b06bb4a606451b81c73d7299dd0ce29fe1c9e36ce91621741735c'
OBSERVATION_SHA256 = 'c72fad298d71b0450353045f82807f2a7d4c0a145276caca948d0fe688bf9702'
KINDS = frozenset((1, 2, 3, 5))
MAX_BYTES = 1024 * 1024
MAX_RECORDS = 65536
MAX_NAME_BYTES = 1024


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def integer(value: int, maximum: int, label: str) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Invalid ' + label)
    return value


@dataclass(frozen=True)
class Record:
    gameloop: int
    kind: int
    user_id: int
    name: bytes
    legacy_color: int | None = None

    def validate(self, legacy: bool) -> None:
        integer(self.gameloop, 0xffffffff, 'game loop')
        integer(self.kind, 255, 'record kind')
        integer(self.user_id, 16, 'user ID')
        if self.kind not in KINDS:
            raise ValueError('Unobserved resumable record kind')
        if not isinstance(self.name, bytes) or len(self.name) > MAX_NAME_BYTES:
            raise ValueError('Invalid resumable name bytes')
        self.name.decode('utf-8', errors='strict')
        if legacy:
            integer(self.legacy_color, 0xffffffff, 'legacy color')
        elif self.legacy_color is not None:
            raise ValueError('Modern encoding cannot silently discard legacy color')


def decode(raw: bytes, legacy: bool) -> list[Record]:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES or type(legacy) is not bool:
        raise ValueError('A bounded byte stream and explicit layout are required')
    cursor = 0
    result = []
    width = 12 if legacy else 8
    while cursor < len(raw):
        if len(result) >= MAX_RECORDS or len(raw) - cursor < width:
            raise ValueError('Truncated or excessive resumable records')
        loop, kind, user = struct.unpack_from('<IBB', raw, cursor)
        cursor += 6
        color = None
        if legacy:
            color = struct.unpack_from('<I', raw, cursor)[0]
            cursor += 4
        size = struct.unpack_from('<H', raw, cursor)[0]
        cursor += 2
        if size > MAX_NAME_BYTES or size > len(raw) - cursor:
            raise ValueError('Resumable name length exceeds the remaining stream')
        record = Record(loop, kind, user, raw[cursor:cursor + size], color)
        record.validate(legacy)
        result.append(record)
        cursor += size
    return result


def encode(records: list[Record], legacy: bool) -> bytes:
    if not isinstance(records, list) or len(records) > MAX_RECORDS or type(legacy) is not bool:
        raise ValueError('Invalid record collection or layout')
    result = bytearray()
    for record in records:
        if not isinstance(record, Record):
            raise ValueError('Expected resumable records')
        record.validate(legacy)
        result += struct.pack('<IBB', record.gameloop, record.kind, record.user_id)
        if legacy:
            result += struct.pack('<I', record.legacy_color)
        result += struct.pack('<H', len(record.name)) + record.name
        if len(result) > MAX_BYTES:
            raise ValueError('Encoded stream exceeds the supported limit')
    return bytes(result)


def migrate(raw: bytes) -> tuple[bytes, list[dict]]:
    before = decode(raw, True)
    if encode(before, True) != raw:
        raise AssertionError('Legacy records did not round-trip')
    after = [replace(record, legacy_color=None) for record in before]
    encoded = encode(after, False)
    if decode(encoded, False) != after:
        raise AssertionError('Modern records did not round-trip')
    changes = [{'record_index': index, 'gameloop': row.gameloop,
                'path': f'/{MEMBER}/{index}/legacy_color',
                'before_u32_le': row.legacy_color, 'after': None,
                'reason': 'Remove the four-byte field absent from all inspected modern records; preserve it in this audit.'}
               for index, row in enumerate(before)]
    restored = [replace(row, legacy_color=changes[index]['before_u32_le']) for index, row in enumerate(after)]
    if encode(restored, True) != raw or len(raw) - len(encoded) != 4 * len(before):
        raise AssertionError('Audit does not reconstruct the original stream')
    return encoded, changes


def summarize(raw: bytes, legacy: bool) -> dict:
    rows = decode(raw, legacy)
    if encode(rows, legacy) != raw:
        raise AssertionError('Resumable stream round-trip failed')
    return {'layout': 'legacy-with-color' if legacy else 'modern-without-color',
            'sha256': sha256(raw), 'bytes': len(raw), 'records': len(rows),
            'kind_counts': {str(k): v for k, v in sorted(Counter(row.kind for row in rows).items())},
            'first_record_gameloop': None if not rows else rows[0].gameloop,
            'last_record_gameloop': None if not rows else rows[-1].gameloop,
            'order_decreases': sum(a.gameloop > b.gameloop for a, b in zip(rows, rows[1:])),
            'roundtrip_exact': True}


def repair(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink() or source.resolve() == output.resolve():
        raise FileExistsError('Use a new R8 checkpoint directory')
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('A bounded regular immutable R7 file is required')
    original_bytes = source.read_bytes()
    if sha256(original_bytes) != R7_SHA256:
        raise ValueError('Only the immutable published R7 checkpoint is accepted')
    from bind_client_metadata import independent_member, publish_binary
    from migrate_replay import dump, write_json
    from mpq_reader import MPQArchive
    from reference_replay import inspect_reference
    from repair_control_masks import integrity
    from repair_startup import native_replace
    from mpyq import MPQArchive as IndependentArchive

    observation_path = Path(__file__).parent / 'observations/resumable-layout-2026-09-29.json'
    if sha256(observation_path.read_bytes()) != OBSERVATION_SHA256:
        raise ValueError('The reviewed resumable observation changed')
    before_profile = inspect_reference(source, 96477, 98285)
    original = MPQArchive(source)
    try:
        header = original.header['user_data_header']['content']
        names = list(dict.fromkeys(original.read_file('(listfile)').decode('ascii').splitlines() + ['(listfile)', '(attributes)']))
        members = {name: original.read_file(name) for name in names}
    finally:
        original.close()
    old = members[MEMBER]
    summary = summarize(old, True)
    if summary['records'] != 65 or summary['bytes'] != 1195 or summary['kind_counts'] != {'1': 61, '2': 2, '3': 1, '5': 1}:
        raise ValueError('The reviewed original resumable record distribution changed')
    encoded, changes = migrate(old)
    if sha256(old) != SOURCE_STREAM_SHA256 or sha256(encoded) != MIGRATED_STREAM_SHA256:
        raise ValueError('Resumable payload differs from the fully inspected source/migration')
    input_integrity = integrity(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.resumable-r8-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'checkpoint'
        stage.mkdir()
        destination = stage / OUTPUT_NAME
        container = native_replace(source, destination, header, {MEMBER: encoded})
        after_profile = inspect_reference(destination, 96477, 98285)
        output_integrity = integrity(destination)
        actual = MPQArchive(destination)
        independent = IndependentArchive(str(destination), listfile=False)
        verification = {}
        try:
            if actual.header['user_data_header']['content'] != header or independent.header['user_data_header']['content'] != header:
                raise AssertionError('R8 changed the replay header')
            for name in names:
                raw = actual.read_file(name)
                if independent_member(independent, name) != raw:
                    raise AssertionError('Independent archive extraction disagrees: ' + name)
                expected = encoded if name == MEMBER else members[name]
                if name != '(attributes)' and raw != expected:
                    raise AssertionError('R8 changed another replay member: ' + name)
                verification[name] = {'before_sha256': sha256(members[name]), 'after_sha256': sha256(raw),
                                      'bytes_identical': raw == members[name], 'independent_reader_equal': True}
            modern = decode(actual.read_file(MEMBER), False)
            restored = [replace(row, legacy_color=changes[index]['before_u32_le']) for index, row in enumerate(modern)]
            if encode(restored, True) != old:
                raise AssertionError('Candidate and audit fail to reconstruct original resumable records')
        finally:
            independent.file.close()
            actual.close()
        if source.read_bytes() != original_bytes:
            raise AssertionError('R7 source was modified')
        counts = {k: v['count'] for k, v in after_profile['streams'].items()}
        if counts != {k: v['count'] for k, v in before_profile['streams'].items()}:
            raise AssertionError('Parsed event counts changed')
        report = {'format': 'hots-resumable-layout-experiment-v1',
                  'status': 'partial-format-repair-not-client-validated', 'input_sha256': R7_SHA256,
                  'artifact': publish_binary(destination), 'before': summary, 'after': summarize(encoded, False),
                  'observation_sha256': OBSERVATION_SHA256,
                  'changed_payloads': [MEMBER], 'removed_color_fields': len(changes),
                  'old_stream_reconstructible_from_audit': True,
                  'game_message_tracker_and_sync_payloads_identical': True,
                  'record_order_preserved': True, 'events': counts, 'member_validation': verification,
                  'container': container, 'input_integrity': input_integrity, 'output_integrity': output_integrity,
                  'known_protocol_payload_roundtrip': True, 'resumable_layout_is_official_schema': False,
                  'protocol_schema_provider': 'Blizzard/heroprotocol', 'schema_build': 96477,
                  'exact_current_schema_verified': False,
                  'client_playback_validated': False, 'simulation_compatibility_validated': False,
                  'desync_cause_proven': False, 'sync_checks_removed_or_disabled': False,
                  'limitations': ['The resumable layout is inferred from complete observed source/reference streams, not an official schema.',
                                  'Record-kind semantics are not assigned by this converter.',
                                  'R7 command flags remain a hypothesis; unit catalogs, instance allocation and original simulation rules remain unresolved.',
                                  'The original synchronization payloads are preserved, so this candidate may still desynchronize.',
                                  'No HotS executable has played this candidate.']}
        write_json(stage / 'report.json', report)
        (stage / 'resumable.changes.jsonl').write_text(''.join(dump(row) + '\n' for row in changes), encoding='utf-8')
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(repair(args.source, args.output), indent=2))
