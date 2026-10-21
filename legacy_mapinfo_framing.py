"""RAM-only, data-specific MapInfo empty-count framing conversion.

Only three source member digests and sixteen saved record spans are admitted.
The legacy interpretation changes only native191 type1828 bounds31to7/max127.
All counts must be empty. No replay/header/body file writer is provided.
"""
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
import hashlib

import native_mapinfo as native
from battlelobby_attribute_layer import MAX_MEMBER_BYTES,LayerError,_Reader,_Writer

PROFILE='legacy-empty-mapinfo-count7-to-native31-v1'
BASELINE_RECEIPT_SHA256='de29dfe84d6906fda09768c7e545d8c1053e641e44d21372692b0f45d6529477'
MAX_RECORDS=6
_ADMITTED=(
 ('original41810','beea9c9b29a7f1a73806fe37b393f453c84a7faed8d6f89a5b4fcd25967f1f44',((205187,206448),(206448,208088),(208088,209376),(209376,211566),(211566,214289))),
 ('R8','2902a33a450491e8717a8006cef4627f2c12d1c0b854fc4f698dc1de0ade9640',((206563,207824),(207824,209464),(209464,210752),(210752,212942),(212942,215665))),
 ('authenticated39445','4deae39a1656618254667ae161b6dec0e7173a0e6e9dedb365ca5cce319adbc1',((191599,192832),(192832,194448),(194448,195712),(195712,197878),(197878,199662),(199662,202041))),
)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def require(value,message='Strict MapInfo framing validation failed'):
    if not value:raise LayerError(message)

@dataclass(frozen=True,repr=False)
class _Edit:
    source_start:int
    source_end:int
    source_count_start:int
    target_start:int
    target_end:int
    target_count_start:int

@dataclass(frozen=True,repr=False)
class ReframedMember:
    profile:str
    source:bytes
    converted:bytes
    source_sha256:str
    converted_sha256:str
    edits:tuple[_Edit,...]
    def summary(self):return _verify_result(self,PROFILE)[1]

class _EmptyLegacyDecoder(native.shared._Decoder):
    def decode(self,identifier,path='',depth=0):
        if identifier!=1828:return super().decode(identifier,path,depth)
        require(depth<=64 and len(self.fields)<native.shared.MAX_TOKENS)
        record=self.schema.records[identifier]
        require(record['kind']=='ARRAY'and record['bounds']['bits']==7 and record['bounds']['min']==0 and record['bounds']['max']==127)
        start=self.reader.position
        require(self.bits(7)==0,'Nonempty legacy permissions are unsupported')
        self.fields.append(native.shared.NativeField(path,identifier,start,self.reader.position,'ARRAY',0))
        return 0

def _admit(raw,profile):
    require(profile==PROFILE,'Explicit strict legacy MapInfo profile required')
    require(type(raw)is bytes and 0<len(raw)<=MAX_MEMBER_BYTES,'Bounded member bytes required')
    digest=sha(raw);rows=[r for r in _ADMITTED if r[1]==digest]
    require(len(rows)==1,'Unadmitted source member digest')
    label,_,spans=rows[0];require(1<=len(spans)<=MAX_RECORDS)
    require(len(raw)+3*len(spans)<=MAX_MEMBER_BYTES)
    previous=-1
    for start,end in spans:
        require(type(start)is int and type(end)is int and 0<=start<end<=len(raw)*8 and start>=previous)
        previous=end
    return label,spans

def _schemas(schema_path):
    current=native._schema(schema_path)
    require(len(current.records)==191 and len(current.records[5852]['field_names'])==32)
    bound=current.records[1828]['bounds'];require((bound['bits'],bound['min'],bound['max'])==(31,0,2147483647))
    old=deepcopy(current.records);old[1828]['bounds'].update(bits=7,max=127)
    for identifier in current.records:
        expected=deepcopy(current.records[identifier])
        if identifier==1828:expected['bounds'].update(bits=7,max=127)
        require(old[identifier]==expected)
    return current,SimpleNamespace(records=old)

def _field(fields,path):
    matches=[f for f in fields if f.path==path and f.kind!='USER']
    require(len(matches)==1,'Exact named field absent or ambiguous');return matches[0]

def _records(raw,spans,old):
    results=[];edits=[]
    for index,(start,end)in enumerate(spans):
        decoder=_EmptyLegacyDecoder(old,raw,start);decoder.decode(5852)
        require(decoder.reader.position==end,'Legacy record end differs from pinned span')
        position=start
        for name in old.records[5852]['field_names']:
            field=_field(decoder.fields,'/'+name);require(field.start_bit==position);position=field.end_bit
        require(position==end)
        count=_field(decoder.fields,'/m_requiredPermissions')
        require(count.kind=='ARRAY'and count.type_id==1828 and count.value==0 and count.end_bit-count.start_bit==7 and count.end_bit==end)
        require(decoder.tokens[-1].width==7 and decoder.tokens[-1].value==0)
        shift=24*index
        edits.append(_Edit(start,end,count.start_bit,start+shift,end+shift+24,count.start_bit+shift))
        results.append(decoder)
    return tuple(edits),results

def _copy(reader,writer,stop):
    require(type(stop)is int and reader.position<=stop<=len(reader.raw)*8)
    while reader.position<stop:
        width=min(64,stop-reader.position);writer.bits(reader.bits(width),width)
        require(len(writer.raw)<=MAX_MEMBER_BYTES)

