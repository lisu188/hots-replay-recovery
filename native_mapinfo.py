"""Read-only S2MapInfo codec for the authenticated native 98348 snapshot.

The selected 191-type closure and the shared scalar decoder are pinned. Authors,
addresses and all other decoded values stay in objects whose repr is disabled.
This module inspects consumed member spans; it never constructs a replay.
"""
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import stat

import native_clientinfo as shared
from battlelobby_attribute_layer import MAX_MEMBER_BYTES, LayerError, _Reader, _Writer

PROFILE = 'mapinfo-98348'
ROOT_TYPE = 5852
SCHEMA_SHA256 = '3900a63c0799474becd2ecfb03eece4f8c523a965b38e539264867d5cdf2075c'
SHARED_DECODER_SHA256 = 'e0abd0b674c97b87f6a1510edc08704eebeca0ad9d43ac0537d5eaaa3eb9b202'
SOURCE_PE_SHA256 = shared.SOURCE_PE_SHA256
SOURCE_BYTECODE_SHA256 = shared.SOURCE_BYTECODE_SHA256
MAX_SCHEMA_BYTES = 256 * 1024


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pinned_file(path, limit, expected):
    path = Path(path)
    if path.is_symlink():
        raise LayerError('Native schema/decoder symlink refused')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= limit:
            raise LayerError('Native schema/decoder size or type differs')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if (len(raw) != before.st_size or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns or _sha(raw) != expected):
        raise LayerError('Pinned native schema/decoder differs')
    return raw


