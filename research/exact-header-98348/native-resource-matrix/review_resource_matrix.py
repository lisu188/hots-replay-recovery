"""Synthetic/source/saved-receipt review; never opens a PE or replay."""
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

HERE = Path(__file__).resolve().parent
READY = HERE.parent/'native-resource-matrix-ready'
PINS = {
    'native-resource-matrix-frozen-receipt.json': 'ad7a1d57c83eae37f633798ebf1a9f4d7f3f6ee74504defc1272cf930eaf53fa',
    'project_native_resource_matrix.py': '47ba59ad6998615a75ae691a943e6b24dd2d73fde5afc0cd3f350c85c1023120',
    'native-resource-matrix-static-98348.json': 'c2c8deb0775bc35e3621dbd2567b39fd9159590263a0fd777c54ce79d5dcb7c7',
    'resource_matrix_binding.py': '2fb1621437c377a3de5b50c8b5f846f0d22af0d27a839903bfd5a6dd2eea2069',
    'test_resource_matrix_binding.py': 'c9c10d22d9bf81810fbc61d320fe7cccfefd6567359ac2bf45696162b81a5347',
    'native-resource-matrix-21case-binding-v2.json': '99300ec26b68f8caa82d133592c142378ba7c1be56629472b9e259d1468687fd',
}
PE = 'efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
BSN = 'ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
PRIOR = 'f077a91d3059380f4390e8fad7b1e6d85d63c84c4f78ec16ae4d5ea7b68ee505'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def read(path):
    if path.is_symlink(): raise ValueError('Source symlink refused')
    with path.open('rb') as stream:
        a = os.fstat(stream.fileno())
        if not stat.S_ISREG(a.st_mode) or not 1 <= a.st_size <= 256*1024:
            raise ValueError('Source size/type refused')
        raw = stream.read(256*1024+1)
        b = os.fstat(stream.fileno())
    if len(raw) != a.st_size or (a.st_size,a.st_mtime_ns) != (b.st_size,b.st_mtime_ns):
        raise ValueError('Source changed while reading')
    return raw

