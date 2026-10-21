"""One guarded original/R8/39445 converter proof; JSON only, output bytes stayRAM."""
from io import BytesIO
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,stat,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
CASES=(('original41810','TEN_GREYMANE_source_41810.StormReplay','e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824',41810,41810,'83d43a8647bb5ca5caa6f2f09064da55',5),('R8','native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay','4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19',96477,98285,None,5),('authenticated39445','legacy-39445-control/htc39445.private.StormReplay','32803cf56e4377a18ea74c908af3d840637faeb7803aaca943f8807ade70ba87',39445,39445,'b3959e128489be464b4ef50eb6259480',6))
SCHEMAS={41810:'879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',96477:'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84',39445:'0898b2e8608c58b24a4a8f71585af7a028a0265d4d61a8074c124de97a577148'}
def require(v,message='Bounded converter proof validation failed'):
    if not v:raise ValueError(message)
def read(path,limit):
    require(not path.is_symlink())
    with path.open('rb')as stream:
        a=os.fstat(stream.fileno());require(stat.S_ISREG(a.st_mode)and 0<a.st_size<=limit)
        raw=stream.read(limit+1);b=os.fstat(stream.fileno())
    require(len(raw)==a.st_size==b.st_size and a.st_mtime_ns==b.st_mtime_ns);return raw

