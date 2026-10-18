"""Read-only online StartGameRequest reader for the pinned native98348 graph.

Only root5917 at bit0 is supported. The current graph and shared private token
types are pinned; no game binary is read or loaded. Authored/private fields stay
in repr-disabled objects. Archive build/root validation belongs to the caller.
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

PROFILE = 'online-start-98348'
ROOT_TYPE = 5917
SCHEMA_SHA256 = '0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640'
SHARED_TYPES_SHA256 = 'e0abd0b674c97b87f6a1510edc08704eebeca0ad9d43ac0537d5eaaa3eb9b202'
SOURCE_PE_SHA256 = 'efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
SOURCE_BYTECODE_SHA256 = 'ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
MAX_SCHEMA_BYTES = 256*1024
MAX_FIELDS = 500000
MAX_WIRE_TOKENS = 250000
MAX_ARRAY = 32768
MAX_STRING = 4096
MAX_DEPTH = 64
ROOT_FIELDS = ('StartGameRequest', 'm_randomSeed', 'm_clientId', 'm_clientInfoList',
    'm_voiceSessionId', 'm_ammHandle', 'm_isCompetitive', 'm_isRanked', 'm_isPractice',
    'm_isCooperative', 'm_saveStats', 'm_saveReplay', 'm_instanceHandle', 'm_ladderStats',
    'm_races', 'm_clientUnlockableInfoList', 'm_achievementTags', 'm_clientLicensesList',
    'm_currentTurn', 'm_turnIntervalMS', 'm_currentSyncEventNumber', 'm_tournamentInfo',
    'm_heroMasteryTiers', 'm_rejoinSaveCacheHandle', 'm_rejoinSaveElapsedGameLoops')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pinned_file(path, limit, expected):
    path = Path(path)
    if path.is_symlink():
        raise LayerError('Native schema/types symlink refused')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= limit:
            raise LayerError('Native schema/types size or file type differs')
        raw = stream.read(limit+1)
        after = os.fstat(stream.fileno())
    if (len(raw) != before.st_size or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns or _sha(raw) != expected):
        raise LayerError('Pinned native schema/types differs')
    return raw


def _schema(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name('native_startgame_schema_98348.json')
    _pinned_file(shared.__file__, 64*1024, SHARED_TYPES_SHA256)
    data = json.loads(_pinned_file(path, MAX_SCHEMA_BYTES, SCHEMA_SHA256))
    if (data['online_root_type_id'] != ROOT_TYPE or data['selected_type_count'] != 513
            or len(data['records']) != 513 or data['source_PE_sha256'] != SOURCE_PE_SHA256
            or data['source_embedded_bytecode_sha256'] != SOURCE_BYTECODE_SHA256):
        raise LayerError('Native online StartGameRequest provenance differs')
    records = {record['id']: record for record in data['records']}
    if len(records) != 513 or tuple(records[ROOT_TYPE]['field_names']) != ROOT_FIELDS:
        raise LayerError('Native online root fields differ')
    return SimpleNamespace(records=records)


class _Decoder:
    """Locally bounded scalar engine; shared module globals are never changed."""
    def __init__(self, schema, raw):
        self.schema = schema
        self.reader = _Reader(raw)
        self.fields = []
        self.tokens = []

    def bits(self, width):
        if len(self.tokens) >= MAX_WIRE_TOKENS:
            raise LayerError('Native online wire-token budget exceeded')
        value = self.reader.bits(width)
        self.tokens.append(shared.WireToken(width, value))
        return value

    def blob(self, size):
        if len(self.tokens) >= MAX_WIRE_TOKENS:
            raise LayerError('Native online wire-token budget exceeded')
        value = self.reader.blob(size)
        self.tokens.append(shared.WireToken(None, value))
        return value

    def decode(self, identifier, path='', depth=0):
        if depth > MAX_DEPTH or len(self.fields) >= MAX_FIELDS:
            raise LayerError('Native online field/depth budget exceeded')
        record = self.schema.records[identifier]
        kind = record['kind']
        bound = record.get('bounds')
        start = self.reader.position
        value = None
        if kind == 'USER':
            value = self.decode(record['element_type'], path, depth+1)
        elif kind == 'STRUCT':
            value = {name: self.decode(child, path+'/'+name, depth+1)
                     for name, child in zip(record['field_names'], record['field_types'])}
        elif kind == 'CHOICE':
            value = self.bits(bound['bits'])+bound['min']
            if value not in record['tags']:
                raise LayerError('Native online choice tag outside declared fields')
            index = record['tags'].index(value)
            self.decode(record['field_types'][index], path+'/'+record['field_names'][index], depth+1)
        elif kind == 'ARRAY':
            value = self.bits(bound['bits'])+bound['min']
            if not 0 <= value <= min(bound['max'], MAX_ARRAY):
                raise LayerError('Native online array exceeds bound')
            for index in range(value):
                self.decode(record['element_type'], path+'/'+str(index), depth+1)
        elif kind == 'OPTIONAL':
            value = self.bits(1)
            if value:
                self.decode(record['element_type'], path+'/value', depth+1)
        elif kind in ('ASCII_STRING', 'STRING', 'BLOB'):
            count = self.bits(bound['bits']+(2 if kind == 'STRING' else 0))+bound['min']
            if not 0 <= count <= min(bound['max']*(4 if kind == 'STRING' else 1), MAX_STRING):
                raise LayerError('Native online string/blob exceeds bound')
            value = self.blob(count)
            try:
                if kind == 'ASCII_STRING':
                    value.decode('ascii')
                if kind == 'STRING' and not bound['min'] <= len(value.decode('utf-8')) <= bound['max']:
                    raise LayerError('Native online UTF8 character count exceeds bound')
            except UnicodeError:
                raise LayerError('Native online string encoding is invalid') from None
        elif kind == 'BIT_ARRAY':
            value = self.bits(bound['bits'])+bound['min']
            if not 0 <= value <= min(bound['max'], 65536):
                raise LayerError('Native online bit array exceeds bound')
            for index in range(0, value, 64):
                self.bits(min(64, value-index))
        elif kind in ('INT', 'ENUM'):
            value = self.bits(bound['bits'])+bound['min']
            if value > bound['max'] or kind == 'ENUM' and value not in record['tags']:
                raise LayerError('Native online scalar outside declared bound')
        elif kind in ('BOOL', 'FOURCC', 'REAL32', 'REAL64'):
            value = self.bits({'BOOL': 1, 'FOURCC': 32, 'REAL32': 32, 'REAL64': 64}[kind])
        elif kind != 'NULL':
            raise LayerError('Unsupported native online kind')
        # A parent suspended during child recursion must also respect the cap.
        if len(self.fields) >= MAX_FIELDS:
            raise LayerError('Native online field/depth budget exceeded')
        self.fields.append(shared.NativeField(path, identifier, start, self.reader.position, kind, value))
        return value


@dataclass(frozen=True, repr=False)
class OnlineStartGame:
    profile: str
    payload_end_bit: int
    padding_bits: int
    fields: tuple[shared.NativeField, ...]
    tokens: tuple[shared.WireToken, ...]
    source: bytes
    source_sha256: str

    def field(self, path, kind=None):
        candidates = [field for field in self.fields if field.path == path
                      and (kind is None or field.kind == kind)]
        if not candidates:
            raise LayerError('Expected native online field absent')
        return next((field for field in candidates if field.kind != 'USER'), candidates[-1])

    def summary(self):
        encode_startgame(self)
        spans = []
        position = 0
        for name in ROOT_FIELDS:
            field = self.field('/'+name)
            if field.start_bit != position:
                raise LayerError('Native online root field spans are not contiguous')
            position = field.end_bit
            spans.append({'name': name, 'kind': field.kind, 'start_bit': field.start_bit, 'end_bit': field.end_bit})
        if position != self.payload_end_bit:
            raise LayerError('Native online root field end differs')
        counts = {}
        for path in ('/StartGameRequest/m_mapInfoList', '/StartGameRequest/m_resourceMap',
                     '/StartGameRequest/m_accessMatrix', '/StartGameRequest/m_disabledHeroList',
                     '/m_clientInfoList', '/m_clientUnlockableInfoList', '/m_achievementTags',
                     '/m_clientLicensesList', '/m_heroMasteryTiers'):
            count = self.field(path, 'ARRAY').value
            if type(count) is not int or not 0 <= count <= MAX_ARRAY:
                raise LayerError('Native online aggregate count differs')
            counts[path] = count
        return {'profile': PROFILE, 'schema_sha256': SCHEMA_SHA256, 'root_type_id': ROOT_TYPE,
            'member_bytes': len(self.source), 'member_sha256': self.source_sha256,
            'native_payload_start_bit': 0, 'native_payload_end_bit': self.payload_end_bit,
            'EOF_alignment_padding_bits': self.padding_bits, 'named_root_fields': 25,
            'root_field_spans': spans, 'safe_array_counts': counts,
            'decoded_fields': len(self.fields), 'wire_tokens': len(self.tokens),
            'complete_EOF_and_readonly_whole_member_reencoding_exact': True,
            'private_author_client_license_network_or_player_values_emitted': False,
            'archive_build_root_or_full_replay_compatibility_claimed': False}


def decode_startgame(raw, profile, *, schema_path=None):
    if profile != PROFILE:
        raise LayerError('Explicit online-start-98348 profile required')
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_MEMBER_BYTES:
        raise LayerError('Invalid bounded native online member')
    decoder = _Decoder(_schema(schema_path), raw)
    decoder.decode(ROOT_TYPE)
    payload_end = decoder.reader.position
    padding = len(raw)*8-payload_end
    if not 0 <= padding < 8:
        raise LayerError('Native online extra EOF bytes or truncated payload')
    if padding and decoder.bits(padding):
        raise LayerError('Native online nonzero EOF alignment padding')
    result = OnlineStartGame(PROFILE, payload_end, padding, tuple(decoder.fields), tuple(decoder.tokens), raw, _sha(raw))
    encode_startgame(result)
    return result


def encode_startgame(value, profile=PROFILE):
    """Reencode the entire source member exactly; all token changes are refused."""
    if (not isinstance(value, OnlineStartGame) or value.profile != PROFILE or profile != PROFILE
            or len(value.tokens) > MAX_WIRE_TOKENS or len(value.fields) > MAX_FIELDS):
        raise LayerError('Pinned decoded native online object required')
    if (type(value.source) is not bytes or not 1 <= len(value.source) <= MAX_MEMBER_BYTES
            or _sha(value.source) != value.source_sha256):
        raise LayerError('Decoded native online source differs')
    if (type(value.payload_end_bit) is not int or type(value.padding_bits) is not int
            or not 0 <= value.padding_bits < 8
            or not 0 < value.payload_end_bit <= len(value.source)*8
            or value.payload_end_bit+value.padding_bits != len(value.source)*8):
        raise LayerError('Decoded native online source extent differs')
    writer = _Writer()
    for token in value.tokens:
        if not isinstance(token, shared.WireToken):
            raise LayerError('Invalid native online wire token')
        if token.width is None:
            if type(token.value) is not bytes or len(token.value) > MAX_STRING:
                raise LayerError('Native online blob token exceeds bound')
            writer.blob(token.value)
        else:
            writer.bits(token.value, token.width)
        if len(writer.raw) > MAX_MEMBER_BYTES:
            raise LayerError('Reencoded native online member exceeds bound')
    output = bytes(writer.raw)
    if writer.position != len(value.source)*8 or output != value.source:
        raise LayerError('Read-only native online reencoding changed source bytes or extent')
    return output


def audit_current_startgame(raw, profile=PROFILE, *, schema_path=None):
    """Return aggregate current structure facts; caller validates archive identity."""
    return decode_startgame(raw, profile, schema_path=schema_path).summary()
