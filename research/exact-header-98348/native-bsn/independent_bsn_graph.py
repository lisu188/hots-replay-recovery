"""Independent static metadata reader; target PE is treated only as file data."""
import hashlib
import os
from pathlib import Path
import re
import struct

PE_SHA='efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
BLOB_SHA='ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
BASE,END=43169040,43560673
KINDS={1:'ARRAY',2:'ASCII_STRING',3:'BIT_ARRAY',4:'BLOB',5:'BOOL',6:'CHOICE',7:'ENUM',8:'FOURCC',9:'INT',10:'NULL',11:'OPTIONAL',12:'REAL32',13:'REAL64',14:'STRUCT',15:'STRING',16:'USER'}

def require(test):
    if not test:raise ValueError('Independent bounded native graph validation failed')

def load(path):
    require(not path.is_symlink())
    out=[];at=0;h=hashlib.sha256()
    with path.open('rb') as f:
        before=os.fstat(f.fileno());require(before.st_size==53573840)
        while at<before.st_size:
            part=f.read(min(65536,before.st_size-at));require(bool(part));h.update(part)
            low,high=max(at,BASE),min(at+len(part),END)
            if low<high:out.append(part[low-at:high-at])
            at+=len(part)
        after=os.fstat(f.fileno())
    require(before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns and h.hexdigest()==PE_SHA)
    raw=b''.join(out);require(len(raw)==END-BASE and hashlib.sha256(raw).hexdigest()==BLOB_SHA)
    return raw,at

class Cursor:
    def __init__(self,raw,start,end):self.raw,self.at,self.end=raw,start,end
    def take(self,n):
        require(type(n)is int and n>=0 and self.at+n<=self.end)
        result=self.raw[self.at:self.at+n];self.at+=n;return result
    def octet(self):return self.take(1)[0]
    def u32(self):return int.from_bytes(self.take(4),'big')
    def integer(self,t):
        require(0<=t<=7);return int.from_bytes(self.take(2**(t//2)),'big',signed=t%2==0)
    def bounds(self,fixed):
        t=self.octet()
        if fixed:
            v=self.integer(t);return dict(int_type=t,variable=False,bits=0,min=v,max=v)
        flags=self.octet();low=self.integer(t);high=self.integer(t)
        return dict(int_type=t,variable=bool(flags&128),bits=flags&127,min=low,max=high)

class Graph:
    def __init__(self,raw):
        self.raw=raw;v,u,n,ts,ds=struct.unpack_from('>5I',raw)
        require((v,u,n,ts,ds)==(7,0,8330,67244,257729))
        start=20+4*n;dump_offsets=start+ts;dump_start=dump_offsets+4*n
        require(dump_start+ds==len(raw))
        offsets=struct.unpack_from('>'+str(n)+'I',raw,20)
        dumps=struct.unpack_from('>'+str(n)+'I',raw,dump_offsets)
        require(tuple(sorted(set(offsets)))==offsets and offsets[0]==start and offsets[-1]<dump_offsets)
        self.records=[]
        for i,at in enumerate(offsets):
            limit=offsets[i+1] if i+1<n else dump_offsets
            c=Cursor(raw,at,limit);head=c.octet();code=head&63;require(code in KINDS)
            r=dict(id=i,offset=at,bytes=limit-at,header=head,kind=KINDS[code],code=code)
            if code in (1,3,4):
                r['bounds']=c.bounds(bool(head&128))
                if code==1:r['element_type']=c.u32()
            elif code in (2,9,15):r['bounds']=c.bounds(False)
            elif code in (6,7,14):
                b=c.bounds(False);r['bounds']=b
                if head&128:count=b['max']-b['min']+1
                else:
                    t=c.octet();require(t<=5);count=int.from_bytes(c.take(2**(t//2)),'big')
                require(0<=count<=20000);r['count']=count
                r['tags']=list(range(b['min'],b['max']+1)) if head&128 else [c.integer(b['int_type']) for _ in range(count)]
                if code!=7:require(len(set(r['tags']))==count)
                if code in (6,14):r['field_types']=[c.u32() for _ in range(count)]
            elif code in (11,16):r['element_type']=c.u32()
            if c.at!=limit:
                require(i==n-1 and 0<=limit-c.at<=3 and not any(c.take(limit-c.at)))
            require(all(0<=child<n for child in r.get('field_types',[])+([r['element_type']] if 'element_type'in r else [])))
            self.records.append(r)
        lengths=[1+r.get('count',0) if r['code']in(6,7,14) else 1 for r in self.records]
        pool=max(ptr+4*length for ptr,length in zip(dumps,lengths) if ptr)
        require(pool==194764 and (pool-dump_start)%4==0)
        names={pool+m.start():m.group().decode('ascii') for m in re.finditer(rb'[^\0]+',raw[pool:])}
        require(len(names)==6937 and all(0<len(s)<=512 and all(32<=ord(c)<=126 for c in s) for s in names.values()))
        words=struct.unpack_from('>'+str((pool-dump_start)//4)+'I',raw,dump_start)
        require(all(ptr==0 or ptr in names for ptr in words))
        self.by_name={}
        for r,ptr,length in zip(self.records,dumps,lengths):
            require(ptr==0 or dump_start<=ptr and ptr+4*length<=pool and (ptr-dump_start)%4==0)
            entries=[struct.unpack_from('>I',raw,ptr+4*j)[0] if ptr else 0 for j in range(length)]
            r['name']=names[entries[0]] if entries[0] else None
            if r['name']:self.by_name.setdefault(r['name'],[]).append(r['id'])
            if r['code']in(6,7,14):r['field_names']=[names[v] if v else None for v in entries[1:]]
        require(self.by_name['Battlenet::Client::S2GameDefines::ClientInfo']==[1768])
    def closure(self,start=1768):
        visited=set();todo=[start]
        while todo:
            i=todo.pop()
            if i in visited:continue
            visited.add(i);r=self.records[i]
            todo+=r.get('field_types',[])+([r['element_type']] if 'element_type'in r else [])
            require(len(visited)<=512)
        return [self.records[i] for i in sorted(visited)]
