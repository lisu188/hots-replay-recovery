"""Bounded, reversible battlelobby attribute-layer inspection.

Profiles describe an observed index capacity, not an authoritative complete
Blizzard schema or a claim about any client build. The suffix after locale
handles is deliberately opaque. This module never writes a replay archive.
Output parents are checked before writing. Multiple output writes are not an
atomic transaction; a later I/O failure can still leave a completed member.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_VALUES = 32768
MAX_TOKENS = 500000
ORIGINAL_SHA256 = 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
PROFILES = {'legacy-10': 10, 'observed-11': 11}


class LayerError(ValueError):
    """Unsupported, malformed, noncanonical or out-of-bounds member data."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def width(profile: str) -> int:
    try:
        return PROFILES[profile]
    except (KeyError, TypeError) as error:
        raise LayerError('An explicit supported capacity profile is required') from error


class _Reader:
    def __init__(self, raw: bytes):
        self.raw, self.position = raw, 0

    def bits(self, count: int) -> int:
        if type(count) is not int or not 0 <= count <= 127:
            raise LayerError('Invalid scalar bit width')
        if self.position + count > len(self.raw) * 8:
            raise LayerError(f'Truncated scalar at bit {self.position}')
        result = 0
        while count:
            chunk = min(count, 8 - self.position % 8)
            part = (self.raw[self.position // 8] >> (self.position % 8)) & ((1 << chunk) - 1)
            result = (result << chunk) | part
            self.position += chunk
            count -= chunk
        return result

    def blob(self, size: int) -> bytes:
        padding = (-self.position) % 8
        if padding and self.bits(padding):
            raise LayerError('Nonzero alignment padding is outside the observed profiles')
        start = self.position // 8
        if type(size) is not int or size < 0 or start + size > len(self.raw):
            raise LayerError(f'Truncated blob at byte {start}')
        self.position += size * 8
        return self.raw[start:start + size]


class _Writer:
    def __init__(self):
        self.raw, self.position = bytearray(), 0

    def bits(self, value: int, count: int) -> None:
        if type(value) is not int or type(count) is not int or not 0 <= count <= 127 or not 0 <= value < (1 << count):
            raise LayerError('Scalar cannot be represented without truncation')
        while count:
            offset = self.position % 8
            if not offset:
                self.raw.append(0)
            chunk = min(count, 8 - offset)
            self.raw[-1] |= ((value >> (count - chunk)) & ((1 << chunk) - 1)) << offset
            self.position += chunk
            count -= chunk

    def blob(self, raw: bytes) -> None:
        if not isinstance(raw, bytes):
            raise LayerError('Blob bytes are required')
        self.position += (-self.position) % 8
        self.raw.extend(raw)
        self.position += len(raw) * 8


@dataclass(frozen=True)
class Token:
    path: str
    kind: str
    value: int | bytes
    fixed_width: int = 0


@dataclass(frozen=True)
class Choice:
    tag: int
    values: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Attribute:
    namespace: int
    identifier: int
    values: tuple[int, ...]
    default_choice: Choice


@dataclass(frozen=True)
class Selection:
    namespace: int
    identifier: int
    choice: Choice


@dataclass(frozen=True)
class Layer:
    profile: str
    tokens: tuple[Token, ...]
    attributes: tuple[Attribute, ...]
    selections: tuple[Selection, ...]
    opaque_suffix: bytes
    boundaries: tuple[tuple[str, int], ...]
    original_sha256: str
    original_bytes: int


def decode_layer(raw: bytes, profile: str) -> Layer:
    index_width = width(profile)
    if not isinstance(raw, bytes) or not 16 <= len(raw) <= MAX_MEMBER_BYTES:
        raise LayerError('A bounded nonempty member is required')
    reader = _Reader(raw)
    tokens: list[Token] = []
    total_values = 0

    def scalar(path: str, count: int, kind: str = 'fixed') -> int:
        value = reader.bits(count)
        if len(tokens) >= MAX_TOKENS:
            raise LayerError('Token budget exceeded')
        tokens.append(Token(path, kind, value, count if kind == 'fixed' else 0))
        return value

    def blob(path: str, count: int) -> None:
        if len(tokens) >= MAX_TOKENS:
            raise LayerError('Token budget exceeded')
        tokens.append(Token(path, 'blob', reader.blob(count)))

    def value_count(path: str) -> int:
        nonlocal total_values
        count = scalar(path, index_width + 1, 'count')
        total_values += count
        if total_values > MAX_TOTAL_VALUES:
            raise LayerError('Attribute-value budget exceeded')
        return count

    def choice(path: str, limit: int) -> Choice:
        tag = scalar(path + '/tag', 8)
        if tag == 0:
            count = 1
        elif tag == 1:
            count = scalar(path + '/slot_count', 5)
            if not 1 <= count <= 16:
                raise LayerError('Unsupported player-slot count')
        else:
            raise LayerError('Unsupported attribute-choice tag')
        values = []
        for slot in range(count):
            index = scalar(f'{path}/{slot}/index', index_width, 'index')
            is_set = scalar(f'{path}/{slot}/is_set', 1)
            if index >= limit:
                raise LayerError('Attribute-choice index is outside its value table')
            values.append((index, is_set))
        return Choice(tag, tuple(values))

    paths = scalar('/dependencies/path_count', 6)
    if paths == 0:
        raise LayerError('An observed nonempty dependency prefix is required')
    for item in range(paths):
        size = scalar(f'/dependencies/paths/{item}/size', 10)
        if not size:
            raise LayerError('Empty dependency path is unsupported')
        blob(f'/dependencies/paths/{item}/bytes', size)
    handles = scalar('/dependencies/handle_count', 6)
    if handles != paths:
        raise LayerError('Dependency path and handle counts disagree')
    for item in range(handles):
        blob(f'/dependencies/handles/{item}', 40)
    boundaries = [('dependency_prefix_end', reader.position)]

    count = scalar('/attributes/count', 9)
    if count == 0:
        raise LayerError('An observed nonempty attribute table is required')
    attributes: list[Attribute] = []
    by_id: dict[tuple[int, int], Attribute] = {}
    for item in range(count):
        path = f'/attributes/{item}'
        namespace = scalar(path + '/namespace', 32)
        identifier = scalar(path + '/id', 32)
        if (namespace, identifier) in by_id:
            raise LayerError('Duplicate attribute identity')
        size = value_count(path + '/value_count')
        if size == 0:
            raise LayerError('Empty attribute values are outside the observed profiles')
        values = []
        for index in range(size):
            vp = f'{path}/values/{index}'
            values.append(scalar(vp + '/fourcc', 32))
            for optional in ('first', 'second'):
                op = vp + '/' + optional
                if scalar(op + '/present', 1):
                    if scalar(op + '/has_f32', 1):
                        scalar(op + '/f32_bits', 32)
                    scalar(op + '/unknown6', 6)
                    scalar(op + '/id16', 16)
            if scalar(vp + '/extra/present', 1):
                for label, bits in (('unknown6', 6), ('unknown32', 32), ('first16', 16), ('second16', 16)):
                    scalar(vp + '/extra/' + label, bits)
            scalar(vp + '/flags', 3)
        if scalar(path + '/enabled/present', 1):
            scalar(path + '/enabled/unknown25', 25)
            rules = scalar(path + '/enabled/rule_count', 5)
            for rule in range(rules):
                rp = f'{path}/enabled/{rule}'
                scalar(rp + '/unknown5', 5)
                scalar(rp + '/namespace', 32)
                scalar(rp + '/id', 32)
                allowed = value_count(rp + '/value_count')
                for index in range(allowed):
                    scalar(f'{rp}/values/{index}', 32)
        scalar(path + '/unknown15', 15)
        scalar(path + '/unknown32', 32)
        default = choice(path + '/default_choice', size)
        scalar(path + '/unknown9', 9)
        attribute = Attribute(namespace, identifier, tuple(values), default)
        by_id[(namespace, identifier)] = attribute
        attributes.append(attribute)
    boundaries.append(('attribute_definitions_end', reader.position))

    scalar('/selected_attributes/unknown127', 127)
    selected_count = scalar('/selected_attributes/count', 9)
    if selected_count != count:
        raise LayerError('Selected-attribute and definition counts disagree')
    selections, seen = [], set()
    for item in range(selected_count):
        path = f'/selected_attributes/{item}'
        namespace = scalar(path + '/namespace', 32)
        identifier = scalar(path + '/id', 32)
        key = namespace, identifier
        if key not in by_id or key in seen:
            raise LayerError('Missing or duplicate selected-attribute identity')
        seen.add(key)
        selected = choice(path + '/choice', len(by_id[key].values))
        selections.append(Selection(namespace, identifier, selected))
    boundaries.append(('selected_attributes_end', reader.position))

    count = scalar('/locales/s2mv_count', 6)
    for item in range(count):
        blob(f'/locales/s2mv/{item}', 40)
    count = scalar('/locales/count', 5)
    for item in range(count):
        path = f'/locales/{item}'
        scalar(path + '/fourcc', 32)
        handles = scalar(path + '/handle_count', 6)
        for handle in range(handles):
            blob(f'{path}/handles/{handle}', 40)
    if reader.position % 8:
        raise LayerError('Locale boundary is not aligned; unsupported member shape')
    boundaries.append(('locale_handles_end', reader.position))
    layer = Layer(profile, tuple(tokens), tuple(attributes), tuple(selections), raw[reader.position // 8:], tuple(boundaries), digest(raw), len(raw))
    if encode_layer(layer, profile) != raw:
        raise LayerError('Same-profile reconstruction is not byte-exact')
    return layer


def encode_layer(layer: Layer, profile: str) -> bytes:
    index_width = width(profile)
    if not isinstance(layer, Layer) or len(layer.tokens) > MAX_TOKENS:
        raise LayerError('A decoded bounded layer is required')
    writer = _Writer()
    for token in layer.tokens:
        if token.kind == 'blob':
            writer.blob(token.value)
        elif token.kind in ('fixed', 'count', 'index'):
            bits = token.fixed_width if token.kind == 'fixed' else index_width + (token.kind == 'count')
            writer.bits(token.value, bits)
        else:
            raise LayerError('Unknown token kind')
    if writer.position % 8:
        raise LayerError('Encoded locale boundary is not aligned')
    writer.blob(layer.opaque_suffix)
    result = bytes(writer.raw)
    if len(result) > MAX_MEMBER_BYTES:
        raise LayerError('Encoded member exceeds the size bound')
    return result


def summary(layer: Layer) -> dict[str, Any]:
    return {'format': 'hots-battlelobby-attribute-layer-v1', 'profile': layer.profile,
            'index_bits': width(layer.profile), 'value_count_bits': width(layer.profile) + 1,
            'member_sha256': layer.original_sha256, 'member_bytes': layer.original_bytes,
            'attribute_definitions': len(layer.attributes), 'selected_attributes': len(layer.selections),
            'boundaries_bits': dict(layer.boundaries), 'count_fields': sum(t.kind == 'count' for t in layer.tokens),
            'index_fields': sum(t.kind == 'index' for t in layer.tokens),
            'opaque_suffix_bytes': len(layer.opaque_suffix), 'opaque_suffix_sha256': digest(layer.opaque_suffix),
            'same_profile_roundtrip_exact': True, 'profile_is_authoritative_schema': False,
            'full_member_semantics_validated': False, 'client_playback_validated': False}


def transcode_member(raw: bytes, source_profile: str, target_profile: str) -> tuple[bytes, dict[str, Any]]:
    source = decode_layer(raw, source_profile)
    target_bytes = encode_layer(source, target_profile)
    target = decode_layer(target_bytes, target_profile)
    if source.tokens != target.tokens or source.attributes != target.attributes or source.selections != target.selections:
        raise LayerError('Transcoding changed a decoded field')
    if source.opaque_suffix != target.opaque_suffix:
        raise LayerError('Opaque suffix changed')
    if encode_layer(target, source_profile) != raw:
        raise LayerError('Inverse transformation did not recover the original bytes')
    audit = [{'path': t.path, 'value': t.value, 'before_bits': width(source_profile) + (t.kind == 'count'),
              'after_bits': width(target_profile) + (t.kind == 'count')}
             for t in source.tokens if t.kind in ('count', 'index') and source_profile != target_profile]
    return target_bytes, {'format': 'hots-battlelobby-attribute-transcode-v1', 'source': summary(source),
                          'target': summary(target), 'numeric_values_and_flags_preserved': True,
                          'opaque_suffix_preserved': True, 'inverse_roundtrip_exact': True,
                          'changes': audit, 'replay_created': False, 'client_playback_validated': False}


def crosscheck_attributes(layer: Layer, decoded_attributes: dict) -> dict[str, Any]:
    """Compare original scope numbers; does not guess modern working-set remaps."""
    by_id = {(a.namespace, a.identifier): a for a in layer.attributes}
    chosen = {}
    for selection in layer.selections:
        table = by_id[(selection.namespace, selection.identifier)].values
        for slot, (index, _is_set) in enumerate(selection.choice.values):
            scope = 16 if selection.choice.tag == 0 else slot + 1
            chosen[(scope, selection.namespace, selection.identifier)] = table[index].to_bytes(4, 'big').strip(b'\0')
    scopes = decoded_attributes.get('scopes')
    if not isinstance(scopes, dict):
        raise LayerError('Decoded attribute scopes are required')
    matched = 0
    for scope, entries in scopes.items():
        for identifier, values in entries.items():
            for value in values:
                if chosen.get((scope, value['namespace'], identifier)) != value['value']:
                    raise LayerError('Attribute-stream value disagrees with the selected battlelobby value')
                matched += 1
    if not matched:
        raise LayerError('An empty attribute cross-check is not evidence')
    return {'scope_policy': 'Original scope16 global; original slot0 corresponds to scope1',
            'values_matched': matched, 'mismatches': 0, 'working_set_remap_inferred': False}


def crosscheck_original(layer: Layer, path: Path) -> dict[str, Any]:
    raw = _read(path, 4 * 1024 * 1024)
    if digest(raw) != ORIGINAL_SHA256:
        raise LayerError('Only the immutable original TEN_GREYMANE replay is accepted')
    from mpq_reader import MPQArchive
    from protocol_loader import load_protocol
    archive = MPQArchive(path)
    try:
        attributes = archive.read_file('replay.attributes.events')
    finally:
        archive.close()
    result = crosscheck_attributes(layer, load_protocol(41810).decode_replay_attributes_events(attributes))
    if digest(_read(path, 4 * 1024 * 1024)) != ORIGINAL_SHA256:
        raise LayerError('Original replay changed during inspection')
    return {'original_sha256': ORIGINAL_SHA256, **result}


def _read(path: Path, limit: int = MAX_MEMBER_BYTES) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= limit:
        raise LayerError('A bounded regular input file is required')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise LayerError('Input grew beyond its bound')
    return raw


def _write_new(path: Path, raw: bytes) -> None:
    _check_new(path)
    with Path(path).open('xb') as stream:
        stream.write(raw)


def _check_new(path: Path) -> None:
    path = Path(path)
    if path.suffix.lower() == '.stormreplay':
        raise LayerError('This tool writes members/reports, never replay archives')
    if path.exists() or path.is_symlink():
        raise FileExistsError('Output already exists')
    if not path.parent.is_dir():
        raise LayerError('Output parent must be an existing directory')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('audit', 'transcode-member'):
        p = sub.add_parser(command)
        p.add_argument('member', type=Path)
        p.add_argument('--source-profile', required=True, choices=PROFILES)
        p.add_argument('--original-replay', type=Path)
        p.add_argument('--report', type=Path)
        if command == 'transcode-member':
            p.add_argument('--target-profile', required=True, choices=PROFILES)
            p.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    outputs = [p for p in (getattr(args, 'output', None), args.report) if p is not None]
    if len({p.resolve() for p in outputs}) != len(outputs):
        raise LayerError('Member and report outputs must be distinct')
    for path in outputs:
        _check_new(path)
    raw = _read(args.member)
    layer = decode_layer(raw, args.source_profile)
    check = crosscheck_original(layer, args.original_replay) if args.original_replay else None
    if args.command == 'transcode-member':
        result, report = transcode_member(raw, args.source_profile, args.target_profile)
        _write_new(args.output, result)
    else:
        report = summary(layer)
    if check is not None:
        report['original_attribute_crosscheck'] = check
    if args.report is not None:
        _write_new(args.report, (json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({k: v for k, v in report.items() if k != 'changes'}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
