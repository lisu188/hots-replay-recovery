"""Bounded, source-preserving sync.events codec for the native98348 type graph.

The graph and native reader establish physical fields only. Anonymous words and
the u16 value are deliberately not assigned checksum or simulation meanings.
This module reads/writes a member in memory; it never opens a replay or client.
"""
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import hashlib
import json

PROFILE = 'native-sync-98348'
SCHEMA_SHA256 = '0c0227b406fcde24f2b3bd56466eae9e867be3b3abeb3f6df303629a10599e1b'
PROGRAM_SHA256 = '245aba71f1702e6bae480924df478c8479978e54c383dff4757eb40863932b2f'
MAX_BYTES = 1024 * 1024
MAX_RECORDS = 200000
MAX_U32 = 0xffffffff


class SyncFormatError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise SyncFormatError(message)


def _integer(value, maximum, label):
    _require(type(value) is int and 0 <= value <= maximum, label + ' outside bounds')


@lru_cache(maxsize=1)
def _spec():
    path = Path(__file__).parent / 'observations' / 'native-sync-98348-type-closure.json'
    body = path.read_bytes()
    _require(len(body) == 7456 and hashlib.sha256(body).hexdigest() == SCHEMA_SHA256,
             'Pinned native schema differs')
    data = json.loads(body)
    _require(data['program']['sha256'] == PROGRAM_SHA256 and
             data['program']['protocol_context_VA'] == 0x14393EB80 and
             data['root_ids'] == [50, 892, 893, 896], 'Native protocol provenance differs')
    records = {row['id']: row for row in data['records']}

    def unwrap(index):
        seen = set()
        while records[index]['kind'] == 'USER':
            _require(index not in seen, 'Cyclic USER chain')
            seen.add(index)
            index = records[index]['element_type']
        return records[index]

    delta = records[50]
    _require(delta['kind'] == 'CHOICE' and delta['tags'] == [0, 1, 2, 3] and
             delta['bounds']['bits'] == 2 and delta['bounds']['min'] == 0,
             'Native delta declaration differs')
    widths = []
    for index in delta['field_types']:
        child = unwrap(index)
        _require(child['kind'] == 'INT' and child['bounds']['min'] == 0,
                 'Native delta scalar differs')
        widths.append(child['bounds']['bits'])
    _require(widths == [6, 14, 22, 32], 'Native delta widths differ')
    identifier = records[892]
    _require(identifier['kind'] == 'ENUM' and identifier['tags'] == [1, 2] and
             identifier['bounds']['bits'] == 1 and identifier['bounds']['min'] == 1,
             'Native event ID differs')
    first, second = records[893], records[896]
    _require(first['kind'] == second['kind'] == 'STRUCT' and
             first['tags'] == [-3, -2] and second['tags'] == [-2],
             'Native payload structure differs')
    vector_struct = unwrap(first['field_types'][0])
    _require(vector_struct['kind'] == 'STRUCT' and vector_struct['tags'] == [-1],
             'Native word-vector wrapper differs')
    vector = unwrap(vector_struct['field_types'][0])
    word = unwrap(vector['element_type'])
    values = [unwrap(first['field_types'][1]), unwrap(second['field_types'][0])]
    _require(vector['kind'] == 'ARRAY' and vector['bounds']['bits'] == 8 and
             vector['bounds']['min'] == 0 and vector['bounds']['max'] == 255 and
             word['kind'] == 'INT' and word['bounds']['bits'] == 32 and
             word['bounds']['min'] == 0 and word['bounds']['max'] == MAX_U32,
             'Native word vector differs')
    _require(all(value['kind'] == 'INT' and value['bounds']['bits'] == 16 and
                 value['bounds']['min'] == 0 and value['bounds']['max'] == 65535
                 for value in values), 'Native u16 payload differs')
    return tuple(widths)


