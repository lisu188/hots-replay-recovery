"""Read-only bounded old/current battlelobby mod-metadata audit.

Community reverse-engineered profiles describe serialization, not verified
runtime semantics. No conversion or replay writing is provided. Reports omit
all blob contents, names, toons, file handles and mod/dependency identifiers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from battlelobby_attribute_layer import MAX_MEMBER_BYTES, LayerError, _Reader, _Writer, _read, decode_layer

HISTORICAL_COMMIT = '85625327fd5623368410e5270a7eeb4869b40af9'
CURRENT_COMMIT = 'd381dd9c273205c0fd7ac402c75eef98c6fa6c78'
PROFILES = ('historical-fixed', 'current-observed')
MAX_MODS = 64
MAX_FIELDS = 100000


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class _Audit:
    def __init__(self, raw: bytes, start: int):
        if not isinstance(raw, bytes) or not 16 <= len(raw) <= MAX_MEMBER_BYTES:
            raise LayerError('A bounded member is required')
        if type(start) is not int or start % 8 or not 0 <= start < len(raw) * 8:
            raise LayerError('An aligned metadata start inside the member is required')
        self.raw, self.reader, self.writer = raw, _Reader(raw), _Writer()
        self.reader.position = start
        self.writer.blob(raw[:start // 8])
        self.field_count = 0

    @property
    def position(self):
        return self.reader.position

    def bits(self, width):
        self.field_count += 1
        if self.field_count > MAX_FIELDS:
            raise LayerError('Metadata field budget exceeded')
        value = self.reader.bits(width)
        self.writer.bits(value, width)
        return value

    def opaque(self, width):
        packer = _Writer()
        nonzero = 0
        for offset in range(0, width, 32):
            count = min(width - offset, 32)
            value = self.bits(count)
            packer.bits(value, count)
            nonzero += value.bit_count()
        return dict(bits=width, packed_sha256=sha256(bytes(packer.raw)), set_bits=nonzero)

    def blob(self, size, allowed_magic=None):
        self.field_count += 1
        if self.field_count > MAX_FIELDS:
            raise LayerError('Metadata field budget exceeded')
        value = self.reader.blob(size)
        self.writer.blob(value)
        if allowed_magic is not None and value[:4] not in allowed_magic:
            raise LayerError('Cache handle magic is invalid for this profile')

    def optional(self, width):
        if self.bits(1): self.opaque(width)

    def toon(self, string=False):
        self.bits(8); self.bits(32); self.bits(32)
        if string: self.blob(self.bits(7) + 2)
        else: self.bits(64)

    def finish(self):
        if self.position % 8:
            raise LayerError('Metadata end is not aligned')
        self.writer.blob(self.raw[self.position // 8:])
        if bytes(self.writer.raw) != self.raw:
            raise LayerError('Same-profile full-member reconstruction differs')


def audit_metadata(raw: bytes, start_bit: int, profile: str) -> dict:
    if profile not in PROFILES:
        raise LayerError('An explicit supported metadata profile is required')
    legacy = profile == 'historical-fixed'
    audit = _Audit(raw, start_bit)
    read, opaque = audit.bits, audit.opaque
    header128 = opaque(128)
    extra = read(3) if legacy else None
    count = read(6 if legacy else 5)
    if not 1 <= count <= MAX_MODS:
        raise LayerError('Unsupported used-mod count')
    used_mods = [(read(32), read(32), read(4)) for _ in range(count)]
    if len({x[:2] for x in used_mods}) != len(used_mods):
        raise LayerError('Duplicate used-mod identity')
    count = read(6 if legacy else 7)
    if not 1 <= count <= MAX_MODS:
        raise LayerError('Unsupported mod-metadata count')
    entries, identities, dependency_pairs = [], [], []
    for index in range(count):
        entry = dict(index=index, start_bit=audit.position)
        identity = (read(32), read(32))
        identities.append(identity)
        for width in (16, 16, 24, 7, 15, 2, 74): opaque(width)
        count = read(6)
        entry['cache_handle_count'] = count
        for _ in range(count): audit.blob(40, (b's2mv',))
        read(1); audit.toon(string=True); audit.toon()
        audit.optional(32); audit.optional(23); read(1); audit.optional(32)
        for width in (3, 30, 3, 16, 8, 8, 34): opaque(width)
        audit.optional(54)
        for width in (1, 5, 5, 5): read(width)
        repeated_identity = (read(32), read(32))
        if identity != repeated_identity:
            raise LayerError('Repeated mod identity does not match')
        read(32); read(1); read(21)
        entry['cafebabe_bit'] = audit.position
        if read(32) != 0xcafebabe:
            raise LayerError('Mod metadata CAFEBABE sentinel is invalid')
        entry['cafebabe_valid'] = True
        opaque(28); opaque(36)
        entry['hero_flag_bit'] = audit.position
        has_hero = bool(read(1))
        entry['has_hero_metadata'] = has_hero
        if has_hero:
            opaque(11)
            if legacy:
                fixed_start = audit.position
                fixed_a93, fixed_b4, fixed_a8x5 = read(4), read(4), read(4)
                payload = opaque(447)  # primary2: 120 + 150 + 29 + 148
                fixed_a23 = read(7)
                entry['historical_fixed_fields'] = dict(start_bit=fixed_start,
                    a93=fixed_a93, b4=fixed_b4, a8x5=fixed_a8x5, a23=fixed_a23,
                    unknown_payload=payload, authoritative_choice_semantics=False,
                    current_mapping_established=False)
            else:
                count = read(4)
                entry['current_a93_record_count'] = count
                for _ in range(count): opaque(93)
                opaque(4)
                tag_bit = audit.position
                tag = read(4)
                if tag > 5:
                    raise LayerError('Unsupported current hero-choice tag')
                entry['current_choice'] = dict(bit=tag_bit, tag=tag, payload_bits=400 if tag == 5 else 0)
                if tag == 5: opaque(400)
                count = read(7)
                entry['current_a23_record_count'] = count
                for _ in range(count): opaque(23)
            opaque(11)
            if read(1): opaque(70)
            read(1)
            count = read(5)
            entry['hero_id_count'] = count
            for _ in range(count): read(32)
            opaque(23)
        count = read(6)
        entry['dependency_count'] = count
        for _ in range(count): dependency_pairs.append((read(32), read(32)))
        entry['final_unknown_filler_bits'] = 8 if legacy else 32
        entry['final_unknown_filler_value'] = read(8 if legacy else 32)
        entry['end_bit'] = audit.position
        entries.append(entry)
    if tuple(identities) != tuple(x[:2] for x in used_mods):
        raise LayerError('Used-mod and metadata identities or ordering differ')
    if any(x[0] not in {i[0] for i in identities} for x in dependency_pairs):
        raise LayerError('Unresolved metadata dependency identity')
    metadata_end = audit.position
    count = read(6)
    if count != len(used_mods):
        raise LayerError('Terminal handle and used-mod counts differ')
    for _ in range(count): audit.blob(40, (b's2mh',))
    end = audit.position
    audit.finish()
    return dict(format='hots-battlelobby-mod-metadata-audit-v1', profile=profile,
        member_bytes=len(raw), member_sha256=sha256(raw), start_bit=start_bit,
        mod_metadata_end_bit=metadata_end, terminal_handles_end_bit=end,
        section_bytes=(end-start_bit)//8, section_sha256=sha256(raw[start_bit//8:end//8]),
        after_section_bytes=len(raw)-end//8, after_section_sha256=sha256(raw[end//8:]),
        header_unknown128=header128, legacy_extra_three_bits=extra,
        used_mod_count=len(used_mods), mod_metadata_count=len(entries), terminal_s2mh_count=count,
        repeated_mod_identities_valid=True, dependency_identifier_components_resolved=True,
        dependency_offset_fields_preserved=True, dependency_offsets_semantically_validated=False,
        dependency_pairs_sha256=sha256(b''.join(value.to_bytes(4, 'big') for pair in dependency_pairs for value in pair)),
        entries=entries, same_profile_full_member_roundtrip_exact=True,
        numeric_and_blob_fields_observed=audit.field_count,
        raw_blob_or_identity_values_emitted=False, conversion_performed=False,
        full_member_semantics_validated=False, current_profile_compatibility_proven=False,
        client_launched=False, playback_or_simulation_validated=False)


def audit_member(raw: bytes, attribute_profile: str, metadata_profile: str) -> dict:
    layer = decode_layer(raw, attribute_profile)
    start = dict(layer.boundaries)['locale_handles_end']
    report = audit_metadata(raw, start, metadata_profile)
    report['attribute_profile'] = attribute_profile
    return report


def source_provenance():
    historical = f'https://github.com/EugenPolyakov/HOTS_battlelobby/blob/{HISTORICAL_COMMIT}/lobby/'
    return dict(historical_version_mapping_url=historical+'version%20list.md',
        historical_source_url=historical+'2.txt', historical_later_comparison_url=historical+'5.txt',
        current_source_url=f'https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/{CURRENT_COMMIT}/Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs',
        schemas_are_community_reverse_engineered=True,
        modern_reference_builds_are_separate_evidence=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', action='append', nargs=4, required=True,
                        metavar=('LABEL', 'ATTRIBUTE_PROFILE', 'METADATA_PROFILE', 'MEMBER'))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.report.exists() or args.report.suffix.lower() != '.json':
        parser.error('Report must be a new .json path')
    if len(args.case) > 8 or len({x[0] for x in args.case}) != len(args.case):
        parser.error('At most eight cases with unique labels are supported')
    results = []
    for label, attribute_profile, metadata_profile, path in args.case:
        member = Path(path)
        if member.resolve() == args.report.resolve():
            parser.error('Input and output paths must differ')
        result = audit_member(_read(member), attribute_profile, metadata_profile)
        result['id'] = label
        results.append(result)
    output = dict(format='hots-battlelobby-mod-metadata-diagnosis-v1',
                  sources=source_provenance(), results=results,
                  no_replay_or_member_written=True,
                  conclusion='Historical fixed hero payloads have no established semantics-preserving current mapping')
    with args.report.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(cases=len(results), all_same_profile_roundtrips_exact=True,
                          no_conversion_performed=True)))


if __name__ == '__main__':
    main()
