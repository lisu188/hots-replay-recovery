"""Offline HTTP-boundary tests; fixture success is not public donor or playback proof."""
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.request
import urllib.response
from contextlib import contextmanager
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import reference_replay
from scripts import fetch_public_reference as public
from scripts.restore_artifact import restore

KEY = 'be3d1611-f774-8f21-d202-00da99d6fdfe.StormReplay'
CLOUD = 'https://storage.cloud.google.com/heroesprofile-replay-storage/' + KEY
PUBLIC = 'https://storage.googleapis.com/heroesprofile-replay-storage/' + KEY
S3 = 'https://heroesprofile.s3.amazonaws.com/older/replay.StormReplay'


@contextmanager
def memory_https(routes):
    """Exercise urllib's real redirect/error processors, replacing only transport."""
    seen = []
    original = urllib.request.build_opener

    class MemoryHTTPS(urllib.request.HTTPSHandler):
        def https_open(self, request):
            seen.append(request.full_url)
            if request.full_url not in routes:
                raise AssertionError('Unexpected HTTP request: ' + request.full_url)
            code, values, body = routes[request.full_url]
            headers = Message()
            for key, value in values.items():
                headers[key] = value
            response = urllib.response.addinfourl(io.BytesIO(body), headers, request.full_url, code)
            response.msg = 'Offline fixture'
            return response

    def opener(*handlers):
        return original(*handlers, MemoryHTTPS())

    with patch.object(urllib.request, 'build_opener', side_effect=opener):
        yield seen


@contextmanager
def temporary_cwd():
    previous = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            yield Path(directory)
        finally:
            os.chdir(previous)


class PublicDownloadBoundaryTests(unittest.TestCase):
    def test_observed_cloud_url_uses_anonymous_public_endpoint(self):
        for url in (CLOUD, PUBLIC, CLOUD.replace('.com/', '.com:443/')):
            with self.subTest(url=url):
                self.assertEqual(public.download_url(url), PUBLIC)
                with memory_https({PUBLIC: (200, {}, b'replay fixture')}) as seen:
                    self.assertEqual(public.get(url, 100), b'replay fixture')
                    self.assertEqual(seen, [PUBLIC])

    def test_existing_s3_hosts_and_http_upgrade_are_preserved(self):
        for host in ('heroesprofile.s3.amazonaws.com', 'heroesprofile.s3.us-west-2.amazonaws.com',
                     'heroesprofile.s3.us-east-1.amazonaws.com'):
            url = 'http://' + host + '/older/replay.StormReplay'
            expected = url.replace('http:', 'https:', 1)
            with self.subTest(host=host):
                with memory_https({expected: (200, {}, b'old replay')}) as seen:
                    self.assertEqual(public.get(url, 100), b'old replay')
                    self.assertEqual(seen, [expected])

    def test_google_boundary_rejects_unrelated_objects_and_ambiguous_urls(self):
        rejected = [
            CLOUD.replace('https:', 'http:'),
            CLOUD.replace('storage.cloud.google.com', 'storage.googleapis.com.evil.test'),
            CLOUD.replace('storage.cloud.google.com', 'evil.test'),
            CLOUD.replace('heroesprofile-replay-storage', 'another-bucket'),
            CLOUD.replace(KEY, 'not-a-uuid.StormReplay'),
            CLOUD.replace(KEY, KEY.upper()),
            CLOUD.replace('.StormReplay', '.zip'),
            CLOUD + '/other', CLOUD + '?token=private', CLOUD + '?', CLOUD + '#private', CLOUD + '#',
            CLOUD.replace('https://', 'https://user:password@'),
            CLOUD.replace('https://', 'https://@'),
            CLOUD.replace('.com/', '.com:444/'),
            CLOUD.replace('/' + KEY, '/../' + KEY),
            CLOUD.replace('/' + KEY, '/%2e%2e/' + KEY),
            CLOUD.replace('/' + KEY, '/%252e%252e/' + KEY),
            CLOUD.replace('/' + KEY, '/folder%2f' + KEY),
            CLOUD.replace('/' + KEY, '/folder\\' + KEY),
            CLOUD.replace('/' + KEY, '//' + KEY),
            '\n' + CLOUD, CLOUD.replace(KEY, '%00' + KEY),
        ]
        for url in rejected:
            with self.subTest(url=url), memory_https({}) as seen:
                with self.assertRaises(ValueError):
                    public.get(url, 100)
                self.assertEqual(seen, [])

    def test_s3_rejects_credentials_ports_queries_fragments_and_traversal(self):
        for url in (S3.replace('https://', 'https://user@'), S3.replace('.com/', '.com:80/'),
                    S3 + '?signature=private', S3 + '#part', S3.replace('/older/', '/../'),
                    S3.replace('/older/', '/%2e%2e/'), S3.replace('/older/', '/%252e%252e/'),
                    S3.replace('/older/', '/older\\')):
            with self.subTest(url=url), memory_https({}) as seen:
                with self.assertRaises(ValueError):
                    public.get(url, 100)
                self.assertEqual(seen, [])

    def test_allowed_redirect_is_normalized_before_second_request(self):
        routes = {S3: (302, {'Location': CLOUD}, b''), PUBLIC: (200, {}, b'allowed replay')}
        with memory_https(routes) as seen:
            self.assertEqual(public.get(S3, 100), b'allowed replay')
            self.assertEqual(seen, [S3, PUBLIC])

    def test_download_redirect_cannot_escape_bucket_or_reach_api(self):
        for url in (PUBLIC.replace('heroesprofile-replay-storage', 'other-bucket'),
                    PUBLIC + '?token=private', PUBLIC.replace('https://', 'https://user@'),
                    PUBLIC.replace('.com/', '.com:444/'), PUBLIC.replace('/' + KEY, '/../' + KEY),
                    public.API + '/Replay/Max', 'https://www.heroesprofile.com/', 'https://evil.test/'):
            routes = {S3: (302, {'Location': url}, b'')}
            with self.subTest(url=url), memory_https(routes) as seen:
                with self.assertRaises(ValueError):
                    public.get(S3, 100)
                self.assertEqual(seen, [S3])

    def test_api_redirect_cannot_change_into_an_object_download(self):
        api = public.API + '/Replay/Max'
        with memory_https({api: (302, {'Location': PUBLIC}, b'')}) as seen:
            with self.assertRaises(ValueError):
                public.get(api, 100)
            self.assertEqual(seen, [api])

    def test_size_limit_survives_normalization(self):
        with memory_https({PUBLIC: (200, {}, b'large')}) as seen:
            with self.assertRaisesRegex(ValueError, 'size limit'):
                public.get(CLOUD, 4)
            self.assertEqual(seen, [PUBLIC])


