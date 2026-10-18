"""Named static ArcadeSection arrays, independently bound to depot s2mh data.

Primary names: s2mdec@b48c60a697b12ae1dc8681a2d42ce313958ce94a,
s2m.go readLocalizationTableKey/readArcadeSectionHeader/readArcadeSectionRaw.
Bit widths are verified against authenticated original package headers and
observed current member records. This module never writes a replay or a file.
"""
from dataclasses import dataclass
import hashlib
import json

from battlelobby_attribute_layer import LayerError, MAX_MEMBER_BYTES, _Reader, _Writer


@dataclass(frozen=True)
class LocalizationKey:
    color: int | None
    table: int
    index: int


@dataclass(frozen=True)
class SectionHeader:
    title: LocalizationKey
    start_offset: int
    list_type: int
    subtitle: LocalizationKey


@dataclass(frozen=True)
class ArcadeSection:
    headers: tuple[SectionHeader, ...]
    items: tuple[LocalizationKey, ...]


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise LayerError('Arcade field cannot be represented without truncation')
    return value


def _key(value):
    if type(value) is not dict or set(value) != {0, 1, 2}:
        raise LayerError('Expected an exact depot localization-key structure')
    color = value[0]
    if color is not None:
        _uint(color, 32)
    return LocalizationKey(color, _uint(value[1], 6), _uint(value[2], 16))


def from_depot_subtree(value):
    """Convert only an already hash-verified s2mh[0][19][4 or5] subtree."""
    if type(value) is not dict or set(value) != {0, 1}:
        raise LayerError('Expected an exact depot arcade-section structure')
    if type(value[0]) is not list or type(value[1]) is not list:
        raise LayerError('Depot arcade sections must contain arrays')
    headers = []
    for item in value[0]:
        if type(item) is not dict or set(item) != {0, 1, 2, 3}:
            raise LayerError('Expected an exact depot section-header structure')
        headers.append(SectionHeader(_key(item[0]), _uint(item[1], 32),
                                     _uint(item[2], 2), _key(item[3])))
    section = ArcadeSection(tuple(headers), tuple(_key(item) for item in value[1]))
    _validate(section)
    return section


def _validate(section):
    if type(section) is not ArcadeSection or type(section.headers) is not tuple or type(section.items) is not tuple:
        raise LayerError('An immutable arcade section is required')
    if len(section.headers) > 15 or len(section.items) > 127:
        raise LayerError('Arcade array count exceeds the verified capacity')
    for header in section.headers:
        if type(header) is not SectionHeader or header.list_type not in (0, 1, 2):
            raise LayerError('Unsupported arcade section list type')
        _uint(header.start_offset, 32)
        _uint(header.list_type, 2)
    offsets = tuple(header.start_offset for header in section.headers)
    if (offsets and (offsets[0] != 0 or offsets != tuple(sorted(offsets)) or offsets[-1] > len(section.items))) or (not offsets and section.items):
        raise LayerError('Arcade section item offsets are inconsistent')
    for key in tuple(h.title for h in section.headers) + tuple(h.subtitle for h in section.headers) + section.items:
        if type(key) is not LocalizationKey:
            raise LayerError('An immutable localization key is required')
        if key.color is not None:
            _uint(key.color, 32)
        _uint(key.table, 6)
        _uint(key.index, 16)


def read_localization_key(read):
    color = read(32) if read(1) else None
    return LocalizationKey(color, read(6), read(16))


def read_section(read):
    """Read a four-bit header count and seven-bit item count, not a choice."""
    headers = []
    for _ in range(read(4)):
        headers.append(SectionHeader(read_localization_key(read), read(32),
                                     read(2), read_localization_key(read)))
    items = tuple(read_localization_key(read) for _ in range(read(7)))
    section = ArcadeSection(tuple(headers), items)
    _validate(section)
    return section


def write_localization_key(write, key):
    write(int(key.color is not None), 1)
    if key.color is not None:
        write(key.color, 32)
    write(key.table, 6)
    write(key.index, 16)


def write_section(write, section):
    _validate(section)
    write(len(section.headers), 4)
    for header in section.headers:
        write_localization_key(write, header.title)
        write(header.start_offset, 32)
        write(header.list_type, 2)
        write_localization_key(write, header.subtitle)
    write(len(section.items), 7)
    for item in section.items:
        write_localization_key(write, item)


def summary(section):
    """Report counts and canonical numeric digest; no localized text or blobs."""
    _validate(section)
    def key(value):
        return [value.color, value.table, value.index]
    numeric = [[key(h.title), h.start_offset, h.list_type, key(h.subtitle)] for h in section.headers], [key(item) for item in section.items]
    digest = hashlib.sha256(json.dumps(numeric, separators=(',', ':'), ensure_ascii=True).encode('ascii')).hexdigest()
    return dict(section_header_count=len(section.headers), localized_item_count=len(section.items),
                all_localization_colors_absent=all(x.color is None for x in tuple(h.title for h in section.headers) + tuple(h.subtitle for h in section.headers) + section.items),
                canonical_numeric_sha256=digest, interpretation='static-package-arcade-section-array')


def verify_binding(raw, start_bit, expected):
    """Compare depot numbers, then independently re-encode at source alignment."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MEMBER_BYTES or type(start_bit) is not int or not 0 <= start_bit < len(raw) * 8:
        raise LayerError('Bounded member and an inside bit offset are required')
    _validate(expected)
    reader = _Reader(raw)
    reader.position = start_bit
    actual = read_section(reader.bits)
    end = reader.position
    if actual != expected:
        raise LayerError('Depot arcade-section values differ from the member')
    writer = _Writer()
    writer.blob(raw[:start_bit // 8])
    prefix_bits = start_bit % 8
    writer.bits(raw[start_bit // 8] & ((1 << prefix_bits) - 1), prefix_bits)
    write_section(writer.bits, expected)
    if writer.position != end:
        raise LayerError('Arcade re-encoding boundary differs')
    padding = (-end) % 8
    writer.bits(reader.bits(padding), padding)
    writer.blob(raw[reader.position // 8:])
    if bytes(writer.raw) != raw:
        raise LayerError('Authenticated arcade reconstruction changes the member')
    return dict(start_bit=start_bit, end_bit=end, section_bits=end-start_bit,
                semantic_values_match=True, full_member_reencoding_exact=True,
                member_sha256=hashlib.sha256(raw).hexdigest(), **summary(actual))