def prove(workspace,repo):
    work=workspace/'work'
    own={'legacy_mapinfo_framing.py':'087965405fa4c97e088b7581c9ffa4d7e384ad45535be859a6d09be10420e2b3','test_legacy_mapinfo_framing.py':'c41dd105a7489a80bce60ea26e2257c4e41feb40633ce219d15bae6e67bf1bd3','code-test-freeze-v2.json':'e2047698edcba6197806c39a673352e89cc1f746e73e7dd96e81d3dd30bd0886'}
    dependencies={'native_mapinfo.py':'b7bd41881c171a606fa3fe5844590e8d935d5ed2e42cb418cd2fcbc859710810','native_mapinfo_schema_98348.json':'3900a63c0799474becd2ecfb03eece4f8c523a965b38e539264867d5cdf2075c','native_clientinfo.py':'e0abd0b674c97b87f6a1510edc08704eebeca0ad9d43ac0537d5eaaa3eb9b202','battlelobby_attribute_layer.py':'3faf056fa8123f66e73dd551fcab2fb05fd9ccba5643826ec6835c771672aeee','audit_battlelobby_mod_metadata.py':'8dad2d923957cdfc44bec5690fe075c16d6e204651e09cc88cbf8503abcdd7c9','battlelobby_arcade_sections.py':'7ab101128268a5a838771760f80a8e3975020ddcaa1d58f12351d21a2190bf27','mpq_reader.py':'9e940dae67c5d457483c814e6169e6e5d0a1cc5a1dcfdbd76dcf9026f1fa0033'}
    guards=[(HERE/name,digest,'producer/'+name)for name,digest in own.items()]+[(repo/name,digest,'repo/'+name)for name,digest in dependencies.items()]
    guards +=[(work/'legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json','de29dfe84d6906fda09768c7e545d8c1053e641e44d21372692b0f45d6529477','saved_legacy_span_proof'),(work/'legacy-header-mapinfo-evidence/original41810-cached-header-MapInfo-evidence.json','1a4b18326303388b12f7d7a72415a5cd8973717954b30154370fb5927727bda3','saved_original_header_controls')]
    controls={}
    for path,digest,label in guards:
        body=read(path,256*1024);require(sha(body)==digest);controls[label]={'bytes':len(body),'sha256':digest}
    prior=json.loads(read(guards[-2][0],256*1024));headers=json.loads(read(guards[-1][0],256*1024));require(headers['aggregate']['exact_shared_field_matches']==75)
    paths=[work/c[1]for c in CASES]
    sizes=[]
    for path in paths:
        require(not path.is_symlink());size=path.stat().st_size;require(0<size<=3*1024*1024);sizes.append(size)
    require(sum(sizes)<=4*1024*1024)
    sys.path[:0]=[str(repo),str(work/'heroprotocol'),str(work/'python-deps'),str(HERE)]
    import legacy_mapinfo_framing as converter
    import native_mapinfo
    from audit_battlelobby_mod_metadata import audit_member
    from battlelobby_attribute_layer import _Reader
    from mpq_reader import MPQArchive
    from protocol_loader import load_protocol
    class Archive(MPQArchive):
        def __init__(self,body):self.file=BytesIO(body);self.header=self.read_header();self.hash_table=self.read_table('hash');self.block_table=self.read_table('block')
    def protocol_for(version):
        if version!=39445:
            p=load_protocol(version);require(p.recovery_schema_sha256==SCHEMAS[version]);return p
        path=work/'legacy-39445-control/protocol39445.canonical-private.py';require(sha(read(path,64*1024))==SCHEMAS[39445])
        spec=importlib.util.spec_from_file_location('_framing_proof_protocol39445',path);p=importlib.util.module_from_spec(spec);sys.modules[spec.name]=p;spec.loader.exec_module(p);return p
    rows=[];replay_bytes=0;field_total=0
    for case,path,size in zip(CASES,paths,sizes):
        label,_,digest,version,build,root,count=case
        body=read(path,3*1024*1024);replay_bytes+=len(body);require(len(body)==size and sha(body)==digest)
        archive=Archive(body)
        try:
            p=protocol_for(version);header=p.decode_replay_header(archive.header['user_data_header']['content']);require(header['m_version']['m_build']==build)
            if root is not None:require(header['m_ngdpRootKey']['m_data'].hex()==root)
            require(all(b.size<=8*1024*1024 for b in archive.block_table));raw=archive.read_file('replay.server.battlelobby');require(type(raw)is bytes and 0<len(raw)<=8*1024*1024)
        finally:archive.close()
        fresh=audit_member(raw,'legacy-10','historical-fixed');require(fresh['same_profile_full_member_roundtrip_exact']and len(fresh['entries'])==count)
        saved=next(c for c in prior['cases']if c['id']==label)
        require(sha(raw)==saved['member_sha256'])
        source_bounds=[(e['start_bit'],e['end_bit'])for e in fresh['entries']]
        require(source_bounds==[(e['baseline_start_bit'],e['baseline_end_bit'])for e in saved['entries']])
        value=converter.convert_mapinfo_framing(raw,converter.PROFILE);summary=value.summary()
        require(summary['source_id']==label and summary['MapInfo_records']==count and summary['added_bytes']==3*count)
        require(converter.inverse_mapinfo_framing(value,converter.PROFILE)==raw)
        record_rows=[]
        for index,(entry,edit)in enumerate(zip(fresh['entries'],value.edits)):
            require((edit.source_start,edit.source_end)==(entry['start_bit'],entry['end_bit']))
            expected_shift=24*index;require(edit.target_start==entry['start_bit']+expected_shift and edit.target_end==entry['end_bit']+expected_shift+24)
            current=native_mapinfo.decode_mapinfo(value.converted,edit.target_start,native_mapinfo.PROFILE)
            physical=_Reader(raw);physical.position=entry['start_bit'];require(current.identity==(physical.bits(32),physical.bits(32)))
            require(current.end_bit==edit.target_end and current.field('/m_requiredPermissions','ARRAY').value==0)
            require(current.summary()['last_two_named_widths']==[1,31])
            record_rows.append({'index':index,'source_start_bit':entry['start_bit'],'source_end_bit':entry['end_bit'],'target_start_bit':edit.target_start,'target_end_bit':edit.target_end,'independent_current_native_identity_and_end_exact':True,'native_32_named_fields_preserved':True,'current_final_widths':[1,31]})
        field_total+=summary['all_native_field_comparisons']
        rows.append({'id':label,'replay_sha256':digest,'actual_header_build':build,'official_schema_sha256':SCHEMAS[version],'source_member_sha256':sha(raw),'fresh_historical_baseline_exact':True,'saved_span_receipt_agrees':True,'converter':summary,'records':record_rows,'converted_member_saved':False})
        after=read(path,3*1024*1024);replay_bytes+=len(after);require(len(after)==size and sha(after)==digest)
        require(replay_bytes<=2*4*1024*1024)
    for path,digest,_ in guards:require(sha(read(path,256*1024))==digest)
    return {'format':'strict-legacy-MapInfo-framing-three-source-proof-v1','producer_sha256':sha(read(Path(__file__),64*1024)),'source_pins':controls,'cases':rows,'aggregate':{'source_cases':3,'records':16,'named_root_field_comparisons':512,'all_native_field_comparisons':field_total,'all_current_native_destinations_32_fields_values_bounds_and_spans_exact':True,'all_non_count_tokens_prefix_suffix_and_other_member_bits_exact':True,'inverse_whole_members_byte_exact':3,'all_input_and_source_guards_unchanged':True,'distinct_replay_input_bytes':sum(sizes),'replay_read_bytes_including_before_after_guards':replay_bytes,'distinct_replay_input_cap':4*1024*1024,'raw_header_dump_PE_or_network_reads':0,'converted_members_or_StormReplay_outputs_written':0},'limits':['Only MapInfo count7zero→31zero framing changes; prefix, ClientInfo, registry, matrix and other fields remain their legacy bytes.','Current native MapInfo destinations are proved; whole-current OnlineStartGameRequest/replay compatibility is not claimed.','Source/R8/39445 members and all source archives remain unchanged; converted private members exist onlyRAM.','The39445 diagnostic and the observed legacy profile do not authenticate a whole old native schema.','Saved original five-header controls are reused bydigest; no header body is reopened.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    require(args.output.suffix=='.json'and args.output.parent.is_dir()and not args.output.exists()and not args.output.is_symlink(),'Refuse unsafe/existing report output before private inputs')
    result=prove(args.workspace,args.repo);data=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode();require(len(data)<=128*1024)
    with args.output.open('xb')as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
