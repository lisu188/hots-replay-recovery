"""Source-preserving versioned replay-header view of numeric root879.

Official names are wire-tag adapters. This module assigns no native memory
offset, build-retarget policy, runtime dispatch or replay compatibility.
Listed ENUM membership is adapter policy from the selected metadata; it does
not establish the native client's rejection behavior for unlisted values.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import importlib
import json
from pathlib import Path

import lossless_wire as wire
from protocol_loader import load_protocol

MAX_HEADER_BYTES = 4096
SCHEMA_RELATIVE = 'observations/numeric-root-879-topology-2026-10-25.json'
SCHEMA_PIN = (9536, '6765c0d8795f3af57333d200e1ea722818e965158bf46a804574a78d4fe2b17b')
LOSSLESS_PIN = (11513, '9d725f9be88c4185419a306ef995e82a774d174a93912ffd381cced2d6ebb7a7')
DECODER_PIN = (9199, '17bfb926af0f7f79e18f6299dbae50fc2821c53b229235d4f9c857c7ef3e96b1')
PROTOCOL_PINS = {
    41810: (25890, '879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd'),
    96477: (26921, 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'),
}


class HeaderError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise HeaderError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pinned(path, expected):
    with Path(path).open('rb') as stream:
        raw = stream.read(expected[0] + 1)
    _need((len(raw), _sha(raw)) == expected, 'Pinned header dependency differs')
    return raw


@lru_cache(maxsize=4)
def _records(schema_path=None):
    path = Path(schema_path) if schema_path else Path(__file__).parent / SCHEMA_RELATIVE
    value = json.loads(_pinned(path, SCHEMA_PIN))
    records = value['closure']['records']
    by = {record['id']: record for record in records}
    _need(value['numeric_root_id'] == 879 and len(records) == len(by) == 22,
          'Unexpected numeric header topology')
    return by


def _unwrap(by, typeid):
    for _ in range(23):
        record = by[typeid]
        if record['kind'] != 'USER':
            return record
        typeid = record['element_type']
    raise HeaderError('Header USER wrapper depth exceeded')


def _view(node, typeid, by, unknown, missing, path=()):
    _need(len(path) <= 32, 'Header projection depth exceeded')
    record = _unwrap(by, typeid)
    kind = record['kind']
    if kind == 'STRUCT':
        _need(node.tag == 5, 'Expected versioned header struct')
        fields = dict(zip(record['tags'], record['field_types']))
        result, seen = {}, set()
        for tag, child in node.value:
            _need(tag not in seen, 'Duplicate header tag')
            seen.add(tag)
            if tag in fields:
                result[tag] = _view(child, fields[tag], by, unknown, missing, path + (tag,))
            else:
                unknown.append(path + (tag,))
        missing.extend(path + (tag,) for tag in fields if tag not in seen)
        return result
    if kind in ('STRING', 'BLOB'):
        bounds = record['bounds']
        _need(node.tag == 2 and bounds['min'] <= len(node.value) <= bounds['max'],
              'Header byte-length constraint failed')
        return node.value
    if kind in ('INT', 'ENUM'):
        bounds = record['bounds']
        _need(node.tag == 9 and type(node.value) is int
              and bounds['min'] <= node.value <= bounds['max'], 'Header integer constraint failed')
        if kind == 'ENUM':
            _need(node.value in record['tags'], 'Header enum membership failed')
        return node.value
    _need(kind == 'BOOL' and node.tag == 6, 'Expected versioned header boolean')
    return bool(node.value)


def _official_numeric(value, typeid, types):
    kind, args = types[typeid]
    if kind == '_struct':
        return {tag: _official_numeric(value[name], child, types)
                for name, child, tag in args[0] if name in value}
    if kind == '_optional':
        return None if value is None else _official_numeric(value, args[0], types)
    if kind == '_array':
        return [_official_numeric(item, args[1], types) for item in value]
    return value


def _known(value, typeid, by):
    record = _unwrap(by, typeid)
    if record['kind'] != 'STRUCT':
        return value
    fields = dict(zip(record['tags'], record['field_types']))
    return {tag: _known(child, fields[tag], by)
            for tag, child in value.items() if tag in fields}


@lru_cache(maxsize=2)
def _oracle(build):
    _need(type(build) is int and build in PROTOCOL_PINS, 'Unsupported official header oracle')
    package = importlib.import_module('heroprotocol')
    roots = [Path(root) for root in package.__path__]
    candidates = [root for root in roots
                  if (root / 'versions' / ('protocol%d.py' % build)).is_file()]
    _need(len(candidates) == 1, 'Exactly one official header schema is required')
    root = candidates[0]
    _pinned(root / 'versions' / ('protocol%d.py' % build), PROTOCOL_PINS[build])
    _pinned(root / 'decoders.py', DECODER_PIN)
    _pinned(Path(wire.__file__), LOSSLESS_PIN)
    protocol = load_protocol(build)
    decoder = importlib.import_module('heroprotocol.decoders')
    return protocol, decoder.VersionedDecoder


def _check_official(raw, value, by, build):
    protocol, decoder_type = _oracle(build)
    try:
        decoder = decoder_type(raw, protocol.typeinfos)
        named = decoder.instance(protocol.replay_header_typeid)
        _need(decoder.done() and decoder.used_bits() == 8 * len(raw),
              'Official header decoder did not consume exact EOF')
        numeric = _official_numeric(named, protocol.replay_header_typeid, protocol.typeinfos)
        _need(_known(numeric, 879, by) == value, 'Official and numeric header projections differ')
    except HeaderError:
        raise
    except Exception as error:
        raise HeaderError('Official header decode failed') from error


@dataclass(frozen=True)
class Header879View:
    """Public projections are copies; retained wire nodes stay private."""
    _tree: wire.Node = field(repr=False, compare=False)
    _by: dict = field(repr=False, compare=False)
    _value: dict = field(repr=False, compare=False)
    _official_build: int = field(repr=False)
    source_sha256: str
    unknown_paths: tuple
    missing_paths: tuple

    @property
    def value(self):
        return copy.deepcopy(self._value)

    def summary(self):
        raw = encode_header879(self)
        return {'format': 'numeric879-header-wire-summary-v1', 'bytes': len(raw),
                'source_sha256': self.source_sha256, 'encoded_sha256': _sha(raw),
                'known_root_tags': sorted(self._value),
                'unknown_paths': [list(path) for path in self.unknown_paths],
                'missing_paths': [list(path) for path in self.missing_paths],
                'official_schema_build': self._official_build, 'official_projection_and_EOF': True,
                'native_runtime_or_memory_layout_claim': False}


def _make(tree, by, build, source_sha256):
    try:
        raw = wire.encode(tree)
        _need(0 < len(raw) <= MAX_HEADER_BYTES, 'Header byte cap exceeded')
        unknown, missing = [], []
        value = _view(tree, 879, by, unknown, missing)
        _check_official(raw, value, by, build)
        return Header879View(tree, by, value, build, source_sha256,
                             tuple(unknown), tuple(missing))
    except wire.WireError as error:
        raise HeaderError('Invalid versioned header tree') from error


def decode_header879(raw, *, schema_path=None, official_build=96477):
    """Decode exactly one bounded header; retain unknown fields and spellings.

    Missing known fields are reported without insertion/defaults. The pinned
    official decoder must independently agree and consume the complete input.
    """
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_HEADER_BYTES, 'Expected bounded header bytes')
    try:
        tree = wire.parse(raw)
    except wire.WireError as error:
        raise HeaderError('Invalid or incomplete versioned header') from error
    result = _make(tree, _records(str(schema_path) if schema_path else None), official_build, _sha(raw))
    _need(wire.encode(result._tree) == raw, 'Header source inverse differs')
    return result


def encode_header879(view):
    """Encode retained nodes, validating constraints, official projection and EOF."""
    _need(type(view) is Header879View, 'Expected Header879View')
    checked = _make(view._tree, view._by, view._official_build, view.source_sha256)
    return wire.encode(checked._tree)


def replace_existing_int(view, tag_path, value):
    """Clone and edit one known integer leaf; never insert missing fields.

    Retained original spellings survive the edit, so reversing an edit can also
    restore a nonminimal integer spelling or negative zero exactly.
    """
    _need(type(view) is Header879View and type(value) is int, 'Expected header view and integer')
    _need(type(tag_path) in (tuple, list) and 0 < len(tag_path) <= 32
          and all(type(tag) is int for tag in tag_path), 'Expected numeric header tag path')
    encode_header879(view)
    tree, typeid = wire.clone(view._tree), 879
    node = tree
    try:
        for tag in tag_path:
            record = _unwrap(view._by, typeid)
            _need(record['kind'] == 'STRUCT', 'Header edit path crosses a scalar')
            fields = dict(zip(record['tags'], record['field_types']))
            _need(tag in fields, 'Header edit path is unknown')
            typeid = fields[tag]
            node = node.field(tag)
    except wire.WireError as error:
        raise HeaderError('Header edit field is missing or ambiguous') from error
    _need(_unwrap(view._by, typeid)['kind'] in ('INT', 'ENUM') and node.tag == 9,
          'Header edit leaf is not a known integer')
    node.value = value
    return _make(tree, view._by, view._official_build, view.source_sha256)
