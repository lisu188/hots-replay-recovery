"""Original41810 exact cached headers vs one explicitly derived MapInfo profile.

Current native names remain a historical hypothesis. No absent field defaults,
namespace/account/author literals, candidate headers or replay writes occur.
"""
from collections import Counter
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,os,stat,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;WORK=HERE.parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
ORIGINAL='e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
MEMBER='beea9c9b29a7f1a73806fe37b393f453c84a7faed8d6f89a5b4fcd25967f1f44'
GRAPH='56fa4fedd97e63737c2c575e63c728d9389d015243ff6acd25020c4d62834147'
HELPER='4a5a7b8483413ea40b49c1ce49d1fd78dd54649ccecaa7c04e9c090cc683dac0'
SHARED='e0abd0b674c97b87f6a1510edc08704eebeca0ad9d43ac0537d5eaaa3eb9b202'
LEGACY='de29dfe84d6906fda09768c7e545d8c1053e641e44d21372692b0f45d6529477'
HEADERS=('565fa52da08615e47c6105dc3036e925e80aa57d12b7bf5fd5c6757b12e7b5bd','593cb51398ea52786c53e9c86d8f4d217148d452a691b38ef67d2a0d3add2596','439eab2a4f3f7d224e5820486ab0cc161729f3de3d2d5ce2e80b35dc7eed3a88','b34d0f30dc3b9cf47694982106a04006a49ce43422e02f71ed18b33b7bfcc6c4','9bdcdbb192244902f650020fa302951b0fd1f5487aad0096df01ddccd7b4acd2')
sha=lambda b:hashlib.sha256(b).hexdigest()
def require(v,message='Bounded original-header evidence guard failed'):
    if not v:raise ValueError(message)
def read(path,limit):
    require(not path.is_symlink())
    with path.open('rb') as stream:
        a=os.fstat(stream.fileno());require(stat.S_ISREG(a.st_mode) and 0<a.st_size<=limit)
        raw=stream.read(limit+1);b=os.fstat(stream.fileno())
    require(len(raw)==a.st_size==b.st_size and a.st_mtime_ns==b.st_mtime_ns)
    return raw
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def resolve(records,index):
    seen=set()
    while records[index]['kind']=='USER':
        require(index not in seen);seen.add(index);index=records[index]['element_type']
    return records[index]

def named_node(records,node,index,names):
    numeric=['root']
    for name in names:
        r=resolve(records,index);require(r['kind']=='STRUCT' and node.tag==5)
        require(name in r['field_names']);at=r['field_names'].index(name);tag=r['tags'][at]
        items=dict(node.value);require(len(items)==len(node.value))
        if tag not in items:raise KeyError('Explicit named tag absent')
        node=items[tag];index=r['field_types'][at];numeric.append(str(tag))
    return node,index,'/'.join(numeric)

def struct_delta(records,node,index,path):
    r=resolve(records,index)
    if node.tag!=5:return {'path':path,'expected_wire_tag':5,'actual_wire_tag':node.tag}
    actual=dict(node.value);require(len(actual)==len(node.value))
    return {'path':path,'missing_current_tags':sorted(set(r['tags'])-set(actual)),'extra_historical_tags':sorted(set(actual)-set(r['tags']))}

class View:
    def __init__(self,decoder):self.fields=decoder.fields
    def field(self,path,kind=None):
        result=[f for f in self.fields if f.path==path and(kind is None or f.kind==kind)]
        require(result);return next((f for f in result if f.kind!='USER'),result[-1])

