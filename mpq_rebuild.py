from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

from mpq_reader import MPQArchive

EXISTS = 0x80000000
SINGLE = 0x01000000
COMPRESS = 0x00000200
ENCRYPTED = 0x00010000


def encrypt_table(data: bytes, key: int, table: dict[int, int]) -> bytes:
    if len(data) % 4:
        raise ValueError('Table is not DWORD aligned')
    result = bytearray()
    seed = 0xEEEEEEEE
    for (plain,) in struct.iter_unpack('<I', data):
        seed = (seed + table[0x400 + (key & 255)]) & 0xFFFFFFFF
        result.extend(struct.pack('<I', (plain ^ (key + seed)) & 0xFFFFFFFF))
        key = (((~key << 21) + 0x11111111) | (key >> 11)) & 0xFFFFFFFF
        seed = (plain + seed + (seed << 5) + 3) & 0xFFFFFFFF
    return bytes(result)


def update_attributes(raw: bytes, count: int, replacements: dict[int, bytes]) -> bytes:
    if len(raw) < 8:
        raise ValueError('Truncated MPQ attributes')
    version, flags = struct.unpack_from('<II', raw)
    if version != 100 or flags & ~7:
        raise ValueError(f'Unsupported MPQ attributes: version={version}, flags={flags}')
    expected = 8 + count * ((4 if flags & 1 else 0) + (8 if flags & 2 else 0) + (16 if flags & 4 else 0))
    if len(raw) != expected:
        raise ValueError(f'MPQ attributes size {len(raw)} != {expected}')
    data = bytearray(raw)
    md5_offset = 8 + count * ((4 if flags & 1 else 0) + (8 if flags & 2 else 0))
    for index, value in replacements.items():
        if not 0 <= index < count:
            raise ValueError('Invalid attribute index')
        if flags & 1:
            struct.pack_into('<I', data, 8 + 4 * index, zlib.crc32(value) & 0xFFFFFFFF)
        if flags & 4:
            data[md5_offset + 16 * index:md5_offset + 16 * (index + 1)] = hashlib.md5(value).digest()
    return bytes(data)


