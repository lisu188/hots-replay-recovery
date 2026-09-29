from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import zipfile
from datetime import datetime
from pathlib import Path

from runtime_catalog_probe import BUILD, CHUNK, MAX_ENTRIES, TOKEN, combine_banks

PROBE_SHA256 = 'a1bc4403fe3f60c6af067ea8ed8a0131ed1d2feaafd1157fe7a1cf5a899d486a'
ANCHORS_SHA256 = '53f70fecc2343f355f67774e9d9694e6dc5f0ac4e0083c83680611da5a2bb7a9'
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_FILES = 2 * ((MAX_ENTRIES + CHUNK - 1) // CHUNK) + 2
CONTEXT_NAME = 'collection-context.json'
BANK_NAME = re.compile(re.escape(TOKEN) + r'_(?:Manifest|(?:Unit|Abil)_(?:0|[1-9][0-9]?))\.StormBank')


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def strict_json(raw: bytes) -> dict:
    if len(raw) > MAX_MEMBER_BYTES:
        raise ValueError('JSON exceeds the capture limit')
    def invalid_constant(value: str):
        raise ValueError('Nonfinite JSON value: ' + value)
    result = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object,
                        parse_constant=invalid_constant)
    if not isinstance(result, dict):
        raise ValueError('Expected a JSON object')
    return result


def read_archive(path: Path) -> tuple[dict[str, bytes], str]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_ARCHIVE_BYTES:
        raise ValueError('Capture must be a bounded regular ZIP file')
    with path.open('rb') as source:
        archive_bytes = source.read(MAX_ARCHIVE_BYTES + 1)
    if not 0 < len(archive_bytes) <= MAX_ARCHIVE_BYTES:
        raise ValueError('Capture changed size or exceeds the limit')
    result = {}
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            items = archive.infolist()
            if not 2 <= len(items) <= MAX_FILES:
                raise ValueError('Unexpected capture member count')
            if sum(item.file_size for item in items) > MAX_ARCHIVE_BYTES:
                raise ValueError('Uncompressed capture exceeds the limit')
            for item in items:
                name = item.filename
                mode = stat.S_IFMT(item.external_attr >> 16)
                if name != CONTEXT_NAME and BANK_NAME.fullmatch(name) is None:
                    raise ValueError('Unexpected capture member: ' + name)
                if name in result or item.is_dir() or mode not in (0, stat.S_IFREG):
                    raise ValueError('Duplicate, linked or nonregular capture member')
                if item.flag_bits & 1 or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ValueError('Encrypted or unsupported ZIP member')
                if not 0 < item.file_size <= MAX_MEMBER_BYTES:
                    raise ValueError('Capture member exceeds the limit or is empty')
                with archive.open(item) as member:
                    raw = member.read(MAX_MEMBER_BYTES + 1)
                if len(raw) != item.file_size:
                    raise ValueError('ZIP member size disagrees with its contents')
                if name != CONTEXT_NAME:
                    raw.decode('utf-8-sig')
                result[name] = raw
    except (zipfile.BadZipFile, UnicodeError, RuntimeError, NotImplementedError) as exc:
        raise ValueError('Invalid capture ZIP or text encoding') from exc
    if CONTEXT_NAME not in result:
        raise ValueError('Collector context is required')
    return result, hashlib.sha256(archive_bytes).hexdigest()


