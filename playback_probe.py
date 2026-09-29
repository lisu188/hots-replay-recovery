from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MAX_LOG_FILES = 200
MAX_LOG_SCAN = 10000
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_HASH_BYTES = 128 * 1024 * 1024
HEX64 = re.compile(r'[0-9a-f]{64}')
HINTS = {
    'desynchronization': re.compile(r'\bdesync(?:hroniz(?:ation|ed))?\b|out.of.sync', re.I),
    'dependency': re.compile(r'failed.{0,80}(?:map|cache|depot)|(?:map|cache|depot).{0,80}(?:missing|not found|failed)', re.I),
    'version': re.compile(r'(?:version|build).{0,80}(?:mismatch|incompatible|unsupported)', re.I),
    'failure': re.compile(r'\b(?:fatal|exception|assertion failed|access violation)\b', re.I),
}


def digest_file(path: Path, limit: int = MAX_HASH_BYTES) -> str:
    if path.stat().st_size > limit:
        raise ValueError('File exceeds hash size limit')
    digest, total = hashlib.sha256(), 0
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ValueError('File grew beyond hash size limit')
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(value: dict) -> dict:
    if not isinstance(value, dict) or value.get('format') != 'hots-playback-manifest-v1':
        raise ValueError('Unsupported playback manifest')
    if not isinstance(value.get('candidate_sha256'), str) or not HEX64.fullmatch(value['candidate_sha256']):
        raise ValueError('Invalid candidate digest')
    if type(value.get('declared_build')) is not int or not 0 < value['declared_build'] < 2**32:
        raise ValueError('Invalid declared build')
    dependencies = value.get('dependencies')
    if not isinstance(dependencies, list) or not 1 <= len(dependencies) <= 64:
        raise ValueError('Invalid dependency list')
    seen = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise ValueError('Invalid dependency record')
        digest, extension = dependency.get('digest'), dependency.get('extension')
        if not isinstance(digest, str) or not HEX64.fullmatch(digest) or extension != 's2ma':
            raise ValueError('Invalid dependency identifier')
        if digest in seen:
            raise ValueError('Duplicate dependency')
        seen.add(digest)
    return value


def verify_replay(path: Path, manifest: dict) -> str:
    validate_manifest(manifest)
    if path.suffix.lower() != '.stormreplay':
        raise ValueError('Only StormReplay files may be opened')
    with path.open('rb') as handle:
        if handle.read(4) != b'MPQ\x1b':
            raise ValueError('Invalid replay signature')
    digest = digest_file(path, 64 * 1024 * 1024)
    if digest != manifest['candidate_sha256']:
        raise ValueError('Replay SHA-256 differs from the pinned candidate')
    return digest


def check_cache(manifest: dict, roots: list[Path]) -> list[dict]:
    validate_manifest(manifest)
    result = []
    for dependency in manifest['dependencies']:
        digest = dependency['digest']
        relative = f'{digest[:2]}/{digest[2:4]}/{digest}.s2ma'
        observations = []
        for index, root in enumerate(roots):
            root = Path(root).resolve()
            path = root / relative
            observation = {'root_index': index, 'status': 'absent'}
            try:
                if not root.is_dir():
                    observation['status'] = 'cache-root-unavailable'
                elif not path.resolve().is_relative_to(root):
                    observation['status'] = 'outside-root-rejected'
                elif path.is_file():
                    observation['bytes'] = path.stat().st_size
                    if observation['bytes'] > MAX_HASH_BYTES:
                        observation['status'] = 'present-not-hashed-size-limit'
                    else:
                        observation['raw_sha256'] = digest_file(path)
                        observation['raw_sha256_matches_identifier'] = observation['raw_sha256'] == digest
                        observation['status'] = 'present'
            except (OSError, ValueError) as exc:
                observation.update(status='read-error', error_type=type(exc).__name__)
            observations.append(observation)
        result.append({'digest': digest, 'relative_path': relative, 'observations': observations})
    return result


def log_snapshot(roots: list[Path]) -> dict:
    entries, scopes = {}, []
    for index, root in enumerate(roots):
        root = Path(root)
        scope = {'root_index': index, 'status': 'checked', 'truncated_listing': False, 'older_logs_omitted': 0}
        scopes.append(scope)
        try:
            if not root.is_dir():
                scope['status'] = 'root-unavailable'
                continue
            paths = []
            for scanned, path in enumerate(root.iterdir()):
                if scanned >= MAX_LOG_SCAN:
                    scope['truncated_listing'] = True
                    break
                if path.suffix.lower() in ('.log', '.txt') and path.is_file():
                    if not path.resolve().is_relative_to(root.resolve()):
                        continue
                    paths.append((path.stat().st_mtime_ns, path))
            scope['older_logs_omitted'] = max(0, len(paths) - MAX_LOG_FILES)
            for _, path in sorted(paths, key=lambda item: (item[0], item[1].name), reverse=True)[:MAX_LOG_FILES]:
                try:
                    with path.open('rb') as handle:
                        size = os.fstat(handle.fileno()).st_size
                        handle.seek(max(0, size - MAX_LOG_BYTES))
                        tail = handle.read(MAX_LOG_BYTES)
                    key = hashlib.sha256(f'{index}:{path.name}'.encode('utf-8')).hexdigest()
                    entries[key] = {'root_index': index, 'bytes': size, 'tail': tail,
                                    'tail_sha256': hashlib.sha256(tail).hexdigest(),
                                    'tail_truncated': size > MAX_LOG_BYTES}
                except OSError:
                    scope['read_errors'] = scope.get('read_errors', 0) + 1
        except OSError as exc:
            scope.update(status='read-error', error_type=type(exc).__name__)
    return {'scopes': scopes, 'entries': entries}


