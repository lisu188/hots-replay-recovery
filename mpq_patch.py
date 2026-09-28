import bz2
import struct
import zlib
from pathlib import Path

from mpq_reader import MPQArchive, MPQ_FILE_COMPRESS


def encrypt_table(data, key, encryption_table):
    if len(data) % 4:
        raise ValueError('MPQ encrypted table length must be divisible by four')
    seed1=key; seed2=0xEEEEEEEE; out=bytearray()
    for i in range(0,len(data),4):
        plain=struct.unpack('<I',data[i:i+4])[0]
        seed2=(seed2+encryption_table[0x400+(seed1&0xFF)])&0xFFFFFFFF
        cipher=(plain ^ (seed1+seed2))&0xFFFFFFFF
        seed1=(((~seed1<<0x15)+0x11111111)|(seed1>>0x0B))&0xFFFFFFFF
        seed2=(plain+seed2+(seed2<<5)+3)&0xFFFFFFFF
        out.extend(struct.pack('<I',cipher))
    return bytes(out)


def best_mpq_payload(raw, max_size=None):
    candidates=[]
    z=b'\x02'+zlib.compress(raw,9)
    candidates.append(('zlib',z))
    for level in (1,6,9):
        candidates.append((f'bzip2-{level}',b'\x10'+bz2.compress(raw,compresslevel=level)))
    candidates.append(('raw',raw))
    candidates.sort(key=lambda x:len(x[1]))
    if max_size is None:
        return candidates[0]
    for candidate in candidates:
        if len(candidate[1])<=max_size:
            return candidate
    raise ValueError(f'no encoding fits allocation {max_size}; best is {len(candidates[0][1])}')


def patch_replay(source_path, output_path, user_data, replacements):
    source_path=Path(source_path); output_path=Path(output_path)
    archive=MPQArchive(source_path)
    image=bytearray(source_path.read_bytes())

    uh=archive.header.get('user_data_header')
    if not uh:
        raise ValueError('StormReplay lacks MPQ user-data header')
    if len(user_data)!=uh['user_data_header_size']:
        raise ValueError(f'user-data size changed: {len(user_data)} != {uh["user_data_header_size"]}')
    image[16:16+len(user_data)]=user_data

    entries=[list(x) for x in archive.block_table]
    report={}
    for name,raw in replacements.items():
        he=archive.get_hash_table_entry(name)
        if he is None: raise KeyError(name)
        idx=he.block_table_index; old=archive.block_table[idx]
        method,payload=best_mpq_payload(raw,old.archived_size)
        absolute=archive.header['offset']+old.offset
        image[absolute:absolute+len(payload)]=payload
        if len(payload)<old.archived_size:
            image[absolute+len(payload):absolute+old.archived_size]=b'\x00'*(old.archived_size-len(payload))
        entries[idx][1]=len(payload)
        entries[idx][2]=len(raw)
        if len(payload)<len(raw): entries[idx][3] |= MPQ_FILE_COMPRESS
        report[name]={
            'block_index':idx,
            'method':method,
            'old_archived_size':old.archived_size,
            'new_archived_size':len(payload),
            'old_size':old.size,
            'new_size':len(raw),
            'allocation_remaining':old.archived_size-len(payload),
        }

    plain=b''.join(struct.pack('<4I',*entry) for entry in entries)
    key=archive._hash('(block table)','TABLE')
    encrypted=encrypt_table(plain,key,archive.encryption_table)
    table_at=archive.header['offset']+archive.header['block_table_offset']
    image[table_at:table_at+len(encrypted)]=encrypted
    output_path.write_bytes(image)
    return report
