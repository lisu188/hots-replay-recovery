"""Offline review of frozen exact-object search evidence; no network requests.

The producer is run only against a synthetic opener in a temporary folder.
Its original report and all frozen source files are never overwritten.
"""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import hashlib
import json
import socket
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import search_exact_public_datamod as subject
from collection_license_audit import _read, write_new_report

WORK = Path(__file__).resolve().parents[1]
BASE = WORK/'exact-datamod-search-ready'
EXPECTED = '42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a'
PINS = {
    'search_exact_public_datamod.py': 'f6ed7abedfe59df1b9df2fb0c7900e67d4e800590055bc6aa5f60bc62ba2ee60',
    'test_search_exact_public_datamod.py': '013baba922a05678556b192ac7f8e779228c5bce986f1a7d743a5c99e0df8806',
    'endpoint-primary-source-provenance.json': '73d53ab5de28afccf651818a0801e17368678b2a4dedd11cdb58469e0aa75bae',
    'exact-datamod-alternate-endpoint-acquisition.json': '405d06816b2e34771c232c96cded7d79a08349d7f11962ec0e9c7b80deee8fb5',
}
PRIOR_SHA = 'babd5479656ce1c4fa6b8ad5d7a0dfbe81574ff9117f8adfeaabef165b85d8ef'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('Exact DataMod search frozen evidence verification failed')


def deny_network(*args, **kwargs):
    raise AssertionError('Network access is forbidden in this independent review')


def verify_pins():
    for name, digest in PINS.items():
        require(sha(_read(BASE/name, 128*1024)) == digest)


class SyntheticOpener:
    def __init__(self):
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request.full_url)
        require(timeout == 10 and len(self.requests) <= 5)
        if len(self.requests) <= 2:
            raise urllib.error.HTTPError(request.full_url, 404, 'synthetic', {}, None)
        raise urllib.error.URLError('synthetic transport failure')


