"""Publish R5 CI evidence without replacing native observations or active work."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re


CANDIDATE_ID = '98285-dragon-r5'
CHECKPOINT = Path('client-checkpoints') / CANDIDATE_ID
ARTIFACT = {
    'name': 'TEN_GREYMANE_client98285_DRAGON_R5_EXPERIMENTAL.StormReplay',
    'sha256': 'f5eac2c4de55db9cc834c97825ac89d5fc0bb4807a2b216ba5ca7fbc63e45f11',
    'size': 1255308,
    'parts': 23,
}
CI_FIELDS = (
    'run_id', 'tested_commit', 'test_count', 'repeated_generation_identical',
    'matches_local_sha256', 'candidate_sha256', 'source_pins',
    'private_donor_supplied_to_ci',
)
METADATA_FILES = ('report.json', 'reference-observation.json',
                  'candidate-profile.json', 'changes.jsonl')


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if type(value) is not dict:
        raise ValueError('Expected a JSON object: ' + str(path))
    return value


def require_identity(value: dict, *, candidate: bool = False) -> None:
    if type(value) is not dict:
        raise ValueError('R5 artifact identity is absent')
    for field, expected in ARTIFACT.items():
        key = 'base64_parts' if candidate and field == 'parts' else field
        if type(value.get(key)) is not type(expected) or value[key] != expected:
            raise ValueError('R5 artifact identity differs: ' + key)


def artifact_files(directory: Path, fallback: dict | None = None) -> dict:
    """Check the actual retained/prospective artifact in RAM, without a replay file."""
    parts = [ARTIFACT['name'] + f'.base64.part{i:03d}' for i in range(ARTIFACT['parts'])]
    if {path.name for path in directory.glob('*.base64.part*')} - set(parts):
        raise ValueError('R5 Base64 part inventory differs')
    result = {}
    checksum_name = ARTIFACT['name'] + '.sha256'
    for name in [*parts, checksum_name]:
        path = directory / name
        if path.is_file():
            if path.stat().st_size > 128 * 1024:
                raise ValueError('R5 artifact text file exceeds its bound')
            result[name] = path.read_bytes()
        elif fallback is not None and name in fallback:
            result[name] = fallback[name]
        else:
            raise ValueError('R5 artifact text file is absent: ' + name)
    if result[checksum_name].decode('ascii').split() != [ARTIFACT['sha256'], ARTIFACT['name']]:
        raise ValueError('R5 checksum sidecar differs')
    encoded = b''.join(b''.join(result[name].split()) for name in parts)
    if len(encoded) > 2 * 1024 * 1024:
        raise ValueError('R5 Base64 artifact exceeds its bound')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ValueError('R5 Base64 artifact is malformed') from exc
    if len(raw) != ARTIFACT['size'] or hashlib.sha256(raw).hexdigest() != ARTIFACT['sha256']:
        raise ValueError('R5 actual artifact identity differs')
    return result


def publish(source: Path, root: Path) -> None:
    """Validate every input before writing; existing R5 gets CI fields only."""
    report = read_object(source / 'report.json')
    verification = read_object(source / 'ci-verification.json')
    progress_path = root / 'progress.json'
    progress = read_object(progress_path)
    require_identity(report.get('artifact'))
    if type(report.get('build')) is not int or report['build'] != 98285:
        raise ValueError('R5 report build differs')
    if report['artifact'].get('base64_roundtrip_validated') is not True:
        raise ValueError('R5 Base64 validation is absent')
    if verification.get('candidate_sha256') != ARTIFACT['sha256']:
        raise ValueError('CI verification artifact identity differs')
    if (type(verification.get('run_id')) is not int or verification['run_id'] <= 0
            or type(verification.get('test_count')) is not int
            or verification['test_count'] < 166
            or type(verification.get('tested_commit')) is not str
            or re.fullmatch('[0-9a-f]{40}', verification['tested_commit']) is None
            or verification.get('repeated_generation_identical') is not True
            or verification.get('matches_local_sha256') is not True
            or verification.get('private_donor_supplied_to_ci') is not False
            or type(verification.get('source_pins')) is not dict):
        raise ValueError('R5 CI verification did not pass')
    if not isinstance(progress.get('client_candidates', {}), dict):
        raise ValueError('Candidate registry is not an object')
    candidates = progress.setdefault('client_candidates', {})
    existing = candidates.get(CANDIDATE_ID)
    if CANDIDATE_ID in candidates:
        require_identity(existing, candidate=True)
        if type(existing.get('build')) is not int or existing['build'] != 98285:
            raise ValueError('Existing R5 candidate build differs')

    destination = root / CHECKPOINT
    source_artifact = artifact_files(source)
    # Check a complete existing artifact, or the exact assembly that would
    # result from adding missing files during its first registration.
    artifact_files(destination, source_artifact if existing is None else None)
    published_report = destination / 'report.json'
    if published_report.exists():
        require_identity(read_object(published_report).get('artifact'))
    published_verification = destination / 'ci-verification.json'
    if published_verification.exists():
        ci_record = read_object(published_verification)
        if ci_record.get('candidate_sha256') != ARTIFACT['sha256']:
            raise ValueError('Published CI artifact identity differs')
        # Preserve independent evidence and unknown fields, even in this file.
        ci_record.update({key: verification[key] for key in CI_FIELDS})
    else:
        ci_record = verification

    copies = []
    if existing is None:
        # A first registration is historical inventory, never active promotion.
        for key in ('reference_sha256', 'changed_members', 'changes',
                    'header_bytes_preserved', 'all_event_bytes_preserved'):
            if key not in report:
                raise ValueError('R5 report field is absent: ' + key)
        candidate = {
            'status': 'experimental-awaiting-client-test', 'build': 98285,
            'report': (CHECKPOINT / 'report.json').as_posix(),
            'name': ARTIFACT['name'], 'sha256': ARTIFACT['sha256'],
            'size': ARTIFACT['size'], 'base64_parts': ARTIFACT['parts'],
            'reference_sha256': report['reference_sha256'],
            'changed_members': report['changed_members'], 'metadata_changes': report['changes'],
            'header_bytes_preserved': report['header_bytes_preserved'],
            'all_event_bytes_preserved': report['all_event_bytes_preserved'],
            'same_map_dependencies': 6, 'private_donor_published': False,
            'client_playback_validated': False, 'simulation_compatibility_validated': False,
        }
        candidates[CANDIDATE_ID] = candidate
        files = dict(source_artifact)
        files.update({name: (source / name).read_bytes() for name in METADATA_FILES})
        for name, data in files.items():
            target = destination / name
            if not target.exists():
                copies.append((target, data))
    else:
        candidate = existing
    candidate.update({
        'ci_run': verification['run_id'], 'ci_validation_passed': True,
        'tests_passed': verification['test_count'], 'tests_skipped': 0,
    })

    # No directory creation, artifact copy or progress write occurs before all
    # generated and previously published identities have been checked above.
    progress_bytes = (json.dumps(progress, indent=2) + '\n').encode('utf-8')
    verification_bytes = (json.dumps(ci_record, indent=2) + '\n').encode('utf-8')
    destination.mkdir(parents=True, exist_ok=True)
    for target, data in copies:
        target.write_bytes(data)
    published_verification.write_bytes(verification_bytes)
    progress_path.write_bytes(progress_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    publish(args.source, Path.cwd())


if __name__ == '__main__':
    main()
