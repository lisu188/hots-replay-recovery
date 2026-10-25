"""Strict inverse for valid wire values of the pinned current native775 graph.

Writer(records, string_count).write(value, type_id=775); finish() returns bytes.
Values use the anonymous tuple/bytes conventions of native_setup775_reader.
The native writer's fifth/context argument is zero in caller133D350, so STRUCT
uses declaration order without the nonzero-context preambles in1A6EBD0.

This models successful logical serialization, not native objects or execution.
It never guesses absent values, computes CRC, or reads a replay or game binary.
Native accessors/pointers, partial output after native failure and invalid-input
status behavior are outside its validated subset. STRING validation deliberately
requires the independently recovered native sequence counter used by the reader.
Zero internal/EOF padding is canonical; decoded value equality alone does not
establish source-byte identity when a source had nonzero discarded padding.
"""
from collections import Counter
import copy
import hashlib
import json

RECORDS_SHA256 = 'b60e4647c3a3d1ebc0344e99f4626f8dd72617bdb3cf4e204df8712990949bb1'
MAX_OUTPUT_BYTES = 1048576
MAX_NODES = 250000
MAX_DEPTH = 128
MAX_ARRAY_ELEMENTS = 100000
KINDS = frozenset(('USER', 'STRUCT', 'ARRAY', 'OPTIONAL', 'BOOL', 'INT',
                   'ENUM', 'FOURCC', 'BIT_ARRAY', 'BLOB', 'STRING'))


class Rejected(ValueError):
    """Safe diagnostics contain cursor/type/reason, never supplied values."""


