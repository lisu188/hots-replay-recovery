"""Bounded native98348 replay.initData value codec, rooted only at type775.

Anonymous tuples preserve declaration order; they are not native object layouts.
This codec validates supplied values and never invents historical/current fields.
Canonical value writing zeroes discarded alignment padding. Source reproduction
is a separate operation and requires an unchanged, revalidated decoded object.
Neither operation proves native setup state, CRC or simulation compatibility.
"""
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

PROFILE = 'setup-98348'
ROOT_TYPE = 775
SCHEMA_SHA256 = '0c9e5d80f745d9e8d7191e3bc3039fb9e07e1d2c5e83c0bbbeb081216e23395e'
OFFICIAL_TYPES_SHA256 = '3f7f2c49851c56db66a7b96cdb98db2e55a48fd8bba85dfd3f3678af59d42233'
MAX_MEMBER_BYTES = 1048576


class SetupError(ValueError):
    """Diagnostics contain only fixed reasons, type IDs and bit positions."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pinned_file(name, size, digest):
    path = Path(__file__).with_name(name)
    try:
        if path.is_symlink():
            raise SetupError('native setup dependency symlink refused')
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != size:
                raise SetupError('native setup dependency size or type differs')
            raw = stream.read(size + 1)
            after = os.fstat(stream.fileno())
        if (len(raw) != size or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns or _sha(raw) != digest):
            raise SetupError('native setup dependency pin differs')
        return raw
    except OSError:
        raise SetupError('native setup dependency unavailable') from None


def _model(name, size, digest):
    raw = _pinned_file(name, size, digest)
    spec = importlib.util.spec_from_loader(name[:-3], loader=None)
    module = importlib.util.module_from_spec(spec)
    # Execute exactly the checked buffer, without reopening a mutable pathname.
    exec(compile(raw, name, 'exec'), module.__dict__)
    return module


_reader = _model('_native_setup_reader.py', 7355,
                '0ed16f26148d940680c89a80bb82220a34081a1de745bb34ca148be1b9c58a39')
_writer = _model('_native_setup_writer.py', 8694,
                'd6dcfadf4bbbfadce361c7939e50172afdf9ba1a0ac0537716e817872e45adb7')
_string = _model('_native_setup_string.py', 2145,
                '56087d34ad3569cb20a01d1831e15697432840d22c2a008c83a267bd65dcea69')


def _profile(profile):
    if type(profile) is not str or profile != PROFILE:
        raise SetupError('unsupported native setup profile')


def _records():
    raw = _pinned_file('native_setup_schema_98348.json', 46829, SCHEMA_SHA256)
    return _reader.load_profile(raw)


@dataclass(frozen=True, repr=False)
class Setup:
    profile: str
    value: tuple
    payload_end_bit: int
    source_sha256: str
    _source: bytes
    _statistics: tuple

    def summary(self):
        checked = _checked_setup(self)
        nodes, array_elements, strings, padding, nonzero, kinds, types = checked._statistics
        return {'profile': PROFILE, 'root_type_id': ROOT_TYPE,
                'schema_sha256': SCHEMA_SHA256,
                'member_bytes': len(checked._source),
                'member_sha256': checked.source_sha256,
                'native_payload_start_bit': 0,
                'native_payload_end_bit': checked.payload_end_bit,
                'EOF_alignment_padding_bits': len(checked._source) * 8 - checked.payload_end_bit,
                'decoded_nodes': nodes, 'array_elements': array_elements,
                'string_instances': strings, 'internal_padding_spans': padding,
                'nonzero_internal_padding_spans': nonzero,
                'kind_counts': dict(kinds), 'observed_type_count': len(types),
                'names_authenticated': False,
                'simulation_or_historical_conversion_proven': False}


def decode_setup(raw, profile=PROFILE):
    """Read exactly one complete native775 member, with zero final padding.

    Internal alignment bits are accepted as the native reader discards them;
    source bytes are retained privately for the source-preserving operation.
    No schema path, type ID, bit offset or STRING callback is caller-selectable.
    """
    _profile(profile)
    records = _records()
    try:
        reader = _reader.Reader(raw, records, _string.count_native_string_sequences)
        value = reader.read()
        payload_end_bit = reader.bit
        statistics = (reader.nodes, reader.array_elements, reader.string_instances,
                      reader.padding_spans, reader.nonzero_padding_spans,
                      tuple(sorted(reader.kinds.items())), tuple(sorted(reader.types.items())))
        reader.finish()
    except _reader.Rejected as error:
        raise SetupError(str(error)) from None
    return Setup(PROFILE, value, payload_end_bit, _sha(raw), raw, statistics)


def encode_setup_values(value, profile=PROFILE):
    """Serialize supplied native775 values with canonical zero alignment bits."""
    _profile(profile)
    try:
        writer = _writer.Writer(_records(), _string.count_native_string_sequences)
        writer.write(value)
        return writer.finish()
    except _writer.Rejected as error:
        raise SetupError(str(error)) from None


def _same_value(left, right, depth=0):
    # Right is freshly decoded and bounded. Exact types matter: True != int1.
    if type(left) is not type(right) or depth > 128:
        return False
    if type(right) is tuple:
        return len(left) == len(right) and all(
            _same_value(a, b, depth + 1) for a, b in zip(left, right))
    return left == right


def _checked_setup(setup):
    if type(setup) is not Setup:
        raise SetupError('decoded native setup required')
    _profile(setup.profile)
    checked = decode_setup(setup._source)
    if (type(setup.payload_end_bit) is not int
            or setup.payload_end_bit != checked.payload_end_bit
            or type(setup.source_sha256) is not str
            or setup.source_sha256 != checked.source_sha256
            or not _same_value(setup._statistics, checked._statistics)
            or not _same_value(setup.value, checked.value)):
        raise SetupError('decoded native setup changed')
    return checked


def reencode_setup_source(setup, profile=PROFILE):
    """Reproduce unchanged validated source bytes, including internal padding."""
    _profile(profile)
    return _checked_setup(setup)._source


def _official_types(typeinfos):
    # A fixed public schema is tiny; bound its containers before JSON encoding.
    nodes = 0

    def check(value, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 10000 or depth > 16:
            raise SetupError('official setup schema budget')
        if type(value) in (tuple, list):
            if len(value) > 1024:
                raise SetupError('official setup schema budget')
            for child in value:
                check(child, depth + 1)
        elif type(value) is dict:
            if len(value) > 1024:
                raise SetupError('official setup schema budget')
            for key, child in value.items():
                check(key, depth + 1)
                check(child, depth + 1)
        elif type(value) is str:
            if len(value) > 256:
                raise SetupError('official setup schema budget')
        elif type(value) is int:
            if value.bit_length() > 128:
                raise SetupError('official setup schema budget')
        elif value is not None:
            raise SetupError('official setup schema type')

    if type(typeinfos) not in (tuple, list) or len(typeinfos) != 213:
        raise SetupError('official setup schema pin')
    check(typeinfos)
    try:
        raw = json.dumps(typeinfos, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True).encode('ascii')
    except (ValueError, TypeError):
        raise SetupError('official setup schema pin') from None
    if _sha(raw) != OFFICIAL_TYPES_SHA256:
        raise SetupError('official setup schema pin')


def compare_setup_with_official(setup, official_initdata, official_typeinfos):
    """Compare with the pinned Blizzard96477 inner70 projection (outer71).

    Agreement authenticates logical wire values for these two selected graphs;
    names, native layout, historical mapping and simulation are separate claims.
    """
    checked = _checked_setup(setup)
    _official_types(official_typeinfos)
    # Refuse foreign Python objects before comparisons/hashing can invoke user
    # methods. Blizzard's decoded tree uses only these exact built-in types.
    nodes = 0

    def check(value, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 250000 or depth > 128:
            raise SetupError('official setup value budget')
        if type(value) is dict:
            if len(value) > 1024:
                raise SetupError('official setup value budget')
            for key, child in value.items():
                if type(key) is not str or len(key) > 256:
                    raise SetupError('official setup field key type')
                check(child, depth + 1)
        elif type(value) in (tuple, list):
            if len(value) > 100000:
                raise SetupError('official setup value budget')
            for child in value:
                check(child, depth + 1)
        elif type(value) is bytes:
            if len(value) > MAX_MEMBER_BYTES:
                raise SetupError('official setup value budget')
        elif type(value) is int:
            if value.bit_length() > MAX_MEMBER_BYTES * 8:
                raise SetupError('official setup value budget')
        elif type(value) is not bool and value is not None:
            raise SetupError('official setup value type')

    check(official_initdata)
    if type(official_initdata) is not dict or set(official_initdata) != {'m_syncLobbyState'}:
        raise SetupError('official setup root shape')
    try:
        return _reader.compare_candidate(checked.value, _records(), ROOT_TYPE,
            official_initdata['m_syncLobbyState'], official_typeinfos, 70)
    except (_reader.Rejected, KeyError, IndexError, TypeError):
        raise SetupError('official setup values differ') from None
