from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import sys

task=Path(__file__).resolve().parent.parent
base=task/'work/licensed-registry-semantics'
repo=Path(r'C:\Users\andrz\git\hots-replay-recovery')
sys.path[:0]=[str(repo),str(task/'work/python-deps'),str(task/'work/heroprotocol')]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
allow_raw=(base/'registry-semantics-final-allowlist.json').read_bytes()
assert sha(allow_raw)=='c869cbec5a1cc399794e8314740597b7d420a86cbd8f704606bfa072b92fc554'
allow=json.loads(allow_raw)
before={row['name']:sha((base/row['name']).read_bytes()) for row in allow['allowlisted_files']}
for row in allow['allowlisted_files']:
    assert before[row['name']]==row['sha256'] and (base/row['name']).stat().st_size==row['bytes']
spec=importlib.util.spec_from_file_location('root_semantics_frozen',base/'record_registry_semantics_findings.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
captured=[]
module.write_new_report=lambda report,path:captured.append((report,path))
with contextlib.redirect_stdout(io.StringIO()):module.main()
assert len(captured)==1
expected=json.loads((base/'registry-access-semantics-findings-v2.json').read_bytes())
assert captured[0][0]==expected
for name,expected_sha in before.items():assert sha((base/name).read_bytes())==expected_sha
summary={'format':'hots-current-access-semantics-root-independent-recompute-v1',
    'root_review_source_sha256':sha(Path(__file__).read_bytes()),
    'findings_report_sha256':sha((base/'registry-access-semantics-findings-v2.json').read_bytes()),
    'frozen_allowlist_sha256':sha(allow_raw),
    'fresh_report_JSON_values_equal_frozen_report':True,
    'original_writer_intercepted_no_report_overwritten':True,
    'executed_recompute_source_sha256':before['record_registry_semantics_findings.py'],
    'all12allowlisted_sources_and_receipts_unchanged':True,
    'six_existing_static_inputs_full_MD5_SHA_and_size_checks_repeated':True,
    'current_local_game_text_Git_blob_hashes_repeated':True,
    'remote_primary_source_retrieval_independently_repeated':False,
    'four_saved_CASC_operation_guards_crosschecked_not_reexecuted':True,
    'four_source_function_branches_rechecked_by_producer':True,
    'old264_raw263unique_and_current5497_raw5418unique_registry_bindings_repeated':True,
    'incorrect_NPC_registry_examples_absent_crosscheck_repeated':True,
    'new_unit_tests_or_CI_claimed':False,'client_launched':False,'network_requests':0,
    'CASC_opened_by_this_recompute':False,'replay_read_or_written':False,
    'limitations':['This repeats the frozen static producer and locally authenticated inputs; it is not an independent implementation of the engine access API.',
        'Remote public-source blob fetch provenance is supplied by the original evidence; this review independently recalculates local Git blob identities only.',
        'No field23-to24 migration, availability ownership or player-cell semantics is established.']}
output=base/'root-registry-semantics-recompute.json'
with output.open('xb') as handle:handle.write((json.dumps(summary,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'fresh_report_exact':True,'report_sha256':sha(output.read_bytes()),'existing_static_input_bytes':expected['total_native_and_text_bytes']}))
