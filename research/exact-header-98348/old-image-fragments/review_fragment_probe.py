"""Static/synthetic/saved-proof review only. Never open a real dump or fragment."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import unittest

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
READY=WORK/'legacy41810-fragment-probe'
PINS={
    'old41810-fragment-frozen-receipt.json':'a0756e24b4954c3640a5e3e8cbe7ee6771b46c3cbd4a0afffc7616014cd443ec',
    'probe_approved_image_fragments.py':'d2ce992a468030e02ef6c0e5640704470a328751aac21a4255405dc18c70319d',
    'test_approved_image_fragments.py':'8bcc81abe649d07226846a24c858650e9115a8672638f80e47d0065dacbe0ac1',
    'old41810-approved-image-fragment-BSN-probe.json':'8ede290703328baa956a64568075e9ae3cbebc1acc5dff2ab278219780a0c425',
}
PRIOR='a40cde35e02707ff2c484dcc98b2bafa4a86bd30eae1ddf2d6b6fc98f7fb85ea'
DESCRIPTORS='86fdb4c998ee393a56fa9165af16d472438aee7eb3221610a3eededa366ad27f'
ALLOWED=((0x02036E40,1032),(0x020399E0,4))
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def require(value):
    if not value:raise ValueError('Independent frozen fragment review differs')

def read(path):
    require(path.suffix in ('.py','.json') and not path.is_symlink())
    with path.open('rb') as stream:
        a=os.fstat(stream.fileno());require(stat.S_ISREG(a.st_mode) and 0<a.st_size<=64*1024)
        raw=stream.read(64*1024+1);b=os.fstat(stream.fileno())
    require(len(raw)==a.st_size and (a.st_size,a.st_mtime_ns)==(b.st_size,b.st_mtime_ns))
    return raw

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def review():
    raw={name:read(READY/name) for name in PINS}
    require(all(sha(raw[name])==pin for name,pin in PINS.items()))
    manifest=json.loads(raw['old41810-fragment-frozen-receipt.json'])
    for entry in manifest['allowlisted_files']:
        require((len(raw[entry['name']]),sha(raw[entry['name']]))==(entry['bytes'],entry['sha256']))
    saved=json.loads(raw['old41810-approved-image-fragment-BSN-probe.json'])
    require(saved['producer_sha256']==PINS['probe_approved_image_fragments.py'])
    prior_raw=read(WORK/'legacy41810-crash-metadata/five-preserved41810-module-metadata.json')
    descriptor_raw=read(WORK/'legacy41810-image-range-feasibility/old41810-image-capture-descriptor-feasibility.json')
    require(sha(prior_raw)==PRIOR and sha(descriptor_raw)==DESCRIPTORS)
    prior=json.loads(prior_raw);descriptors=json.loads(descriptor_raw)
    require(saved['case_count']==prior['case_count']==descriptors['case_count']==len(saved['cases'])==5)
    metadata_bytes=0;dump_bytes=0
    for case,old,desc in zip(saved['cases'],prior['cases'],descriptors['cases']):
        require(case['case_id']==old['case_id']==desc['case_id'])
        require(case['dump_sha256_before_and_after']==old['dump']['sha256_before']==old['dump']['sha256_after']==desc['dump_SHA256_before']==desc['dump_SHA256_after'])
        require(case['dump_bytes']==old['dump']['bytes']==desc['dump_bytes'])
        require(case['header_module_fixed_versions_RSDS_and_descriptors_revalidated'] and case['selected_pointed_image_bytes']==1036)
        require(tuple((r['image_relative_start'],r['bytes']) for r in case['fragments'])==ALLOWED)
        require(tuple((r['image_relative_start'],r['byte_count']) for r in desc['image_intersections'])==ALLOWED)
        for fragment in case['fragments']:
            require(set(fragment)=={'bytes','image_relative_start','probe','sha256'})
            probe=fragment['probe']
            require(probe['selected_bytes']==fragment['bytes'] and probe['constructor_shape_header_candidates']==probe['header_candidates_requiring_uncaptured_bytes']==probe['complete_type_grammar_candidate_count']==0 and probe['complete_type_grammar_candidates']==[])
        metadata_bytes+=32+12*old['dump']['directory_stream_count']+4+108+24+4+16*desc['memory_range_count']
        dump_bytes+=case['dump_bytes']
    expected={'opaque_full_file_hash_bytes':2*dump_bytes,'pinned_receipt_bytes':len(prior_raw)+len(descriptor_raw),'selected_metadata_bytes':metadata_bytes,'selected_pointed_image_bytes':5*1036}
    require(saved['read_counts']==expected and manifest['successful_run_read_counts']==expected)
    require(expected=={'opaque_full_file_hash_bytes':2259526,'pinned_receipt_bytes':27052,'selected_metadata_bytes':10988,'selected_pointed_image_bytes':5180})
    for index,row in enumerate(saved['cross_case_fragment_reproducibility']):
        counter=Counter(case['fragments'][index]['sha256'] for case in saved['cases'])
        equal=sum(n*(n-1)//2 for n in counter.values())
        require((row['image_relative_start'],row['bytes'])==ALLOWED[index])
        require((row['exact_equal_case_pairs'],row['different_case_pairs'],row['distinct_fragment_SHA256_count'])==(equal,10-equal,len(counter)))
        require(0<=row['different_byte_count_min']<=row['different_byte_count_max']<=row['bytes'])
    require(saved['complete_constructor_type_grammar_candidates']==0 and saved['all_five_dump_hashes_unchanged'])
    for key in ('fragment_strings_addresses_or_pointers_decoded_or_emitted','other_pointed_memory_heap_stack_thread_or_custom_data_read_or_decoded','static_code_data_or_PE_section_classification_performed','raw_dump_or_fragment_bytes_exported','discontinuous_fragments_concatenated_as_a_schema','game_process_debugger_or_native_code_loaded','network_or_repo_cloud_writes'):
        require(saved[key] is False)
    sys.dont_write_bytecode=True
    module=load('probe_approved_image_fragments',READY/'probe_approved_image_fragments.py')
    require(module.ALLOWED==ALLOWED)
    tests=load('_independent_approved_fragment_tests',READY/'test_approved_image_fragments.py')
    result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    require(result.testsRun==13 and result.wasSuccessful() and not result.skipped)
    require(all(sha(read(READY/name))==pin for name,pin in PINS.items()))
    return {'format':'old41810-fragment-static-independent-review-v1','producer_sha256':sha(read(Path(__file__))),
        'reviewed_file_sha256s':PINS,'prior_module_receipt_sha256':PRIOR,'prior_descriptor_receipt_sha256':DESCRIPTORS,
        'synthetic_tests':13,'failures':0,'errors':0,'skips':0,
        'saved_actual_cases':5,'saved_exact_approved_image_bytes_per_case':1036,'saved_total_selected_image_bytes':5180,
        'saved_source_pins_case_bindings_and_read_accounting_recomputed':True,
        'saved_complete_type_grammar_candidates':0,
        'reviewed_guards':['Opaque full-file hash before and after each bounded run', 'Exact authenticated old module/version/24-byte RSDS and descriptor identity', 'Only two wholly-module approved RVA/length pairs can reach the selected read callback', 'Single-case1036-byte and aggregate64KiB selected metadata limits', 'No string reads, pointer traversal, thread/custom/heap/stack decoding or fragment concatenation', 'Complete constructor geometry/type grammar is required; partial candidates are not promoted'],
        'remaining_material_findings':[],
        'real_dumps_or_pointed_memory_reopened_in_this_review':False,
        'actual_producer_analyze_called_in_this_review':False,
        'network_client_debugger_repo_or_cloud_used':False,
        'private_memory_bytes_strings_pointer_or_module_values_emitted':False,
        'limits':['This is a source, synthetic-test and saved-proof review. The five real dump hashes or selected memory bytes were not reread.', 'Zero candidates is limited to the two captured ranges and heuristic constructor-version window1..16.', 'No section/code/data classification, complete historical schema, historical ClientInfo width or serialization conversion is established.']}

if __name__=='__main__':
    output=HERE/'old41810-fragment-independent-review.json'
    raw=(json.dumps(review(),indent=2,sort_keys=True)+'\n').encode()
    require(len(raw)<=64*1024)
    with output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'bytes':len(raw),'sha256':sha(raw)}))
