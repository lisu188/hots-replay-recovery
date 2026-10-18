"""Bounded data-only BSN metadata decoder; never executes target code.

Framing hypothesis came from the separately pinned cross-game BSN source.
Acceptance requires every declared record and reference to validate locally.
"""
import re
import struct

KINDS={1:'ARRAY',2:'ASCII_STRING',3:'BIT_ARRAY',4:'BLOB',5:'BOOL',6:'CHOICE',7:'ENUM',8:'FOURCC',9:'INT',10:'NULL',11:'OPTIONAL',12:'REAL32',13:'REAL64',14:'STRUCT',15:'STRING',16:'USER'}
MAX_BLOB=2*1024*1024
MAX_TYPES=20000
MAX_FIELDS=200000

class MetadataError(ValueError): pass

class Reader:
    def __init__(self,raw,start,end):
        if not isinstance(raw,bytes) or not 0<=start<=end<=len(raw):raise MetadataError('Invalid reader bounds')
        self.raw=raw;self.pos=start;self.end=end
    def take(self,n):
        if type(n) is not int or n<0 or self.pos+n>self.end:raise MetadataError('Truncated record')
        value=self.raw[self.pos:self.pos+n];self.pos+=n;return value
    def u8(self):return self.take(1)[0]
    def u32(self):return int.from_bytes(self.take(4),'big')
    def integer(self,t):
        if type(t) is not int or not 0<=t<=7:raise MetadataError('Invalid integer width')
        return int.from_bytes(self.take(1<<(t>>1)),'big',signed=not(t&1))
    def size(self):
        t=self.u8()
        if t>5:raise MetadataError('Invalid count width')
        n=int.from_bytes(self.take(1<<(t>>1)),'big')
        if n>MAX_TYPES:raise MetadataError('Count exceeds bound')
        return n
    def bounds(self,fixed=False):
        t=self.u8()
        if fixed:minimum=self.integer(t);return {'int_type':t,'variable':False,'bits':0,'min':minimum,'max':minimum}
        flags=self.u8();minimum=self.integer(t);maximum=self.integer(t)
        return {'int_type':t,'variable':bool(flags&128),'bits':flags&127,'min':minimum,'max':maximum}