def _same(a,apos,b,bpos,width):
    require(type(width)is int and width>=0)
    x=_Reader(a);x.position=apos;y=_Reader(b);y.position=bpos
    left=width
    while left:
        n=min(64,left)
        if x.bits(n)!=y.bits(n):return False
        left-=n
    return True

def _emit(raw,edits):
    reader=_Reader(raw);writer=_Writer()
    for edit in edits:
        _copy(reader,writer,edit.source_count_start)
        require(writer.position==edit.target_count_start and reader.bits(7)==0)
        writer.bits(0,31)
    _copy(reader,writer,len(raw)*8)
    require(writer.position==(len(raw)+3*len(edits))*8)
    return bytes(writer.raw)

def _outside_equal(source,target,edits):
    a=b=0
    for edit in edits:
        require(edit.source_count_start-a==edit.target_count_start-b)
        require(_same(source,a,target,b,edit.source_count_start-a),'Non-count source bits changed')
        a=edit.source_count_start+7;b=edit.target_count_start+31
    require(len(source)*8-a==len(target)*8-b)
    require(_same(source,a,target,b,len(source)*8-a),'Trailing non-count source bits changed')

def _check_current(source,target,edits,old_records,schema_path):
    require(type(target)is bytes and len(target)==len(source)+3*len(edits) and len(target)<=MAX_MEMBER_BYTES)
    fields=0
    for edit,old in zip(edits,old_records):
        r=_Reader(target);r.position=edit.target_count_start
        require(r.bits(31)==0,'Nonempty target permissions are unsupported')
        current=native.decode_mapinfo(target,edit.target_start,native.PROFILE,schema_path=schema_path)
        require(current.end_bit==edit.target_end,'Current native destination end differs')
        require(len(current.fields)==len(old.fields)and len(current.tokens)==len(old.tokens))
        shift=edit.target_start-edit.source_start
        for a,b in zip(old.fields,current.fields):
            require((a.path,a.kind,a.type_id,a.value)==(b.path,b.kind,b.type_id,b.value),'Native field value or type changed')
            expected_start=a.start_bit+shift+(24 if a.start_bit>edit.source_count_start else 0)
            expected_end=a.end_bit+shift+(24 if a.end_bit>edit.source_count_start else 0)
            require((b.start_bit,b.end_bit)==(expected_start,expected_end),'Native field shifted extent differs')
        require(tuple(old.tokens[:-1])==current.tokens[:-1]and current.tokens[-1].width==31 and current.tokens[-1].value==0,'Non-count wire token changed')
        require(native.shared._span_exact(current,native.encode_mapinfo(current)))
        fields+=len(current.fields)
    _outside_equal(source,target,edits)
    return fields

def _inverse_bytes(target,edits):
    reader=_Reader(target);writer=_Writer()
    for edit in edits:
        _copy(reader,writer,edit.target_count_start)
        require(writer.position==edit.source_count_start and reader.bits(31)==0)
        writer.bits(0,7)
    _copy(reader,writer,len(target)*8)
    require(writer.position==(len(target)-3*len(edits))*8)
    return bytes(writer.raw)

def _verify_result(value,profile,*,schema_path=None):
    require(isinstance(value,ReframedMember)and value.profile==profile==PROFILE)
    label,spans=_admit(value.source,profile)
    require(type(value.converted)is bytes and len(value.converted)==len(value.source)+3*len(spans) and len(value.converted)<=MAX_MEMBER_BYTES,'Target member type or extent differs before hashing')
    require(sha(value.source)==value.source_sha256 and type(value.converted)is bytes and sha(value.converted)==value.converted_sha256,'Stored member digest differs')
    _,old=_schemas(schema_path);edits,records=_records(value.source,spans,old)
    require(value.edits==edits,'Stored framing edits differ')
    fields=_check_current(value.source,value.converted,edits,records,schema_path)
    restored=_inverse_bytes(value.converted,edits);require(restored==value.source,'Inverse member bytes differ')
    report={'profile':PROFILE,'source_id':label,'source_member_sha256':value.source_sha256,'converted_member_sha256':value.converted_sha256,'source_member_bytes':len(value.source),'converted_member_bytes':len(value.converted),'MapInfo_records':len(edits),'added_bits_per_record':24,'added_bytes':len(value.converted)-len(value.source),'named_root_field_comparisons':32*len(edits),'all_native_field_comparisons':fields,'unchanged_current_native_32_field_destination_values_and_bounds_exact':True,'all_non_count_tokens_and_outside_bits_exact':True,'inverse_whole_member_bytes_exact':True,'nonempty_permissions_supported':False,'whole_replay_upgrade_or_historical_schema_authenticated':False,'raw_author_account_player_values_emitted':False}
    return restored,report

def convert_mapinfo_framing(raw,profile,*,schema_path=None):
    """Return private RAM bytes only after admission and complete inverse proof."""
    _,spans=_admit(raw,profile);_,old=_schemas(schema_path);edits,records=_records(raw,spans,old)
    output=_emit(raw,edits);_check_current(raw,output,edits,records,schema_path)
    value=ReframedMember(PROFILE,raw,output,sha(raw),sha(output),edits)
    require(_inverse_bytes(output,edits)==raw,'Inverse member bytes differ')
    return value

def inverse_mapinfo_framing(value,profile,*,schema_path=None):
    """Validate the current records and undo only the declared empty-count edits."""
    return _verify_result(value,profile,schema_path=schema_path)[0]
