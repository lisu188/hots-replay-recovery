import struct

class CorruptedError(Exception): pass
class TruncatedError(Exception): pass

class BitPackedBuffer:
    def __init__(self, contents, endian='big'):
        self._data=bytes(contents) if contents else b''
        self._used=0; self._next=0; self._nextbits=0; self._bigendian=endian=='big'
    def __str__(self):
        s=f'{self._data[self._used]:02x}' if self._used < len(self._data) else '--'
        return f'buffer({self._next if self._nextbits else 0:02x}/{self._nextbits:d},[{self._used:d}]={s})'
    def done(self): return self._nextbits==0 and self._used>=len(self._data)
    def used_bits(self): return self._used*8-self._nextbits
    def byte_align(self): self._nextbits=0
    def read_aligned_bytes(self,n):
        self.byte_align(); d=self._data[self._used:self._used+n]; self._used+=n
        if len(d)!=n: raise TruncatedError(self)
        return d
    def read_bits(self,bits):
        result=0; resultbits=0
        while resultbits!=bits:
            if self._nextbits==0:
                if self.done(): raise TruncatedError(self)
                self._next=self._data[self._used]; self._used+=1; self._nextbits=8
            copybits=min(bits-resultbits,self._nextbits)
            copy=self._next & ((1<<copybits)-1)
            if self._bigendian: result |= copy << (bits-resultbits-copybits)
            else: result |= copy << resultbits
            self._next >>= copybits; self._nextbits-=copybits; resultbits+=copybits
        return result
    def read_unaligned_bytes(self,n): return bytes(self.read_bits(8) for _ in range(n))

class BitPackedDecoder:
    def __init__(self,contents,typeinfos): self._buffer=BitPackedBuffer(contents); self._typeinfos=typeinfos
    def __str__(self): return str(self._buffer)
    def instance(self,typeid):
        if typeid>=len(self._typeinfos): raise CorruptedError(self)
        info=self._typeinfos[typeid]; return getattr(self,info[0])(*info[1])
    def byte_align(self): self._buffer.byte_align()
    def done(self): return self._buffer.done()
    def used_bits(self): return self._buffer.used_bits()
    def _array(self,bounds,typeid): return [self.instance(typeid) for _ in range(self._int(bounds))]
    def _bitarray(self,bounds):
        n=self._int(bounds); return (n,self._buffer.read_bits(n))
    def _blob(self,bounds): return self._buffer.read_aligned_bytes(self._int(bounds))
    def _bool(self): return self._int((0,1))!=0
    def _choice(self,bounds,fields):
        tag=self._int(bounds)
        if tag not in fields: raise CorruptedError(self)
        name,tid=fields[tag]; return {name:self.instance(tid)}
    def _fourcc(self): return struct.pack('!I',self._buffer.read_bits(32))
    def _int(self,bounds): return bounds[0]+self._buffer.read_bits(bounds[1])
    def _null(self): return None
    def _optional(self,typeid): return self.instance(typeid) if self._bool() else None
    def _real32(self): return struct.unpack('!f',self._buffer.read_unaligned_bytes(4))[0]
    def _real64(self): return struct.unpack('!d',self._buffer.read_unaligned_bytes(8))[0]
    def _struct(self,fields):
        result={}
        for name,tid,_tag in fields:
            if name=='__parent':
                parent=self.instance(tid)
                if isinstance(parent,dict): result.update(parent)
                elif len(fields)==1: result=parent
                else: result[name]=parent
            else: result[name]=self.instance(tid)
        return result

class VersionedDecoder:
    def __init__(self,contents,typeinfos): self._buffer=BitPackedBuffer(contents); self._typeinfos=typeinfos
    def __str__(self): return str(self._buffer)
    def instance(self,typeid):
        if typeid>=len(self._typeinfos): raise CorruptedError(self)
        info=self._typeinfos[typeid]; return getattr(self,info[0])(*info[1])
    def byte_align(self): self._buffer.byte_align()
    def done(self): return self._buffer.done()
    def used_bits(self): return self._buffer.used_bits()
    def _expect_skip(self,expected):
        if self._buffer.read_bits(8)!=expected: raise CorruptedError(self)
    def _vint(self):
        b=self._buffer.read_bits(8); negative=b&1; result=(b>>1)&0x3f; bits=6
        while b&0x80:
            b=self._buffer.read_bits(8); result |= (b&0x7f)<<bits; bits+=7
        return -result if negative else result
    def _array(self,bounds,typeid):
        self._expect_skip(0); n=self._vint(); return [self.instance(typeid) for _ in range(n)]
    def _bitarray(self,bounds):
        self._expect_skip(1); n=self._vint(); return (n,self._buffer.read_aligned_bytes((n+7)//8))
    def _blob(self,bounds): self._expect_skip(2); return self._buffer.read_aligned_bytes(self._vint())
    def _bool(self): self._expect_skip(6); return self._buffer.read_bits(8)!=0
    def _choice(self,bounds,fields):
        self._expect_skip(3); tag=self._vint()
        if tag not in fields: self._skip_instance(); return {}
        name,tid=fields[tag]; return {name:self.instance(tid)}
    def _fourcc(self): self._expect_skip(7); return self._buffer.read_aligned_bytes(4)
    def _int(self,bounds): self._expect_skip(9); return self._vint()
    def _null(self): return None
    def _optional(self,typeid):
        self._expect_skip(4); exists=self._buffer.read_bits(8)!=0; return self.instance(typeid) if exists else None
    def _real32(self): self._expect_skip(7); return struct.unpack('>f',self._buffer.read_aligned_bytes(4))[0]
    def _real64(self): self._expect_skip(8); return struct.unpack('>d',self._buffer.read_aligned_bytes(8))[0]
    def _struct(self,fields):
        self._expect_skip(5); result={}; n=self._vint()
        for _ in range(n):
            tag=self._vint(); field=next((f for f in fields if f[2]==tag),None)
            if field:
                name,tid,_=field
                if name=='__parent':
                    parent=self.instance(tid)
                    if isinstance(parent,dict): result.update(parent)
                    elif len(fields)==1: result=parent
                    else: result[name]=parent
                else: result[name]=self.instance(tid)
            else: self._skip_instance()
        return result
    def _skip_instance(self):
        skip=self._buffer.read_bits(8)
        if skip==0:
            for _ in range(self._vint()): self._skip_instance()
        elif skip==1:
            n=self._vint(); self._buffer.read_aligned_bytes((n+7)//8)
        elif skip==2: self._buffer.read_aligned_bytes(self._vint())
        elif skip==3: self._vint(); self._skip_instance()
        elif skip==4:
            if self._buffer.read_bits(8)!=0: self._skip_instance()
        elif skip==5:
            for _ in range(self._vint()): self._vint(); self._skip_instance()
        elif skip==6: self._buffer.read_aligned_bytes(1)
        elif skip==7: self._buffer.read_aligned_bytes(4)
        elif skip==8: self._buffer.read_aligned_bytes(8)
        elif skip==9: self._vint()
        else: raise CorruptedError(f'Unknown skip {skip}')
