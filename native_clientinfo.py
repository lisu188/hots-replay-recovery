"""Read-only ClientInfo codec for the authenticated native98348 snapshot.

Only the pinned104-type ClientInfo closure is supported. Values, identities,
network fields and strings remain private Python objects with disabled repr.
The historical/current observed tail codecs are independent profiles.
"""
from dataclasses import dataclass
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import stat

from battlelobby_attribute_layer import MAX_MEMBER_BYTES,LayerError,_Reader,_Writer

PROFILE='clientinfo-98348'
SCHEMA_SHA256='6e8711939ede15505debb043ae626b5c529749557d7e824226863c92e4f6a229'
SOURCE_PE_SHA256='efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
SOURCE_BYTECODE_SHA256='ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
MAX_TOKENS=100000
MAX_ARRAY=32768
MAX_STRING=4096

def _sha(raw):return hashlib.sha256(raw).hexdigest()

def _schema(path=None):
    path=Path(path) if path is not None else Path(__file__).with_name('native_clientinfo_schema_98348.json')
    if path.is_symlink():raise LayerError('Native schema symlink refused')
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 1<=before.st_size<=64*1024:raise LayerError('Native schema size/type differs')
        raw=stream.read(64*1024+1);after=os.fstat(stream.fileno())
    if len(raw)!=before.st_size or before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns or _sha(raw)!=SCHEMA_SHA256:raise LayerError('Pinned native schema differs')
    data=json.loads(raw)
    if (data['profile']!=PROFILE or data['root_type_id']!=1768 or data['source_PE_sha256']!=SOURCE_PE_SHA256 or data['source_embedded_bytecode_sha256']!=SOURCE_BYTECODE_SHA256 or data['selected_type_count']!=104 or len(data['records'])!=104):raise LayerError('Native schema provenance differs')
    return SimpleNamespace(records={r['id']:r for r in data['records']})

@dataclass(frozen=True,repr=False)
class NativeField:
    path:str
    type_id:int
    start_bit:int
    end_bit:int
    kind:str
    value:object

@dataclass(frozen=True,repr=False)
class WireToken:
    width:int|None
    value:int|bytes

@dataclass(frozen=True,repr=False)
class ClientInfo:
    profile:str
    start_bit:int
    end_bit:int
    fields:tuple[NativeField,...]
    tokens:tuple[WireToken,...]
    source:bytes
    source_sha256:str
    def field(self,path,kind=None):
        candidates=[f for f in self.fields if f.path==path and (kind is None or f.kind==kind)]
        if not candidates:raise LayerError('Expected native field absent')
        return next((f for f in candidates if f.kind!='USER'),candidates[-1])
    @property
    def slot(self):return self.field('/m_playerScope').value
    @property
    def toon(self):return self.field('/m_toonHandle').value
    def summary(self):
        names=('/m_talkerNetworkId','/m_voiceSessionId','/m_profileAddress','/m_relevantPermissions')
        fields=[self.field(n) for n in names]
        return {'profile':PROFILE,'schema_sha256':SCHEMA_SHA256,'start_bit':self.start_bit,'end_bit':self.end_bit,
            'named_segment_widths':[f.end_bit-f.start_bit for f in fields],
            'TalkerId_choice':self.field('/m_talkerInfo/m_id/m_id','CHOICE').value,
            'permission_count':self.field('/m_relevantPermissions','ARRAY').value,
            'exact_span_reencoding':_span_exact(self,encode_clientinfo(self)),
            'private_values_emitted':False}

