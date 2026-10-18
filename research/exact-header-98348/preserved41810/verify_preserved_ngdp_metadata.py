"""Independent offline RAM reproduction of only fifteen public NGDP/build inputs."""
import collections
import hashlib
import json
import os
import runpy
import socket
import sys
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
WORK=HERE.parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO)]
from collection_license_audit import _read,write_new_report

SOURCE=WORK/'inspect_legacy41810_ngdp.py'
RESULT=WORK/'legacy41810-ngdp-metadata/preserved41810-NGDP-build-metadata.json'
SOURCE_SHA='1124bec56be4e7249180752cf96992f1499124eeb88f72be05b021b802d06266'
RESULT_SHA='35901fd7f0d3ea774fedabe8e9f76cc13b1d788001c18f5bf0a7d1675b3131e0'
BASE=Path('C:/Users/andrz/OneDrive/Dokumenty/Heroes of the Storm/GameLogs')
ROOT='83d43a8647bb5ca5caa6f2f09064da55'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
    source_raw=_read(SOURCE,32768);frozen_raw=_read(RESULT,131072)
    assert sha(source_raw)==SOURCE_SHA and sha(frozen_raw)==RESULT_SHA
    folders=sorted(p for p in BASE.iterdir() if p.is_dir() and 'B41810 Error' in p.name)
    assert len(folders)==5 and all(not p.is_symlink() for p in folders)
    paths=[];folder_paths=[]
    for folder in folders:
        members=[folder/'.build.info',*sorted(folder.glob('* NGDP.txt')),*sorted(folder.glob('*NGDPTrace.txt'))]
        assert len(members)==3
        assert [('.build.info' if p.name=='.build.info' else 'trace' if p.name.endswith('NGDPTrace.txt') else 'NGDP') for p in members]==['.build.info','NGDP','trace']
        assert all(not p.is_symlink() and p.resolve().is_relative_to(BASE.resolve()) for p in members)
        folder_paths.append(members);paths.extend(members)
    assert len(set(paths))==15 and sum(p.stat().st_size for p in paths)==13364
    allowed=set(paths)|{SOURCE}
    data={};captures=[];counters={'network_attempts':0,'write_open_attempts':0}
    original_read=Path.read_bytes;original_open=Path.open
    def checked_open(path,mode='r',*args,**kwargs):
        if any(c in mode for c in 'wax+'):
            counters['write_open_attempts']+=1
            raise RuntimeError('Review disallows producer writes')
        return original_open(path,mode,*args,**kwargs)
    def checked_read(path):
        assert path in allowed and not path.is_symlink(), 'Read escaped the exact metadata/source allowlist'
        with original_open(path,'rb') as f:
            before=os.fstat(f.fileno());assert before.st_size<=32768
            raw=f.read(32769);after=os.fstat(f.fileno())
        assert len(raw)==before.st_size<=32768 and before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
        if path in data:assert data[path]==raw
        data[path]=raw;captures.append((path,len(raw),sha(raw)))
        return raw
    def block_network(*args,**kwargs):
        counters['network_attempts']+=1
        raise RuntimeError('Review disallows network')
    patches=[(socket,'create_connection',socket.create_connection),(socket,'getaddrinfo',socket.getaddrinfo),
             (socket.socket,'connect',socket.socket.connect),(socket.socket,'connect_ex',socket.socket.connect_ex)]
    try:
        for obj,key,_ in patches:setattr(obj,key,block_network)
        Path.read_bytes=checked_read;Path.open=checked_open
        namespace=runpy.run_path(str(SOURCE),run_name='independent_metadata_review_import')
        fresh=namespace['analyze']()
    finally:
        Path.read_bytes=original_read;Path.open=original_open
        for obj,key,previous in patches:setattr(obj,key,previous)
    assert counters=={'network_attempts':0,'write_open_attempts':0}
    reads=collections.Counter(path for path,_,_ in captures)
    assert reads[SOURCE]==1 and all(reads[path]==2 for path in paths) and len(reads)==16
    assert sum(size for path,size,_ in captures if path!=SOURCE)==26728
    frozen=json.loads(frozen_raw)
    assert fresh==frozen
    encoded=(json.dumps(fresh,indent=2,sort_keys=True)+'\n').encode()
    assert encoded==frozen_raw
    # Independently inspect the captured manifest bytes; no second raw-input pass.
    manifest_rows=[];observed_sha=[];literal_hits=0
    public_keys={'Build Key','CDN Key','Build Id','Version','Product','Active','Branch'}
    for number,members in enumerate(folder_paths,1):
        manifest=data[members[0]];observed_sha.append(sha(manifest))
        lines=manifest.decode('utf-8-sig').splitlines()
        columns=[x.partition('!')[0] for x in lines[0].split('|')]
        rows=[]
        for line in lines[1:]:
            if not line:continue
            values=line.split('|');assert len(values)==len(columns)
            rows.append({key:value for key,value in zip(columns,values) if key in public_keys})
        assert rows==[{'Active':'1','Branch':'eu','Build Key':'0534650161f366f2f048320d85b32893',
                       'CDN Key':'c53d29ee65044954474c758516b15ab4','Version':'2.55.3.88481'}]
        manifest_rows.append({'id':'crash41810-'+str(number).zfill(2),'public_build_fields':rows,
                              'build_manifest_sha256':sha(manifest)})
        for path in members:
            raw=data[path];literal_hits+=ROOT.encode() in raw.lower()
    assert set(observed_sha)=={'9b99aaae34342d18704c29d7021f3b84f87b874f7784e9c6a3b10e353f043f2b'}
    assert literal_hits==0
    for folder in fresh['folders']:
        assert len(folder['files'])==3
        assert all(not x['literal_original_replay_root_occurs'] and x['source_unchanged'] for x in folder['files'])
        assert all(not x['public_labeled_build_hashes'] for x in folder['files'] if x['kind']!='build_manifest')
    assert fresh['Variables_Error_text_or_minidump_memory_read'] is False
    assert fresh['distinct_input_files']==15 and fresh['distinct_input_bytes']==13364 and fresh['explicit_input_reads_bytes']==26728
    assert sha(_read(SOURCE,32768))==SOURCE_SHA and sha(_read(RESULT,131072))==RESULT_SHA
    # Bound exact root attribution to the already independently verified source header.
    old_review=WORK/'legacy-build-root-independent-review/legacy-build-root-independent-review.json'
    old_review_raw=_read(old_review,131072)
    assert sha(old_review_raw)=='d078024b051ea1c2b9fcb381c4307ea5987c74b7a9c0405de4405bebb00991c3'
    assert json.loads(old_review_raw)['fresh_original_header']['root']==ROOT
    report={'format':'hots-preserved41810-NGDP-metadata-independent-review-v1','result':'PASS','material_findings':[],
        'review_source_sha256':sha(_read(Path(__file__),32768)),
        'producer_source_sha256':SOURCE_SHA,'frozen_report_sha256':RESULT_SHA,
        'fresh_report_JSON_matches_frozen':True,'fresh_serialized_report_bytes_match_frozen':True,
        'producer_analyze_called_in_RAM_only':True,'producer_main_or_output_directory_creation_invoked':False,
        'bounded_read_capture':{'exact_public_metadata_files':15,'folders':5,'distinct_input_bytes':13364,
             'metadata_read_calls':30,'metadata_bytes_read':26728,'producer_source_hash_read_calls':1,
             'maximum_file_bytes':32768,'source_input_paths_reported':False,'other_content_files_read':0,
             'Variables_Error_text_minidump_or_other_memory_content_reads':0},
        'fresh_manifest_public_projections':manifest_rows,
        'all_five_manifests_byte_identical':True,
        'literal_original_root':ROOT,'literal_original_root_occurrences_in_15_UTF8_inputs':0,
        'root_attribution_review_sha256':sha(old_review_raw),
        'weak_build_line_label_extractor':{'timestamp_prefixes_are_not_metadata_field_names':True,
             'empty_public_labeled_build_hashes_does_not_mean_all_metadata_absent':True,
             'not_promoted_to_evidence_of_old_BuildConfig_absence':True},
        'scope_of_conclusion':'Five preserved .build.info files report88481 identities; no exact41810 BuildConfig attribution is established by these metadata files.',
        'actual_loaded_dump_module_build_proof':'separate investigation; no dump was read in this review',
        'all_reviewed_source_and_report_bytes_unchanged':True,'unexpected_network_attempts':0,'producer_write_attempts':0,
        'client_launched':False,'repo_modified':False,'raw_log_or_manifest_bodies_exported':False,
        'limitations':['These fifteen allowlisted public metadata files do not exhaust other crash-folder contents or historical metadata sources.',
             'Only literal case-insensitive32hex root text absence is established; no alternate encoding or other identity representation is excluded.',
             'The weak timestamp-prefix label extraction is retained as executed, not treated as a meaningful schema or absence result.',
             'Folder names alone do not authenticate module build or original content; metadata88481 does not prove which data the old executable loaded.']}
    output=HERE/'legacy41810-ngdp-independent-review.json'
    write_new_report(report,output)
    print(json.dumps({'result':'PASS','exact_metadata_files':15,'RAM_JSON_exact':True,'report_sha256':sha(_read(output,131072))}))
    data.clear()

if __name__=='__main__':main()