def exact_tokens(shared,raw,start,end,tokens):
    from battlelobby_attribute_layer import _Reader,_Writer
    writer=_Writer();writer.position=start//8*8;writer.raw=bytearray(raw[:start//8])
    if start%8:
        reader=_Reader(raw);reader.position=writer.position;writer.bits(reader.bits(start%8),start%8)
    for t in tokens:
        if t.width is None:writer.blob(t.value)
        else:writer.bits(t.value,t.width)
    require(writer.position==end)
    body=bytes(writer.raw[start//8:]);whole=end//8-start//8;remaining=end%8
    require(len(body)==(end+7)//8-start//8 and body[:whole]==raw[start//8:start//8+whole])
    require(not remaining or body[-1]==raw[end//8]&((1<<remaining)-1))
    return True

def analyze():
    source_paths=[Path(__file__),WORK/'current-header-field-exposure/review_header_field_exposure.py',WORK/'current-header-field-exposure/native-header-mapinfo-selected-graph.json',WORK/'native-client-codec-ready/native_clientinfo.py',WORK/'header-reconstruction/lossless_wire.py',WORK/'mod-metadata-publish-ready/depot_s2mh_wire.py',WORK/'legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json',WORK/'mod-package-handles-and-realms.json',REPO/'audit_battlelobby_mod_metadata.py',REPO/'battlelobby_attribute_layer.py',REPO/'mpq_reader.py',REPO/'mod_data_audit.py']
    pins={p.relative_to(WORK).as_posix() if p.is_relative_to(WORK) else 'repo/'+p.name:sha(read(p,256*1024)) for p in source_paths}
    for rel,expected in [('current-header-field-exposure/review_header_field_exposure.py',HELPER),('current-header-field-exposure/native-header-mapinfo-selected-graph.json',GRAPH),('native-client-codec-ready/native_clientinfo.py',SHARED),('legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json',LEGACY)]:require(pins[rel]==expected)
    sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
    helper=load('_original_header_named_fields',source_paths[1]);shared=load('_original_header_shared_scalar',source_paths[3]);wire=load('_original_header_lossless',source_paths[4]);generic=load('depot_s2mh_wire',source_paths[5])
    from audit_battlelobby_mod_metadata import audit_member
    from battlelobby_attribute_layer import _Reader
    from mod_data_audit import dependency_prefix
    from mpq_reader import MPQArchive
    from protocol_loader import load_protocol
    records={r['id']:r for r in json.loads(read(source_paths[2],256*1024))['records']}
    legacy=json.loads(read(source_paths[6],64*1024));old=next(c for c in legacy['cases']if c['id']=='original41810')
    manifest=next(c for c in json.loads(read(source_paths[7],128*1024))['results']if c['id']=='original41810')
    require(tuple(h['digest']for h in manifest['terminal_s2mh_handles'])==HEADERS and all(h['region']=='EU'for h in manifest['terminal_s2mh_handles']))
    modified=deepcopy(records);modified[1828]['bounds'].update(bits=7,max=127)
    require(records[1828]['bounds']['bits']==31 and len(records[5852]['field_names'])==32)
    replay=WORK/'TEN_GREYMANE_source_41810.StormReplay';source=read(replay,3*1024*1024);replay_reads=len(source);require(sha(source)==ORIGINAL)
    class Archive(MPQArchive):
        def __init__(self,body):self.file=BytesIO(body);self.header=self.read_header();self.hash_table=self.read_table('hash');self.block_table=self.read_table('block')
    archive=Archive(source)
    try:
        protocol=load_protocol(41810);require(protocol.recovery_schema_sha256=='879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd')
        header=protocol.decode_replay_header(archive.header['user_data_header']['content']);require(header['m_version']['m_build']==header['m_version']['m_baseBuild']==header['m_dataBuildNum']==41810 and header['m_ngdpRootKey']['m_data'].hex()=='83d43a8647bb5ca5caa6f2f09064da55')
        require(all(b.size<=8*1024*1024 for b in archive.block_table));raw=archive.read_file('replay.server.battlelobby');require(sha(raw)==MEMBER and len(raw)<=8*1024*1024)
    finally:archive.close()
    baseline=audit_member(raw,'legacy-10','historical-fixed');require(baseline['same_profile_full_member_roundtrip_exact']and len(baseline['entries'])==5)
    reader=_Reader(raw);reader.position=baseline['mod_metadata_end_bit'];terminal=[reader.blob(40)for _ in range(reader.bits(6))];require(reader.position==baseline['terminal_handles_end_bit']and [v[8:].hex()for v in terminal]==list(HEADERS))
    prefix=[bytes.fromhex(v)for v in dependency_prefix(raw)['handles']];require(len(prefix)==5 and [v[8:].hex()for v in prefix]==[v['digest']for v in manifest['dependency_prefix_handles']])
    infos=[]
    for entry,previous in zip(baseline['entries'],old['entries']):
        require(entry['start_bit']==previous['baseline_start_bit']and entry['end_bit']==previous['baseline_end_bit'])
        d=shared._Decoder(SimpleNamespace(records=modified),raw,entry['start_bit']);d.decode(5852);require(d.reader.position==entry['end_bit']);exact_tokens(shared,raw,entry['start_bit'],d.reader.position,d.tokens)
        value=helper.native_value(View(d),modified,5852);require(set(value)==set(records[5852]['field_names']));infos.append(value)
    out=[];rawreads=0;distinct=0;opened=0;guards=[]
    for index,digest in enumerate(HEADERS):
        path=WORK/'depot-headers/original-eu'/(digest+'.s2mh')
        if not path.exists():out.append({'index':index,'header_sha256':digest,'status':'exact_local_object_missing'});continue
        require(opened<6);body=read(path,256*1024);rawreads+=len(body);distinct+=len(body);opened+=1;require(rawreads+24685<=256*1024 and sha(body)==digest);guards.append((path,digest,len(body)))
        node=wire.parse(body);require(wire.encode(node)==body and wire.to_generic(node)==generic.decode_verified_header(body,digest))
        bnetnode,bnetid,_=named_node(records,node,4376,('m_bnet',))
        fullstatus='complete_current_named_graph_binds'
        try:helper.NamedVersioned(records).bind(node,4376)
        except Exception as error:fullstatus=type(error).__name__
        handle,tid,_=named_node(records,node,4376,('m_bnet','m_handle'));handle=helper.NamedVersioned(records).bind(handle,tid)
        archive_node,tid,_=named_node(records,node,4376,('m_bnet','m_archiveCacheHandle'));archive_value=helper.NamedVersioned(records).bind(archive_node,tid)
        require(handle==infos[index]['m_handle']and archive_value==prefix[index])
        comparisons=[]
        for label,names,name in helper.DIRECT:
            row={'field':label,'header_current_named_path':'Header/m_bnet/'+'/'.join(names),'candidate_MapInfo_field':name}
            try:
                n,tid,wp=named_node(records,node,4376,('m_bnet',)+names);row['wire_path']=wp;row['wire_tag']=n.tag
                v=helper.NamedVersioned(records).bind(n,tid);row.update(status='compared',equal_exact_no_locale_rebase=v==infos[index][name])
                if name=='m_requiredPermissions':row.update(explicit_tag_present=True,versioned_ARRAY_wire_tag=n.tag==0,header_array_empty=type(v)is list and len(v)==0,candidate_array_empty=type(infos[index][name])is list and len(infos[index][name])==0)
            except Exception as error:row.update(status='named_binding_failed',exception_class=type(error).__name__,exception_message_or_value_emitted=False)
            comparisons.append(row)
        require(len(comparisons)==15)
        out.append({'index':index,'header_sha256':digest,'bytes':len(body),'status':'exact_digest_full_versioned_decode_roundtrip','full_current_named_graph_result':fullstatus,'root_tag_delta':struct_delta(records,node,4376,'root'),'BnetHeader_tag_delta':struct_delta(records,bnetnode,bnetid,'root/0'),'prefix_archive_and_candidate_handle_exact':True,'shared_current_named_fields':comparisons})
    for path,digest,size in guards:
        after=read(path,256*1024);rawreads+=len(after);require(rawreads+24685<=256*1024 and len(after)==size and sha(after)==digest)
    after=read(replay,3*1024*1024);replay_reads+=len(after);require(sha(after)==ORIGINAL)
    for path in source_paths:require(sha(read(path,256*1024))==pins[path.relative_to(WORK).as_posix()if path.is_relative_to(WORK)else'repo/'+path.name])
    matches=sum(r.get('equal_exact_no_locale_rebase',False)for o in out for r in o.get('shared_current_named_fields',[]));compared=sum(r['status']=='compared'for o in out for r in o.get('shared_current_named_fields',[]))
    return {'format':'original41810-cached-header-MapInfo-evidence-v1','producer_sha256':sha(read(Path(__file__),256*1024)),'source_pins':pins,'replay_sha256':ORIGINAL,'member_sha256':MEMBER,'current_named_graph_sha256':GRAPH,'derived_legacy_hypothesis_receipt_sha256':LEGACY,'header_limit':6,'header_raw_byte_limit_including_guards':256*1024,'distinct_header_bytes':distinct,'actual_header_read_bytes_including_before_after_guards':rawreads,'prior_aborted_adapter_type_identity_check_header_read_bytes':24685,'lane_total_header_bytes_including_aborted_attempt':rawreads+24685,'replay_read_bytes_including_before_after_guards':replay_reads,'original_root_and_base_build41810_authenticated':True,'baseline_member_roundtrip_and_5_candidate_record_boundaries_exact':True,'all_source_and_input_guards_unchanged':True,'headers':out,'aggregate':{'exact_headers_available':opened,'missing_headers':5-opened,'explicit_shared_field_comparisons':compared,'exact_shared_field_matches':matches,'exact_shared_field_mismatches':compared-matches,'named_subfield_binding_failures':75-compared},'private_values_namespace_authors_accounts_or_raw_bodies_emitted':False,'old_names_or_permission_semantics_authenticated':False,'old_to_current_conversion_rule_proven':False,'network_client_PE_repo_or_cloud_used':False,'limits':['Current native names and types supply explicit common-field comparison paths only; exact historical semantics are not authenticated.','The sole candidate delta is permission-array count31to7/max127; original boundaries and token spans are compared to the separately frozen historical baseline.','Missing/extra tags and subfield binding failures are retained; absent fields are never defaulted.','Versioned array count framing is self-described and does not establish the historical bitpacked count width or permission meanings.','No R8/39445 replay or other local archive was opened; all values remain RAM except approved aggregate booleans/counts and source hashes.']}

if __name__=='__main__':
    target=HERE/'original41810-cached-header-MapInfo-evidence.json';require(not target.exists()and not target.is_symlink())
    data=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode();require(len(data)<=64*1024)
    with target.open('xb')as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
