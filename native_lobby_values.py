"""Strict value codec for the current native5917 battlelobby graph, context0.

The fixed graph is distinct from native775. Values are immutable anonymous
tuples/bytes; REAL values are unsigned raw bit patterns, never Python floats.
Writing validates supplied values and canonicalizes alignment padding. It does
not construct historical fields, retarget replay metadata or prove playback.
"""
from collections import Counter
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

PROFILE = 'online-values-98348'
ROOT_TYPE = 5917
SCHEMA_SHA256 = '0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640'
RECORDS_SHA256 = 'f1036e04c503b36ca95c8fbcf72e96c9d7af7a4d91559a95ab5f01271ec2c3f3'
MAX_MEMBER_BYTES = 1048576
MAX_NODES = 500000
MAX_DEPTH = 128
MAX_ARRAY = 32768
MAX_ARRAY_ELEMENTS = 250000
MAX_STRING_BYTES = 4096
KINDS = frozenset(('USER', 'STRUCT', 'ARRAY', 'OPTIONAL', 'BOOL', 'INT',
                   'ENUM', 'FOURCC', 'BIT_ARRAY', 'BLOB', 'STRING',
                   'ASCII_STRING', 'CHOICE', 'NULL', 'REAL32', 'REAL64'))


class LobbyError(ValueError):
    """Fixed diagnostics do not contain supplied values or private field paths."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pinned_file(name, size, digest):
    path = Path(__file__).with_name(name)
    try:
        if path.is_symlink():
            raise LobbyError('native lobby dependency symlink refused')
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != size:
                raise LobbyError('native lobby dependency size or type differs')
            raw = stream.read(size + 1)
            after = os.fstat(stream.fileno())
        if (len(raw) != size or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns or _sha(raw) != digest):
            raise LobbyError('native lobby dependency pin differs')
        return raw
    except OSError:
        raise LobbyError('native lobby dependency unavailable') from None


_string_namespace = {}
exec(compile(_pinned_file('_native_setup_string.py', 2145,
    '56087d34ad3569cb20a01d1831e15697432840d22c2a008c83a267bd65dcea69'),
    '_native_setup_string.py', 'exec'), _string_namespace)
_string_count = _string_namespace['count_native_string_sequences']


def _records():
    obj = json.loads(_pinned_file('native_startgame_schema_98348.json', 125279, SCHEMA_SHA256))
    return {record['id']: record for record in obj['records']}


def _checked_records(records):
    try:
        if type(records) is not dict or len(records) != 513:
            raise ValueError
        raw = json.dumps(records, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True).encode('ascii')
        if _sha(raw) != RECORDS_SHA256 or {r['kind'] for r in records.values()} != KINDS:
            raise ValueError
    except (ValueError, TypeError, KeyError):
        raise LobbyError('pinned native5917 records required') from None
    return copy.deepcopy(records)


class _State:
    def __init__(self, records):
        self.records = _checked_records(records)
        self.bit = 0
        self.nodes = 0
        self.array_elements = 0
        self.padding_spans = 0
        self.nonzero_padding_spans = 0
        self.kinds = Counter()
        self.types = Counter()
        self._failed = False
        self._finished = False

    def fail(self, reason):
        self._failed = True
        raise LobbyError('bit%d:%s' % (self.bit, reason))

    def _open(self):
        if self._failed:
            self.fail('discard rejected native lobby codec')
        if self._finished:
            self.fail('native lobby codec already finished')

    def record(self, type_id, depth):
        self._open()
        if type(type_id) is not int or type_id not in self.records:
            self.fail('unknown native lobby type')
        if type(depth) is not int or not 0 <= depth <= MAX_DEPTH:
            self.fail('native lobby depth budget')
        self.nodes += 1
        if self.nodes > MAX_NODES:
            self.fail('native lobby node budget')
        record = self.records[type_id]
        self.kinds[record['kind']] += 1
        self.types[type_id] += 1
        return record

    def array(self, length):
        self.array_elements += length
        if length > MAX_ARRAY or self.array_elements > MAX_ARRAY_ELEMENTS:
            self.fail('native lobby array budget')


class _Reader(_State):
    def __init__(self, raw, records):
        if type(raw) is not bytes or len(raw) > MAX_MEMBER_BYTES:
            raise LobbyError('native lobby input type or byte budget')
        super().__init__(records)
        self.raw = raw

    def bits(self, width):
        self._open()
        if (type(width) is not int or not 0 <= width <= MAX_MEMBER_BYTES * 8
                or self.bit + width > len(self.raw) * 8):
            self.fail('truncated or unsupported bit width')
        result = 0
        while width:
            take = min(width, 8 - self.bit % 8)
            width -= take
            chunk = (self.raw[self.bit // 8] >> (self.bit % 8)) & ((1 << take) - 1)
            result = (result << take) | chunk
            self.bit += take
        return result

    def octets(self, length):
        self._open()
        if type(length) is not int or not 0 <= length <= MAX_STRING_BYTES:
            self.fail('native lobby octet type or budget')
        width = (-self.bit) % 8
        if width:
            self.padding_spans += 1
            self.nonzero_padding_spans += bool(self.bits(width))
        if length > MAX_STRING_BYTES or self.bit + length * 8 > len(self.raw) * 8:
            self.fail('native lobby octet budget or truncation')
        start = self.bit // 8
        self.bit += length * 8
        return self.raw[start:start + length]

    def count(self, record, string=False):
        bound = record['bounds']
        width, maximum = bound['bits'], bound['max']
        if string:
            width += 2
            maximum *= 4
        value = bound['min'] + self.bits(width)
        if not bound['min'] <= value <= maximum:
            self.fail('native lobby bounds type%d' % record['id'])
        return value

    def read(self, type_id=ROOT_TYPE, depth=0):
        record = self.record(type_id, depth)
        kind = record['kind']
        child = lambda item: self.read(item, depth + 1)
        if kind == 'USER':
            return child(record['element_type'])
        if kind == 'STRUCT':
            return tuple(child(item) for item in record['field_types'])
        if kind == 'ARRAY':
            length = self.count(record)
            self.array(length)
            return tuple(child(record['element_type']) for _ in range(length))
        if kind == 'OPTIONAL':
            return child(record['element_type']) if self.bits(1) else None
        if kind == 'CHOICE':
            tag = self.count(record)
            if tag not in record['tags']:
                self.fail('native lobby CHOICE domain type%d' % type_id)
            return tag, child(record['field_types'][record['tags'].index(tag)])
        if kind == 'BOOL':
            return bool(self.bits(1))
        if kind in ('INT', 'ENUM'):
            value = self.count(record)
            if kind == 'ENUM' and value not in record['tags']:
                self.fail('native lobby ENUM domain type%d' % type_id)
            return value
        if kind == 'FOURCC':
            return self.bits(32).to_bytes(4, 'big')
        if kind in ('REAL32', 'REAL64'):
            return self.bits(32 if kind == 'REAL32' else 64)
        if kind == 'NULL':
            return None
        if kind == 'BIT_ARRAY':
            length = self.count(record)
            return length, self.bits(length)
        if kind in ('BLOB', 'STRING', 'ASCII_STRING'):
            value = self.octets(self.count(record, string=(kind == 'STRING')))
            _check_octets(self, record, value)
            return value
        self.fail('unsupported native lobby kind')

    def finish(self):
        self._open()
        remaining = len(self.raw) * 8 - self.bit
        if remaining >= 8:
            self.fail('native lobby whole-member trailing bytes')
        if remaining and self.bits(remaining):
            self.fail('native lobby nonzero EOF padding')
        self._finished = True


def _check_octets(state, record, value):
    if type(value) is not bytes or len(value) > MAX_STRING_BYTES:
        state.fail('native lobby bytes type or budget')
    if record['kind'] == 'ASCII_STRING' and any(not 1 <= byte <= 126 for byte in value):
        state.fail('native lobby ASCII domain type%d' % record['id'])
    if record['kind'] == 'STRING':
        try:
            count = _string_count(value)
        except ValueError:
            state.fail('native lobby STRING sequences type%d' % record['id'])
        if not record['bounds']['min'] <= count <= record['bounds']['max']:
            state.fail('native lobby STRING count type%d' % record['id'])


class _Writer(_State):
    def __init__(self, records):
        super().__init__(records)
        self._raw = bytearray()

    def bits(self, value, width):
        self._open()
        if (type(width) is not int or not 0 <= width <= MAX_MEMBER_BYTES * 8
                or type(value) is not int or value < 0 or value.bit_length() > width):
            self.fail('native lobby bit value or width')
        if self.bit + width > MAX_MEMBER_BYTES * 8:
            self.fail('native lobby output byte budget')
        while width:
            offset = self.bit % 8
            take = min(width, 8 - offset)
            width -= take
            if offset == 0:
                self._raw.append(0)
            self._raw[-1] |= ((value >> width) & ((1 << take) - 1)) << offset
            self.bit += take

    def octets(self, value):
        self._open()
        if type(value) is not bytes or len(value) > MAX_STRING_BYTES:
            self.fail('native lobby bytes type or budget')
        width = (-self.bit) % 8
        if self.bit + width + len(value) * 8 > MAX_MEMBER_BYTES * 8:
            self.fail('native lobby output byte budget')
        if width:
            self.padding_spans += 1
            self.bits(0, width)
        self._raw.extend(value)
        self.bit += len(value) * 8

    def count(self, record, value, string=False):
        bound = record['bounds']
        width, maximum = bound['bits'], bound['max']
        if string:
            width += 2
            maximum *= 4
        if type(value) is not int or not bound['min'] <= value <= maximum:
            self.fail('native lobby bounds type%d' % record['id'])
        self.bits(value - bound['min'], width)

    def write(self, value, type_id=ROOT_TYPE, depth=0):
        record = self.record(type_id, depth)
        kind = record['kind']
        child = lambda item, identifier: self.write(item, identifier, depth + 1)
        if kind == 'USER':
            child(value, record['element_type'])
        elif kind == 'STRUCT':
            if type(value) is not tuple or len(value) != len(record['field_types']):
                self.fail('native lobby STRUCT shape type%d' % type_id)
            for item, identifier in zip(value, record['field_types']):
                child(item, identifier)
        elif kind == 'ARRAY':
            if type(value) is not tuple:
                self.fail('native lobby ARRAY tuple type%d' % type_id)
            self.array(len(value))
            self.count(record, len(value))
            for item in value:
                child(item, record['element_type'])
        elif kind == 'OPTIONAL':
            self.bits(int(value is not None), 1)
            if value is not None:
                child(value, record['element_type'])
        elif kind == 'CHOICE':
            if (type(value) is not tuple or len(value) != 2
                    or type(value[0]) is not int or value[0] not in record['tags']):
                self.fail('native lobby CHOICE domain type%d' % type_id)
            tag, item = value
            self.count(record, tag)
            child(item, record['field_types'][record['tags'].index(tag)])
        elif kind == 'BOOL':
            if type(value) is not bool:
                self.fail('native lobby BOOL type%d' % type_id)
            self.bits(int(value), 1)
        elif kind in ('INT', 'ENUM'):
            if kind == 'ENUM' and (type(value) is not int or value not in record['tags']):
                self.fail('native lobby ENUM domain type%d' % type_id)
            self.count(record, value)
        elif kind == 'FOURCC':
            if type(value) is not bytes or len(value) != 4:
                self.fail('native lobby FOURCC width type%d' % type_id)
            self.bits(int.from_bytes(value, 'big'), 32)
        elif kind in ('REAL32', 'REAL64'):
            self.bits(value, 32 if kind == 'REAL32' else 64)
        elif kind == 'NULL':
            if value is not None:
                self.fail('native lobby NULL value type%d' % type_id)
        elif kind == 'BIT_ARRAY':
            if type(value) is not tuple or len(value) != 2:
                self.fail('native lobby BIT_ARRAY shape type%d' % type_id)
            length, pattern = value
            self.count(record, length)
            self.bits(pattern, length)
        elif kind in ('BLOB', 'STRING', 'ASCII_STRING'):
            _check_octets(self, record, value)
            self.count(record, len(value), string=(kind == 'STRING'))
            self.octets(value)
        else:
            self.fail('unsupported native lobby kind')

    def finish(self):
        if self._failed:
            self.fail('discard rejected native lobby codec')
        if self.bit % 8:
            self._raw[-1] &= (1 << (self.bit % 8)) - 1
        self._finished = True
        return bytes(self._raw)


def _profile(profile):
    if type(profile) is not str or profile != PROFILE:
        raise LobbyError('unsupported native lobby value profile')


def _statistics(reader):
    return (reader.nodes, reader.array_elements, reader.padding_spans,
            reader.nonzero_padding_spans, tuple(sorted(reader.kinds.items())),
            tuple(sorted(reader.types.items())))


@dataclass(frozen=True, repr=False)
class LobbyValues:
    profile: str
    value: tuple
    payload_end_bit: int
    source_sha256: str
    _source: bytes
    _statistics: tuple

    def summary(self):
        checked = _checked(self)
        nodes, arrays, padding, nonzero, kinds, types = checked._statistics
        return {'profile': PROFILE, 'root_type_id': ROOT_TYPE,
                'schema_sha256': SCHEMA_SHA256, 'native_writer_context': 0,
                'member_bytes': len(checked._source), 'member_sha256': checked.source_sha256,
                'native_payload_start_bit': 0, 'native_payload_end_bit': checked.payload_end_bit,
                'EOF_alignment_padding_bits': len(checked._source) * 8 - checked.payload_end_bit,
                'decoded_nodes': nodes, 'array_elements': arrays,
                'internal_padding_spans': padding, 'nonzero_internal_padding_spans': nonzero,
                'kind_counts': dict(kinds), 'observed_type_count': len(types),
                'simulation_or_historical_conversion_proven': False}


def decode_lobby_values(raw, profile=PROFILE):
    """Validate a complete current5917 member, preserving source padding privately."""
    _profile(profile)
    reader = _Reader(raw, _records())
    value = reader.read()
    end_bit = reader.bit
    statistics = _statistics(reader)
    reader.finish()
    return LobbyValues(PROFILE, value, end_bit, _sha(raw), raw, statistics)


def encode_lobby_values(value, profile=PROFILE):
    """Write supplied current5917 values with canonical zero internal/EOF padding."""
    _profile(profile)
    writer = _Writer(_records())
    writer.write(value)
    return writer.finish()


def _same(left, right, depth=0):
    if type(left) is not type(right) or depth > MAX_DEPTH:
        return False
    if type(right) is tuple:
        return len(left) == len(right) and all(
            _same(a, b, depth + 1) for a, b in zip(left, right))
    return left == right


def _checked(decoded):
    if type(decoded) is not LobbyValues:
        raise LobbyError('decoded native lobby values required')
    _profile(decoded.profile)
    checked = decode_lobby_values(decoded._source)
    if (type(decoded.payload_end_bit) is not int
            or decoded.payload_end_bit != checked.payload_end_bit
            or type(decoded.source_sha256) is not str
            or decoded.source_sha256 != checked.source_sha256
            or not _same(decoded._statistics, checked._statistics)
            or not _same(decoded.value, checked.value)):
        raise LobbyError('decoded native lobby values changed')
    return checked


def reencode_lobby_source(decoded, profile=PROFILE):
    """Reproduce exact source bytes only after revalidation of unchanged values."""
    _profile(profile)
    return _checked(decoded)._source
