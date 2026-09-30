from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from import_catalog_capture import strict_json
from runtime_catalog_journal import ANCHORS_SHA256, BUILD, MAX_BYTES, TOKEN, parse_journal

PROBE_SHA256 = '4733de8491521fac99a26b41c1691f65c8fd894e8ac14f200dfa7afe905672be'
CONTEXT_NAME = 'collection-context.json'
MAX_CONTEXT_BYTES = 64 * 1024
MAX_JOURNALS = 8
MAX_ARCHIVE_BYTES = MAX_JOURNALS * MAX_BYTES + MAX_CONTEXT_BYTES + 65536
JOURNAL_NAME = re.compile(r'journal-([0-7])\.txt')


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_archive(path: Path) -> tuple[dict[str, bytes], str]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_ARCHIVE_BYTES:
        raise ValueError('A bounded regular J2 capture ZIP is required')
    with path.open('rb') as source:
        raw = source.read(MAX_ARCHIVE_BYTES + 1)
    if not 0 < len(raw) <= MAX_ARCHIVE_BYTES:
        raise ValueError('Capture exceeds the archive bound')
    files = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not 1 <= len(entries) <= MAX_JOURNALS + 1:
                raise ValueError('Unexpected capture member count')
            if sum(entry.file_size for entry in entries) > MAX_JOURNALS * MAX_BYTES + MAX_CONTEXT_BYTES:
                raise ValueError('Uncompressed capture exceeds the total bound')
            for entry in entries:
                name = entry.filename
                limit = MAX_CONTEXT_BYTES if name == CONTEXT_NAME else MAX_BYTES
                if name != CONTEXT_NAME and JOURNAL_NAME.fullmatch(name) is None:
                    raise ValueError('Unexpected capture member')
                if entry.orig_filename != name or name in files or entry.is_dir():
                    raise ValueError('Duplicate, truncated or directory ZIP name')
                if stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG):
                    raise ValueError('Nonregular ZIP member')
                if entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ValueError('Encrypted or unsupported ZIP member')
                if not 0 <= entry.file_size <= limit or (name == CONTEXT_NAME and entry.file_size == 0):
                    raise ValueError('Capture member exceeds its size bound')
                with archive.open(entry) as member:
                    data = member.read(limit + 1)
                if len(data) != entry.file_size:
                    raise ValueError('ZIP member size mismatch')
                files[name] = data
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ValueError('Invalid capture ZIP') from exc
    if CONTEXT_NAME not in files:
        raise ValueError('Collector context is required')
    if {name for name in files if name != CONTEXT_NAME} != {f'journal-{i}.txt' for i in range(len(files) - 1)}:
        raise ValueError('Collector journal numbering is not contiguous')
    return files, sha256(raw)


def utc_time(value: str) -> datetime:
    if not isinstance(value, str) or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|\+00:00)', value) is None:
        raise ValueError('Expected an explicit UTC collector timestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def validate_context(context: dict, journals: dict[str, bytes]) -> dict:
    required = {'format', 'token', 'expected_build', 'map_sha256', 'launched_by_this_invocation',
                'launch_utc', 'graphics_log_fresh_for_launch', 'graphics_map_argument_matched',
                'observed_version_lines', 'journals', 'warnings', 'export_contents_validated',
                'client_playback_validated'}
    if not isinstance(context, dict) or set(context) != required:
        raise ValueError('Unexpected or incomplete J2 collector context')
    expected = {'format': 'hots-catalog-journal-collection-v1', 'token': TOKEN, 'expected_build': BUILD}
    if any(type(context[k]) is not type(v) or context[k] != v for k, v in expected.items()):
        raise ValueError('Wrong collector format, token or expected build')
    flags = ['launched_by_this_invocation', 'graphics_log_fresh_for_launch', 'graphics_map_argument_matched',
             'export_contents_validated', 'client_playback_validated']
    if any(type(context[k]) is not bool for k in flags):
        raise ValueError('Collector flags must be explicit booleans')
    if context['export_contents_validated'] or context['client_playback_validated']:
        raise ValueError('The collector cannot attest export validation or playback')
    map_hash = context['map_sha256']
    if map_hash is not None and (not isinstance(map_hash, str) or re.fullmatch(r'[0-9a-f]{64}', map_hash) is None):
        raise ValueError('Invalid map digest')
    launch = utc_time(context['launch_utc'])
    warnings = context['warnings']
    if not isinstance(warnings, list) or len(warnings) > 64 or any(not isinstance(w, str) or re.fullmatch(r'[a-z0-9_]{1,120}', w) is None for w in warnings):
        raise ValueError('Invalid collector warning list')
    rows = context['journals']
    if not isinstance(rows, list) or len(rows) != len(journals):
        raise ValueError('Journal inventory does not match ZIP contents')
    seen, freshness = set(), []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'name', 'bytes', 'sha256', 'modified_utc', 'fresh_for_launch'}:
            raise ValueError('Invalid journal inventory record')
        name = row['name']
        if not isinstance(name, str) or name not in journals or name in seen:
            raise ValueError('Unexpected or duplicated inventoried journal')
        seen.add(name)
        if type(row['bytes']) is not int or row['bytes'] != len(journals[name]) or row['sha256'] != sha256(journals[name]):
            raise ValueError('Journal byte count or digest disagrees with inventory')
        if type(row['fresh_for_launch']) is not bool:
            raise ValueError('Invalid journal freshness flag')
        modified = utc_time(row['modified_utc'])
        freshness.append({'name': name, 'modified_utc': modified.isoformat(),
                          'reported_fresh': row['fresh_for_launch'],
                          'mtime_not_before_launch_tolerance': modified >= launch - timedelta(seconds=5)})
    lines = context['observed_version_lines']
    if not isinstance(lines, list) or len(lines) > 16 or any(not isinstance(line, str) or len(line) > 512 or '\n' in line or '\r' in line for line in lines):
        raise ValueError('Invalid captured version lines')
    patterns = {'versions': r'<Version>\s+(\d+\.\d+\.\d+\.\d+)\s*$',
                'data_builds': r'<DataBuild>\s+B(\d+)\s*$',
                'executable_builds': r'Heroes of the Storm \(B(\d+)\)\s*$'}
    observed = {key: sorted({match[1] for line in lines if (match := re.search(pattern, line))}) for key, pattern in patterns.items()}
    checks = [
        ('collector_did_not_launch_this_probe', context['launched_by_this_invocation']),
        ('graphics_log_not_reported_fresh', context['graphics_log_fresh_for_launch']),
        ('graphics_map_argument_not_matched', context['graphics_map_argument_matched']),
        ('launched_map_digest_missing_or_different', map_hash == PROBE_SHA256),
        ('version_log_missing_conflicting_or_wrong', observed['versions'] == [f'2.57.0.{BUILD}']),
        ('data_build_log_missing_conflicting_or_wrong', observed['data_builds'] == [str(BUILD)]),
        ('executable_build_header_missing_conflicting_or_wrong', observed['executable_builds'] == [str(BUILD)]),
        ('collector_reported_incomplete_search_or_capture', not warnings),
        ('journal_not_reported_fresh', all(row['reported_fresh'] for row in freshness)),
        ('journal_mtime_predates_launch', all(row['mtime_not_before_launch_tolerance'] for row in freshness)),
    ]
    return {'observed': observed, 'launch_utc': launch.isoformat(), 'journal_timestamps': freshness,
            'warnings': sorted(set(warnings)), 'blocking_checks': [name for name, ok in checks if not ok],
            'inventory_digests_checked': True, 'reported_context_only': True,
            'graphics_timestamp_independently_verified': False,
            'evidence_scope': 'Validates supplied records and text, not a live or authenticated game process.'}


