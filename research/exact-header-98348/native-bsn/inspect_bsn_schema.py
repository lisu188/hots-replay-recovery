"""Read-only, one-pass, hash-bound current-PE BSN metadata research."""
import hashlib
import importlib.util
import json
import os
import struct
from collections import Counter
from pathlib import Path
from parse_bsn_metadata import Protocol

HERE=Path(__file__).resolve().parent
BASE=43169040
END=43560673
EXPECTED='efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
BLOB_SHA='ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
SELECTED=('Battlenet::S2Map::BnetHeader','Battlenet::Client::S2Game::EncodedGameDataHeader','Battlenet::Client::S2GameDefines::ClientLicensesList','Battlenet::Client::S2GameDefines::ClientLicenses','Battlenet::Client::S2GameDefines::ClientInfo','Battlenet::S2Game::SharedPlayerInfo','Battlenet::S2Game::SharedPlayerInfo::InfoHero','Battlenet::Client::ComSat::TalkerInfo','Battlenet::Client::ComSat::TalkerId::Id','Battlenet::Profile::RecordAddress','Battlenet::Permission::Handle','Battlenet::S2Map::ResourceAccessListBits','Battlenet::License::Id')

def chain(p,i):
    result=[];seen=set()
    while i not in seen:
        seen.add(i);r=p.records[i]
        item={k:r[k] for k in ('id','offset','bytes','header','kind','name','bounds') if k in r}
        item['PE_file_offset']=BASE+r['offset'];item['PE_rva']=BASE+r['offset']+4096
        result.append(item)
        if r['kind'] not in ('USER','OPTIONAL','ARRAY'):break
        i=r['element_type']
    return result

def selected(p,name):
    ids=p.by_name.get(name,[])
    if len(ids)!=1:raise ValueError('Selected native name is not unique')
    r=p.records[ids[0]];result={'type':chain(p,ids[0])}
    if 'field_types' in r:
        result['members']=[{'name':n,'tag':t,'type_chain':chain(p,c)} for n,t,c in zip(r['field_names'],r['tags'],r['field_types'])]
    return result

def analyze(raw):
    if type(raw) is not bytes or len(raw)!=53573840 or sha(raw)!=EXPECTED:raise ValueError('Pinned current PE differs')
    blob=raw[BASE:END]
    if sha(blob)!=BLOB_SHA:raise ValueError('Pinned embedded blob differs')
    p=Protocol(blob)
    if (p.version,p.unknown,p.count,p.type_size,p.dump_size)!=(7,0,8330,67244,257729):raise ValueError('Actual framing differs')
    if p.name_start!=194764 or len(p.name_starts)!=6937:raise ValueError('Actual name-pool boundary differs')
    files={name:sha((HERE/name).read_bytes()) for name in ('parse_bsn_metadata.py','inspect_bsn_schema.py','test_parse_bsn_metadata.py')}
    report={'format':'hots-current-native-BSN-metadata-v1','source_PE_bytes':len(raw),'source_PE_sha256':EXPECTED,
        'source_hashes':files,'game_code_executed_or_loaded':False,'network_requests':0,'raw_binary_or_full_schema_dump_saved':False,
        'container':{'PE_file_offset':BASE,'PE_rva':BASE+4096,'end_exclusive':END,'bytes':len(blob),'sha256':sha(blob),
            'version':p.version,'second_header_word_uninterpreted':p.unknown,'type_count':p.count,'type_info_bytes':p.type_size,'dump_info_bytes':p.dump_size,
            'type_offsets_start':BASE+20,'type_info_start':BASE+p.type_start,'dump_offsets_start':BASE+p.dump_offsets,'dump_info_start':BASE+p.dump_start,
            'all_8330_type_offsets_ordered_unique_in_section':True,'all_8330_dump_offsets_in_section':True,
            'all_8330_type_records_and_child_type_references_validated':True,'last_type_record_alignment_zero_bytes':p.records[-1].get('trailing_zero_alignment_bytes',0),
            'all_15215_dump_words_null_or_true_name_token_start':True,'dump_words':len(p.dump_words),'dump_zero_words':sum(x==0 for x in p.dump_words),
            'DumpString_lookup_count':p.name_reference_count,'unique_complete_static_names':len(p.name_starts),'name_pool_start':BASE+p.name_start,
            'following_alignment_zero_bytes':3,'following_alignment_matches':raw[END:END+3]==b'\0'*3},
        'meta_type_counts':dict(sorted(Counter(r['kind'] for r in p.records).items())),
        'header_bit6_counts_uninterpreted':dict(Counter(str(bool(r['header']&64)) for r in p.records)),
        'selected_native_type_projections':{name:selected(p,name) for name in SELECTED},
        'conditional_198_boundary_hypothesis':{'requires_actual_replay_binding':True,'TalkerInfo_invalid_choice_then_next_fields_bits':[8,64,32,64,31],
            'sum_bits':199,'legacy_auditer_consumes_one_of_these_bits_as_secondary_present_before_198':True},
        'limits':['Cross-game primary source suggested the grammar; actual current record/name/reference validation supplies local evidence.',
            'DumpString index0/type-name and subsequent member names are an observed current convention validated by selected known header fields.',
            'Header bit6 and separate native codeInfo/member memory offsets are uninterpreted.',
            'This report alone does not bind named fields to replay player bits or ownership semantics.']}
    return report,p

def load_current_PE():
    path=Path(r'C:\Program Files (x86)\Heroes of the Storm\Versions\Base98348\HeroesOfTheStorm_x64.exe')
    if path.is_symlink():raise ValueError('PE symlink refused')
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno())
        if before.st_size!=53573840:raise ValueError('PE size differs')
        raw=stream.read(512*1024*1024+1);after=os.fstat(stream.fileno())
    if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns:raise ValueError('PE changed during read')
    return raw

def write_new(path,report):
    data=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    if len(data)>256*1024:raise ValueError('Compact report cap exceeded')
    if path.is_symlink():raise ValueError('Output symlink refused')
    with path.open('xb') as stream:stream.write(data)
    return len(data),sha(data)

if __name__=='__main__':
    report,_=analyze(load_current_PE());print(write_new(HERE/'native-BSN-metadata-98348.json',report))
