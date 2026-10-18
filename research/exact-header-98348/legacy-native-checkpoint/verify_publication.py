"""Verify this published checkpoint without opening private inputs or networking.

The research producers remain byte-exact historical scratch snapshots. This
portable verifier checks the published hashes, saved-proof gates, canonical
public Git trees and optionally the 31 self-contained synthetic tests only.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
import io
import unittest
from pathlib import Path, PurePosixPath
import subprocess
import sys

PREFIX='observations/exact-header-98348/'
RESEARCH='research/exact-header-98348/'
sha=lambda b:hashlib.sha256(b).hexdigest()

def require(value):
    if not value: raise ValueError('Published checkpoint validation failed')

def bounded(root,relative):
    p=PurePosixPath(relative)
    require(not p.is_absolute() and '..' not in p.parts and '\\' not in relative)
    require(relative.startswith((PREFIX,RESEARCH)))
    path=root.joinpath(*p.parts)
    require(not path.is_symlink() and path.is_file() and path.stat().st_size<=512*1024)
    require(path.resolve().is_relative_to(root.resolve()))
    raw=path.read_bytes();require(len(raw)<=512*1024)
    return raw

def verify(root,run_tests=False):
    binding=json.loads(bounded(root,PREFIX+'legacy-native-checkpoint/publication-bindings.json'))
    require(binding['format']=='legacy-native-research-publication-bindings-v1')
    rows=binding['files'];require(1<=len(rows)<=40)
    require(len({r['target'] for r in rows})==len(rows))
    total=0
    for row in rows:
        raw=bounded(root,row['target']);total+=len(raw)
        require(len(raw)==row['bytes'] and sha(raw)==row['sha256'])
        require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob_sha1'])
        if row['target'].endswith('.py'):ast.parse(raw)
        elif row['target'].endswith('.json'):json.loads(raw)
        else:raise ValueError('Only source/JSON is allowed')
    require(total<=1024*1024)
    def j(lane,name):return json.loads(bounded(root,PREFIX+lane+'/'+name))
    f=j('old-image-fragments','old41810-approved-image-fragment-BSN-probe.json')
    require(f['case_count']==5 and f['all_five_dump_hashes_unchanged'] and f['complete_constructor_type_grammar_candidates']==0)
    require(not f['raw_dump_or_fragment_bytes_exported'] and not f['fragment_strings_addresses_or_pointers_decoded_or_emitted'])
    i=j('old-image-fragments','old41810-fragment-independent-review.json')
    require(i['synthetic_tests']==13 and i['remaining_material_findings']==[] and not i['real_dumps_or_pointed_memory_reopened_in_this_review'])
    h=j('historical-fixture-screen','htc-20-unique-fixture-header-observation.json');a=h['aggregate']
    require((a['strict206_prefixes_acquired'],a['header_decode_successes'],a['application_body_bytes_read'],a['exact41810_candidates'])==(20,20,81920,0))
    require(h['full_replay_acquisitions']==0 and not h['raw_prefixes_or_players_or_messages_saved'])
    source=root/RESEARCH/'historical-fixture-screen/inspect_htc_fixture_headers.py'
    spec=importlib.util.spec_from_file_location('published_htc_header_probe',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=j('historical-fixture-screen','source-binding.json')
    require(module.canonical_trees(tree['tree'],tree['tree_sha'])==24)
    old=j('legacy-client-constraints','legacy-client-layout-constraints.json')
    require(not old['old_ClientInfo_schema_authenticated'] and not old['old_to_current_conversion_rule_established'])
    require(old['original_R8_candidate_slices_identical_in_order'])
    require(len(old['results'])==2)
    for r in old['results']:
        require(r['players']==10 and r['candidate7_all_175bit_boundaries_exact'] and r['candidate31_permission_payload_exceeds_remaining_member_records']==10 and r['required_private_crosschecks_passed'])
    control=j('39445-control','39445-core-and-unchanged-tail-observation.json')
    require(control['actual_header_version']['m_build']==39445 and control['original_R8_before_after_guards_pass'])
    require(all(control['results'][s]['binary_roundtrip'] for s in ('header','details','initData','game','message','tracker')))
    require(control['results']['battlelobby']['status']=='failed')
    d=j('39445-control','39445-schema1-player-diagnostic-v2.json')
    require(d['result']['full_schema1_EOF_and_member_reencoding_exact'] and d['result']['required_private_identity_seed_gates_passed'])
    require(d['result']['players']==10 and not d['unchanged_historical_tail_failure_superseded'] and not d['old41810_schema_or_conversion_rule_proven'])
    n=j('native-namespace','native-formal-namespace-exposure-assessment.json')
    require(n['all_input_header_and_replay_digests_unchanged'] and len(n['known_exact_US_header_positive_controls'])==5)
    require(n['observed_prefix']['definition_count']==87 and n['observed_prefix']['definition_pairs_not_in_five_exact_headers']==0)
    require(not n['DataMod']['actual_US_DataMod_namespace_directly_bound'] and n['DataMod']['actual_US_definition_rows_attributed_to_DataMod'] is None)
    require(not n['candidate_header_created_or_scalar_chosen'] and not n['namespace_account_creator_values_digests_or_additive_offsets_emitted'])
    tests=0
    if run_tests:
        for lane,name,count in (('old-image-fragments','test_approved_image_fragments',13),('native-namespace','test_formal_namespace_carriers',10)):
            subprocess.run([sys.executable,'-B','-m','unittest','-q',name],cwd=root/RESEARCH/lane,check=True)
            tests+=count
        # These eight HTC transport cases need mocks only. The two historical
        # fixtures() tests require the excluded private API-cache body. Their
        # earlier scratch result stays separate; the public canonical trees
        # have already been checked directly above without that dependency.
        sys.modules['inspect_htc_fixture_headers']=module
        ts=importlib.util.spec_from_file_location('published_htc_tests',source.parent/'test_inspect_htc_fixture_headers.py')
        tm=importlib.util.module_from_spec(ts);ts.loader.exec_module(tm)
        names=unittest.defaultTestLoader.getTestCaseNames(tm.ProbeTests)
        excluded={'test_actual_metadata_all20_and24canonical_trees','test_canonical_tree_negative_control'}
        require(excluded.issubset(names))
        suite=unittest.TestSuite(tm.ProbeTests(name) for name in names if name not in excluded)
        require(suite.countTestCases()==8)
        result=unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        require(result.testsRun==8 and result.wasSuccessful() and not result.skipped)
        tests+=result.testsRun
    return {'format':'legacy-native-publication-verification-v1','published_files_checked':len(rows),'published_bytes_checked':total,'canonical_Git_trees_recomputed':24,'focused_synthetic_tests_run':tests,'historical_context_tests_not_repeated_in_relocated_run':2 if run_tests else 0,'private_inputs_opened':False,'actual_producers_rerun':False,'network_or_client_used':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--tests',action='store_true');args=p.parse_args()
    print(json.dumps(verify(args.repo,args.tests),sort_keys=True))