class OfflineDiscoveryIntegrationTests(unittest.TestCase):
    """Run real profile verification on a hash-bound tracked serialization fixture."""
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        base = Path(reference_replay.__file__).resolve().parent / 'checkpoints/96477/TEN_GREYMANE_protocol96477.StormReplay'
        fixture = Path(cls.directory.name) / 'fixture.StormReplay'
        cls.digest = restore(Path(str(base) + '.base64'), fixture, Path(str(base) + '.sha256'))
        cls.raw = fixture.read_bytes()

    def routes(self, url=CLOUD, build=96477, payload=None):
        return {
            public.API + '/Replay/Max': (200, {}, b'{"max_replayID": 501}'),
            public.API + '/Replay/Min_id?min_id=301':
                (200, {}, json.dumps([{'replayID': 501, 'game_version': f'2.55.15.{build}',
                                      'url': url}]).encode()),
            PUBLIC: payload or (200, {}, self.raw),
        }

    def test_discovery_normalized_fetch_and_real_profile_verification(self):
        with temporary_cwd() as root, memory_https(self.routes()) as seen:
            report = public.fetch(root / 'profiles', 96477, 96477)
            self.assertEqual(report['status'], 'references-found')
            self.assertEqual(report['attempts'][0]['status'], 'observed-payload-verified')
            self.assertEqual(report['attempts'][0]['stage'], 'complete')
            self.assertEqual(seen[-1], PUBLIC)
            self.assertNotIn(CLOUD, seen)
            profile = json.loads(Path(report['profiles'][0]).read_text())
            self.assertEqual(profile['file_sha256'], self.digest)
            self.assertEqual(profile['target']['m_version']['m_build'], 96477)
            self.assertEqual(profile['provenance']['download_host'], 'storage.googleapis.com')
            self.assertTrue(profile['observed_payload_roundtrip'])
            self.assertEqual(set(profile['streams']), {'game', 'message', 'tracker'})
            self.assertTrue(all(value['binary_roundtrip'] for value in profile['streams'].values()))
            self.assertFalse(profile['client_playback_validated'])
            self.assertFalse(profile['proven_authentic_by_signature'])
            self.assertEqual(hashlib.sha256((root / 'work/reference-donors/reference-501.StormReplay').read_bytes()).hexdigest(), self.digest)

    def test_403_download_is_distinct_from_schema_validation_failure(self):
        with temporary_cwd() as root, memory_https(self.routes(payload=(403, {}, b'AccessDenied private detail'))) as seen:
            with patch.object(public, 'inspect_reference', side_effect=AssertionError('403 reached parser')):
                denied = public.fetch(root / 'denied', 96477, 96477)
            self.assertEqual(seen[-1], PUBLIC)
            attempt = denied['attempts'][0]
            self.assertEqual(denied['status'], 'no-validated-reference-in-window')
            self.assertEqual((attempt['stage'], attempt['status'], attempt['http_status']),
                             ('download', 'download-unavailable', 403))
            self.assertEqual(denied['profiles'], [])
            self.assertFalse((root / 'work/reference-donors').exists())
            self.assertNotIn('private detail', json.dumps(denied))
        # The same valid fixture with a falsely declared API build must not be accepted.
        with temporary_cwd() as root, memory_https(self.routes(build=98348)):
            incompatible = public.fetch(root / 'incompatible', 98348, 96477)
            attempt = incompatible['attempts'][0]
            self.assertEqual((attempt['stage'], attempt['status'], attempt['http_status']),
                             ('schema-validation', 'reference-validation-failed', None))
            self.assertEqual(incompatible['profiles'], [])

    def test_rejected_api_url_is_not_fetched_or_exposed_in_report(self):
        url = CLOUD + '?token=do-not-publish'
        with temporary_cwd() as root, memory_https(self.routes(url=url)) as seen:
            report = public.fetch(root / 'profiles', 96477, 96477)
            self.assertEqual(report['attempts'][0]['status'], 'download-url-rejected')
            self.assertEqual(report['attempts'][0]['stage'], 'url-validation')
            self.assertEqual(len(seen), 2)
            self.assertEqual(report['profiles'], [])
            self.assertNotIn('do-not-publish', json.dumps(report))
            self.assertNotIn('storage.', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
