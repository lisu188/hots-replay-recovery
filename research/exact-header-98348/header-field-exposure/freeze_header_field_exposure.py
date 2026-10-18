"""Offline allowlist freeze; no PE, replay, header body or network is opened."""
import json
from pathlib import Path
import review_header_field_exposure as review

HERE=Path(__file__).resolve().parent
FILES=('project_header_field_graph.py','native-header-mapinfo-selected-graph.json',
       'review_header_field_exposure.py','test_header_field_exposure.py',
       'native-mapinfo-header-field-exposure-v2.json','freeze_header_field_exposure.py')

def freeze():
    raw={name:review.read(HERE/name) for name in FILES}
    report=json.loads(raw['native-mapinfo-header-field-exposure-v2.json'])
    review.require(report['producer_sha256']==review.sha(raw['review_header_field_exposure.py']))
    review.require(report['native_selected_graph_sha256']==review.sha(raw['native-header-mapinfo-selected-graph.json'])==review.GRAPH_SHA)
    review.require(report['aggregate']['exact_common_named_field_comparisons']==75 and report['aggregate']['exact_common_variant_field_comparisons']==45 and report['aggregate']['wrong_module_handle_negative_comparisons']==25)
    review.require(report['selected_MapInfo_schema_comparison']['all191_complete_record_dictionaries_exact'] and report['selected_MapInfo_schema_comparison']['ordered32_root_fields_exact'])
    review.require(report['EU_DataMod_exposed_retained_fields_exact']==12 and report['EU_DataMod_exposed_common_variant_fields_exact']==9 and report['unexposed_retained_field_group_count_including_namespace']==18 and not report['old_recipe_fully_authenticated_except_namespace'])
    return {'format':'native-header-field-exposure-frozen-receipt-v1',
        'allowlisted_files':[{'file':name,'bytes':len(body),'sha256':review.sha(body)} for name,body in raw.items()],
        'validation':{'focused_synthetic_tests_executed':14,'failures':0,'errors':0,'skips':0,
            'selected_MapInfo_records_compared_exact':191,'named_root_fields':32,'known_complete_US_headers':5,
            'native_MapInfo_records_independently_walked_in_this_comparison':6,
            'direct_named_value_matches':75,'common_variant_value_matches':45,'wrong_module_identity_negative_controls':25,
            'target_exposed_retained_fields_exact':12,'target_common_variant_fields_exact':9,'unexposed_retained_groups_including_namespace':18},
        'actual21case136record_owner_receipt_sha256':review.MAPINFO_PROOF,
        'matched_selected_schema_sha256':review.MAPINFO_SCHEMA,
        'source_experiment_PE_read_passes':1,'comparison_stage_PE_read_passes':0,
        'raw_candidate_header_or_replay_written':False,
        'private_author_namespace_creator_player_literals_or_per_value_hashes_emitted':False,
        'root1_GameHeader_dummy_value_for_missing_target_claimed':False,
        'full_US_DataMod_header_recovered':False,
        'network_or_client_or_repo_cloud_writes':False,
        'excluded_historical_report':'native-mapinfo-header-field-exposure.json',
        'excluded_historical_report_reason':'Initial comparison result predates explicit per-field native type-link table. v2 retains identical75/45/25andtarget conclusions with final source binding.',
        'limits':['This is a named-field exposure assessment, not a new header-candidate experiment.',
            'Full unknown target metadata remains unproven beyond the directly compared fields.',
            'Outer root1 is authenticated as GameHeader with one BOOL named m_dummy; five known controls and the EUtemplate agree, but target value is not observed.',
            'No author/flag/namespace mapping is inferred from equal numbers or boolean coincidence.']}

if __name__=='__main__':
    output=HERE/'header-field-exposure-frozen-receipt.json'
    raw=(json.dumps(freeze(),indent=2,sort_keys=True)+'\n').encode()
    with output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'bytes':len(raw),'sha256':review.sha(raw)}))
