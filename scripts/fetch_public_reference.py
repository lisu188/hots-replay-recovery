from __future__ import annotations

import argparse
import json
import re
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
API_HOSTS = {'api.heroesprofile.com', 'www.heroesprofile.com'}
GCS_HOSTS = {'storage.cloud.google.com', 'storage.googleapis.com'}
GCS_REPLAY_PATH = re.compile(
    r'/heroesprofile-replay-storage/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
    r'[0-9a-f]{4}-[0-9a-f]{12}\.StormReplay')


def checked_url(url: str):
    if not isinstance(url, str) or re.search(r'[\x00-\x20\x7f]', url):
        raise ValueError('Invalid public URL')
    parsed = urllib.parse.urlsplit(url)
    if (parsed.username is not None or parsed.password is not None or
            parsed.port not in (None, 443) or '#' in url):
        raise ValueError('Public URLs must not contain credentials, non-443 ports or fragments')
    return parsed


def download_url(url: str) -> str:
    """Accept only documented replay providers, without authentication or signed URLs."""
    parsed = checked_url(url)
    if '?' in url:
        raise ValueError('Public replay URLs must not contain queries')
    if parsed.hostname in GCS_HOSTS:
        if parsed.scheme != 'https' or not GCS_REPLAY_PATH.fullmatch(parsed.path):
            raise ValueError('Download URL is outside the public Heroes Profile replay bucket')
        # Cloud browser URLs require login even for public objects. Google documents
        # this public endpoint: https://cloud.google.com/storage/docs/request-endpoints
        return 'https://storage.googleapis.com' + parsed.path
    if parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS or parsed.scheme not in ('http', 'https'):
        raise ValueError('Download URL is outside the documented public replay bucket')
    decoded_path = urllib.parse.unquote(parsed.path, errors='strict')
    # Refuse another decoding layer instead of allowing an encoded traversal to
    # acquire a different meaning at a redirect or storage frontend.
    if (not parsed.path.startswith('/') or '\\' in decoded_path or
            re.search(r'%[0-9a-fA-F]{2}', decoded_path) or
            any(part in ('.', '..') for part in decoded_path.split('/')) or
            re.search(r'[\x00-\x20\x7f]', decoded_path)):
        raise ValueError('Invalid public replay object path')
    return urllib.parse.urlunsplit(parsed._replace(scheme='https'))


def api_url(url: str) -> str:
    parsed = checked_url(url)
    if parsed.scheme != 'https' or parsed.hostname not in API_HOSTS:
        raise ValueError('Refused an unexpected API destination')
    return url


class TrustedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, download: bool = False):
        self.download = download

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newurl = download_url(newurl) if self.download else api_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get(url: str, limit: int) -> bytes:
    download = urllib.parse.urlsplit(url).hostname not in API_HOSTS
    url = download_url(url) if download else api_url(url)
    request = urllib.request.Request(url, headers={'User-Agent': 'hots-replay-recovery/1.0 (public reference validation)'})
    with urllib.request.build_opener(TrustedRedirect(download)).open(request, timeout=30) as response:
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
            attempt = {'replay_id': replay_id, 'declared_api_build': build, 'stage': 'url-validation'}
            report['attempts'].append(attempt)
            try:
                url = download_url(url)
                parsed = urllib.parse.urlsplit(url)
                attempt['stage'] = 'download'
                raw = get(url, MAX_FILE_BYTES)
                attempt['stage'] = 'payload-validation'
                if raw[:4] != b'MPQ\x1b':
                    raise ValueError('Download is not a replay')
                destination = Path('work/reference-donors') / f'reference-{replay_id}.StormReplay'
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                attempt['stage'] = 'schema-validation'
                profile = inspect_reference(destination, schema_build, build)
                profile['provenance'] = {'provider': 'Heroes Profile public replay bucket', 'replay_id': replay_id,
                                         'api_build': build, 'download_host': parsed.hostname}
                profile_path = output / f'profile-{replay_id}.json'
                attempt['stage'] = 'profile-write'
                write_json(profile_path, profile)
                report['profiles'].append(str(profile_path))
                attempt['status'] = 'observed-payload-verified'
                attempt['stage'] = 'complete'
            except Exception as error:
                failure = {'url-validation': 'download-url-rejected', 'download': 'download-unavailable',
                           'payload-validation': 'invalid-or-unsaved-payload',
                           'schema-validation': 'reference-validation-failed',
                           'profile-write': 'profile-write-failed'}[attempt['stage']]
                attempt.update(status=failure, error_type=type(error).__name__,
                               http_status=getattr(error, 'code', None))
        report['status'] = 'references-found' if report['profiles'] else 'no-validated-reference-in-window'
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
