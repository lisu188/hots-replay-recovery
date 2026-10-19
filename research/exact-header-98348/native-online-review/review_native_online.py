"""Independent bounded whole-lobby review: synthetic tests plus one pinned RAM case.

No network, PE, dumps, game client, extra replay, raw output or source mutation.
The independent physical walker does not call the codec bit reader/writer and
compares every postorder field span and scalar/blob value privately in RAM.
"""
from pathlib import Path
from io import BytesIO, StringIO
import collections, hashlib, importlib.util, json, os, stat, sys, tempfile, unittest
HERE=Path(__file__).resolve().parent
WORK=HERE.parent
READY=WORK/'native-online-codec-ready'
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(READY),str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
sys.dont_write_bytecode=True
sha=lambda raw:hashlib.sha256(raw).hexdigest()
PINS={'native_startgame.py':'4a77f974d439f8f44eaac9afd8d4de99a8b6e12e96464f82fa7daf0e6aefd543','native_startgame_schema_98348.json':'0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640','test_native_startgame.py':'e9ee35f9b5774ce6307e7697185e88eee6797299e2b921e87e8e4ac88f412173','native-online-portable-frozen-receipt.json':'c36e87f03b9d746a3c830d903a95ffc83c987b73bd4f3fb2fc1ef79876628ca9','native-online-startgame-21case-binding.json':'756a5ab92f7910a7e217a884d0609375b6ae050d169935b58b58de9147f357f1'}
REPLAY_SHA='882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'
MEMBER_SHA='ab03d9533081e9d69d205a6adec9df6a0aaf5ff47a05ecc8bf670b6760b0ab55'
REPLAY_LIMIT=1200000
reads=collections.Counter()
def need(ok,message):
    if not ok:raise ValueError(message)
def read(path,limit,category):
    path=Path(path);need(not path.is_symlink(),'Input symlink refused')
    with path.open('rb') as stream:
        a=os.fstat(stream.fileno());need(stat.S_ISREG(a.st_mode) and 1<=a.st_size<=limit,'Input bounds/type differ')
        data=stream.read(limit+1);b=os.fstat(stream.fileno())
    need(len(data)==a.st_size and (a.st_size,a.st_mtime_ns,a.st_ino)==(b.st_size,b.st_mtime_ns,b.st_ino),'Input changed or exceeded bounds')
    reads[category]+=len(data)
    return data,(a.st_size,a.st_mtime_ns,a.st_ino)

