"""Synthetic/static independent framing review; no replay/header/PE/network reads."""
from pathlib import Path
from io import StringIO
import argparse,collections,hashlib,importlib,json,os,stat,sys,tempfile,unittest
HERE=Path(__file__).resolve().parent;WORK=HERE.parent
READY=WORK/'legacy-mapinfo-framing-ready';REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(READY),str(REPO)];sys.dont_write_bytecode=True
sha=lambda raw:hashlib.sha256(raw).hexdigest()
BASELINE_SHA='de29dfe84d6906fda09768c7e545d8c1053e641e44d21372692b0f45d6529477'
counts=collections.Counter()
def need(ok,message):
    if not ok:raise ValueError(message)
def read(path,limit):
    path=Path(path);need(not path.is_symlink(),'Source/proof symlink refused')
    with path.open('rb') as stream:
        a=os.fstat(stream.fileno());need(stat.S_ISREG(a.st_mode) and 0<a.st_size<=limit,'Source/proof bounds differ')
        raw=stream.read(limit+1);b=os.fstat(stream.fileno())
    need(len(raw)==a.st_size and (a.st_size,a.st_mtime_ns)==(b.st_size,b.st_mtime_ns),'Source/proof changed')
    counts['explicit_source_metadata_bytes']+=len(raw)
    return raw