def _schema(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name('native_mapinfo_schema_98348.json')
    _pinned_file(shared.__file__, 64 * 1024, SHARED_DECODER_SHA256)
    data = json.loads(_pinned_file(path, MAX_SCHEMA_BYTES, SCHEMA_SHA256))
    if (data['profile'] != PROFILE or data['root_type_id'] != ROOT_TYPE
            or data['source_PE_sha256'] != SOURCE_PE_SHA256
            or data['source_embedded_bytecode_sha256'] != SOURCE_BYTECODE_SHA256
            or data['selected_type_count'] != 191 or len(data['records']) != 191):
        raise LayerError('Native MapInfo provenance differs')
    return SimpleNamespace(records={record['id']: record for record in data['records']})


@dataclass(frozen=True, repr=False)
class MapInfo:
    profile: str
    start_bit: int
    end_bit: int
    fields: tuple[shared.NativeField, ...]
    tokens: tuple[shared.WireToken, ...]
    source: bytes
    source_sha256: str

    def field(self, path, kind=None):
        candidates = [field for field in self.fields if field.path == path
                      and (kind is None or field.kind == kind)]
        if not candidates:
            raise LayerError('Expected native MapInfo field absent')
        return next((field for field in candidates if field.kind != 'USER'), candidates[-1])

    @property
    def identity(self):
        handle = self.field('/m_handle').value
        return handle['m_id'], handle['m_version']

    def summary(self):
        return {'profile': PROFILE, 'schema_sha256': SCHEMA_SHA256,
                'start_bit': self.start_bit, 'end_bit': self.end_bit,
                'named_root_fields': 32,
                'required_permission_count': self.field('/m_requiredPermissions', 'ARRAY').value,
                'last_two_named_widths': [self.field('/m_addMultiMod').end_bit - self.field('/m_addMultiMod').start_bit,
                    self.field('/m_requiredPermissions').end_bit - self.field('/m_requiredPermissions').start_bit],
                'exact_span_reencoding': shared._span_exact(self, encode_mapinfo(self)),
                'private_values_emitted': False}


def decode_mapinfo(raw, start_bit, profile, *, schema_path=None):
    if profile != PROFILE:
        raise LayerError('Explicit native MapInfo98348 profile required')
    if (type(raw) is not bytes or not 1 <= len(raw) <= MAX_MEMBER_BYTES
            or type(start_bit) is not int or not 0 <= start_bit < len(raw) * 8):
        raise LayerError('Invalid bounded native MapInfo input')
    decoder = shared._Decoder(_schema(schema_path), raw, start_bit)
    decoder.decode(ROOT_TYPE)
    result = MapInfo(PROFILE, start_bit, decoder.reader.position, tuple(decoder.fields),
                     tuple(decoder.tokens), raw, _sha(raw))
    encode_mapinfo(result)
    return result


def encode_mapinfo(value, profile=PROFILE):
    """Reconstruct exactly the consumed span; reject any changed wire token."""
    if (not isinstance(value, MapInfo) or value.profile != PROFILE or profile != PROFILE
            or len(value.tokens) > shared.MAX_TOKENS):
        raise LayerError('Pinned decoded native MapInfo required')
    if (type(value.source) is not bytes or not 1 <= len(value.source) <= MAX_MEMBER_BYTES
            or _sha(value.source) != value.source_sha256):
        raise LayerError('Decoded native MapInfo source differs')
    if (type(value.start_bit) is not int or type(value.end_bit) is not int
            or not 0 <= value.start_bit < value.end_bit <= len(value.source) * 8):
        raise LayerError('Decoded native MapInfo span bounds differ')
    writer = _Writer()
    writer.position = value.start_bit // 8 * 8
    writer.raw = bytearray(value.source[:value.start_bit // 8])
    if value.start_bit % 8:
        reader = _Reader(value.source)
        reader.position = writer.position
        writer.bits(reader.bits(value.start_bit % 8), value.start_bit % 8)
    for token in value.tokens:
        if not isinstance(token, shared.WireToken):
            raise LayerError('Invalid native MapInfo wire token')
        if token.width is None:
            if type(token.value) is not bytes or len(token.value) > shared.MAX_STRING:
                raise LayerError('Native MapInfo blob token exceeds budget')
            writer.blob(token.value)
        else:
            writer.bits(token.value, token.width)
        if len(writer.raw) > MAX_MEMBER_BYTES:
            raise LayerError('Reencoded native MapInfo span exceeds budget')
    if writer.position != value.end_bit:
        raise LayerError('Reencoded native MapInfo span extent differs')
    output = bytes(writer.raw[value.start_bit // 8:])
    if not shared._span_exact(value, output):
        raise LayerError('Read-only native MapInfo reencoding changed consumed bits')
    return output


def audit_current_map_infos(raw, metadata=None):
    """Crossbind every native record to a freshly parsed observed-current member.

    The archive build/root and private initData/details checks belong to the
    caller. The optional saved metadata report must equal fresh source-bound
    parsing; it cannot supply arbitrary offsets or substitute a different file.
    """
    from audit_battlelobby_mod_metadata import audit_member
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_MEMBER_BYTES:
        raise LayerError('A bounded current member is required')
    actual = audit_member(raw, 'observed-11', 'current-observed')
    if metadata is not None and metadata != actual:
        raise LayerError('Observed metadata differs from this unchanged member')
    if (actual['profile'] != 'current-observed'
            or actual['same_profile_full_member_roundtrip_exact'] is not True
            or actual['member_bytes'] != len(raw) or actual['member_sha256'] != _sha(raw)
            or not 1 <= len(actual['entries']) <= 100):
        raise LayerError('Observed current MapInfo metadata differs')
    last_widths = Counter()
    permissions = Counter()
    for entry in actual['entries']:
        info = decode_mapinfo(raw, entry['start_bit'], PROFILE)
        if info.end_bit != entry['end_bit']:
            raise LayerError('Native MapInfo end differs from observed record')
        reader = _Reader(raw)
        reader.position = entry['start_bit']
        if info.identity != (reader.bits(32), reader.bits(32)):
            raise LayerError('Native MapInfo identity differs from observed pair')
        summary = info.summary()
        last_widths[tuple(summary['last_two_named_widths'])] += 1
        permissions[summary['required_permission_count']] += 1
    return {'profile': PROFILE, 'schema_sha256': SCHEMA_SHA256,
            'records_checked': len(actual['entries']), 'named_fields_per_record': 32,
            'all_native_ends_and_identities_match_observed_records': True,
            'all_consumed_spans_reencode_exact': True,
            'last_two_field_width_histogram': [{'widths': list(widths), 'records': count}
                for widths, count in sorted(last_widths.items())],
            'required_permission_count_histogram': dict(sorted(permissions.items())),
            'raw_author_or_player_values_emitted': False, 'full_replay_compatibility_claimed': False}