class _Reader:
    def __init__(self, raw):
        self.raw, self.position = raw, 0

    def bits(self, count):
        _require(0 <= count <= 32 and self.position + count <= len(self.raw) * 8,
                 'Truncated sync field')
        value = 0
        while count:
            width = min(count, 8 - self.position % 8)
            part = (self.raw[self.position // 8] >> (self.position % 8)) & ((1 << width) - 1)
            value = (value << width) | part
            self.position += width
            count -= width
        return value


class _Writer:
    def __init__(self):
        self.raw, self.position = bytearray(), 0

    def bits(self, value, count):
        _integer(value, (1 << count) - 1, 'Sync scalar')
        while count:
            offset = self.position % 8
            if offset == 0:
                self.raw.append(0)
            width = min(count, 8 - offset)
            self.raw[-1] |= ((value >> (count - width)) & ((1 << width) - 1)) << offset
            self.position += width
            count -= width


@dataclass(frozen=True, repr=False)
class SyncRecord:
    gameloop: int
    delta: int
    delta_variant: int
    event_id: int
    words: tuple[int, ...] | None
    value_u16: int
    padding_value: int = 0
    start_bit: int = 0
    payload_end_bit: int = 0
    end_bit: int = 0


def canonical_delta_variant(delta):
    _integer(delta, MAX_U32, 'Sync delta')
    return 0 if delta < 64 else 1 if delta < 16384 else 2 if delta < 4194304 else 3


def decode_sync(raw, profile=PROFILE):
    """Decode both native event variants, retaining delta choice and padding.

    Native DWORD frame accumulation can wrap. This bounded research profile
    rejects wrap rather than silently accepting ambiguous frame ordering.
    Nonzero alignment bits are retained because the native reader skips them.
    """
    _require(profile == PROFILE and type(raw) is bytes and len(raw) <= MAX_BYTES,
             'Explicit bounded native98348 sync bytes required')
    widths = _spec()
    reader = _Reader(raw)
    frame, records = 0, []
    while reader.position < len(raw) * 8:
        _require(len(records) < MAX_RECORDS, 'Sync event budget exceeded')
        start = reader.position
        variant = reader.bits(2)
        delta = reader.bits(widths[variant])
        _require(frame + delta <= MAX_U32, 'Sync frame accumulation would wrap u32')
        frame += delta
        event_id = reader.bits(1) + 1
        words = None
        if event_id == 1:
            count = reader.bits(8)
            words = tuple(reader.bits(32) for _ in range(count))
        value = reader.bits(16)
        payload_end = reader.position
        padding = reader.bits((-reader.position) % 8)
        records.append(SyncRecord(frame, delta, variant, event_id, words, value,
                                  padding, start, payload_end, reader.position))
    return tuple(records)


def encode_sync(records, profile=PROFILE):
    """Encode physical records without changing anonymous values or choices."""
    _require(profile == PROFILE and type(records) in (tuple, list) and len(records) <= MAX_RECORDS,
             'Bounded native sync records required')
    widths = _spec()
    writer, frame = _Writer(), 0
    for record in records:
        _require(type(record) is SyncRecord, 'SyncRecord required')
        _integer(record.delta_variant, 3, 'Sync delta variant')
        _integer(record.delta, (1 << widths[record.delta_variant]) - 1, 'Sync delta')
        _require(frame + record.delta <= MAX_U32, 'Sync frame accumulation would wrap u32')
        frame += record.delta
        _require(type(record.gameloop) is int and record.gameloop == frame,
                 'Sync frame disagrees with accumulated delta')
        _require(type(record.event_id) is int and record.event_id in (1, 2), 'Invalid sync event ID')
        writer.bits(record.delta_variant, 2)
        writer.bits(record.delta, widths[record.delta_variant])
        writer.bits(record.event_id - 1, 1)
        if record.event_id == 1:
            _require(type(record.words) is tuple and len(record.words) <= 255,
                     'Native word vector exceeds count bound')
            writer.bits(len(record.words), 8)
            for word in record.words:
                _integer(word, MAX_U32, 'Sync vector word')
                writer.bits(word, 32)
        else:
            _require(record.words is None, 'Event2 has no word vector')
        _integer(record.value_u16, 65535, 'Sync u16')
        writer.bits(record.value_u16, 16)
        writer.bits(record.padding_value, (-writer.position) % 8)
        _require(len(writer.raw) <= MAX_BYTES, 'Encoded sync stream exceeds byte budget')
    return bytes(writer.raw)


def summarize_sync(raw):
    records = decode_sync(raw)
    _require(encode_sync(records) == raw, 'Sync decode/encode bytes differ')
    return dict(profile=PROFILE, schema_sha256=SCHEMA_SHA256,
                bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), records=len(records),
                event_id_counts=dict(sorted(Counter(r.event_id for r in records).items())),
                delta_variant_counts=dict(sorted(Counter(r.delta_variant for r in records).items())),
                first_recorded_gameloop=records[0].gameloop if records else None,
                last_recorded_gameloop=records[-1].gameloop if records else None,
                vector_words=sum(len(r.words or ()) for r in records),
                nonzero_padding_records=sum(r.padding_value != 0 for r in records),
                record_byte_lengths=dict(sorted(Counter((r.end_bit-r.start_bit)//8 for r in records).items())),
                byte_exact_roundtrip=True, checksum_algorithm_identified=False,
                first_divergent_tick_identified=False, playback_compatibility_proven=False,
                anonymous_payload_values_emitted=False)