def review(freeze_sha,expected_tests,proof=None,proof_sha=None):
    frozen_raw=read(READY/'code-test-freeze-v2.json',64*1024);need(sha(frozen_raw)==freeze_sha,'Freeze receipt differs');frozen=json.loads(frozen_raw)
    source_pins={}
    for item in frozen['allowlisted_files']:
        raw=read(READY/item['name'],64*1024);need(len(raw)==item['bytes'] and sha(raw)==item['sha256'],'Frozen source/test differs')
        source_pins[item['name']]=item['sha256']
    import legacy_mapinfo_framing as codec
    need(Path(codec.__file__).resolve()==(READY/'legacy_mapinfo_framing.py').resolve(),'Wrong converter imported')
    baseline_raw=read(WORK/'legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json',64*1024)
    need(sha(baseline_raw)==BASELINE_SHA==codec.BASELINE_RECEIPT_SHA256,'Baseline receipt pin differs')
    baseline=json.loads(baseline_raw)
    expected=tuple((case['id'],case['member_sha256'],tuple((r['baseline_start_bit'],r['baseline_end_bit']) for r in case['entries']))for case in baseline['cases'])
    need(codec._ADMITTED==expected and len(expected)==3 and sum(len(row[2]) for row in expected)==16,'Admitted hashes/spans differ')
    deps={}
    for row in frozen['current_dependencies']:
        path=REPO/row['name'];raw=read(path,256*1024)
        need(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'Native dependency differs')
        deps[row['name']]=(path,row['sha256'])
    caps={k:v for k,v in vars(codec.native.shared).items() if k.startswith('MAX_') and type(v)is int}
    admitted_before=codec._ADMITTED
    suite=unittest.defaultTestLoader.discover(str(READY),pattern='test_legacy_mapinfo_framing.py',top_level_dir=str(READY))
    temp=HERE/'synthetic-test-temp';temp.mkdir(exist_ok=True);prior=tempfile.tempdir;tempfile.tempdir=str(temp)
    try:result=unittest.TextTestRunner(stream=StringIO(),verbosity=1).run(suite)
    finally:tempfile.tempdir=prior
    need(result.testsRun==expected_tests and not result.failures and not result.errors and not result.skipped,'Focused tests failed/count differs')
    module=sys.modules['test_legacy_mapinfo_framing']
    independent=[]
    for start in range(8):
        fixture=module.Fixture(start=start,records=6,overrides={'/m_handle/m_id':37,'/m_handle/m_version':91,'/m_addMultiMod':1,'/m_extraDependencies':2})
        with module.admitted(fixture):
            value=codec.convert_mapinfo_framing(fixture.raw,codec.PROFILE)
            need(value.converted==fixture.expected(),'Independent max-record physical splice differs')
            need(codec.inverse_mapinfo_framing(value,codec.PROFILE)==fixture.raw,'Max-record whole inverse differs')
            summary=value.summary();need(summary['added_bytes']==18 and summary['MapInfo_records']==6 and summary['named_root_field_comparisons']==192,'Max-record aggregate differs')
            independent.append(start)
    fixture=module.Fixture(records=7)
    with module.admitted(fixture):
        try:codec.convert_mapinfo_framing(fixture.raw,codec.PROFILE)
        except codec.LayerError:pass
        else:raise ValueError('Seven records were admitted')
    fixture=module.Fixture();unexpected_hash=False
    with module.admitted(fixture):
        value=codec.convert_mapinfo_framing(fixture.raw,codec.PROFILE)
        from dataclasses import replace
        bad=value.converted+b'\x00';changed=replace(value,converted=bad,converted_sha256=sha(bad));old_sha=codec.sha
        def checked_hash(raw):
            nonlocal unexpected_hash
            if raw is bad:unexpected_hash=True;raise AssertionError('Incorrect-length target hashed before rejection')
            return old_sha(raw)
        codec.sha=checked_hash
        try:
            try:codec.inverse_mapinfo_framing(changed,codec.PROFILE)
            except codec.LayerError:pass
            else:raise ValueError('Wrong target length admitted')
        finally:codec.sha=old_sha
    need(not unexpected_hash,'Fail-fast target length hash guard differs')
    need(codec._ADMITTED==admitted_before,'Synthetic source admission patch persisted')
    need(caps=={k:v for k,v in vars(codec.native.shared).items() if k.startswith('MAX_')and type(v)is int},'Shared native budgets changed')
    proof_info={'actual_16_record_proof_recomputed':False,'raw_inputs_reread':False}
    if proof:
        proof_raw=read(Path(proof),256*1024);need(sha(proof_raw)==proof_sha,'Actual proof hash differs')
        proof_info.update(saved_actual_proof_sha256=proof_sha,saved_actual_proof_bytes=len(proof_raw),saved_actual_proof_read=True)
    for name,pin in source_pins.items():need(sha(read(READY/name,64*1024))==pin,'Converter/test changed during review')
    for name,(path,pin)in deps.items():need(sha(read(path,256*1024))==pin,'Dependency changed during review')
    need(sha(read(READY/'code-test-freeze-v2.json',64*1024))==freeze_sha and sha(read(WORK/'legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json',64*1024))==BASELINE_SHA,'Proof receipts changed during review')
    return {'format':'strict-source-limited-legacy-MapInfo-framing-independent-review-v1','code_test_freeze_sha256':freeze_sha,'reviewed_source_sha256s':source_pins,'native_dependency_sha256s':{k:v[1]for k,v in deps.items()},'baseline_span_report_sha256':BASELINE_SHA,'admission_review':{'exact_source_member_digests':3,'exact_source_record_spans':16,'all_rows_match_hash_pinned_saved_baseline':True,'only_explicit_profile_admitted':True,'all_old_counts_must_be_zero':True},'focused_synthetic_tests':{'run':result.testsRun,'passed':result.testsRun,'skipped':0},'additional_independent_synthetic_checks':{'six_records_each_start_alignment_0_through7_match_physical_splice_and_whole_inverse':len(independent)==8,'seven_record_case_rejected':True,'wrong_target_length_rejected_before_target_hash':True,'admission_patch_and_shared_budgets_restored':True},'code_review':{'all191_current_schema_records_unchanged_except_declared_legacy_bounds':'PASS','same_all32_named_values_types_and_adjusted_spans':'PASS','all_non_count_wire_tokens_unchanged':'PASS','prefix_interrecord_suffix_physical_bits_preserved':'PASS','24_added_zero_bits_per_record_byte_phase_preserved':'PASS','whole_member_inverse':'PASS','private_repr_and_safe_aggregate_report':'PASS','no_current_ClientInfo_values_or_other_default_bits_inserted':'PASS'},'actual_proof_scope':proof_info,'material_findings':[],'resolved_findings':[{'finding':'Inverse verification hashed caller-supplied converted bytes before exact-size/cap checks','resolution':'Fail-fast type/exact-length/cap check before SHA, confirmed with independent synthetic hash-call sentinel','historical_conversion_semantics_affected':False}],'explicit_read_accounting':dict(counts),'limits':['This review opens only source/schema/test/saved metadata files; no replay/header/PE/dump/network/client access or repository edits.','The actual16 historical records are not reread or independently converted here; any saved producer proof is a separate validation scope.','The7-bit source count is a data-specific structural interpretation with exact member admission, not an authenticated historical native schema or proof of legacy permission semantics.','No whole-replay, oldClientInfo or deterministic-simulation compatibility is established.']}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--freeze-sha',required=True);ap.add_argument('--tests',type=int,required=True);ap.add_argument('--actual-proof');ap.add_argument('--actual-sha');a=ap.parse_args()
    need(bool(a.actual_proof)==bool(a.actual_sha),'Both actual proof arguments required')
    output=HERE/'legacy-mapinfo-framing-independent-review.json';need(not output.exists(),'Refuse review overwrite')
    data=review(a.freeze_sha,a.tests,a.actual_proof,a.actual_sha);data['reviewer_source_sha256']=sha(read(Path(__file__),64*1024))
    raw=(json.dumps(data,sort_keys=True,indent=2)+'\n').encode();need(len(raw)<=32*1024,'Review report bound exceeded')
    with output.open('xb')as stream:stream.write(raw)
    print(json.dumps({'review':'PASS','focused_tests':a.tests,'extra_synthetic_alignment_cases':8,'raw_input_reads':0,'bytes':len(raw),'sha256':sha(raw)}))