class _Decoder:
    def __init__(self,schema,raw,start):
        self.schema=schema;self.reader=_Reader(raw);self.reader.position=start
        self.fields=[];self.tokens=[]
    def bits(self,n):
        if len(self.tokens)>=MAX_TOKENS:raise LayerError('Native wire-token budget exceeded')
        value=self.reader.bits(n);self.tokens.append(WireToken(n,value));return value
    def blob(self,n):
        if len(self.tokens)>=MAX_TOKENS:raise LayerError('Native wire-token budget exceeded')
        value=self.reader.blob(n);self.tokens.append(WireToken(None,value));return value
    def decode(self,i,path='',depth=0):
        if depth>64 or len(self.fields)>=MAX_TOKENS:raise LayerError('Native field budget exceeded')
        rec=self.schema.records[i];kind=rec['kind'];start=self.reader.position;value=None;b=rec.get('bounds')
        if kind=='USER':value=self.decode(rec['element_type'],path,depth+1)
        elif kind=='STRUCT':value={n:self.decode(c,path+'/'+n,depth+1) for n,c in zip(rec['field_names'],rec['field_types'])}
        elif kind=='CHOICE':
            value=self.bits(b['bits'])+b['min']
            if value not in rec['tags']:raise LayerError('Native choice tag outside declared fields')
            at=rec['tags'].index(value);self.decode(rec['field_types'][at],path+'/'+rec['field_names'][at],depth+1)
        elif kind=='ARRAY':
            value=self.bits(b['bits'])+b['min']
            if not 0<=value<=min(b['max'],MAX_ARRAY):raise LayerError('Native array exceeds budget')
            for j in range(value):self.decode(rec['element_type'],path+'/'+str(j),depth+1)
        elif kind=='OPTIONAL':
            value=self.bits(1)
            if value:self.decode(rec['element_type'],path+'/value',depth+1)
        elif kind in ('ASCII_STRING','STRING','BLOB'):
            count=self.bits(b['bits']+(2 if kind=='STRING' else 0))+b['min']
            if not 0<=count<=min(b['max']*(4 if kind=='STRING' else 1),MAX_STRING):raise LayerError('Native string exceeds budget')
            value=self.blob(count)
            try:
                if kind=='ASCII_STRING':value.decode('ascii')
                if kind=='STRING' and not b['min']<=len(value.decode('utf-8'))<=b['max']:raise LayerError('Native UTF8 character count exceeds bound')
            except UnicodeError as error:raise LayerError('Native string encoding is invalid') from None
        elif kind=='BIT_ARRAY':
            value=self.bits(b['bits'])+b['min']
            if not 0<=value<=min(b['max'],65536):raise LayerError('Native bit-array exceeds budget')
            for j in range(0,value,64):self.bits(min(64,value-j))
        elif kind in ('INT','ENUM'):
            value=self.bits(b['bits'])+b['min']
            if value>b['max'] or (kind=='ENUM' and value not in rec['tags']):raise LayerError('Native scalar outside declared bounds')
        elif kind in ('BOOL','FOURCC','REAL32','REAL64'):value=self.bits({'BOOL':1,'FOURCC':32,'REAL32':32,'REAL64':64}[kind])
        elif kind!='NULL':raise LayerError('Unsupported native kind')
        if len(self.fields)>=MAX_TOKENS:raise LayerError('Native field budget exceeded')
        self.fields.append(NativeField(path,i,start,self.reader.position,kind,value));return value

def decode_clientinfo(raw,start_bit,profile,*,schema_path=None):
    if profile!=PROFILE:raise LayerError('Explicit native ClientInfo98348 profile required')
    if type(raw) is not bytes or not 1<=len(raw)<=MAX_MEMBER_BYTES or type(start_bit) is not int or not 0<=start_bit<len(raw)*8:raise LayerError('Invalid bounded ClientInfo input')
    decoder=_Decoder(_schema(schema_path),raw,start_bit);decoder.decode(1768)
    result=ClientInfo(PROFILE,start_bit,decoder.reader.position,tuple(decoder.fields),tuple(decoder.tokens),raw,_sha(raw))
    if not _span_exact(result,encode_clientinfo(result)):raise LayerError('Native ClientInfo span reencoding differs')
    return result