class Protocol:
    def __init__(self,raw):
        if type(raw) is not bytes or not 20<=len(raw)<=MAX_BLOB:raise MetadataError('Invalid bytecode size')
        self.raw=raw
        self.version,self.unknown,self.count,self.type_size,self.dump_size=struct.unpack_from('>5I',raw)
        if not 1<=self.version<=16 or not 1<=self.count<=MAX_TYPES:raise MetadataError('Invalid protocol header')
        self.type_start=20+4*self.count;self.dump_offsets=self.type_start+self.type_size
        self.dump_start=self.dump_offsets+4*self.count;self.end=self.dump_start+self.dump_size
        if self.end!=len(raw) or not self.type_start<self.dump_offsets<self.dump_start<self.end:raise MetadataError('Declared extent mismatch')
        self.type_offsets=list(struct.unpack_from('>'+str(self.count)+'I',raw,20))
        self.dump_values=list(struct.unpack_from('>'+str(self.count)+'I',raw,self.dump_offsets))
        if self.type_offsets!=sorted(set(self.type_offsets)) or self.type_offsets[0]!=self.type_start:raise MetadataError('Invalid ordered type offsets')
        if any(not self.type_start<=x<self.dump_offsets for x in self.type_offsets):raise MetadataError('Type offset outside section')
        if any(x and not self.dump_start<=x<self.end for x in self.dump_values):raise MetadataError('Dump offset outside section')
        self.materialized_fields=0
        self.records=[self._record(i) for i in range(self.count)]
        sizes=[1+(r.get('count',0) if r['kind'] in ('STRUCT','CHOICE','ENUM') else 0) for r in self.records]
        ends=[p+4*n for p,n in zip(self.dump_values,sizes) if p]
        if not ends:raise MetadataError('No declared dump records')
        self.name_start=max(ends)
        if not self.dump_start<=self.name_start<self.end or (self.name_start-self.dump_start)%4:raise MetadataError('Invalid dump/name boundary')
        pool=self.raw[self.name_start:]
        if not pool or pool[-1]!=0:raise MetadataError('Unterminated name pool')
        matches=list(re.finditer(rb'[^\x00]+',pool))
        if any(len(m.group())>512 or any(not 32<=b<=126 for b in m.group()) for m in matches):raise MetadataError('Invalid bounded static name pool')
        self.name_starts={self.name_start+m.start() for m in matches}
        for p,n in zip(self.dump_values,sizes):
            if p and ((p-self.dump_start)%4 or p+4*n>self.name_start):raise MetadataError('Invalid dump record boundary')
        self.dump_words=struct.unpack_from('>'+str((self.name_start-self.dump_start)//4)+'I',self.raw,self.dump_start)
        if any(p and p not in self.name_starts for p in self.dump_words):raise MetadataError('Name reference is not a complete token start')
        self.by_name={}
        for rec in self.records:
            rec['name']=self.dump_string(rec['id'],0)
            if rec['name']:self.by_name.setdefault(rec['name'],[]).append(rec['id'])
            if rec['kind'] in ('STRUCT','CHOICE','ENUM'):
                rec['field_names']=[self.dump_string(rec['id'],j+1) for j in range(rec['count'])]
        self.name_reference_count=sum(1+(r.get('count',0) if r['kind'] in ('STRUCT','CHOICE','ENUM') else 0) for r in self.records)
    def _record(self,i):
        start=self.type_offsets[i];end=self.type_offsets[i+1] if i+1<self.count else self.dump_offsets
        r=Reader(self.raw,start,end);header=r.u8();kind=header&63
        if kind not in KINDS:raise MetadataError('Unknown meta type')
        rec={'id':i,'offset':start,'bytes':end-start,'header':header,'kind':KINDS[kind]}
        if kind in (1,3,4):
            rec['bounds']=r.bounds(bool(header&128))
            if kind==1:rec['element_type']=r.u32()
        elif kind in (2,9,15):rec['bounds']=r.bounds()
        elif kind in (6,7,14):
            bounds=r.bounds();rec['bounds']=bounds
            count=bounds['max']-bounds['min']+1 if header&128 else r.size()
            if not 0<=count<=MAX_TYPES:raise MetadataError('Member count exceeds bound')
            if self.count+self.materialized_fields+count>MAX_FIELDS:raise MetadataError('Aggregate field/name budget exceeded')
            self.materialized_fields+=count
            rec['count']=count
            rec['tags']=list(range(bounds['min'],bounds['max']+1)) if header&128 else [r.integer(bounds['int_type']) for _ in range(count)]
            if kind!=7 and len(set(rec['tags']))!=count:raise MetadataError('Duplicate member tags')
            if kind in (6,14):rec['field_types']=[r.u32() for _ in range(count)]
        elif kind in (11,16):rec['element_type']=r.u32()
        if r.pos!=end:
            pad=end-r.pos
            if i!=self.count-1 or pad>3 or any(r.take(pad)):raise MetadataError('Record does not exactly consume declared boundary')
            rec['trailing_zero_alignment_bytes']=pad
        if 'bounds' in rec and rec['bounds']['min']>rec['bounds']['max']:
            if not (kind in (6,7,14) and header&128 and rec['bounds']['min']==rec['bounds']['max']+1):raise MetadataError('Reversed bounds')
        for child in rec.get('field_types',[])+([rec['element_type']] if 'element_type' in rec else []):
            if not 0<=child<self.count:raise MetadataError('Child type out of range')
        return rec
    def dump_string(self,type_id,index):
        ptr=self.dump_values[type_id]
        if not ptr:return None
        at=ptr+4*index
        if not self.dump_start<=at<=self.end-4:raise MetadataError('Dump record exceeds section')
        dest=int.from_bytes(self.raw[at:at+4],'big')
        if dest==0:return None
        if not self.dump_start<=dest<self.end:raise MetadataError('Name offset outside dump section')
        end=self.raw.find(b'\0',dest,min(self.end,dest+513))
        if end<0 or end==dest or any(not 32<=b<=126 for b in self.raw[dest:end]):raise MetadataError('Invalid bounded static name')
        return self.raw[dest:end].decode('ascii')
    def projection(self,name,depth=4):
        ids=self.by_name.get(name,[])
        if len(ids)!=1:raise MetadataError('Name is not unique')
        def walk(i,d,seen):
            r=self.records[i];out={k:r[k] for k in ('id','offset','bytes','header','kind','name')}
            if 'bounds' in r:out['bounds']=r['bounds']
            if 'tags' in r:out['tags']=r['tags']
            if d and i not in seen:
                if 'element_type' in r:out['element']=walk(r['element_type'],d-1,seen|{i})
                if 'field_types' in r:out['members']=[{'name':n,'tag':t,'type':walk(c,d-1,seen|{i})} for n,t,c in zip(r['field_names'],r['tags'],r['field_types'])]
            return out
        return walk(ids[0],depth,set())
