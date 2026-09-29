from __future__ import annotations

import bz2
import struct
import zlib

MAX_MEMBER = 32 * 1024 * 1024
EXISTS = 0x80000000
COMPRESS = 0x200
ENCRYPTED = 0x10000
SINGLE_UNIT = 0x01000000
SECTOR_CRC = 0x04000000


def unpack_sector(raw: bytes, expected: int) -> bytes:
    if not 0 < expected <= MAX_MEMBER or not raw or len(raw) > expected:
        raise ValueError('Invalid sector lengths')
    if len(raw) == expected:
        return raw
    if raw[0] == 2:
        decoder = zlib.decompressobj()
        output = decoder.decompress(raw[1:], expected + 1)
        complete = decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    elif raw[0] == 16:
        decoder = bz2.BZ2Decompressor()
        output = decoder.decompress(raw[1:], max_length=expected + 1)
        complete = decoder.eof and not decoder.unused_data
    else:
        raise ValueError(f'Unsupported compressed-sector mask: {raw[0]}')
    if len(output) != expected or not complete:
        raise ValueError('Compressed sector is truncated, oversized or has trailing data')
    return output


def decode_storage(raw: bytes, size: int, flags: int, shift: int) -> bytes:
    if type(size) is not int or not 0 <= size <= MAX_MEMBER or len(raw) > MAX_MEMBER:
        raise ValueError('Member exceeds size limits')
    if flags & ENCRYPTED or flags & 0x100 or not flags & EXISTS:
        raise ValueError('Encrypted, imploded or unallocated member is unsupported')
    if size == 0:
        if raw:
            raise ValueError('Nonempty storage for an empty member is unsupported')
        return b''
    if not flags & COMPRESS:
        if len(raw) != size:
            raise ValueError('Raw member length differs from the block table')
        return raw
    if flags & SINGLE_UNIT:
        return unpack_sector(raw, size)
    if type(shift) is not int or not 0 <= shift <= 15:
        raise ValueError('Invalid sector size shift')
    sector_size = 512 << shift
    count = (size + sector_size - 1) // sector_size
    offset_count = count + 1 + bool(flags & SECTOR_CRC)
    table_size = offset_count * 4
    if len(raw) < table_size:
        raise ValueError('Truncated sector-offset table')
    offsets = struct.unpack(f'<{offset_count}I', raw[:table_size])
    if offsets[0] != table_size or offsets[-1] != len(raw):
        raise ValueError('Sector offsets do not span the exact stored payload')
    if any(a > b or b > len(raw) for a, b in zip(offsets, offsets[1:])):
        raise ValueError('Reversed or out-of-bounds sector offset')
    result = bytearray()
    for index in range(count):
        expected = min(sector_size, size - index * sector_size)
        result.extend(unpack_sector(raw[offsets[index]:offsets[index + 1]], expected))
    if len(result) != size:
        raise ValueError('Extracted member size differs from its block table')
    return bytes(result)


def read_member(archive, name: str) -> bytes:
    entry = archive.get_hash_table_entry(name)
    if entry is None:
        raise ValueError('Missing member: ' + name)
    index = entry.block_table_index
    if not 0 <= index < len(archive.block_table):
        raise ValueError('Invalid block-table index')
    block = archive.block_table[index]
    start = archive.header['offset'] + block.offset
    if not 0 <= block.archived_size <= MAX_MEMBER or start < 0:
        raise ValueError('Invalid archive allocation')
    position = archive.file.tell()
    try:
        archive.file.seek(0, 2)
        if start + block.archived_size > archive.file.tell():
            raise ValueError('Member allocation exceeds the file')
        archive.file.seek(start)
        raw = archive.file.read(block.archived_size)
        if len(raw) != block.archived_size:
            raise ValueError('Short archive read')
        return decode_storage(raw, block.size, block.flags, archive.header['sector_size_shift'])
    finally:
        archive.file.seek(position)
