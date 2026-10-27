"""Bounded value codec for the 22 observed native98348 game-event payloads.

The pinned 191-type closure includes the complete frame envelope. Other native
event IDs fail explicitly; there is no upstream payload fallback. Values are
anonymous tuples, bytes and Choice objects, not native in-memory objects.
Encoding chooses minimal delta tags and zero alignment padding. It does not
preserve discarded source padding or prove historical simulation compatibility.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

PROFILE = 'game-events-98348-observed22'
SCHEMA_SHA256 = 'bbb2ca6a0c1511a6756cf0f5ab9d0309f4b8b6cdf397963d020390f549082895'
MAX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 250000
MAX_NODES = 20000000
MAX_ELEMENTS = 2000000
MAX_DEPTH = 64


class GameEventsError(ValueError):
    """Value-free diagnostics contain fixed reasons, type IDs and bit positions."""


def _pinned(name, size, digest):
    path = Path(__file__).with_name(name)
    try:
        if path.is_symlink():
            raise GameEventsError('dependency symlink')
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != size:
                raise GameEventsError('dependency size or type')
            raw = stream.read(size + 1)
            after = os.fstat(stream.fileno())
        if (len(raw) != size or hashlib.sha256(raw).hexdigest() != digest
                or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
            raise GameEventsError('dependency pin')
        return raw
    except OSError:
        raise GameEventsError('dependency unavailable') from None


_string_source = _pinned('_native_setup_string.py', 2145,
                        '56087d34ad3569cb20a01d1831e15697432840d22c2a008c83a267bd65dcea69')
_string_namespace = {}
exec(compile(_string_source, '_native_setup_string.py', 'exec'), _string_namespace)
_string_count = _string_namespace['count_native_string_sequences']


def _profile(profile):
    if type(profile) is not str or profile != PROFILE:
        raise GameEventsError('unsupported game-events profile')
    schema = json.loads(_pinned('native_game_events_schema_98348.json', 49231, SCHEMA_SHA256))
    records = {r['id']: r for r in schema['records']}
    roots = {int(i): root for i, root in schema['payload_roots'].items()}
    if len(records) != 191 or len(roots) != 22 or schema['profile'] != PROFILE:
        raise GameEventsError('profile closure')
    return records, roots


@dataclass(frozen=True, repr=False)
class Choice:
    tag: int
    value: object


@dataclass(frozen=True, repr=False)
class GameEvent:
    delta: int
    user_id: int
    event_id: int
    payload: object


@dataclass(frozen=True, repr=False)
class DecodedGameEvent:
    event: GameEvent
    delta_tag: int
    start_bit: int
    payload_end_bit: int
    aligned_end_bit: int
    discarded_padding_bits: int
    nonzero_padding_spans: int


class _Budget:
    def __init__(self, records):
        self.records = records
        self.nodes = self.elements = self.bit = 0

    def fail(self, reason):
        raise GameEventsError('bit%d:%s' % (self.bit, reason))

    def enter(self, type_id, depth):
        self.nodes += 1
        if depth > MAX_DEPTH or self.nodes > MAX_NODES:
            self.fail('node/depth budget')
        return self.records[type_id]

    def sequence(self, count):
        self.elements += count
        if self.elements > MAX_ELEMENTS:
            self.fail('array-element budget')

    def string(self, value, record):
        try:
            count = _string_count(value)
        except ValueError:
            self.fail('native STRING encoding type%d' % record['id'])
        b = record['bounds']
        if not b['min'] <= count <= b['max']:
            self.fail('native STRING sequence bounds type%d' % record['id'])


class _Reader(_Budget):
    def __init__(self, raw, records):
        super().__init__(records)
        if type(raw) is not bytes or len(raw) > MAX_MEMBER_BYTES:
            self.fail('member type/byte budget')
        self.raw = raw
        self.padding_bits = self.nonzero_padding_spans = 0

    def bits(self, width):
        if not 0 <= width <= MAX_MEMBER_BYTES * 8 or self.bit + width > len(self.raw) * 8:
            self.fail('truncated bit field')
        value = 0
        remaining = width
        while remaining:
            index, offset = divmod(self.bit, 8)
            take = min(8 - offset, remaining)
            value = (value << take) | ((self.raw[index] >> offset) & ((1 << take) - 1))
            self.bit += take
            remaining -= take
        return value

    def align(self):
        width = (-self.bit) % 8
        if width:
            self.padding_bits += width
            self.nonzero_padding_spans += bool(self.bits(width))

    def count(self, record, string=False):
        b = record['bounds']
        value = b['min'] + self.bits(b['bits'] + (2 if string else 0))
        if not b['min'] <= value <= b['max'] * (4 if string else 1):
            self.fail('native bounds type%d' % record['id'])
        return value

    def read(self, type_id, depth=0):
        r = self.enter(type_id, depth)
        k = r['kind']
        child = lambda i: self.read(i, depth + 1)
        if k == 'USER':
            return child(r['element_type'])
        if k == 'STRUCT':
            return tuple(child(i) for i in r['field_types'])
        if k in ('INT', 'ENUM'):
            value = self.count(r)
            if k == 'ENUM' and value not in r['tags']:
                self.fail('native ENUM membership type%d' % type_id)
            return value
        if k == 'BOOL':
            return bool(self.bits(1))
        if k == 'NULL':
            return None
        if k == 'OPTIONAL':
            return child(r['element_type']) if self.bits(1) else None
        if k == 'CHOICE':
            tag = self.count(r)
            if tag not in r['tags']:
                self.fail('native CHOICE membership type%d' % type_id)
            return Choice(tag, child(r['field_types'][r['tags'].index(tag)]))
        if k == 'ARRAY':
            count = self.count(r)
            self.sequence(count)
            return tuple(child(r['element_type']) for _ in range(count))
        if k == 'BIT_ARRAY':
            count = self.count(r)
            return count, self.bits(count)
        if k == 'STRING':
            count = self.count(r, string=True)
            self.align()
            if self.bit + count * 8 > len(self.raw) * 8:
                self.fail('truncated STRING')
            start = self.bit // 8
            self.bit += count * 8
            value = self.raw[start:start + count]
            self.string(value, r)
            return value
        self.fail('unsupported native kind')


class _Writer(_Budget):
    def __init__(self, records):
        super().__init__(records)
        self.raw = bytearray()

    def bits(self, value, width):
        if (type(value) is not int or value < 0 or value.bit_length() > width
                or not 0 <= width <= MAX_MEMBER_BYTES * 8):
            self.fail('bit value/width')
        if self.bit + width > MAX_MEMBER_BYTES * 8:
            self.fail('output byte budget')
        remaining = width
        while remaining:
            offset = self.bit % 8
            take = min(8 - offset, remaining)
            remaining -= take
            if not offset:
                self.raw.append(0)
            self.raw[-1] |= ((value >> remaining) & ((1 << take) - 1)) << offset
            self.bit += take

    def align(self):
        self.bits(0, (-self.bit) % 8)

    def count(self, record, value, string=False):
        b = record['bounds']
        if type(value) is not int or not b['min'] <= value <= b['max'] * (4 if string else 1):
            self.fail('native bounds type%d' % record['id'])
        self.bits(value - b['min'], b['bits'] + (2 if string else 0))

    def write(self, value, type_id, depth=0):
        r = self.enter(type_id, depth)
        k = r['kind']
        child = lambda v, i: self.write(v, i, depth + 1)
        if k == 'USER':
            child(value, r['element_type'])
        elif k == 'STRUCT':
            if type(value) is not tuple or len(value) != len(r['field_types']):
                self.fail('STRUCT shape type%d' % type_id)
            for v, i in zip(value, r['field_types']):
                child(v, i)
        elif k in ('INT', 'ENUM'):
            self.count(r, value)
            if k == 'ENUM' and value not in r['tags']:
                self.fail('native ENUM membership type%d' % type_id)
        elif k == 'BOOL':
            if type(value) is not bool:
                self.fail('BOOL type')
            self.bits(int(value), 1)
        elif k == 'NULL':
            if value is not None:
                self.fail('NULL value')
        elif k == 'OPTIONAL':
            self.bits(int(value is not None), 1)
            if value is not None:
                child(value, r['element_type'])
        elif k == 'CHOICE':
            if type(value) is not Choice or type(value.tag) is not int or value.tag not in r['tags']:
                self.fail('CHOICE shape/domain type%d' % type_id)
            self.count(r, value.tag)
            child(value.value, r['field_types'][r['tags'].index(value.tag)])
        elif k == 'ARRAY':
            if type(value) is not tuple:
                self.fail('ARRAY type')
            self.count(r, len(value))
            self.sequence(len(value))
            for v in value:
                child(v, r['element_type'])
        elif k == 'BIT_ARRAY':
            if type(value) is not tuple or len(value) != 2:
                self.fail('BIT_ARRAY shape')
            self.count(r, value[0])
            self.bits(value[1], value[0])
        elif k == 'STRING':
            if type(value) is not bytes:
                self.fail('STRING type')
            self.count(r, len(value), string=True)
            self.string(value, r)
            self.align()
            if self.bit + len(value) * 8 > MAX_MEMBER_BYTES * 8:
                self.fail('output byte budget')
            self.raw.extend(value)
            self.bit += len(value) * 8
        else:
            self.fail('unsupported native kind')


def iter_game_events(raw, profile=PROFILE):
    """Yield complete frames using only the pinned native graph.

    Consume the iterator to exhaustion to validate the whole member. Internal
    and final per-event alignment bits are discarded, counted, and may be nonzero.
    Returned metadata contains positions and counters, not raw padding contents.
    Unknown payload IDs fail even when the native ID enum admits them.
    """
    records, roots = _profile(profile)
    reader = _Reader(raw, records)
    count = 0
    while reader.bit < len(raw) * 8:
        count += 1
        if count > MAX_EVENTS:
            reader.fail('event budget')
        start = reader.bit
        padding_before, nonzero_before = reader.padding_bits, reader.nonzero_padding_spans
        delta = reader.read(50)
        user_id, = reader.read(890)
        event_id = reader.read(138)
        if event_id not in roots:
            reader.fail('unsupported native payload ID')
        payload = reader.read(roots[event_id])
        end = reader.bit
        reader.align()
        yield DecodedGameEvent(GameEvent(delta.value, user_id, event_id, payload), delta.tag,
                               start, end, reader.bit, reader.padding_bits - padding_before,
                               reader.nonzero_padding_spans - nonzero_before)


def encode_game_events(events, profile=PROFILE):
    """Encode supplied GameEvent values with minimal deltas and zero padding.

    Returns member bytes only after every supplied event passes. No replay or
    filesystem is written. Source byte identity requires a separate comparison.
    """
    records, roots = _profile(profile)
    writer = _Writer(records)
    for count, event in enumerate(events, 1):
        if count > MAX_EVENTS:
            writer.fail('event budget')
        if type(event) is not GameEvent:
            writer.fail('GameEvent type')
        if type(event.delta) is not int or not 0 <= event.delta <= 0xffffffff:
            writer.fail('delta bounds')
        if type(event.event_id) is not int or event.event_id not in roots:
            writer.fail('unsupported native payload ID')
        tag = 0 if event.delta < 0x40 else 1 if event.delta < 0x4000 else 2 if event.delta < 0x400000 else 3
        writer.write(Choice(tag, event.delta), 50)
        writer.write((event.user_id,), 890)
        writer.write(event.event_id, 138)
        writer.write(event.payload, roots[event.event_id])
        writer.align()
    return bytes(writer.raw)
