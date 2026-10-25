"""Bounded wire-value model for the pinned native775 graph.

Anonymous tuples model STRUCT fields in declaration order. They are not native
object layouts. A caller must supply the independently recovered native STRING
sequence-count callback; no default Python text codec is substituted.
"""
import hashlib
import json
from collections import Counter

PROFILE_SHA256 = '0c9e5d80f745d9e8d7191e3bc3039fb9e07e1d2c5e83c0bbbeb081216e23395e'
PROFILE_BYTES = 46829
MAX_INPUT_BYTES = 1048576
MAX_NODES = 250000
MAX_DEPTH = 128
MAX_ARRAY_ELEMENTS = 100000


class Rejected(ValueError):
    """Messages contain type/cursor/reason only, never supplied values."""


def load_profile(raw):
    if type(raw) is not bytes or len(raw) != PROFILE_BYTES or hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise Rejected('profile pin')
    obj = json.loads(raw)
    records = {r['id']: r for r in obj['records']}
    if len(records) != 200 or obj['slot']['value'] != 775:
        raise Rejected('profile closure')
    return records


class Reader:
    def __init__(self, raw, records, string_count):
        if type(raw) is not bytes or len(raw) > MAX_INPUT_BYTES:
            raise Rejected('input type or research byte budget')
        if not callable(string_count):
            raise Rejected('native STRING callback required')
        self.raw = raw
        self.records = records
        self.string_count = string_count
        self.bit = 0
        self.nodes = 0
        self.array_elements = 0
        self.kinds = Counter()
        self.types = Counter()
        self.bounds_checks = Counter()
        self.string_instances = 0
        self.padding_spans = 0
        self.nonzero_padding_spans = 0

    def fail(self, kind='invalid wire value'):
        raise Rejected('bit%d:%s' % (self.bit, kind))

    def bits(self, width):
        # Native reads low available bits from each byte, placing each chunk
        # at the high end of the remaining result; see1A71740 assembly.
        if type(width) is not int or width < 0 or width > MAX_INPUT_BYTES * 8 or self.bit + width > len(self.raw) * 8:
            self.fail('truncated or unsupported width')
        result = 0
        remaining = width
        while remaining:
            take = min(remaining, 8 - self.bit % 8)
            remaining -= take
            chunk = (self.raw[self.bit // 8] >> (self.bit % 8)) & ((1 << take) - 1)
            result = (result << take) | chunk
            self.bit += take
        return result

    def align(self):
        width = (-self.bit) % 8
        if width:
            self.padding_spans += 1
            self.nonzero_padding_spans += bool(self.bits(width))

    def octets(self, length):
        self.align()
        if type(length) is not int or length < 0 or self.bit + length * 8 > len(self.raw) * 8:
            self.fail('truncated bytes')
        start = self.bit // 8
        self.bit += length * 8
        return self.raw[start:start + length]

    def count(self, record, derived_string=False):
        b = record['bounds']
        minimum, maximum, width = b['min'], b['max'], b['bits']
        if derived_string:
            width += 2
            maximum *= 4
        value = minimum + self.bits(width)
        self.bounds_checks[record['id']] += 1
        if not minimum <= value <= maximum:
            self.fail('native bounds type%d' % record['id'])
        return value

    def read(self, type_id=775, depth=0):
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            self.fail('research node/depth budget')
        r = self.records[type_id]
        kind = r['kind']
        self.kinds[kind] += 1
        self.types[type_id] += 1
        descend = lambda child: self.read(child, depth + 1)
        if kind == 'USER':
            return descend(r['element_type'])
        if kind == 'STRUCT':
            return tuple(descend(child) for child in r['field_types'])
        if kind == 'ARRAY':
            length = self.count(r)
            self.array_elements += length
            if self.array_elements > MAX_ARRAY_ELEMENTS:
                self.fail('research total array budget')
            return tuple(descend(r['element_type']) for _ in range(length))
        if kind == 'OPTIONAL':
            return descend(r['element_type']) if self.bits(1) else None
        if kind == 'BOOL':
            return bool(self.bits(1))
        if kind == 'INT':
            return self.count(r)
        if kind == 'ENUM':
            value = self.count(r)
            if value not in r['tags']:
                self.fail('native ENUM domain type%d' % type_id)
            return value
        if kind == 'FOURCC':
            return self.bits(32).to_bytes(4, 'big')
        if kind == 'BIT_ARRAY':
            length = self.count(r)
            return length, self.bits(length)
        if kind == 'BLOB':
            return self.octets(self.count(r))
        if kind == 'STRING':
            length = self.count(r, derived_string=True)
            value = self.octets(length)
            try:
                count = self.string_count(value)
            except ValueError:
                self.fail('native STRING sequences type%d' % type_id)
            b = r['bounds']
            if type(count) is not int or not b['min'] <= count <= b['max']:
                self.fail('native STRING sequence count type%d' % type_id)
            self.string_instances += 1
            return value
        self.fail('unsupported kind')

    def finish(self):
        # A whole-member research gate, not a native callee EOF requirement.
        remaining = len(self.raw) * 8 - self.bit
        if remaining >= 8:
            self.fail('whole-member trailing bytes')
        if remaining and self.bits(remaining):
            self.fail('whole-member nonzero EOF padding')


def compare_candidate(value, records, type_id, official_value, official_types, official_id):
    """Compare anonymous wire values with official names only as a candidate map."""
    nodes = 0
    def walk(v, ni, o, oi):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES:
            raise Rejected('comparison research node budget')
        r = records[ni]
        if r['kind'] == 'USER':
            return walk(v, r['element_type'], o, oi)
        op, args = official_types[oi]
        kind = r['kind']
        if kind == 'STRUCT':
            if type(o) is not dict or len(v) != len(args[0]) or len(o) != len(v):
                raise Rejected('candidate STRUCT shape')
            for item, child, (name, oid, tag) in zip(v, r['field_types'], args[0]):
                if name not in o:
                    raise Rejected('candidate field absent')
                walk(item, child, o[name], oid)
        elif kind == 'ARRAY':
            if type(o) is not list or len(v) != len(o):
                raise Rejected('candidate ARRAY shape')
            for a, b in zip(v, o):
                walk(a, r['element_type'], b, args[1])
        elif kind == 'OPTIONAL':
            if (v is None) != (o is None):
                raise Rejected('candidate OPTIONAL presence')
            if v is not None:
                walk(v, r['element_type'], o, args[0])
        elif type(v) is not type(o) or v != o:
            raise Rejected('candidate leaf differs')
    walk(value, type_id, official_value, official_id)
    return nodes
