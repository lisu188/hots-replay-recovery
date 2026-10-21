"""Validate saved actual-proof pins/arithmetic; no raw input access/execution."""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent;WORK=BASE.parent;READY=WORK/'legacy-mapinfo-framing-ready'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
PINS={'verify_legacy_mapinfo_framing.py':'de0d47d8e17f641f1d43cc976df7e3291744171a8d915829ce86bff04899a0a8','legacy-MapInfo-framing-16-record-proof.json':'96557a661968afb1b459ec45eb01944681e7f3900c2c460d09eaa1c83c0b5db7','code-test-freeze-v2.json':'e2047698edcba6197806c39a673352e89cc1f746e73e7dd96e81d3dd30bd0886','legacy_mapinfo_framing.py':'087965405fa4c97e088b7581c9ffa4d7e384ad45535be859a6d09be10420e2b3'}
def need(ok,message):
    if not ok:raise ValueError(message)
def read(path,limit=64*1024):
    need(not path.is_symlink()and path.is_file()and 0<path.stat().st_size<=limit,'Source/metadata bounds differ')
    with path.open('rb')as stream:raw=stream.read(limit+1)
    need(len(raw)<=limit,'Source/metadata exceeded bound');return raw

def main():
    blobs={name:read(READY/name)for name in PINS}
    need(all(sha(blobs[name])==pin for name,pin in PINS.items()),'Saved producer/proof/source pin differs')
    baseline_raw=read(WORK/'legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json')
    need(sha(baseline_raw)=='de29dfe84d6906fda09768c7e545d8c1053e641e44d21372692b0f45d6529477','Baseline differs')
    baseline=json.loads(baseline_raw);proof=json.loads(blobs['legacy-MapInfo-framing-16-record-proof.json']);saved={c['id']:c for c in baseline['cases']}
    need(proof['producer_sha256']==PINS['verify_legacy_mapinfo_framing.py']and len(proof['cases'])==3,'Proof producer/cases differ')
    records=roots=fields=0
    for case in proof['cases']:
        old=saved[case['id']];summary=case['converter'];rows=case['records'];count=len(rows)
        need(case['source_member_sha256']==old['member_sha256']==summary['source_member_sha256']and case['replay_sha256']==old['replay_sha256'],'Saved actual source identity differs')
        need(case['actual_header_build']==old['actual_header_build']and count==old['baseline_entries']==summary['MapInfo_records'],'Saved actual build/count differs')
        need(summary['added_bits_per_record']==24 and summary['added_bytes']==3*count and summary['converted_member_bytes']==summary['source_member_bytes']+3*count,'Length arithmetic differs')
        need(summary['named_root_field_comparisons']==32*count,'Root comparison count differs')
        need(summary['inverse_whole_member_bytes_exact']and summary['all_non_count_tokens_and_outside_bits_exact']and summary['unchanged_current_native_32_field_destination_values_and_bounds_exact'],'Proof invariant missing')
        need(not summary['whole_replay_upgrade_or_historical_schema_authenticated']and not case['converted_member_saved'],'Overclaim/output scope differs')
        for index,(row,prior)in enumerate(zip(rows,old['entries'])):
            a,b=prior['baseline_start_bit'],prior['baseline_end_bit']
            need((row['source_start_bit'],row['source_end_bit'])==(a,b),'Saved source span differs')
            need((row['target_start_bit'],row['target_end_bit'])==(a+24*index,b+24*(index+1)),'Target shift differs')
            need(row['current_final_widths']==[1,31]and prior['derived_7bit_count_graph']['final_two_widths']==[1,7],'Current/derived framing width differs')
        records+=count;roots+=32*count;fields+=summary['all_native_field_comparisons']
    aggregate=proof['aggregate']
    need((records,roots,fields)==(16,512,3888),'Aggregate comparison arithmetic differs')
    need(aggregate['records']==records and aggregate['named_root_field_comparisons']==roots and aggregate['all_native_field_comparisons']==fields,'Stored aggregate differs')
    need(aggregate['inverse_whole_members_byte_exact']==3 and aggregate['converted_members_or_StormReplay_outputs_written']==0 and aggregate['distinct_replay_input_bytes']==3726042 and aggregate['replay_read_bytes_including_before_after_guards']==7452084,'Saved input/output accounting differs')
    for name,pin in PINS.items():need(sha(read(READY/name))==pin,'Saved source/proof changed after inspection')
    data={'format':'saved-sixteen-record-MapInfo-proof-independent-source-and-metadata-review-v1','reviewed_pins':PINS,'saved_proof_arithmetic':{'source_cases':3,'records':16,'named_root_field_comparisons':512,'all_native_field_comparisons':3888,'all_source_spans_and_shift_arithmetic_match_frozen_baseline':True},'producer_source_review':{'exact_source_archive_and_member_admission':True,'fresh_baseline_recomputed_before_conversion':True,'all_32_current_native_destination_fields_end_and_identity_checked':True,'outside_bits_and_whole_inverse_checked_by_reviewed_converter':True,'before_after_archive_source_guards':True,'private_converted_bodies_RAM_only':True,'no_whole_replay_or_old_native_schema_claim':True},'future_reproducer_note':'Producer pins HERE source but searches repo before HERE at import. The repository converter was absent in a contemporaneous metadata-only review check. Pin the loaded module before any future raw-input rerun if import locations evolve; current saved proof is not contradicted.','raw_replay_header_PE_dump_or_network_reads_in_this_review':0,'actual_16_records_independently_reconverted':False,'private_values_emitted':False,'material_current_conversion_findings':[],'review_source_sha256':sha(read(Path(__file__)))}
    encoded=(json.dumps(data,sort_keys=True,indent=2)+'\n').encode();out=BASE/'saved-16-record-proof-independent-review.json'
    with out.open('xb')as stream:stream.write(encoded)
    print(json.dumps({'file':out.name,'bytes':len(encoded),'sha256':sha(encoded),'raw_input_reads':0}))
if __name__=='__main__':main()