def rebuild_replay(source: Path, output: Path, user_data: bytes, replacements: dict[str, bytes]) -> dict:
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('Source replay must not be overwritten')
    original = source.read_bytes()
    archive = MPQArchive(source)
    try:
        header = archive.header
        if header['format_version'] != 3 or header['header_size'] != 208:
            raise ValueError('This writer requires an MPQ v4 source')
        base = header['offset']
        if struct.unpack_from('<Q', original, base + 32)[0] or any(struct.unpack_from('<HH', original, base + 40)):
            raise ValueError('MPQ offsets above 4 GiB are not supported')
        if archive.get_hash_table_entry('(signature)') is not None:
            raise ValueError('Signed archives require explicit signature handling')
        indexed = {}
        for name, raw in replacements.items():
            entry = archive.get_hash_table_entry(name)
            if entry is None:
                raise KeyError(name)
            if entry.block_table_index in indexed:
                raise ValueError('Duplicate block replacement')
            indexed[entry.block_table_index] = bytes(raw)
        attributes = archive.get_hash_table_entry('(attributes)')
        if attributes is not None and indexed:
            idx = attributes.block_table_index
            if idx in indexed:
                raise ValueError('Attributes are managed automatically')
            indexed[idx] = update_attributes(archive.read_file('(attributes)'), len(archive.block_table), indexed)
        data = bytearray(208)
        blocks = []
        changed = []
        for index, entry in enumerate(archive.block_table):
            if entry.flags & ENCRYPTED:
                raise ValueError('Encrypted member relocation is not supported')
            if index in indexed:
                raw = indexed[index]
                compressed = b'\x02' + zlib.compress(raw, 9)
                payload = compressed if len(compressed) < len(raw) else raw
                flags = EXISTS | SINGLE | (COMPRESS if payload is compressed else 0)
                size = len(raw)
                changed.append(index)
            else:
                start = base + entry.offset
                payload = original[start:start + entry.archived_size]
                if len(payload) != entry.archived_size:
                    raise ValueError('Truncated archived member')
                flags, size = entry.flags, entry.size
            offset = len(data) if payload else 0
            data.extend(payload)
            blocks.append((offset, len(payload), size, flags))
        hash_plain = b''.join(struct.pack('<IIHHI', *entry) for entry in archive.hash_table)
        hash_data = encrypt_table(hash_plain, archive._hash('(hash table)', 'TABLE'), archive.encryption_table)
        block_plain = b''.join(struct.pack('<IIII', *entry) for entry in blocks)
        block_data = encrypt_table(block_plain, archive._hash('(block table)', 'TABLE'), archive.encryption_table)
        hash_offset = len(data)
        data.extend(hash_data)
        block_offset = len(data)
        data.extend(block_data)
        if len(data) > 0xFFFFFFFF:
            raise ValueError('Archive exceeds supported size')
        struct.pack_into('<4sIIHHIIII', data, 0, b'MPQ\x1a', 208, len(data), 3,
                         header['sector_size_shift'], hash_offset, block_offset,
                         len(archive.hash_table), len(blocks))
        struct.pack_into('<Q', data, 44, len(data))
        struct.pack_into('<QQ', data, 68, len(hash_data), len(block_data))
        data[112:128] = hashlib.md5(block_data).digest()
        data[128:144] = hashlib.md5(hash_data).digest()
        data[192:208] = hashlib.md5(data[:192]).digest()
        prefix_size = max(header['offset'], ((16 + len(user_data) + 511) // 512) * 512)
        prefix = bytearray(prefix_size)
        capacity = max(header['user_data_header']['user_data_size'], len(user_data))
        if capacity + 16 > prefix_size:
            raise ValueError('Insufficient MPQ user-data capacity')
        struct.pack_into('<4sIII', prefix, 0, b'MPQ\x1b', capacity, prefix_size, len(user_data))
        prefix[16:16 + len(user_data)] = user_data
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(prefix + data)
        return {'format': 'MPQ-v4-classic-tables', 'changed_block_indices': changed,
                'het_bet_tables': 'removed; classic hash/block tables rebuilt',
                'raw_chunk_size': 0, 'member_crc32_md5_updated': attributes is not None,
                'archive_size': len(data)}
    finally:
        archive.close()


def verify_container(path: Path) -> dict:
    image = Path(path).read_bytes()
    archive = MPQArchive(path)
    try:
        h = archive.header
        base = h['offset']
        if h['format_version'] != 3 or h['header_size'] != 208:
            raise ValueError('Expected MPQ v4')
        if hashlib.md5(image[base:base + 192]).digest() != image[base + 192:base + 208]:
            raise ValueError('MPQ header MD5 mismatch')
        if struct.unpack_from('<Q', image, base + 44)[0] != h['archive_size']:
            raise ValueError('32/64-bit archive sizes disagree')
        if len(image) != base + h['archive_size']:
            raise ValueError('Archive length mismatch')
        if struct.unpack_from('<I', image, base + 108)[0] != 0:
            raise ValueError('Raw-chunk verification is not supported by this validator')
        for kind, digest_offset, size_offset in [('hash', 128, 68), ('block', 112, 76)]:
            offset = base + h[f'{kind}_table_offset']
            length = h[f'{kind}_table_entries'] * 16
            if length != struct.unpack_from('<Q', image, base + size_offset)[0]:
                raise ValueError(f'{kind} table size mismatch')
            if hashlib.md5(image[offset:offset + length]).digest() != image[base + digest_offset:base + digest_offset + 16]:
                raise ValueError(f'{kind} table MD5 mismatch')
        table_ranges = [(h['hash_table_offset'], h['hash_table_offset'] + 16 * h['hash_table_entries']),
                        (h['block_table_offset'], h['block_table_offset'] + 16 * h['block_table_entries'])]
        spans = [(0, 208)] + table_ranges
        for block in archive.block_table:
            if block.archived_size:
                if block.offset + block.archived_size > h['archive_size']:
                    raise ValueError('Member outside archive')
                spans.append((block.offset, block.offset + block.archived_size))
        spans.sort()
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise ValueError('Overlapping archive regions')
        return {'header_md5': True, 'table_md5': True, 'sizes': True, 'non_overlapping_regions': True}
    finally:
        archive.close()
