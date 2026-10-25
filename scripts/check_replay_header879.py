"""Audit three fixed user-data headers in RAM; retain sanitized evidence only."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys

import native_replay_header as header
from protocol_loader import load_protocol
from heroprotocol.decoders import VersionedDecoder, BitPackedDecoder, CorruptedError, TruncatedError

FIXTURES = (
    ('original41810', 635140, 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824', 41810),
    ('R8partial98285', 2438570, '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19', 98285),
    ('public98348', 978482, 'a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4', 98348),
)
HASH_CAP = 4 * 1024 * 1024


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sig(value):
    return [str(value.st_dev), str(value.st_ino), str(value.st_size), str(value.st_mtime_ns)]


def prior_guards(path, expected_sha):
    if path is None:
        need(expected_sha is None, 'Guard digest requires a guard report')
        return None
    need(expected_sha is not None and len(expected_sha) == 64, 'Explicit prior-report SHA is required')
    with Path(path).open('rb') as stream:
        raw = stream.read(32769)
    need(len(raw) <= 32768 and sha(raw) == expected_sha, 'Prior guard report digest or cap differs')
    value = json.loads(raw)
    need(value['format'] == 'actual-replay-header-numeric879-versioned-comparison-v1'
         and value['status'] == 'all-three-actual-headers-passed', 'Wrong prior guard report')
    by = {row['label']: row for row in value['cases']}
    need(len(by) == len(value['cases']) == 3, 'Prior source cases differ')
    for label, size, digest, _ in FIXTURES:
        row = by[label]
        need(row['source_bytes'] == size and row['source_sha256'] == digest,
             'Prior source fingerprint differs')
        identities = row['all_four_identity_checkpoints']
        need(len(identities) == 4 and all(type(x) is list and len(x) == 4 for x in identities)
             and all(x == identities[0] for x in identities)
             and row['post_analysis_identity'] == identities[0], 'Prior identity checkpoints differ')
    return by


def read_fixture(path, spec, prior):
    label, size, digest, _ = spec
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and not path.is_symlink()
         and not getattr(before, 'st_file_attributes', 0) & 1024 and before.st_size == size,
         'Fixture regular-file identity differs')
    expected = prior['all_four_identity_checkpoints'][0] if prior else None
    if expected is not None:
        need(sig(before) == expected, 'Fixture differs from prior authenticated identity')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        need(sig(opened) == sig(before), 'Fixture changed before open')
        hash_bytes = 0
        if prior is None:
            remaining, hasher = size, hashlib.sha256()
            while remaining:
                part = stream.read(min(1024 * 1024, remaining))
                need(bool(part), 'Truncated fixture authentication stream')
                hash_bytes += len(part)
                remaining -= len(part)
                hasher.update(part)
            need(hasher.hexdigest() == digest, 'Fixture SHA differs')
            need(sig(os.fstat(stream.fileno())) == sig(before), 'Fixture changed during hash')
        stream.seek(0)
        prefix = stream.read(16)
        need(len(prefix) == 16, 'Truncated MPQ user-data prefix')
        magic, capacity, base, length = struct.unpack('<4sIII', prefix)
        need(magic == b'MPQ\x1b' and 0 < length <= capacity and 16 + capacity <= base
             and base + 4 <= min(size, 4096) and 16 + length + 4 <= 4096,
             'Invalid bounded MPQ user-data header')
        raw = stream.read(length)
        need(len(raw) == length, 'Truncated declared wire header')
        stream.seek(base)
        need(stream.read(4) == b'MPQ\x1a', 'Declared archive signature differs')
        after = os.fstat(stream.fileno())
    need(sig(before) == sig(opened) == sig(after) == sig(path.stat()), 'Fixture identity changed')
    if prior:
        need(length == prior['declared_wire_bytes'] and sha(raw) == prior['wire_sha256'],
             'Header differs from prior authenticated wire payload')
    return raw, {'fixture': label, 'source_bytes': size, 'source_sha256': digest,
                 'header_bytes': length, 'header_sha256': sha(raw), 'hashstream_bytes': hash_bytes,
                 'prefix_bytes_read': 16 + length + 4, 'source_identity_unchanged': True,
                 'authentication': 'prior-SHA-report-and-current-four-field-identity' if prior else 'full-SHA-stream'}


def official(raw, build):
    protocol = load_protocol(build)
    decoder = VersionedDecoder(raw, protocol.typeinfos)
    value = decoder.instance(protocol.replay_header_typeid)
    need(decoder.done() and decoder.used_bits() == 8 * len(raw), 'Independent official EOF differs')
    return value


def audit(raw, expected_build, schema_path):
    view = header.decode_header879(raw, schema_path=schema_path)
    need(view.value[1][4] == view.value[1][5] == view.value[6] == expected_build,
         'Actual fixture build anchors differ')
    need(header.encode_header879(view) == raw, 'Source inverse differs')
    edited = header.replace_existing_int(view, (1, 4), expected_build + 1)
    edited_raw = header.encode_header879(edited)
    oracle_checks = 0
    for build in (41810, 96477):
        other = header.decode_header879(raw, schema_path=schema_path, official_build=build)
        need(other.value == view.value, 'Official schema numeric projections differ')
        expected = copy.deepcopy(official(raw, build))
        expected['m_version']['m_build'] = expected_build + 1
        # Deliberately decode the edited bytes directly with the independent
        # official implementation, not through the adapter's numeric view.
        need(official(edited_raw, build) == expected, 'Official edited header changed another field')
        oracle_checks += 1
    restored = header.replace_existing_int(edited, (1, 4), expected_build)
    need(header.encode_header879(restored) == raw and header.encode_header879(view) == raw,
         'Reverse edit/source preservation differs')
    for refused in (raw[:-1], raw + b'\0'):
        try:
            header.decode_header879(refused, schema_path=schema_path)
        except header.HeaderError:
            pass
        else:
            raise ValueError('Truncated/trailing header accepted')
    protocol = load_protocol(96477)
    try:
        bitpacked = BitPackedDecoder(raw, protocol.typeinfos)
        wrong = bitpacked.instance(protocol.replay_header_typeid)
    except (CorruptedError, TruncatedError, struct.error):
        negative = 'refused'
    else:
        need(not(bitpacked.done() and wrong == official(raw, 96477)), 'Unexpected bitpacked parity')
        negative = 'different-or-incomplete'
    return {'numeric_constraints_and_official_projection_EOF': True, 'source_inverse_exact': True,
            'edited_bytes_independent_official_checks': oracle_checks,
            'only_numeric_path_1_4_changed': True, 'reverse_edit_exact': True,
            'source_view_unchanged': True, 'truncated_and_trailing_refused': True,
            'bitpacked_negative_control': negative, 'unknown_paths': [list(p) for p in view.unknown_paths],
            'missing_paths': [list(p) for p in view.missing_paths]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--r8', type=Path, required=True)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--schema-path', type=Path)
    parser.add_argument('--prior-guard-report', type=Path)
    parser.add_argument('--prior-guard-sha256')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    need(not args.report.exists() and args.report.parent.is_dir(), 'Preserve prior report or create its parent first')
    need(sum(spec[1] for spec in FIXTURES) <= HASH_CAP, 'Fixed fixture hashstream budget differs')
    guards = prior_guards(args.prior_guard_report, args.prior_guard_sha256)
    rows = []
    for path, spec in zip((args.original, args.r8, args.current), FIXTURES):
        raw, row = read_fixture(path, spec, guards[spec[0]] if guards else None)
        row.update(audit(raw, spec[3], args.schema_path))
        rows.append(row)
    report = {'format': 'numeric879-three-actual-header-integration-v1', 'fixtures': rows,
              'fixture_count': 3, 'header_bytes': sum(row['header_bytes'] for row in rows),
              'hashstream_bytes': sum(row['hashstream_bytes'] for row in rows),
              'hashstream_cap_bytes': HASH_CAP, 'prefix_bytes_read': sum(row['prefix_bytes_read'] for row in rows),
              'prefix_cap_each': 4096, 'edited_bytes_official_oracle_checks': 6,
              'source_pins': {'schema': {'bytes': header.SCHEMA_PIN[0], 'sha256': header.SCHEMA_PIN[1]},
                              'lossless': {'bytes': header.LOSSLESS_PIN[0], 'sha256': header.LOSSLESS_PIN[1]},
                              'official_decoder': {'bytes': header.DECODER_PIN[0], 'sha256': header.DECODER_PIN[1]},
                              'official_protocols': {str(build): {'bytes': p[0], 'sha256': p[1]} for build, p in header.PROTOCOL_PINS.items()}},
              'replay_header_or_member_written': False, 'archive_members_read': False,
              'native_runtime_memory_offsets_or_full_compatibility_claim': False,
              'controlled_edit_is_build_retarget_policy': False}
    payload = (json.dumps(report, indent=2, ensure_ascii=True) + '\n').encode('ascii')
    need(len(payload) <= 32768, 'Sanitized audit report exceeds prewrite cap')
    with args.report.open('xb') as stream:
        need(stream.write(payload) == len(payload), 'Short report write')
    print(json.dumps({'header879_fixtures': 3, 'source_inverse_exact': True,
                      'edited_bytes_official_checks': 6, 'header_bytes': report['header_bytes'],
                      'hashstream_bytes': report['hashstream_bytes'], 'prefix_bytes': report['prefix_bytes_read'],
                      'report_bytes': len(payload), 'report_sha256': sha(payload)}, sort_keys=True))


if __name__ == '__main__':
    main()
