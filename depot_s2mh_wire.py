"""Bounded generic versioned-wire decoder; decoded blobs stay private in RAM.

Wire tags independently documented by Blizzard's versioned decoder and pinned
sc2-arcade-watcher/s2mdec/versioneddec.go. No mapheader writer is implemented.
"""
from dataclasses import dataclass
import hashlib


@dataclass
class Choice:
    tag: int
    value: object


@dataclass
class BitArray:
    count: int
    raw: bytes


class Reader:
    def __init__(self, raw):
        if not isinstance(raw, bytes) or len(raw) > 2 * 1024 * 1024:
            raise ValueError('Bounded bytes required')
        self.raw, self.pos, self.nodes = raw, 0, 0

    def take(self, count):
        if type(count) is not int or count < 0 or self.pos + count > len(self.raw):
            raise ValueError('Truncated or invalid versioned-wire field')
        value = self.raw[self.pos:self.pos + count]
        self.pos += count
        return value

    def vint(self):
        value = 0
        for shift in range(0, 70, 7):
            byte = self.take(1)[0]
            value |= (byte & 127) << shift
            if not byte & 128:
                return -(value >> 1) if value & 1 else value >> 1
        raise ValueError('Overlong varint')

    def count(self):
        count = self.vint()
        if not 0 <= count <= 200000:
            raise ValueError('Count exceeds depot decoder budget')
        return count

    def read(self, depth=0):
        self.nodes += 1
        if self.nodes > 200000 or depth > 64:
            raise ValueError('Versioned-wire node or depth budget exceeded')
        tag = self.take(1)[0]
        if tag == 0:
            return [self.read(depth + 1) for _ in range(self.count())]
        if tag == 1:
            count = self.count()
            return BitArray(count, self.take((count + 7) // 8))
        if tag == 2:
            return self.take(self.count())
        if tag == 3:
            return Choice(self.vint(), self.read(depth + 1))
        if tag == 4:
            exists = self.take(1)[0]
            if exists not in (0, 1):
                raise ValueError('Noncanonical optional flag')
            return self.read(depth + 1) if exists else None
        if tag == 5:
            output = {}
            for _ in range(self.count()):
                key = self.vint()
                if key in output:
                    raise ValueError('Duplicate struct field')
                output[key] = self.read(depth + 1)
            return output
        if tag == 6:
            return self.take(1)[0]
        if tag in (7, 8):
            return self.take(4 if tag == 7 else 8)
        if tag == 9:
            return self.vint()
        raise ValueError('Unknown versioned-wire tag')


def decode_verified_header(raw, expected_sha256):
    """Decode a bounded content-addressed header; return private values in RAM."""
    if type(expected_sha256) is not str or len(expected_sha256) != 64 or any(x not in '0123456789abcdef' for x in expected_sha256):
        raise ValueError('An explicit canonical SHA256 is required')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 2 * 1024 * 1024:
        raise ValueError('Bounded header bytes required')
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Depot header content digest differs')
    reader = Reader(raw)
    value = reader.read()
    if reader.pos != len(raw):
        raise ValueError('Trailing bytes remain after depot header')
    if type(value) is not dict or set(value) != {0, 1} or type(value[0]) is not dict:
        raise ValueError('Expected exact outer depot mapheader structure')
    return value