def verify():
    verify_pins()
    frozen_raw = _read(BASE/'exact-datamod-search-frozen-receipt.json', 128*1024)
    frozen = json.loads(frozen_raw)
    for row in frozen['allowlisted_files']:
        require(row['relative_to_work'].startswith('exact-datamod-search-ready/'))
        name = Path(row['relative_to_work']).name
        require(name in PINS and row['sha256'] == PINS[name])
        require(len(_read(BASE/name, 128*1024)) == row['bytes'])
    require(len(frozen['allowlisted_files']) == len(PINS))
    sources_raw = _read(BASE/'endpoint-primary-source-provenance.json', 128*1024)
    sources = json.loads(sources_raw)
    roles = {row['role']: row for row in sources['sources']}
    require(set(roles) == {'modern', 'legacy'})
    modern, legacy = roles['modern'], roles['legacy']
    require(modern['commit'] == 'e10fc9344417d0aa9649e4ed8d6423e38f6af4c9')
    require(modern['git_blob_sha1'] == '893cc8c99e91202811db936c96babf9f8c9795ff')
    require(modern['full_source_sha256'] == '2a3a98df7ed48a0f1794ae61b87e1a02e5e368970b8b7d3681f67d1c59698db8')
    require(legacy['git_blob_sha1'] == '76ea3dac94da026adc0b4864a9bdd87b7265e86c')
    require(legacy['full_source_sha256'] == '60d359afcf5d7e5b9c923e1146063b400ea4a91ef6dc927f1a953ad25f287b48')
    # These exact excerpts were inspected as source; derive only their public URL templates.
    require('url_template = "{}://{}-s2-depot.{}/{}.{}"' in modern['exact_function_excerpt'])
    require('scheme = "https"' in modern['exact_function_excerpt'])
    require('domain = "classic.blizzard.com"' in modern['exact_function_excerpt'])
    require('domain = "necdn.leihuo.netease.com"' in modern['exact_function_excerpt'])
    require("'http://'" in legacy['exact_function_excerpt'] and "'.depot.battle.net:1119/'" in legacy['exact_function_excerpt'])
    expected_urls = [
        f'https://kr-s2-depot.classic.blizzard.com/{EXPECTED}.s2mh',
        f'https://cn-s2-depot.necdn.leihuo.netease.com/{EXPECTED}.s2mh',
        *[f'http://{region}.depot.battle.net:1119/{EXPECTED}.s2mh' for region in ('us', 'eu', 'kr')],
    ]
    require([url for _, url, _ in subject.PLAN] == expected_urls)
    prior_raw = _read(WORK/'independent-parser/exact-current-s2mh-acquisition.json', 128*1024)
    require(sha(prior_raw) == PRIOR_SHA)
    prior = [row for row in json.loads(prior_raw)['attempts'] if row.get('expected_sha256') == EXPECTED]
    require(len(prior) == 2 and all(row['http_status'] == 404 for row in prior))
    require(not set(expected_urls) & {row['url'] for row in prior})
    report = json.loads(_read(BASE/'exact-datamod-alternate-endpoint-acquisition.json', 128*1024))
    attempts = report['attempts']
    require(len(attempts) == report['actual_object_requests'] == 5)
    require([row['url'] for row in attempts] == expected_urls)
    require(len({row['url'] for row in attempts}) == 5)
    require(report['source_producer_sha256'] == PINS['search_exact_public_datamod.py'])
    require(report['primary_endpoint_source_evidence_sha256'] == PINS['endpoint-primary-source-provenance.json'])
    require(report['prior_acquisition_receipt_sha256'] == PRIOR_SHA)
    require(report['expected_package'] == {'mod_id': 280539, 'version': 16})
    require(report['expected_object_sha256'] == EXPECTED)
    require(report['actual_body_bytes_read'] == sum(row['body_bytes_read'] for row in attempts) == 0)
    require(all(row['status'] == 'acquisition_failed' and not row['body_saved'] for row in attempts))
    require([row.get('http_status') for row in attempts[:2]] == [404, 404])
    require(all(row['reason'] == 'transport_failure' and row['error_type'] == 'URLError' for row in attempts[2:]))
    require(report['acquisition_failure_count'] == 5 and report['validation_failure_count'] == 0)
    require(report['application_retries'] == report['redirects_followed'] == 0)
    require(not report['verified_exact_object_saved_privately'])
    require(not (BASE/'verified-private').exists())
    require(all(not urlsplit(url).username and not urlsplit(url).password and not urlsplit(url).query and not urlsplit(url).fragment for url in expected_urls))
    suite = unittest.defaultTestLoader.loadTestsFromName('test_search_exact_public_datamod')
    with patch.object(socket, 'create_connection', deny_network), patch.object(socket.socket, 'connect', deny_network), patch.object(urllib.request, 'urlopen', deny_network):
        tests = unittest.TextTestRunner(verbosity=1).run(suite)
        require(tests.testsRun == 8 and tests.wasSuccessful() and not tests.skipped)
        fake = SyntheticOpener()
        with tempfile.TemporaryDirectory(prefix='datamod-review-', dir=Path(__file__).resolve().parent) as temporary:
            temp = Path(temporary)
            (temp/'endpoint-primary-source-provenance.json').write_bytes(sources_raw)
            with patch.object(subject, 'HERE', temp), patch.object(subject.urllib.request, 'build_opener', return_value=fake), redirect_stdout(StringIO()):
                subject.run()
            synthetic = json.loads(_read(temp/'exact-datamod-alternate-endpoint-acquisition.json', 128*1024))
            require(fake.requests == expected_urls)
            require(synthetic['actual_object_requests'] == synthetic['acquisition_failure_count'] == 5)
            require(synthetic['actual_body_bytes_read'] == synthetic['validation_failure_count'] == 0)
            require(not synthetic['verified_exact_object_saved_privately'])
            require(not (temp/'verified-private').exists())
    verify_pins()
    require(sha(_read(BASE/'exact-datamod-search-frozen-receipt.json', 128*1024)) == sha(frozen_raw))
    return {
        'format': 'hots-exact-datamod-alternate-search-independent-review-v1',
        'review_source_sha256': sha(_read(Path(__file__), 128*1024)),
        'reviewed_frozen_input_pins': PINS,
        'frozen_allowlist_receipt_sha256': sha(frozen_raw), 'prior_acquisition_receipt_sha256': PRIOR_SHA,
        'focused_synthetic_tests_passed': 8, 'focused_test_errors_failures_or_skips': 0,
        'additional_synthetic_full_producer_run': {
            'requests_to_fake_opener': 5, 'HTTP404_failures': 2, 'URLError_failures': 3,
            'body_bytes_read': 0, 'private_bodies_saved': 0,
            'fixed_plan_order_exact': True, 'no_application_retries_or_redirects': True},
        'saved_actual_receipt_consistency': {
            'recorded_requests': 5, 'recorded_HTTP404_failures': 2, 'recorded_URLError_failures': 3,
            'recorded_body_bytes_read': 0, 'recorded_validation_failures': 0,
            'recorded_private_bodies_saved': 0, 'prior_two_404_URLs_not_repeated': True},
        'primary_source_review': {
            'recorded_source_function_excerpts_support_exact_endpoint_plan': True,
            'source_blob_and_full_source_hash_pins_preserved': True,
            'full_primary_sources_refetched_or_rehashed_by_reviewer': False},
        'privacy': {'raw_bodies_response_messages_accounts_credentials_or_private_paths_emitted': False,
                    'public_exact_content_handle_and_package_tuple_only': True},
        'all_frozen_sources_reports_and_prior_receipt_unchanged': True,
        'material_findings_in_recorded_actual_scope': [],
        'reviewer_network_requests': 0, 'client_launched': False, 'replay_or_repo_modified': False,
        'limits': [
            'Recorded actual network outcomes are checked against frozen evidence; no live request or independent packet-level observation is performed.',
            'Primary function excerpts and recorded source pins are available locally; full remote source objects were not independently retrieved in this offline review.',
            'All five recorded attempts failed acquisition before body reads. They establish neither header incompatibility nor exact object recovery.',
            'The additional producer execution uses a synthetic opener only; its temporary metadata report is discarded and the frozen actual report is preserved.']}


if __name__ == '__main__':
    result = verify()
    output = Path(__file__).with_name('exact-datamod-search-independent-review.json')
    write_new_report(result, output)
    print(json.dumps({'synthetic_tests': result['focused_synthetic_tests_passed'],
                      'synthetic_full_run_requests': 5, 'network_requests': 0,
                      'review_receipt_sha256': sha(_read(output, 128*1024))}))