def load(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def review():
    raw = {name:read(READY/name) for name in PINS}
    if any(sha(raw[name]) != pin for name,pin in PINS.items()):
        raise ValueError('Frozen matrix inputs changed')
    manifest = json.loads(raw['native-resource-matrix-frozen-receipt.json'])
    for row in manifest['allowlisted_files']:
        if (len(raw[row['name']]),sha(raw[row['name']])) != (row['bytes'],row['sha256']):
            raise ValueError('Allowlist entry differs')
    static = json.loads(raw['native-resource-matrix-static-98348.json'])
    actual = json.loads(raw['native-resource-matrix-21case-binding-v2.json'])
    if (static['source_PE_sha256'],static['embedded_blob_sha256']) != (PE,BSN):
        raise ValueError('Static source provenance differs')
    if static['producer_sha256'] != PINS['project_native_resource_matrix.py']:
        raise ValueError('Static projection producer pin differs')
    if (actual['producer_sha256'],actual['test_source_sha256'],actual['static_projection_sha256']) != (PINS['resource_matrix_binding.py'],PINS['test_resource_matrix_binding.py'],PINS['native-resource-matrix-static-98348.json']):
        raise ValueError('Actual binding source pins differ')
    prior_path = HERE.parent/'native-client-independent-review/native-ClientInfo-independent-review.json'
    prior_raw = read(prior_path)
    if sha(prior_raw) != PRIOR: raise ValueError('Prior independent cohort receipt differs')
    prior = json.loads(prior_raw)
    if sorted((x['id'],x['replay_sha256']) for x in actual['cases']) != sorted((x['id'],x['replay_sha256']) for x in prior['cases']):
        raise ValueError('Actual current corpus differs from earlier independent case list')
    if actual['current_cases'] != 21 or len(actual['cases']) != 21 or len({x['id'] for x in actual['cases']}) != 21:
        raise ValueError('Actual case count/uniqueness differs')
    case_keys = {'id','replay_sha256','profile_sha256','member_sha256','build_base_data','root','resource_identifiers','matrix_rows','matrix_cells','matrix_bytes_including_count','full_mod_tail_EOF_roundtrip_and_private_crosschecks_passed','native_resourceMap_matrix_disabled_boundaries_exact','all_native_u16_values_equal_prior_row_bytes','independent_resource_block_encode_decode_exact'}
    for row in actual['cases']:
        if set(row) != case_keys: raise ValueError('Unexpected per-case fields')
        if (row['build_base_data'],row['resource_identifiers'],row['matrix_rows'],row['matrix_cells'],row['matrix_bytes_including_count']) != (98348,5418,5418,5418*16,4+5418*32):
            raise ValueError('Actual row representation/count differs')
        if not all(row[k] for k in ('full_mod_tail_EOF_roundtrip_and_private_crosschecks_passed','native_resourceMap_matrix_disabled_boundaries_exact','all_native_u16_values_equal_prior_row_bytes','independent_resource_block_encode_decode_exact')):
            raise ValueError('Saved per-case structural proof incomplete')
    a = actual['aggregate']
    if (a['matrix_rows'],a['u16_cells'],a['bytes_per_matrix_row'],a['u16_cells_per_row']) != (21*5418,21*5418*16,32,16):
        raise ValueError('Saved aggregates differ')
    counts = actual['actual_reads']
    if sum(counts['read_categories'].values()) + counts['source_code_verification_read_bytes'] != counts['explicit_analysis_read_bytes']:
        raise ValueError('Read accounting does not add up')
    if counts['explicit_analysis_read_bytes'] != 61324571 or counts['PE_reads_in_this_binding_stage'] != 0:
        raise ValueError('Final explicit read scope differs')
    for key in ('private_cell_values_patterns_vector_hashes_positions_accounts_or_masks_emitted','matrix_ownership_or_bit_index_meaning_inferred','replay_member_header_or_private_resource_block_written','client_launched','network_used','repo_or_cloud_modified'):
        if actual[key]: raise ValueError('Saved privacy/claim scope differs')
    sys.dont_write_bytecode = True
    module = load('resource_matrix_binding',READY/'resource_matrix_binding.py')
    module.check_static()
    tests = load('_independent_matrix_tests',READY/'test_resource_matrix_binding.py')
    with tempfile.TemporaryDirectory(dir=HERE) as folder:
        old = tempfile.tempdir;tempfile.tempdir = folder
        try:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
        finally: tempfile.tempdir = old
    if result.testsRun != 12 or not result.wasSuccessful() or result.skipped:
        raise ValueError('Focused matrix tests did not all pass')
    if any(sha(read(READY/name)) != pin for name,pin in PINS.items()):
        raise ValueError('Frozen sources changed during review')
    return {
        'format':'hots-native-resource-matrix-independent-code-review-v1',
        'producer_sha256':sha(read(Path(__file__))),
        'reviewed_file_sha256s':PINS,
        'focused_tests':12,'failures':0,'errors':0,'skips':0,
        'static_shape_validation_rerun':True,
        'reviewed_static_shape':'ResourceIdentifierMap<u64 LicenseId> followed by ResourceAccessMatrix<ScopeResources[16] ResourceState/u16> then DisabledHeroList<FourCC>.',
        'saved_actual_case_count':21,'saved_actual_matrix_rows':113778,'saved_actual_u16_cells':1820448,
        'saved_actual_case_digests_equal_earlier_independent_corpus':True,
        'saved_actual_source_pins_and_aggregate_read_accounting_verified':True,
        'explicit_producer_read_bytes':61324571,
        'reviewed_checks':['Exact pinned PE/BSN/static graph projection and parent adjacency', 'Distinct ResourceAccessList is not substituted for ResourceAccessMatrix', 'Big-endian byte-aligned scalars, bounded counts and exact byte extent', 'Exact resource-map/matrix/disabled-list boundaries and whole selected-block reencoding', 'Current98348 root/schema/profile gates and unchanged legacy/current input pins', 'Full mod/tail EOF plus private details/initData slot/Toon/seed guards', 'Aggregate-only reports with no cell values, vectors, vector hashes, masks or account/slot identifiers'],
        'remaining_material_findings':[],
        'PE_or_replay_opened_in_this_review':False,
        'actual21_case_producer_rerun_in_this_review':False,
        'network_client_repo_or_cloud_used':False,
        'private_player_or_matrix_values_emitted':False,
        'limits':['This review independently reran synthetic tests and static-shape checks, and verified saved source/report/corpus pins and aggregate arithmetic.', 'The21-case actual producer result was inspected, not recomputed by reopening the PE or replays in this review.', 'Static names and exact16-u16 row structure establish representation only; ownership, entitlement rules, scope-to-player mapping, license filling and historical conversion are not inferred.'],
    }

if __name__ == '__main__':
    output = HERE/'native-resource-matrix-independent-review.json'
    body = (json.dumps(review(),indent=2,sort_keys=True)+'\n').encode()
    if len(body)>64*1024: raise ValueError('Receipt too large')
    with output.open('xb') as stream: stream.write(body)
    print(json.dumps({'bytes':len(body),'sha256':sha(body)}))
