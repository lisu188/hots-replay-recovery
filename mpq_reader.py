import bz2
import struct
import zlib
from collections import namedtuple
from io import BytesIO

MPQ_FILE_IMPLODE=0x00000100
MPQ_FILE_COMPRESS=0x00000200
MPQ_FILE_ENCRYPTED=0x00010000
MPQ_FILE_FIX_KEY=0x00020000
MPQ_FILE_SINGLE_UNIT=0x01000000
MPQ_FILE_DELETE_MARKER=0x02000000
MPQ_FILE_SECTOR_CRC=0x04000000
MPQ_FILE_EXISTS=0x80000000

MPQFileHeader=namedtuple('MPQFileHeader','magic header_size archive_size format_version sector_size_shift hash_table_offset block_table_offset hash_table_entries block_table_entries')
MPQFileHeader.struct_format='<4s2I2H4I'
MPQFileHeaderExt=namedtuple('MPQFileHeaderExt','extended_block_table_offset hash_table_offset_high block_table_offset_high')
MPQFileHeaderExt.struct_format='<q2h'
MPQUserDataHeader=namedtuple('MPQUserDataHeader','magic user_data_size mpq_header_offset user_data_header_size')
MPQUserDataHeader.struct_format='<4s3I'
MPQHashTableEntry=namedtuple('MPQHashTableEntry','hash_a hash_b locale platform block_table_index')
MPQHashTableEntry.struct_format='<2I2HI'
MPQBlockTableEntry=namedtuple('MPQBlockTableEntry','offset archived_size size flags')
MPQBlockTableEntry.struct_format='<4I'

class MPQArchive:
    def __init__(self, filename):
        self.file=open(filename,'rb')
        self.header=self.read_header()
        self.hash_table=self.read_table('hash')
        self.block_table=self.read_table('block')
    def close(self):
        if self.file:
            self.file.close(); self.file=None
    def read_header(self):
        self.file.seek(0)
        magic=self.file.read(4); self.file.seek(0)
        def mpq_header(offset=0):
            self.file.seek(offset)
            data=self.file.read(32)
            h=MPQFileHeader._make(struct.unpack(MPQFileHeader.struct_format,data))._asdict()
            if h['format_version']==1:
                h.update(MPQFileHeaderExt._make(struct.unpack(MPQFileHeaderExt.struct_format,self.file.read(12)))._asdict())
            return h
        if magic==b'MPQ\x1a':
            h=mpq_header(0); h['offset']=0; return h
        if magic==b'MPQ\x1b':
            data=self.file.read(16)
            uh=MPQUserDataHeader._make(struct.unpack(MPQUserDataHeader.struct_format,data))._asdict()
            uh['content']=self.file.read(uh['user_data_header_size'])
            h=mpq_header(uh['mpq_header_offset']); h['offset']=uh['mpq_header_offset']; h['user_data_header']=uh; return h
        raise ValueError('Invalid MPQ header')
    def read_table(self, kind):
        cls=MPQHashTableEntry if kind=='hash' else MPQBlockTableEntry
        off=self.header[f'{kind}_table_offset']+self.header['offset']
        count=self.header[f'{kind}_table_entries']
        key=self._hash(f'({kind} table)','TABLE')
        self.file.seek(off)
        data=self._decrypt(self.file.read(count*16),key)
        return [cls._make(struct.unpack(cls.struct_format,data[i*16:i*16+16])) for i in range(count)]
    def get_hash_table_entry(self, filename):
        if isinstance(filename,str): filename=filename.encode()
        a=self._hash(filename,'HASH_A'); b=self._hash(filename,'HASH_B')
        for e in self.hash_table:
            if e.hash_a==a and e.hash_b==b: return e
        return None
    def read_file(self, filename, force_decompress=False):
        he=self.get_hash_table_entry(filename)
        if he is None: return None
        be=self.block_table[he.block_table_index]
        if not (be.flags & MPQ_FILE_EXISTS): return None
        if be.archived_size==0:
            if be.size!=0: raise ValueError('Nonempty MPQ member has no archived payload')
            return b''
        self.file.seek(be.offset+self.header['offset'])
        data=self.file.read(be.archived_size)
        if be.flags & MPQ_FILE_ENCRYPTED: raise NotImplementedError('Encrypted MPQ files unsupported')
        def decompress(d):
            t=d[0]
            if t==0: return d
            if t==2: return zlib.decompress(d[1:],15)
            if t==16: return bz2.decompress(d[1:])
            raise RuntimeError(f'Unsupported compression type {t}')
        if not (be.flags & MPQ_FILE_SINGLE_UNIT):
            sector_size=512 << self.header['sector_size_shift']
            sectors=be.size//sector_size+1
            crc=bool(be.flags & MPQ_FILE_SECTOR_CRC)
            if crc: sectors+=1
            positions=struct.unpack(f'<{sectors+1}I',data[:4*(sectors+1)])
            out=BytesIO(); left=be.size
            for i in range(len(positions)-(2 if crc else 1)):
                sector=data[positions[i]:positions[i+1]]
                if be.flags & MPQ_FILE_COMPRESS and (force_decompress or left>len(sector)):
                    sector=decompress(sector)
                left-=len(sector); out.write(sector)
            return out.getvalue()
        if be.flags & MPQ_FILE_COMPRESS and (force_decompress or be.size>be.archived_size):
            data=decompress(data)
        return data
    @staticmethod
    def _prepare_encryption_table():
        seed=0x00100001; table={}
        for i in range(256):
            idx=i
            for _ in range(5):
                seed=(seed*125+3)%0x2AAAAB; t1=(seed & 0xFFFF)<<16
                seed=(seed*125+3)%0x2AAAAB; t2=seed & 0xFFFF
                table[idx]=t1|t2; idx+=0x100
        return table
    def _hash(self,s,hash_type):
        if isinstance(s,str): s=s.encode()
        types={'TABLE_OFFSET':0,'HASH_A':1,'HASH_B':2,'TABLE':3}
        seed1=0x7FED7FED; seed2=0xEEEEEEEE
        for ch in s.upper():
            value=self.encryption_table[(types[hash_type]<<8)+ch]
            seed1=(value ^ (seed1+seed2)) & 0xFFFFFFFF
            seed2=(ch+seed1+seed2+(seed2<<5)+3)&0xFFFFFFFF
        return seed1
    def _decrypt(self,data,key):
        seed1=key; seed2=0xEEEEEEEE; out=BytesIO()
        for i in range(len(data)//4):
            seed2=(seed2+self.encryption_table[0x400+(seed1&0xFF)])&0xFFFFFFFF
            value=struct.unpack('<I',data[i*4:i*4+4])[0]
            value=(value ^ (seed1+seed2))&0xFFFFFFFF
            seed1=(((~seed1<<0x15)+0x11111111)|(seed1>>0x0B))&0xFFFFFFFF
            seed2=(value+seed2+(seed2<<5)+3)&0xFFFFFFFF
            out.write(struct.pack('<I',value))
        return out.getvalue()
    encryption_table=_prepare_encryption_table.__func__()
