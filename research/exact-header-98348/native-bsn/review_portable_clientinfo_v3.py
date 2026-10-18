"""Review the frozen portable codec with synthetic data and saved receipts only.

This does not open a PE or replay, execute a corpus producer, or use a network.
"""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
READY = HERE.parent / 'native-client-codec-ready'
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
PINS = {
    'native-clientinfo-frozen-receipt-v3.json': '1bc68a48f1e75491625488a8c4ddc1cd103874611401a3a3b19e2bc47dc1e16b',
    'native_clientinfo.py': 'e0abd0b674c97b87f6a1510edc08704eebeca0ad9d43ac0537d5eaaa3eb9b202',
    'test_native_clientinfo.py': '8e0b680dda9d14753a3747fb0d8579237d56f731a0c47976ba768b556b65e086',
    'native_clientinfo_schema_98348.json': '6e8711939ede15505debb043ae626b5c529749557d7e824226863c92e4f6a229',
    'verify_native_clientinfo_controls.py': 'e32af54bb79725b0d98c5fefa3d3b78942bd1761308ba8cbefb2a31b84668fb6',
    'portable-native-clientinfo-21control-verification-v3-local-source.json': '903617b7f41af0a8377fea6227487dc94582c59babaf3b164bf745abb4120400',
    'README_NATIVE_CLIENTINFO.md': '1389db6604e19acfbf5e32c9bfd8c675860c44b1b71b4585246bbf7aba62f7ff',
}
PRIOR = 'f077a91d3059380f4390e8fad7b1e6d85d63c84c4f78ec16ae4d5ea7b68ee505'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def read(path, limit=256*1024):
    if path.is_symlink(): raise ValueError('Review source symlink refused')
    with path.open('rb') as stream:
        a = os.fstat(stream.fileno())
        if not stat.S_ISREG(a.st_mode) or not 1 <= a.st_size <= limit:
            raise ValueError('Review source type/size refused')
        raw = stream.read(limit+1)
        b = os.fstat(stream.fileno())
    if len(raw) != a.st_size or (a.st_size, a.st_mtime_ns) != (b.st_size, b.st_mtime_ns):
        raise ValueError('Review source changed during read')
    return raw

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def review():
    raw = {name: read(READY/name) for name in PINS}
    if any(sha(raw[name]) != pin for name, pin in PINS.items()):
        raise ValueError('Frozen portable input changed')
    manifest = json.loads(raw['native-clientinfo-frozen-receipt-v3.json'])
    for entry in manifest['files']:
        body = raw[entry['file']]
        if (len(body), sha(body)) != (entry['bytes'], entry['sha256']):
            raise ValueError('Manifest entry differs')
    if manifest['focused_tests'] != 14 or not manifest['post_recursion_field_cap_checked']:
        raise ValueError('Final field-cap proof absent')
    actual = json.loads(raw['portable-native-clientinfo-21control-verification-v3-local-source.json'])
    if actual['cases'] != 21 or actual['players'] != 222 or not actual['native_module_loaded_by_exact_local_source_path']:
        raise ValueError('Saved actual portable proof scope differs')
    for name, value in actual['source_hashes'].items():
        if value != PINS[name]: raise ValueError('Actual proof source binding differs')
    earlier = read(HERE/'native-ClientInfo-independent-review.json')
    if sha(earlier) != PRIOR: raise ValueError('Prior independent proof pin differs')
    earlier = json.loads(earlier)
    if sorted((x['id'], x['replay_sha256']) for x in actual['results']) != sorted((x['id'], x['replay_sha256']) for x in earlier['cases']):
        raise ValueError('Actual portable and independently decoded cohorts differ')
    if sum(x['facts']['players_checked'] for x in actual['results']) != 222:
        raise ValueError('Actual player aggregate differs')
    for case in actual['results']:
        facts = case['facts']
        if not all(facts[k] for k in ('native_ClientInfo_complete_ends_match', 'all_13_named_anchors_match', 'private_native_scope_and_toon_match', 'all_consumed_spans_reencode_exact')):
            raise ValueError('Saved actual structural proof incomplete')
        if facts['raw_player_values_emitted'] or facts['full_replay_compatibility_claimed']:
            raise ValueError('Saved proof privacy/claim differs')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPO))
    codec = load('native_clientinfo', READY/'native_clientinfo.py')
    tests = load('_independent_final_clientinfo_tests', READY/'test_native_clientinfo.py')
    if Path(codec.__file__).resolve() != (READY/'native_clientinfo.py').resolve():
        raise ValueError('Wrong codec loaded')
    with tempfile.TemporaryDirectory(dir=HERE) as folder:
        old = tempfile.tempdir
        tempfile.tempdir = folder
        try:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
        finally: tempfile.tempdir = old
    if result.testsRun != 14 or not result.wasSuccessful() or result.skipped:
        raise ValueError('Final synthetic tests did not all pass')
    synthetic, start, _ = tests.fixture()
    value = codec.decode_clientinfo(synthetic, start, codec.PROFILE)
    cap = len(value.fields)-1
    if not cap > len(value.tokens): raise ValueError('Probe does not isolate field budget')
    with patch.object(codec, 'MAX_TOKENS', cap):
        try: codec.decode_clientinfo(synthetic, start, codec.PROFILE)
        except codec.LayerError as error:
            if 'field budget' not in str(error): raise
        else: raise ValueError('Postorder field-budget overrun still accepted')
    if any(getattr(t, '__repr__') is not object.__repr__ for t in (codec.NativeField, codec.WireToken, codec.ClientInfo)):
        raise ValueError('Private dataclass repr differs')
    if any(sha(read(READY/name)) != pin for name, pin in PINS.items()):
        raise ValueError('Portable source changed during review')
    return {
        'format': 'hots-portable-ClientInfo-v3-independent-review-v1',
        'producer_sha256': sha(read(Path(__file__))),
        'reviewed_file_sha256s': PINS,
        'focused_synthetic_tests': 14, 'failures': 0, 'errors': 0, 'skips': 0,
        'postorder_field_budget_regression_independently_reproduced_and_fixed': True,
        'read_only_reencode_same_width_token_mutation_refused': True,
        'reviewed_guards': ['Explicit authenticated profile and immutable source/hash/span binding', 'Pinned104-type schema/provenance and bounded regular-file read', 'Depth, preappend field, wire token, array, bit-array and UTF8/ASCII byte/character limits', 'Disabled dataclass repr and aggregate-only adapter result', 'Current observed-tail adapter independently validates unchanged member, thirteen anchors, complete record ends and private scope/Toon equality'],
        'saved_actual_proof_hash_checked': True,
        'saved_actual_proof_cases': 21, 'saved_actual_proof_players': 222,
        'saved_actual_proof_cases_equal_prior_independent_decoder_cases': True,
        'prior_independent_actual_reader_receipt_sha256': PRIOR,
        'remaining_material_findings': [],
        'PE_or_replay_reopened_in_this_review': False,
        'actual_portable_corpus_producer_rerun_in_this_review': False,
        'private_values_or_vectors_or_account_identifiers_emitted': False,
        'network_or_client_or_repo_write_used': False,
        'limits': ['The saved fresh exact-local-source21/222 result was hash/aggregate/cohort checked, not independently rerun in this code-only review.', 'The earlier independent native reader supplied separate actual21/222 bit/identity/end/reencoding proof.', 'Native decoding and observed-tail crossbinding do not establish historical174-bit conversion, entitlement semantics or full replay/client compatibility.'],
    }

if __name__ == '__main__':
    out = HERE/'portable-ClientInfo-v3-independent-review.json'
    data = (json.dumps(review(), indent=2, sort_keys=True)+'\n').encode()
    if len(data) > 64*1024: raise ValueError('Review report too large')
    with out.open('xb') as stream: stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': sha(data)}))
