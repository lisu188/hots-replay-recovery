"""Freeze the completed review; no replay/PE/network access or test rerun."""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent;WORK=BASE.parent;READY=WORK/'native-online-codec-ready'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
PINS={'review_native_online.py':'16bb5a9cc4a8566cacdfaed9261ccdb1f0c6183d99e0a553720ed9939ae0dc91','test_independent_physical_walker.py':'b1c8b74a19538efa8e57c0f48d3e9ad088d9d0c3ca21a565799394d287e6e39a','native-online-independent-review.json':'da113f669ee525bb17a629d38959508ced9d88f14da42d2f7fcc5f00f2f60697'}
GRAPH_SHA='56fa4fedd97e63737c2c575e63c728d9389d015243ff6acd25020c4d62834147'
SCHEMA_SHA='0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640'
def read(path,limit):
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=limit:raise ValueError('Frozen input bounds/type differ')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Input exceeded cap')
    return raw
def main():
    files=[]
    for name,pin in PINS.items():
        raw=read(BASE/name,64*1024)
        if sha(raw)!=pin:raise ValueError('Review source/test/report changed')
        files.append({'path':name,'bytes':len(raw),'sha256':pin})
    graph=read(WORK/'current-header-field-exposure/native-header-mapinfo-selected-graph.json',128*1024)
    schema=read(READY/'native_startgame_schema_98348.json',256*1024)
    if sha(graph)!=GRAPH_SHA or sha(schema)!=SCHEMA_SHA:raise ValueError('Authenticated cached/schema input differs')
    old={r['id']:r for r in json.loads(graph)['records']};new={r['id']:r for r in json.loads(schema)['records']}
    common=set(old)&set(new)
    if len(common)!=293 or not all(old[i]==new[i] for i in common):raise ValueError('Hash-pinned native projection overlap differs')
    for name,pin in PINS.items():
        if sha(read(BASE/name,64*1024))!=pin:raise ValueError('Review input changed after followup')
    raw=read(Path(__file__),64*1024);files.append({'path':Path(__file__).name,'bytes':len(raw),'sha256':sha(raw)})
    output={'format':'whole-native-online-independent-review-frozen-v1','files':files,'review_conclusion':'PASS; no material finding in current read-only structural scope','focused_production_tests':{'run':14,'passed':14,'skipped':0},'independent_physical_walker_synthetic_negative_tests':{'run':7,'passed':7,'skipped':0},'fresh_hash_pinned_projection_overlap':{'cached_authenticated_graph_sha256':GRAPH_SHA,'portable_schema_sha256':SCHEMA_SHA,'records_compared':293,'all_exact':True,'PE_reopened':False},'actual_control_scope':{'existing_current_US_Dragon_files_read':1,'replay_read_bytes':1113273,'whole_member_bytes':282976,'postorder_fields_compared':423660,'tokens_compared':157802,'physical_bit_reencoding_exact':True,'summary_JSON_exact_to_frozen21_case':True,'whole21case_rerun':False,'second_replay_content_read':False},'local_environment_notes':{'default_temp_sandbox_PermissionError_test_only_attempts':2,'actual_replay_reads_in_failed_attempts':0,'successful_tests_used_work_subdirectory':True,'initial_CMD_multiline_command_not_counted_as_tests':True},'privacy':{'raw_values_or_replay_bodies_included':False,'PE_or_dump_bytes_included':False,'public_claim_limited_to_structural_source_and_one_case_bit_proof':True},'network_client_or_repo_writes':False,'no_historical_transcoding_or_simulation_parity_claimed':True}
    data=(json.dumps(output,sort_keys=True,indent=2)+'\n').encode();out=BASE/'native-online-independent-frozen-receipt.json'
    with out.open('xb') as stream:stream.write(data)
    print(json.dumps({'file':out.name,'bytes':len(data),'sha256':sha(data)}))
if __name__=='__main__':main()