def capture_context(context: dict, banks: dict[str, bytes]) -> dict:
    expected = {'format': 'hots-runtime-probe-collection-v1', 'token': TOKEN, 'expected_build': BUILD}
    if any(type(context.get(key)) is not type(value) or context.get(key) != value for key, value in expected.items()):
        raise ValueError('Wrong collector format, token or expected build')
    for key in ('launched_by_this_invocation', 'graphics_log_fresh_for_launch', 'export_contents_validated',
                'runtime_catalog_context_validated', 'client_playback_validated'):
        if type(context.get(key)) is not bool:
            raise ValueError('Collector status must use explicit booleans: ' + key)
    if any(context[key] for key in ('export_contents_validated', 'runtime_catalog_context_validated', 'client_playback_validated')):
        raise ValueError('Collector cannot attest validation or playback')
    try:
        launch = datetime.fromisoformat(context['launch_utc'].replace('Z', '+00:00'))
    except (KeyError, AttributeError, ValueError) as exc:
        raise ValueError('Invalid collection timestamp') from exc
    if launch.utcoffset() is None:
        raise ValueError('Collection timestamp requires a timezone')
    rows = context.get('input_banks')
    if not isinstance(rows, list) or len(rows) != len(banks):
        raise ValueError('Collector bank inventory is incomplete')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'name', 'sha256', 'bytes'}:
            raise ValueError('Invalid collector inventory row')
        name = row['name']
        if not isinstance(name, str) or name not in banks or name in seen:
            raise ValueError('Unexpected or duplicate inventoried bank')
        seen.add(name)
        if type(row['bytes']) is not int or row['bytes'] != len(banks[name]):
            raise ValueError('Collector byte count disagrees: ' + name)
        if row['sha256'] != hashlib.sha256(banks[name]).hexdigest():
            raise ValueError('Collector SHA-256 disagrees: ' + name)
    lines = context.get('observed_version_lines')
    if not isinstance(lines, list) or len(lines) > 32 or any(not isinstance(line, str) or len(line) > 512 for line in lines):
        raise ValueError('Invalid captured version lines')
    versions, data_builds, headers = set(), set(), set()
    for line in lines:
        match = re.search(r'<Version>\s+(\d+\.\d+\.\d+\.\d+)\s*$', line)
        if match:
            versions.add(match[1])
        match = re.search(r'<DataBuild>\s+B(\d+)\s*$', line)
        if match:
            data_builds.add(int(match[1]))
        match = re.search(r'Heroes of the Storm \(B(\d+)\)\s*$', line)
        if match:
            headers.add(int(match[1]))
    blockers = []
    checks = [
        ('collector_did_not_launch_this_probe', context['launched_by_this_invocation']),
        ('collector_did_not_observe_a_fresh_graphics_log', context['graphics_log_fresh_for_launch']),
        ('launched_map_digest_is_missing_or_different', context.get('map_sha256') == PROBE_SHA256),
        ('version_log_missing_conflicting_or_wrong', versions == {f'2.57.0.{BUILD}'}),
        ('data_build_log_missing_conflicting_or_wrong', data_builds == {BUILD}),
        ('executable_build_header_missing_conflicting_or_wrong', headers == {BUILD}),
    ]
    for reason, passed in checks:
        if not passed:
            blockers.append(reason)
    return {'captured_versions': sorted(versions), 'captured_data_builds': sorted(data_builds),
            'captured_executable_builds': sorted(headers), 'collection_timestamp': launch.isoformat(),
            'reported_context_checks_pass': not blockers, 'context_blockers': blockers,
            'collector_manifest_hashes_match': True,
            'evidence_scope': 'Checks collector records and captured text; it does not inspect or authenticate the live process.'}


def validate_capture(path: Path, anchors: dict[str, int]) -> dict:
    files, capture_digest = read_archive(path)
    context = strict_json(files.pop(CONTEXT_NAME))
    provenance = capture_context(context, files)
    result = combine_banks(files, anchors)
    blockers = list(provenance['context_blockers'])
    if not result['all_unit_anchors_match']:
        blockers.append('runtime_unit_indices_do_not_match_reference_anchors')
    result.update({'capture_format': 'hots-runtime-catalog-capture-v1',
                   'capture_zip_sha256': capture_digest,
                   'collector_context': provenance, 'blocking_checks': blockers,
                   'ready_for_unit_catalog_review': not blockers,
                   'status': 'eligible-for-unit-catalog-review' if not blockers else 'blocked-context-or-unit-anchors',
                   'actual_build_verified': False, 'evidence_is_authenticated': False,
                   'ability_indices_independently_validated': False,
                   'automatically_applied_to_replay': False, 'client_playback_validated': False})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--anchors', type=Path, default=Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Output already exists')
    raw = args.anchors.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ANCHORS_SHA256:
        raise ValueError('Reference anchor file differs from the reviewed observation')
    result = validate_capture(args.capture, strict_json(raw)['unit_anchors'])
    serialized = json.dumps(result, indent=2, sort_keys=True) + '\n'
    with args.output.open('x', encoding='utf-8') as output:
        output.write(serialized)
    print(json.dumps({key: result[key] for key in ('status', 'reference_anchor_count', 'blocking_checks',
                     'ready_for_unit_catalog_review', 'client_playback_validated')}, indent=2))
    if result['blocking_checks']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
