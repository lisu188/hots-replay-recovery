import struct

class BitPackedWriter:
    def __init__(self, endian='big'):
        self.data=bytearray(); self.bitpos=0; self.bigendian=endian=='big'
    def write_bits(self,value,bits):
        if value < 0 or value >= (1<<bits):
            raise ValueError(f'value {value} does not fit {bits} bits')
        remaining=bits
        consumed=0
        while remaining:
            if self.bitpos==0: self.data.append(0)
            copybits=min(remaining,8-self.bitpos)
            if self.bigendian:
                shift=remaining-copybits
                chunk=(value>>shift)&((1<<copybits)-1)
            else:
                chunk=(value>>consumed)&((1<<copybits)-1)
            self.data[-1] |= chunk<<self.bitpos
            self.bitpos+=copybits
            remaining-=copybits
            consumed+=copybits
            if self.bitpos==8: self.bitpos=0
    def byte_align(self):
        if self.bitpos: self.bitpos=0
    def write_aligned_bytes(self,b):
        self.byte_align(); self.data.extend(b)
    def getvalue(self): return bytes(self.data)

class BitPackedEncoder:
    def __init__(self,typeinfos): self._buffer=BitPackedWriter(); self._typeinfos=typeinfos
    def instance(self,typeid,value):
        info=self._typeinfos[typeid]; return getattr(self,info[0])(*info[1],value)
    def byte_align(self): self._buffer.byte_align()
    def getvalue(self): return self._buffer.getvalue()
    def _array(self,bounds,typeid,value):
        self._int(bounds,len(value))
        for x in value: self.instance(typeid,x)
    def _bitarray(self,bounds,value):
        n,bits=value; self._int(bounds,n); self._buffer.write_bits(bits,n)
    def _blob(self,bounds,value):
        self._int(bounds,len(value)); self._buffer.write_aligned_bytes(value)
    def _bool(self,value): self._int((0,1),1 if value else 0)
    def _choice(self,bounds,fields,value):
        if len(value)!=1: raise ValueError(f'choice must have exactly one key: {value!r}')
        name=next(iter(value)); match=next((tag_info for tag_info in fields.items() if tag_info[1][0]==name),None)
        if match is None: raise ValueError(f'unknown choice {name}')
        tag,(_,tid)=match; self._int(bounds,tag); self.instance(tid,value[name])
    def _fourcc(self,value):
        if isinstance(value,str): value=value.encode('ascii')
        self._buffer.write_bits(int.from_bytes(value,'big'),32)
    def _int(self,bounds,value): self._buffer.write_bits(value-bounds[0],bounds[1])
    def _null(self,value=None): pass
    def _optional(self,typeid,value):
        self._bool(value is not None)
        if value is not None: self.instance(typeid,value)
    def _real32(self,value):
        for b in struct.pack('!f',value): self._buffer.write_bits(b,8)
    def _real64(self,value):
        for b in struct.pack('!d',value): self._buffer.write_bits(b,8)
    def _struct(self,fields,value):
        for name,tid,_tag in fields:
            if name=='__parent': self.instance(tid,value)
            else: self.instance(tid,value[name])

class VersionedEncoder:
    def __init__(self,typeinfos): self._buffer=BitPackedWriter(); self._typeinfos=typeinfos
    def instance(self,typeid,value):
        info=self._typeinfos[typeid]; return getattr(self,info[0])(*info[1],value)
    def getvalue(self): return self._buffer.getvalue()
    def _byte(self,b): self._buffer.write_aligned_bytes(bytes([b]))
    def _vint(self,value):
        neg=value<0; x=-value if neg else value
        b=((x & 0x3f)<<1) | (1 if neg else 0); x >>= 6
        if x: b|=0x80
        self._byte(b)
        while x:
            b=x & 0x7f; x >>= 7
            if x: b|=0x80
            self._byte(b)
    def _array(self,bounds,typeid,value):
        self._byte(0); self._vint(len(value))
        for x in value: self.instance(typeid,x)
    def _bitarray(self,bounds,value):
        self._byte(1); n,b=value; self._vint(n)
        if isinstance(b,int): b=b.to_bytes((n+7)//8,'big')
        self._buffer.write_aligned_bytes(b)
    def _blob(self,bounds,value): self._byte(2); self._vint(len(value)); self._buffer.write_aligned_bytes(value)
    def _bool(self,value): self._byte(6); self._byte(1 if value else 0)
    def _choice(self,bounds,fields,value):
        self._byte(3)
        if len(value)!=1: raise ValueError(f'choice must have exactly one key: {value!r}')
        name=next(iter(value)); match=next((x for x in fields.items() if x[1][0]==name),None)
        if match is None: raise ValueError(f'unknown choice {name}')
        tag,(_,tid)=match; self._vint(tag); self.instance(tid,value[name])
    def _fourcc(self,value):
        self._byte(7)
        if isinstance(value,str): value=value.encode('ascii')
        self._buffer.write_aligned_bytes(value)
    def _int(self,bounds,value): self._byte(9); self._vint(value)
    def _null(self,value=None): pass
    def _optional(self,typeid,value):
        self._byte(4); self._byte(1 if value is not None else 0)
        if value is not None: self.instance(typeid,value)
    def _real32(self,value): self._byte(7); self._buffer.write_aligned_bytes(struct.pack('>f',value))
    def _real64(self,value): self._byte(8); self._buffer.write_aligned_bytes(struct.pack('>d',value))
    def _struct(self,fields,value):
        self._byte(5)
        encoded=[]
        for name,tid,tag in fields:
            if name=='__parent':
                encoded.append((tag,tid,value))
            elif name in value:
                encoded.append((tag,tid,value[name]))
        self._vint(len(encoded))
        for tag,tid,v in encoded:
            self._vint(tag); self.instance(tid,v)

def _event_stream(events,typeinfos,eventid_typeid,event_types,decode_user_id,versioned=False):
    enc=VersionedEncoder(typeinfos) if versioned else BitPackedEncoder(typeinfos)
    previous=0
    for event in events:
        gl=event['_gameloop']; delta=gl-previous; previous=gl
        choice={}
        if delta < 64: choice={'m_uint6':delta}
        elif delta < 16384: choice={'m_uint14':delta}
        elif delta < 4194304: choice={'m_uint22':delta}
        else: choice={'m_uint32':delta}
        enc.instance(7,choice)
        if decode_user_id: enc.instance(8,event['_userid'])
        eid=event['_eventid']; enc.instance(eventid_typeid,eid)
        tid,_=event_types[eid]; enc.instance(tid,event)
        if not versioned: enc.byte_align()
    return enc.getvalue()

def encode_game_events(events,p): return _event_stream(events,p.typeinfos,p.game_eventid_typeid,p.game_event_types,True,False)
def encode_message_events(events,p): return _event_stream(events,p.typeinfos,p.message_eventid_typeid,p.message_event_types,True,False)
def encode_tracker_events(events,p): return _event_stream(events,p.typeinfos,p.tracker_eventid_typeid,p.tracker_event_types,False,True)
def encode_header(value,p):
    e=VersionedEncoder(p.typeinfos); e.instance(p.replay_header_typeid,value); return e.getvalue()
def encode_details(value,p):
    e=VersionedEncoder(p.typeinfos); e.instance(p.game_details_typeid,value); return e.getvalue()
def encode_initdata(value,p):
    e=BitPackedEncoder(p.typeinfos); e.instance(p.replay_initdata_typeid,value); return e.getvalue()