def find_hints(raw: bytes) -> dict:
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8'
    text = raw.decode(encoding, errors='replace')
    return {name: sum(bool(pattern.search(line)) for line in text.splitlines()) for name, pattern in HINTS.items()}


def write_bundle(output: Path, manifest: dict, before: dict, after: dict, cache: list[dict],
                 launch_status: str, user_result: str, replay_unchanged: bool) -> dict:
    validate_manifest(manifest)
    if launch_status not in ('not-requested', 'association-open-requested', 'launch-error'):
        raise ValueError('Invalid launch status')
    if user_result not in ('unknown', 'failed-to-load', 'playing', 'finished'):
        raise ValueError('Invalid user observation')
    changed = []
    for key, value in sorted(after['entries'].items()):
        previous = before['entries'].get(key)
        if previous is None or (value['bytes'], value['tail_sha256']) != (previous['bytes'], previous['tail_sha256']):
            changed.append(value)
    report = {
        'format': 'hots-playback-probe-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
        'candidate_sha256': manifest['candidate_sha256'], 'declared_build': manifest['declared_build'],
        'launch_status': launch_status, 'user_reported_result': user_result,
        'candidate_unchanged_after_probe': replay_unchanged,
        'log_scopes_before': before['scopes'], 'log_scopes_after': after['scopes'],
        'cache': cache, 'changed_logs': [], 'client_playback_validated': False,
        'simulation_compatibility_validated': False,
        'limitations': [
            'Opening the file association does not prove the game loaded the replay.',
            'Log hints are unclassified text matches, not a diagnosis or proof of failure.',
            'User observations are recorded separately and are not automated validation.',
            'Raw log tails in this private bundle can contain personal data; do not commit them to a public repository.',
            'A missing cache file under inspected roots does not prove it is unavailable elsewhere or undownloadable.',
            'A raw SHA-256 comparison is not a game-level cache validation.',
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for index, value in enumerate(changed, 1):
            name = f'logs/changed-{index:03}.txt'
            bundle.writestr(name, value['tail'])
            report['changed_logs'].append({key: v for key, v in value.items() if key != 'tail'} |
                                          {'file': name, 'text_hints': find_hints(value['tail'])})
        bundle.writestr('probe.json', json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report


def default_log_roots() -> list[Path]:
    documents = [Path.home() / 'Documents']
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                documents.append(Path(os.path.expandvars(winreg.QueryValueEx(key, 'Personal')[0])))
        except OSError:
            pass
    for name in ('OneDrive', 'OneDriveConsumer'):
        if os.environ.get(name):
            documents.extend(Path(os.environ[name]) / folder for folder in ('Documents', 'Dokumenty'))
    return list(dict.fromkeys(root / 'Heroes of the Storm' / 'GameLogs' for root in documents))


def launch_replay(path: Path, requested: bool) -> str:
    if not requested:
        return 'not-requested'
    if sys.platform != 'win32':
        raise OSError('Launching this replay probe is supported only on Windows')
    os.startfile(str(path.resolve()))
    return 'association-open-requested'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('playback-manifest.json'))
    parser.add_argument('--replay', type=Path, default=Path(__file__).with_name('TEN_GREYMANE_client98285_EXPERIMENTAL.StormReplay'))
    parser.add_argument('--cache-root', type=Path, action='append')
    parser.add_argument('--log-root', type=Path, action='append')
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        raise FileExistsError(args.output)
    manifest = validate_manifest(json.loads(args.manifest.read_text(encoding='utf-8')))
    verify_replay(args.replay, manifest)
    roots = args.log_root if args.log_root is not None else default_log_roots()
    cache_roots = args.cache_root if args.cache_root is not None else [Path(os.environ.get('ProgramData', 'C:/ProgramData')) / 'Blizzard Entertainment/Battle.net/Cache']
    cache = check_cache(manifest, cache_roots)
    before = log_snapshot(roots)
    status, user_result = 'not-requested', 'unknown'
    try:
        status = launch_replay(args.replay, args.launch)
    except OSError as exc:
        status = 'launch-error'
        print(f'Launch failed: {type(exc).__name__}', file=sys.stderr)
    if args.launch and status != 'launch-error':
        print('Test the replay in HotS, then return here. No game files or cache files are modified.')
        try:
            value = input('Result [unknown/failed-to-load/playing/finished]: ').strip().lower()
            user_result = value if value in ('failed-to-load', 'playing', 'finished') else 'unknown'
        except (EOFError, KeyboardInterrupt):
            pass
    after = log_snapshot(roots)
    try:
        unchanged = verify_replay(args.replay, manifest) == manifest['candidate_sha256']
    except (OSError, ValueError):
        unchanged = False
    output = args.output or Path(__file__).parent / 'work' / f'playback-probe-{uuid.uuid4().hex}.zip'
    report = write_bundle(output, manifest, before, after, cache, status, user_result, unchanged)
    print(f'Private diagnostic bundle: {output.resolve()}')
    print(f'Changed logs: {len(report["changed_logs"])}; playback remains unvalidated.')


if __name__ == '__main__':
    main()