class PhysicalWalker:
    """Literal physical-bit walker/writer, independent of shared _Reader/_Writer."""
    def __init__(self,records,raw,native):
        self.records,self.raw,self.native=records,raw,native
        self.pos=0;self.out=bytearray(len(raw));self.ti=0;self.fi=0
        self.scalar_comparisons=0;self.blob_comparisons=0
    def number(self,width,token=True):
        need(type(width) is int and 0<=width<=127 and self.pos+width<=len(self.raw)*8,'Physical scalar bounds')
        spans=[];at=self.pos;end=at+width
        while at<end:
            stop=min(end,((at//8)+1)*8);spans.append((at,stop));at=stop
        value=0
        for start,stop in spans:
            part=sum(((self.raw[p//8]>>(p%8))&1)<<(p-start) for p in range(start,stop))
            value=(value<<(stop-start))|part
        # Re-emit each chunk from the logical value, rather than copying bits.
        remaining=width
        for start,stop in spans:
            size=stop-start;remaining-=size;chunk=(value>>remaining)&((1<<size)-1)
            for bit in range(size):self.out[(start+bit)//8]|=((chunk>>bit)&1)<<((start+bit)%8)
        self.pos=end
        if token:
            need(self.ti<len(self.native.tokens),'Native token missing')
            other=self.native.tokens[self.ti];need(other.width==width and other.value==value,'Independent scalar token differs')
            self.ti+=1;self.scalar_comparisons+=1
        return value
    def blob(self,count):
        padding=(-self.pos)%8
        if padding:need(self.number(padding,False)==0,'Physical alignment is nonzero')
        need(type(count) is int and 0<=count<=4096 and self.pos+count*8<=len(self.raw)*8,'Physical blob bounds')
        start=self.pos//8;value=self.raw[start:start+count];self.out[start:start+count]=value;self.pos+=count*8
        other=self.native.tokens[self.ti];need(other.width is None and other.value==value,'Independent blob token differs')
        self.ti+=1;self.blob_comparisons+=1
        return value
    def walk(self,identifier,path='',depth=0):
        need(depth<=64 and self.fi<500000,'Physical recursive/field bound')
        r=self.records[identifier];kind=r['kind'];b=r.get('bounds');start=self.pos;value=None
        if kind=='USER':value=self.walk(r['element_type'],path,depth+1)
        elif kind=='STRUCT':
            for name,child in zip(r['field_names'],r['field_types']):self.walk(child,path+'/'+name,depth+1)
        elif kind=='CHOICE':
            value=self.number(b['bits'])+b['min'];need(value in r['tags'],'Physical choice tag')
            index=r['tags'].index(value);self.walk(r['field_types'][index],path+'/'+r['field_names'][index],depth+1)
        elif kind=='ARRAY':
            value=self.number(b['bits'])+b['min'];need(0<=value<=min(b['max'],32768),'Physical array bounds')
            for index in range(value):self.walk(r['element_type'],path+'/'+str(index),depth+1)
        elif kind=='OPTIONAL':
            value=self.number(1)
            if value:self.walk(r['element_type'],path+'/value',depth+1)
        elif kind in ('ASCII_STRING','STRING','BLOB'):
            count=self.number(b['bits']+(2 if kind=='STRING' else 0))+b['min']
            need(0<=count<=min(b['max']*(4 if kind=='STRING' else 1),4096),'Physical string bound')
            value=self.blob(count)
            if kind=='ASCII_STRING':value.decode('ascii')
            if kind=='STRING':need(b['min']<=len(value.decode('utf8'))<=b['max'],'Physical UTF8 length')
        elif kind=='BIT_ARRAY':
            value=self.number(b['bits'])+b['min'];need(0<=value<=min(b['max'],65536),'Physical bit-array bound')
            for index in range(0,value,64):self.number(min(64,value-index))
        elif kind in ('INT','ENUM'):
            value=self.number(b['bits'])+b['min'];need(b['min']<=value<=b['max'],'Physical scalar bound')
            if kind=='ENUM':need(value in r['tags'],'Physical enum tag')
        elif kind in ('BOOL','FOURCC','REAL32','REAL64'):value=self.number({'BOOL':1,'FOURCC':32,'REAL32':32,'REAL64':64}[kind])
        elif kind!='NULL':raise ValueError('Unexpected physical kind')
        need(self.fi<500000 and self.fi<len(self.native.fields),'Physical field cap or field missing')
        f=self.native.fields[self.fi];need((f.path,f.type_id,f.start_bit,f.end_bit,f.kind)==(path,identifier,start,self.pos,kind),'Independent postorder field span differs')
        if kind not in ('USER','STRUCT'):need(f.value==value,'Independent logical scalar/blob field differs')
        self.fi+=1
        return value
    def finish(self):
        self.walk(5917)
        end=self.pos;padding=len(self.raw)*8-self.pos;need(0<=padding<8,'Physical EOF extent')
        if padding:need(self.number(padding)==0,'Physical EOF padding')
        need(self.pos==len(self.raw)*8 and bytes(self.out)==self.raw,'Independent whole physical reencoding differs')
        need(self.fi==len(self.native.fields) and self.ti==len(self.native.tokens),'Physical field/token totals differ')
        need(end==self.native.payload_end_bit and padding==self.native.padding_bits,'Physical native EOF positions differ')
        return {'all_postorder_field_ids_kinds_paths_and_spans_match':True,'all_scalar_blob_values_compared_privately':True,'whole_physical_bits_reencoded_exact':True,'decoded_fields':self.fi,'wire_tokens':self.ti,'scalar_tokens':self.scalar_comparisons,'blob_tokens':self.blob_comparisons,'payload_start_bit':0,'payload_end_bit':end,'zero_EOF_padding_bits':padding,'uses_codec_bit_reader_or_writer':False}

def review():
    blobs={}
    for name,pin in PINS.items():
        blobs[name]=read(READY/name,256*1024,'frozen_source_schema_and_reports')[0];need(sha(blobs[name])==pin,'Frozen input hash differs')
    import native_startgame as codec
    import native_clientinfo as shared
    import mpyq
    from protocol_loader import load_protocol
    need(Path(codec.__file__).resolve()==(READY/'native_startgame.py').resolve(),'Wrong codec imported')
    guarded={name:(Path(module.__file__),sha(read(Path(module.__file__),1024*1024,'runtime_source_guards')[0])) for name,module in [('codec',codec),('shared',shared),('mpyq',mpyq),('bit_io',sys.modules['battlelobby_attribute_layer']),('protocol_loader',sys.modules['protocol_loader'])]}
    need(guarded['shared'][1]==codec.SHARED_TYPES_SHA256,'Shared source differs')
    caps={k:v for k,v in vars(shared).items() if k.startswith('MAX_') and type(v) is int}
    suite=unittest.defaultTestLoader.discover(str(READY),pattern='test_native_startgame.py',top_level_dir=str(READY))
    temp_root=HERE/'synthetic-test-temp';temp_root.mkdir(exist_ok=True)
    previous_temp=tempfile.tempdir;tempfile.tempdir=str(temp_root)
    try:result=unittest.TextTestRunner(stream=StringIO(),verbosity=1).run(suite)
    finally:tempfile.tempdir=previous_temp
    if result.testsRun!=14 or result.failures or result.errors or result.skipped:
        print(json.dumps({'testsRun':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors],'skipped':result.skipped}),flush=True)
        raise ValueError('Focused tests failed or count differs')
    schema=json.loads(blobs['native_startgame_schema_98348.json']);records={r['id']:r for r in schema['records']}
    selected=json.loads(read(WORK/'current-header-field-exposure/native-header-mapinfo-selected-graph.json',128*1024,'cached_authenticated_projection')[0]);old={r['id']:r for r in selected['records']}
    overlap=set(old)&set(records);need(overlap and all(old[i]==records[i] for i in overlap),'Cached native projection overlap differs')
    path=WORK/'reference-donors/ngs-20261016-protectors-dragon.StormReplay'
    raw,meta=read(path,REPLAY_LIMIT,'one_pinned_replay');need(len(raw)==1113273 and sha(raw)==REPLAY_SHA,'Bounded pinned replay differs')
    archive=mpyq.MPQArchive(BytesIO(raw),listfile=False)
    need(all(0<=b.archived_size<=len(raw) and b.size<=8*1024*1024 for b in archive.block_table),'Pinned archive block bounds')
    protocol=load_protocol(96477);need(protocol.recovery_schema_sha256=='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84','Canonical official header schema differs')
    h=protocol.decode_replay_header(archive.header['user_data_header']['content'])
    need(h['m_version']['m_build']==h['m_version']['m_baseBuild']==h['m_dataBuildNum']==98348 and h['m_ngdpRootKey']['m_data'].hex()=='c3b3c8bc82e3a5a62e550fdde9a40c28','Actual current header/root differs')
    block=archive.get_hash_table_entry('replay.server.battlelobby');need(block is not None,'Lobby absent')
    need(archive.block_table[block.block_table_index].size==282976,'Known bounded lobby extent differs')
    member=archive.read_file('replay.server.battlelobby');need(len(member)==282976 and sha(member)==MEMBER_SHA,'Pinned raw lobby differs')
    decoded=codec.decode_startgame(member,codec.PROFILE);summary=decoded.summary()
    report=json.loads(blobs['native-online-startgame-21case-binding.json']);case=next(x for x in report['cases'] if x['replay_sha256']==REPLAY_SHA)
    need(summary==case['native_OnlineStartGameRequest'],'Fresh one-case summary differs from frozen21 proof')
    physical=PhysicalWalker(records,member,decoded).finish()
    need(caps=={k:v for k,v in vars(shared).items() if k.startswith('MAX_') and type(v) is int},'Shared module budgets mutated')
    after=path.stat();need((after.st_size,after.st_mtime_ns,after.st_ino)==meta,'Replay metadata changed after one-read audit')
    for name,(p,pin) in guarded.items():need(sha(read(p,1024*1024,'runtime_source_guards')[0])==pin,'Runtime source changed')
    for name,pin in PINS.items():need(sha(read(READY/name,256*1024,'frozen_after_guards')[0])==pin,'Frozen source/schema/report changed')
    return {'format':'whole-native-online-StartGameRequest-independent-review-v1','reviewed_inputs_sha256':PINS,'runtime_source_sha256s':{k:pin for k,(_,pin) in guarded.items()},'focused_tests':{'run':14,'passed':14,'skipped':0,'fixture_kind':'invented independent physical writer','temporary_files_relocated_to_review_workspace':True},'source_review':{'separate_field_token_depth_array_string_bounds':'PASS','preentry_and_postrecursive_field_cap':'PASS','source_and_schema_pinning':'PASS','shared_module_globals_unchanged':'PASS','strict_alignment_and_0_to7_zero_EOF_pad':'PASS','readonly_same_width_scalar_blob_token_mutation_rejection':'PASS','private_repr_and_aggregate_summary_scope':'PASS','no_historical_transform_or_playback_claim':'PASS'},'cached_authenticated_schema_overlap':{'records_compared':len(overlap),'all_records_exact':True,'PE_reopened':False,'entire513_independently_rederived_from_PE_in_this_review':False},'one_actual_current_control':{'replay_sha256':REPLAY_SHA,'member_sha256':MEMBER_SHA,'actual_executable_base_data_build':98348,'actual_NGDP_root':'c3b3c8bc82e3a5a62e550fdde9a40c28','fresh_summary_JSON_exact_to_frozen21_case':True,'physical_reconstruction':physical,'one_file_read_bytes':len(raw),'file_metadata_unchanged_after_audit':True,'second_replay_content_read_performed':False},'explicit_read_bytes':dict(reads),'material_findings':[],'prior_local_attempts':[{'synthetic_tests_completed':14,'errors':1,'category':'Sandbox default TemporaryDirectory PermissionError; rerun uses review-workspace temporary directory','actual_replay_reads_before_failure':0},{'initial_command':'CMD multiline environment setup did not execute test runner; not counted as validation','actual_replay_reads':0}],'limitations':['Only one existing pinned replay was reread; the21-case aggregate was inspected and hash-bound, not independently rerun in full.','The physical walker independently checks bit I/O, field spans and scalar/blob values against the same authenticated513 schema; it does not independently recover native schema semantics.','Before/after hashes cover source/schema/report files. Replay content is hashed on its one bounded read; final stat metadata is checked without a second replay-content read.','No PE, dumps, old headers, network, game client, native code, full core-event decode or replay mutation was used.','Decoded player/author/network/license values remain inRAM; only safe counts, extents and whole-file/member input hashes are reported.']}

if __name__=='__main__':
    out=HERE/'native-online-independent-review.json';need(not out.exists(),'Refuse existing review receipt')
    data=review();data['review_producer_sha256']=sha(read(Path(__file__),64*1024,'producer_hash')[0])
    encoded=(json.dumps(data,sort_keys=True,indent=2)+'\n').encode();need(len(encoded)<=32*1024,'Review report exceeds bound')
    with out.open('xb') as stream:stream.write(encoded)
    print(json.dumps({'review':'PASS','focused_tests':14,'report_bytes':len(encoded),'report_sha256':sha(encoded),'actual_controls':1,'private_values_emitted':False}),flush=True)
