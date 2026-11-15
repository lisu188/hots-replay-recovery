"""Inspect preserved J2 exports against fixed98348 runtime/anchor evidence.

The emitter remains98285. Eligibility validates supplied collector records only;
it does not authenticate a running game, prove playback, or migrate a replay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import import_catalog_capture as capture_json
import import_catalog_journal as legacy
import runtime_catalog_journal as journal
import runtime_catalog_probe as probe

RUNTIME_BUILD = 98348
EMITTER_BUILD = 98285
ANCHORS_SHA256 = '8371d65c0c680ad8aaf9fa283f489f76c8dd6660595a566d438cbf62a003f73e'
MAX_PROFILE_BYTES = 64 * 1024
DEFAULT_ANCHORS = Path(__file__).parent / 'observations/runtime-catalog-reference-anchors-98348.json'
SHARED_SOURCE_PINS = {
    'import_catalog_capture': 'b8c501f4f611a33634545bb1a625e50c345208ac885456628a89b2c606265bf4',
    'import_catalog_journal': '91d4ea675b059026ca29cb3d990039b442f43089f92e0aa173244b55f83d31cb',
    'runtime_catalog_journal': '6cb64d75644821c3e68451eddc91ce5bf36be63a13ee1b5db495ea3a60f98004',
    'runtime_catalog_probe': 'a6f7c816ec0106ca2b2e687ff6ee0f17a189cfd078e626b287649e6c48b21c5a',
}
RUNTIME_REQUIREMENTS = {
    'version_log_missing_conflicting_or_wrong': ('versions', ['2.57.0.98348']),
    'data_build_log_missing_conflicting_or_wrong': ('data_builds', ['98348']),
    'executable_build_header_missing_conflicting_or_wrong': ('executable_builds', ['98348']),
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bounded_file(path: Path, cap: int) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= cap:
        raise ValueError('A bounded regular profile/source file is required')
    with path.open('rb') as source:
        raw = source.read(cap + 1)
    if not 0 < len(raw) <= cap:
        raise ValueError('Profile/source file exceeds its bound')
    return raw


def load_profile(path: Path | None = None) -> dict:
    raw = _bounded_file(path or DEFAULT_ANCHORS, MAX_PROFILE_BYTES)
    if sha256(raw) != ANCHORS_SHA256:
        raise ValueError('Current98348 profile differs from the pinned observation')
    # The reused checks are immutable evidence; fail closed on a changed dependency.
    for module in (capture_json, legacy, journal, probe):
        if sha256(_bounded_file(Path(module.__file__), 64 * 1024)) != SHARED_SOURCE_PINS[module.__name__]:
            raise ValueError('A shared legacy contract source differs from its pin')
    profile = capture_json.strict_json(raw)
    emitter = {'token': 'HRC98285_20260929_J2', 'declared_build': EMITTER_BUILD,
        'source_map_sha256': probe.MAP_SHA256, 'delivered_map_sha256': legacy.PROBE_SHA256}
    if (profile.get('format') != 'hots-runtime-catalog-reference-anchors-98348-v1'
            or type(profile.get('build')) is not int or profile['build'] != RUNTIME_BUILD
            or profile.get('emitter_identity') != emitter
            or legacy.BUILD != EMITTER_BUILD or journal.TOKEN != emitter['token']):
        raise ValueError('Inconsistent fixed runtime or emitter profile')
    anchors = profile.get('unit_anchors')
    candidates = profile.get('all_unambiguous_current_candidates')
    provenance = profile.get('anchor_provenance')
    refs = profile.get('reference_bindings')
    if (not isinstance(anchors, dict) or len(anchors) != 48
            or not isinstance(candidates, dict) or len(candidates) != 103
            or not isinstance(provenance, list) or len(provenance) != 48
            or not isinstance(refs, list) or len(refs) != 12
            or any(not isinstance(n, str) or not n or type(i) is not int or not 1 <= i <= probe.MAX_ENTRIES
                   for n, i in candidates.items())
            or len(set(candidates.values())) != len(candidates)
            or any(n not in candidates or candidates[n] != i for n, i in anchors.items())):
        raise ValueError('Inconsistent measured anchor inventory')
    ref_hashes = {row['replay_sha256'] for row in refs}
    seen = set()
    for row in provenance:
        name, index = row['unit_type'], row['index']
        support = row['supporting_reference_replay_sha256']
        if (name in seen or anchors.get(name) != index or not isinstance(support, list)
                or len(set(support)) != len(support) or len(support) < 3
                or not set(support) <= ref_hashes):
            raise ValueError('Inconsistent independent anchor provenance')
        seen.add(name)
    if seen != set(anchors) or len(ref_hashes) != 12:
        raise ValueError('Incomplete independent anchor provenance')
    return profile


def validate_runtime_context(context: dict, journals: dict[str, bytes]) -> dict:
    provenance = legacy.validate_context(context, journals)
    # Supplied records are unchanged. Replace only the three fixed runtime gates;
    # every map, inventory, freshness, flag, token and warning check remains intact.
    blockers = [b for b in provenance['blocking_checks'] if b not in RUNTIME_REQUIREMENTS]
    for blocker, (key, expected) in RUNTIME_REQUIREMENTS.items():
        if provenance['observed'][key] != expected:
            blockers.append(blocker)
    return {**provenance, 'blocking_checks': blockers,
        'emitter_context_expected_build': EMITTER_BUILD, 'runtime_profile_build': RUNTIME_BUILD,
        'evidence_scope': 'Checks unchanged supplied collector records against fixed98348 runtime fields; not a live or authenticated process.'}


def validate_capture(path: Path, anchors_path: Path | None = None) -> dict:
    profile = load_profile(anchors_path)  # Pin before JSON use, ZIP reads or output creation.
    files, capture_digest = legacy.read_archive(path)
    context = capture_json.strict_json(files.pop(legacy.CONTEXT_NAME))
    provenance = validate_runtime_context(context, files)
    blockers = list(provenance['blocking_checks'])
    result = {'catalogs': {'Unit': [], 'Abil': []}, 'reference_anchor_count': 48,
        'all_unit_anchors_match': False, 'complete_sequence': False}
    if len(files) != 1:
        blockers.append('no_journal_collected' if not files else 'multiple_journals_require_explicit_session_resolution')
    else:
        try:
            result = journal.parse_journal(next(iter(files.values())), profile['unit_anchors'])
        except (ValueError, UnicodeError):
            blockers.append('journal_sequence_invalid_or_incomplete')
        else:
            if not result['all_unit_anchors_match']:
                blockers.append('unit_reference_anchors_mismatch')
    emitter_build = result.pop('expected_build', EMITTER_BUILD)
    if emitter_build != EMITTER_BUILD:
        raise ValueError('Unexpected emitter declaration')
    result.update({'format': 'hots-catalog-journal-98348-capture-v1',
        'emitter_declared_build': emitter_build, 'runtime_profile_build': RUNTIME_BUILD,
        'source_map_sha256': probe.MAP_SHA256, 'delivered_map_sha256': legacy.PROBE_SHA256,
        'profile_sha256': ANCHORS_SHA256, 'profile_evidence_scope': profile['measurement_scope'],
        'capture_zip_sha256': capture_digest, 'collector_context': provenance,
        'blocking_checks': blockers, 'journal_inventory': [
            {'name': name, 'sha256': sha256(raw), 'bytes': len(raw)} for name, raw in sorted(files.items())],
        'ready_for_98348_unit_catalog_review': not blockers,
        'ready_for_unit_catalog_review': False, 'legacy_98285_migration_planner_eligible': False,
        'status': 'eligible-for-98348-unit-catalog-review' if not blockers else 'blocked-capture',
        'actual_build_verified': False, 'evidence_is_authenticated': False,
        'ability_indices_independently_validated': False, 'automatically_applied_to_replay': False,
        'client_playback_validated': False, 'simulation_compatibility_validated': False,
        'eligibility_scope': 'Reported-context and complete-journal review only; no historical semantics or migration authorization.'})
    return result


def run(capture: Path, output: Path, anchors_path: Path | None = None) -> dict:
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output must be a new directory')
    result = validate_capture(capture, anchors_path)
    summary = {'format': 'hots-catalog-journal-98348-import-v1', 'status': result['status'],
        'emitter_declared_build': EMITTER_BUILD, 'runtime_profile_build': RUNTIME_BUILD,
        'profile_sha256': ANCHORS_SHA256, 'capture_zip_sha256': result['capture_zip_sha256'],
        'ready_for_98348_unit_catalog_review': result['ready_for_98348_unit_catalog_review'],
        'ready_for_unit_catalog_review': False, 'legacy_98285_migration_planner_eligible': False,
        'blocking_checks': result['blocking_checks'], 'reference_anchor_count': result['reference_anchor_count'],
        'catalog_counts': {name: len(rows) for name, rows in result['catalogs'].items()},
        'actual_build_verified': False, 'evidence_is_authenticated': False,
        'ability_indices_independently_validated': False, 'automatically_applied_to_replay': False,
        'replay_modified': False, 'catalog_plan_created': False,
        'client_playback_validated': False, 'simulation_compatibility_validated': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.journal-98348-import-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'result'
        stage.mkdir()
        for name, value in {'capture.json': result, 'summary.json': summary}.items():
            (stage / name).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        if output.exists() or output.is_symlink():
            raise FileExistsError('Output appeared during validation')
        stage.rename(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--anchors', type=Path, default=DEFAULT_ANCHORS)
    args = parser.parse_args()
    try:
        summary = run(args.capture, args.output, args.anchors)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(0 if summary['ready_for_98348_unit_catalog_review'] else 2)


if __name__ == '__main__':
    main()