def encode_clientinfo(value,profile=PROFILE):
    """Reencode the consumed byte span, preserving leading partial-byte bits.

    Last-byte unused high bits are zero. No replay/archive is created and the
    independent suffix after ClientInfo is not interpreted or copied here.
    """
    if not isinstance(value,ClientInfo) or value.profile!=PROFILE or profile!=PROFILE or len(value.tokens)>MAX_TOKENS:raise LayerError('Pinned decoded ClientInfo required')
    if len(value.source)>MAX_MEMBER_BYTES or _sha(value.source)!=value.source_sha256:raise LayerError('Decoded ClientInfo source differs')
    if type(value.start_bit) is not int or type(value.end_bit) is not int or not 0<=value.start_bit<value.end_bit<=len(value.source)*8:raise LayerError('Decoded native span bounds differ')
    writer=_Writer();writer.position=value.start_bit//8*8;writer.raw=bytearray(value.source[:value.start_bit//8])
    if value.start_bit%8:
        r=_Reader(value.source);r.position=writer.position;writer.bits(r.bits(value.start_bit%8),value.start_bit%8)
    for token in value.tokens:
        if not isinstance(token,WireToken):raise LayerError('Invalid native wire token')
        if token.width is None:
            if type(token.value) is not bytes or len(token.value)>MAX_STRING:raise LayerError('Native blob token exceeds budget')
            writer.blob(token.value)
        else:writer.bits(token.value,token.width)
        if len(writer.raw)>MAX_MEMBER_BYTES:raise LayerError('Reencoded native span exceeds budget')
    if writer.position!=value.end_bit:raise LayerError('Reencoded native span extent differs')
    output=bytes(writer.raw[value.start_bit//8:])
    if not _span_exact(value,output):raise LayerError('Read-only native reencoding changed consumed bits')
    return output

def _span_exact(value,encoded):
    start=value.start_bit//8;whole=value.end_bit//8-start;remaining=value.end_bit%8
    expected=(value.end_bit+7)//8-start
    return len(encoded)==expected and encoded[:whole]==value.source[start:start+whole] and (not remaining or encoded[-1]==value.source[value.end_bit//8]&((1<<remaining)-1))

def audit_current_client_infos(raw,tail):
    """Crossbind native ClientInfo against an existing observed-current Tail.

    The caller separately validates the archive header/build, initData and
    details. This helper returns aggregate structural facts without identities.
    """
    from battlelobby_tail import Tail,encode_tail
    if not isinstance(tail,Tail) or tail.profile!='current-tail' or not 1<=len(tail.players)<=16:raise LayerError('Observed current Tail required for crossbinding')
    if type(raw) is not bytes or len(raw)!=tail.member_bytes or _sha(raw)!=tail.member_sha256 or encode_tail(tail)!=raw:raise LayerError('Tail is not bound to this unchanged member')
    position=len(tail.prefix)*8;positions={}
    for token in tail.tokens:
        if token.width is None:position+=(-position)%8
        positions[token.path]=position;position+=token.width if token.width is not None else len(token.value)*8
    if position!=len(raw)*8:raise LayerError('Tail extent differs')
    infos=[];widths=Counter();choices=Counter();counts=Counter();overlaps=0
    anchors={'/m_clientId':'/unknown32','/m_playerScope':'/slot','/m_toonHandle':'/toon/region','/m_toonName':'/string_toon/region',
        '/m_talkerInfo':'/name_flag','/m_talkerInfo/m_id/m_id':'/unknown2bits','/m_talkerNetworkId':'/secondary/present',
        '/m_rating':'/optional64/present','/m_clientBuildVersion/value':'/community_named_build32','/m_sharedPlayerInfo':'/collection_choice',
        '/m_accountNickname':'/tag/present','/m_playerLevel':'/account_level','/m_hasActiveBoost':'/boost_flag'}
    for index,player in enumerate(tail.players):
        prefix=f'/players/{index}';info=decode_clientinfo(raw,positions[prefix+'/unknown32'],PROFILE)
        end=positions[f'/players/{index+1}/unknown32'] if index+1<len(tail.players) else tail.report['boundaries_bits']['players_end']
        if info.end_bit!=end:raise LayerError('Native ClientInfo end differs from observed boundary')
        for native,observed in anchors.items():
            if info.field(native).start_bit!=positions[prefix+observed]:raise LayerError('Native/observed anchor differs')
        toon=info.toon
        if info.slot!=player.slot or (toon['m_region'],toon['m_programId'],toon['m_realm'],toon['m_id'])!=(player.toon.region,int.from_bytes(player.toon.program,'big'),player.toon.realm,player.toon.identifier):raise LayerError('Private native/observed identity differs')
        summary=info.summary();widths[tuple(summary['named_segment_widths'])]+=1;choices[summary['TalkerId_choice']]+=1;counts[summary['permission_count']]+=1
        overlaps+=positions[prefix+'/unknown_player_block/0']==info.field('/m_talkerNetworkId').start_bit+1
        infos.append(info)
    return {'profile':PROFILE,'schema_sha256':SCHEMA_SHA256,'players_checked':len(infos),'native_ClientInfo_complete_ends_match':True,
        'all_13_named_anchors_match':True,'private_native_scope_and_toon_match':True,'all_consumed_spans_reencode_exact':True,
        'named_segment_width_histogram':[{'widths':list(w),'records':n} for w,n in sorted(widths.items())],
        'TalkerId_choice_histogram':dict(sorted(choices.items())),'permission_count_histogram':dict(sorted(counts.items())),
        'observed_opaque_starts_one_bit_inside_native_network_field_records':overlaps,
        'raw_player_values_emitted':False,'full_replay_compatibility_claimed':False}