class Writer:
    def __init__(self, records, string_count):
        try:
            if type(records) is not dict:
                raise ValueError
            encoded = json.dumps(records, sort_keys=True, separators=(',', ':'),
                                 ensure_ascii=True).encode('ascii')
            if (len(records) != 200 or hashlib.sha256(encoded).hexdigest() != RECORDS_SHA256
                    or {r['kind'] for r in records.values()} != KINDS):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise Rejected('pinned native775 records required') from None
        if not callable(string_count):
            raise Rejected('native STRING callback required')
        self._records = copy.deepcopy(records)
        self.string_count = string_count
        self._raw = bytearray()
        self.bit = 0
        self.nodes = 0
        self.array_elements = 0
        self.kinds = Counter()
        self.types = Counter()
        self.bounds_checks = Counter()
        self.string_instances = 0
        self.padding_spans = 0
        self.nonzero_padding_spans = 0
        self._failed = False
        self._finished = False

    def fail(self, reason):
        self._failed = True
        raise Rejected('bit%d:%s' % (self.bit, reason))

    def _open(self):
        if self._failed:
            self.fail('discard rejected writer')
        if self._finished:
            self.fail('writer already finished')

    def bits(self, value, width):
        """Native EA50/EB10 chunk convention, generalized for BIT_ARRAY values."""
        self._open()
        if (type(width) is not int or not 0 <= width <= MAX_OUTPUT_BYTES * 8
                or type(value) is not int or value < 0 or value.bit_length() > width):
            self.fail('bit value/width')
        if self.bit + width > MAX_OUTPUT_BYTES * 8:
            self.fail('research output byte budget')
        remaining = width
        while remaining:
            offset = self.bit % 8
            take = min(remaining, 8 - offset)
            remaining -= take
            if offset == 0:
                self._raw.append(0)
            mask = (1 << take) - 1
            chunk = (value >> remaining) & mask
            self._raw[-1] = ((self._raw[-1] & ~(mask << offset))
                             | (chunk << offset))
            self.bit += take

    def align(self):
        self._open()
        width = (-self.bit) % 8
        if width:
            self.padding_spans += 1
            self.bits(0, width)

    def octets(self, value):
        self._open()
        if type(value) is not bytes:
            self.fail('bytes required')
        if self.bit + (-self.bit) % 8 + len(value) * 8 > MAX_OUTPUT_BYTES * 8:
            self.fail('research output byte budget')
        self.align()
        self._raw.extend(value)
        self.bit += len(value) * 8

    def count(self, record, value, derived_string=False):
        bounds = record['bounds']
        minimum, maximum, width = bounds['min'], bounds['max'], bounds['bits']
        if derived_string:
            width += 2
            maximum *= 4
        if type(value) is not int or not minimum <= value <= maximum:
            self.fail('native bounds type%d' % record['id'])
        self.bounds_checks[record['id']] += 1
        self.bits(value - minimum, width)

    def write(self, value, type_id=775, depth=0):
        self._open()
        if type(type_id) is not int or type_id not in self._records:
            self.fail('unknown type')
        if type(depth) is not int or depth < 0:
            self.fail('invalid depth')
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            self.fail('research node/depth budget')
        record = self._records[type_id]
        kind = record['kind']
        self.kinds[kind] += 1
        self.types[type_id] += 1
        descend = lambda v, child: self.write(v, child, depth + 1)
        if kind == 'USER':
            descend(value, record['element_type'])
        elif kind == 'STRUCT':
            if type(value) is not tuple or len(value) != len(record['field_types']):
                self.fail('STRUCT shape type%d' % type_id)
            for item, child in zip(value, record['field_types']):
                descend(item, child)
        elif kind == 'ARRAY':
            if type(value) is not tuple:
                self.fail('ARRAY tuple type%d' % type_id)
            length = len(value)
            self.array_elements += length
            if self.array_elements > MAX_ARRAY_ELEMENTS:
                self.fail('research total array budget')
            self.count(record, length)
            for item in value:
                descend(item, record['element_type'])
        elif kind == 'OPTIONAL':
            self.bits(int(value is not None), 1)
            if value is not None:
                descend(value, record['element_type'])
        elif kind == 'BOOL':
            if type(value) is not bool:
                self.fail('BOOL type%d' % type_id)
            self.bits(int(value), 1)
        elif kind in ('INT', 'ENUM'):
            if kind == 'ENUM' and (type(value) is not int or value not in record['tags']):
                self.fail('native ENUM domain type%d' % type_id)
            self.count(record, value)
        elif kind == 'FOURCC':
            if type(value) is not bytes or len(value) != 4:
                self.fail('FOURCC width type%d' % type_id)
            self.bits(int.from_bytes(value, 'big'), 32)
        elif kind == 'BIT_ARRAY':
            if type(value) is not tuple or len(value) != 2:
                self.fail('BIT_ARRAY shape type%d' % type_id)
            length, pattern = value
            bounds = record['bounds']
            if (type(length) is not int or not bounds['min'] <= length <= bounds['max']
                    or type(pattern) is not int or pattern < 0 or pattern.bit_length() > length):
                self.fail('BIT_ARRAY length/pattern type%d' % type_id)
            self.count(record, length)
            self.bits(pattern, length)
        elif kind in ('BLOB', 'STRING'):
            if type(value) is not bytes:
                self.fail('bytes type%d' % type_id)
            if kind == 'STRING':
                try:
                    sequences = self.string_count(value)
                except ValueError:
                    self.fail('native STRING sequences type%d' % type_id)
                bounds = record['bounds']
                if type(sequences) is not int or not bounds['min'] <= sequences <= bounds['max']:
                    self.fail('native STRING sequence count type%d' % type_id)
                self.string_instances += 1
            self.count(record, len(value), derived_string=(kind == 'STRING'))
            self.octets(value)
        else:
            self.fail('unsupported kind')

    def finish(self):
        if self._failed:
            self.fail('discard rejected writer')
        # Bytearray growth/align keeps unwritten high bits zero. Native final
        # mask1A6FA70 preserves the payload cursor instead of adding wire bits.
        if self.bit % 8:
            self._raw[-1] &= (1 << (self.bit % 8)) - 1
        self._finished = True
        return bytes(self._raw)
