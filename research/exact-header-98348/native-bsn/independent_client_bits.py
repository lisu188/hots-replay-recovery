"""Independent bounded bitpacked data reader/encoder for native graph review.

Uses per-byte numeric bit strings and a separate operation encoder, not the
producer's _Reader/_Writer. Private decoded data are never serialized.
"""
from dataclasses import dataclass
from independent_bsn_graph import require

@dataclass(repr=False)
class Event:
    path:str
    code:int
    start:int
    end:int
    value:object

class Wire:
    def __init__(self,graph,raw,start):
        require(type(raw)is bytes and len(raw)<=8*1024*1024 and type(start)is int and 0<=start<len(raw)*8)
        self.g,self.raw,self.pos,self.start=graph,raw,start,start
        self.operations=[];self.events=[]
    def bits(self,n):
        require(type(n)is int and 0<=n<=64 and self.pos+n<=8*len(self.raw))
        if not n:return 0
        begin=self.pos;end=begin+n;pieces=[]
        while self.pos<end:
            take=min(end-self.pos,8-self.pos%8)
            group=(self.raw[self.pos//8]>>(self.pos%8))&((1<<take)-1)
            pieces.append(format(group,'0'+str(take)+'b'));self.pos+=take
        value=int(''.join(pieces),2)
        self.operations.append(('bits',begin,n,value));return value
    def blob(self,n):
        require(type(n)is int and 0<=n<=4096)
        require(self.bits((-self.pos)%8)==0)
        begin=self.pos;require(begin//8+n<=len(self.raw))
        value=self.raw[begin//8:begin//8+n];self.pos+=8*n
        self.operations.append(('blob',begin,n,value));return value
    def decode(self,i=1768,path='',depth=0):
        require(depth<=64 and len(self.events)<100000)
        r=self.g.records[i];code=r['code'];b=r.get('bounds');begin=self.pos
        if code==16:value=self.decode(r['element_type'],path,depth+1)
        elif code==14:value={name:self.decode(child,path+'/'+name,depth+1) for name,child in zip(r['field_names'],r['field_types'])}
        elif code==6:
            tag=self.bits(b['bits'])+b['min'];require(tag in r['tags']);at=r['tags'].index(tag)
            value=(tag,self.decode(r['field_types'][at],path+'/'+r['field_names'][at],depth+1))
        elif code==1:
            count=self.bits(b['bits'])+b['min'];require(0<=count<=min(32768,b['max']))
            value=[self.decode(r['element_type'],path+'/'+str(j),depth+1) for j in range(count)]
        elif code==11:value=self.decode(r['element_type'],path+'/value',depth+1) if self.bits(1) else None
        elif code in(2,4,15):
            count=self.bits(b['bits']+(2 if code==15 else 0))+b['min']
            require(0<=count<=min(4096,b['max']*(4 if code==15 else 1)))
            value=self.blob(count)
            if code==2:value.decode('ascii')
            if code==15:require(b['min']<=len(value.decode('utf8'))<=b['max'])
        elif code==3:
            count=self.bits(b['bits'])+b['min'];require(0<=count<=min(65536,b['max']))
            for at in range(0,count,64):self.bits(min(64,count-at))
            value=count
        elif code in(7,9):
            value=self.bits(b['bits'])+b['min'];require(b['min']<=value<=b['max'])
            if code==7:require(value in r['tags'])
        elif code in(5,8,12,13):value=self.bits({5:1,8:32,12:32,13:64}[code])
        else:require(code==10);value=None
        self.events.append(Event(path,code,begin,self.pos,value));return value
    def event(self,path,code=None):
        matches=[e for e in self.events if e.path==path and (code is None and e.code!=16 or code==e.code)]
        require(len(matches)==1);return matches[0]
    def exact_reencode(self):
        out=bytearray(len(self.raw))
        for kind,start,n,value in self.operations:
            if kind=='blob':out[start//8:start//8+n]=value;continue
            digits=format(value,'0'+str(n)+'b');position=start
            while digits:
                take=min(len(digits),8-position%8)
                out[position//8]|=int(digits[:take],2)<<(position%8)
                digits=digits[take:];position+=take
        return all(((out[at//8]^self.raw[at//8])&(1<<(at%8)))==0 for at in range(self.start,self.pos))