def validate_capture(path: Path, anchors: dict[str, int]) -> dict:
    files, capture_digest = read_archive(path)
    context = strict_json(files.pop(CONTEXT_NAME))
    provenance = validate_context(context, files)
    blockers = list(provenance['blocking_checks'])
    result = {'catalogs': {'Unit': [], 'Abil': []}, 'reference_anchor_count': len(anchors),
              'all_unit_anchors_match': False, 'complete_sequence': False}
    if len(files) != 1:
        blockers.append('no_journal_collected' if not files else 'multiple_journals_require_explicit_session_resolution')
    else:
        try:
            result = parse_journal(next(iter(files.values())), anchors)
        except (ValueError, UnicodeError):
            blockers.append('journal_sequence_invalid_or_incomplete')
        else:
            if not result['all_unit_anchors_match']:
                blockers.append('unit_reference_anchors_mismatch')
    result.update({'format': 'hots-catalog-journal-capture-v1', 'capture_zip_sha256': capture_digest,
                   'collector_context': provenance, 'blocking_checks': blockers,
                   'journal_inventory': [{'name': name, 'sha256': sha256(raw), 'bytes': len(raw)} for name, raw in sorted(files.items())],
                   'ready_for_unit_catalog_review': not blockers,
                   'status': 'eligible-for-unit-catalog-review' if not blockers else 'blocked-capture',
                   'actual_build_verified': False, 'evidence_is_authenticated': False,
                   'ability_indices_independently_validated': False, 'automatically_applied_to_replay': False,
                   'client_playback_validated': False})
    return result


def run(capture: Path, output: Path, source: Path | None = None, anchors_path: Path | None = None) -> dict:
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output must be a new directory')
    anchors_path = anchors_path or Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json'
    anchor_raw = Path(anchors_path).read_bytes()
    if sha256(anchor_raw) != ANCHORS_SHA256:
        raise ValueError('Independent anchors differ from the pinned observation')
    capture_result = validate_capture(capture, strict_json(anchor_raw)['unit_anchors'])
    plan = None
    if source is not None:
        from plan_catalog_migration import propose, read_source
        plan = propose(read_source(source), capture_result)
    summary = {'format': 'hots-catalog-journal-import-v1', 'status': capture_result['status'],
               'capture_zip_sha256': capture_result['capture_zip_sha256'],
               'ready_for_unit_catalog_review': capture_result['ready_for_unit_catalog_review'],
               'blocking_checks': capture_result['blocking_checks'],
               'catalog_plan_created': plan is not None, 'replay_modified': False,
               'client_playback_validated': False, 'simulation_compatibility_validated': False}
    if plan is not None:
        summary['plan_coverage'] = plan['coverage']
        summary['plan_blocking_checks'] = plan['blocking_checks']
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.journal-import-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'result'
        stage.mkdir()
        data = {'capture.json': capture_result, 'summary.json': summary}
        if plan is not None:
            data['plan.json'] = plan
        for name, value in data.items():
            (stage / name).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        if output.exists() or output.is_symlink():
            raise FileExistsError('Output appeared during validation')
        stage.rename(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    try:
        result = run(args.capture, args.output, args.source)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Journal import failed: {exc}\n')
    print(json.dumps(result, indent=2))
    if not result['ready_for_unit_catalog_review']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
