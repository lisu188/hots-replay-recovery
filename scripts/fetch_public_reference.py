from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from migrate_replay import write_json
from reference_replay import MAX_FILE_BYTES, inspect_reference

API = 'https://api.heroesprofile.com/openApi'
ALLOWED_DOWNLOAD_HOSTS = {'heroesprofile.s3.amazonaws.com', 'heroesprofile.s3.us-west-2.amazonaws.com',
                          'heroesprofile.s3.us-east-1.amazonaws.com'}


class TrustedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS | {'api.heroesprofile.com', 'www.heroesprofile.com'}:
            raise ValueError('Refused an unexpected redirect destination')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'hots-replay-recovery/1.0 (public reference validation)'})
    with urllib.request.build_opener(TrustedRedirect()).open(request, timeout=30) as response:
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError('Response exceeds size limit')
        return body


def fetch(output: Path, minimum_build: int, schema_build: int) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'source': 'Heroes Profile documented OpenAPI', 'minimum_build': minimum_build,
              'schema_build': schema_build, 'maximum_downloads': 3, 'profiles': [], 'attempts': [],
              'client_playback_validated': False}
    try:
        maximum = json.loads(get(API + '/Replay/Max', 1024 * 1024))
        if isinstance(maximum, dict):
            maximum = maximum['max_replayID']
        maximum = int(maximum)
        if not 1 <= maximum < 2**63:
            raise ValueError('Invalid replay cursor')
        minimum = max(0, maximum - 200)
        report['searched_id_window'] = [minimum, maximum]
        records = json.loads(get(API + f'/Replay/Min_id?min_id={minimum}', 8 * 1024 * 1024))
        if isinstance(records, dict):
            records = records.get('replays', list(records.values()))
        if not isinstance(records, list):
            raise ValueError('Unexpected replay-list response')
        choices = []
        for row in records:
            if not isinstance(row, dict) or row.get('deleted') or not row.get('url'):
                continue
            version = str(row.get('game_version', '')).split('.')
            if len(version) == 4 and all(v.isdigit() for v in version) and int(version[-1]) >= minimum_build:
                choices.append((int(row['replayID']), int(version[-1]), row['url']))
        for replay_id, build, url in sorted(choices, reverse=True)[:3]:
            attempt = {'replay_id': replay_id, 'declared_api_build': build}
            report['attempts'].append(attempt)
            try:
                parsed = urllib.parse.urlsplit(url)
                if parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
                    raise ValueError('Download URL is outside the documented public replay bucket')
                if parsed.scheme not in ('http', 'https'):
                    raise ValueError('Unsupported download URL scheme')
                url = urllib.parse.urlunsplit(parsed._replace(scheme='https'))
                raw = get(url, MAX_FILE_BYTES)
                if raw[:4] != b'MPQ\x1b':
                    raise ValueError('Download is not a replay')
                destination = Path('work/reference-donors') / f'reference-{replay_id}.StormReplay'
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                profile = inspect_reference(destination, schema_build, build)
                profile['provenance'] = {'provider': 'Heroes Profile public replay bucket', 'replay_id': replay_id,
                                         'api_build': build, 'download_host': parsed.hostname}
                profile_path = output / f'profile-{replay_id}.json'
                write_json(profile_path, profile)
                report['profiles'].append(str(profile_path))
                attempt['status'] = 'observed-payload-verified'
            except Exception as error:
                attempt.update(status='unavailable-or-incompatible', error_type=type(error).__name__,
                               http_status=getattr(error, 'code', None))
        report['status'] = 'references-found' if report['profiles'] else 'no-compatible-reference-in-window'
    except Exception as error:
        report.update(status='public-discovery-unavailable', error_type=type(error).__name__,
                      http_status=getattr(error, 'code', None))
    write_json(output / 'discovery.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('references/probes'))
    parser.add_argument('--minimum-build', type=int, default=98025)
    parser.add_argument('--schema-build', type=int, default=96477)
    args = parser.parse_args()
    print(json.dumps(fetch(args.output, args.minimum_build, args.schema_build), indent=2))
