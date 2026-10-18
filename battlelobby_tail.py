"""Bounded read-only battlelobby suffix codec; private values stay in memory.

The explicit profiles describe observed historical/current layouts. Unknown
fields remain opaque, and no cross-profile conversion or replay writing exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from battlelobby_attribute_layer import MAX_MEMBER_BYTES, LayerError, _Reader, _Writer

PROFILES = ('historical-tail', 'current-tail')
MAX_TOKENS = 500000
MAX_COLLECTIONS = 65535
TOON_HANDLE = re.compile(rb'([0-9]+)-([A-Za-z0-9]{4})-([0-9]+)-([0-9]+)')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, repr=False)
class Token:
    path: str
    width: int | None
    value: int | bytes


@dataclass(frozen=True, repr=False)
class Toon:
    region: int
    program: bytes
    realm: int
    identifier: int


@dataclass(frozen=True, repr=False)
class Player:
    slot: int
    toon: Toon


@dataclass(frozen=True, repr=False)
class Tail:
    profile: str
    prefix: bytes
    tokens: tuple[Token, ...]
    players: tuple[Player, ...]
    random_seed: int
    disabled_heroes: tuple[bytes, ...] | None
    member_sha256: str
    member_bytes: int
    report: dict


def encode_tail(tail: Tail, profile: str | None = None) -> bytes:
    if not isinstance(tail, Tail) or tail.profile not in PROFILES or len(tail.tokens) > MAX_TOKENS:
        raise LayerError('A bounded decoded tail is required')
    if profile is not None and profile != tail.profile:
        raise LayerError('Tail conversion between profiles is not established')
    if len(tail.prefix) > MAX_MEMBER_BYTES:
        raise LayerError('Prefix exceeds member bound')
    writer = _Writer()
    writer.blob(tail.prefix)
    for token in tail.tokens:
        if not isinstance(token, Token):
            raise LayerError('Invalid tail token')
        if token.width is None:
            if not isinstance(token.value, bytes) or len(token.value) > MAX_MEMBER_BYTES:
                raise LayerError('Invalid bounded blob token')
            writer.blob(token.value)
        else:
            writer.bits(token.value, token.width)
        if len(writer.raw) > MAX_MEMBER_BYTES:
            raise LayerError('Encoded member exceeds its bound')
    output = bytes(writer.raw)
    if len(output) != tail.member_bytes or digest(output) != tail.member_sha256:
        raise LayerError('Read-only encoding changed the original member')
    return output


def decode_tail(raw: bytes, start_bit: int, profile: str) -> Tail:
    if profile not in PROFILES:
        raise LayerError('An explicit supported tail profile is required')
    if not isinstance(raw, bytes) or not 16 <= len(raw) <= MAX_MEMBER_BYTES:
        raise LayerError('A bounded member is required')
    if type(start_bit) is not int or start_bit % 8 or not 0 <= start_bit < len(raw)*8:
        raise LayerError('An aligned tail start inside the member is required')
    modern = profile == 'current-tail'
    reader, tokens = _Reader(raw), []
    reader.position = start_bit

    def add(token):
        if len(tokens) >= MAX_TOKENS:
            raise LayerError('Tail token budget exceeded')
        tokens.append(token)

    def scalar(path, width):
        value = reader.bits(width)
        add(Token(path, width, value))
        return value

    def opaque(path, width):
        nonzero = 0
        for offset in range(0, width, 32):
            nonzero += scalar(f'{path}/{offset}', min(32, width-offset)).bit_count()
        return nonzero

    def blob(path, size):
        value = reader.blob(size)
        add(Token(path, None, value))
        return value

    def bounded(path, width, limit):
        count = scalar(path, width)
        if count > limit:
            raise LayerError('Tail count exceeds its supported bound')
        return count

    def string_toon(path):
        scalar(path+'/region', 8)
        program = scalar(path+'/program', 32).to_bytes(4, 'big')
        if program != b'Hero':
            raise LayerError('Unexpected string-toon program in observed profile')
        scalar(path+'/realm', 32)
        blob(path+'/value', scalar(path+'/size', 7)+2)

    count = bounded('/collections/count', 16 if modern else 32, MAX_COLLECTIONS)
    sizes = set()
    for index in range(count):
        path = f'/collections/{index}'
        size = 8 if modern else scalar(path+'/size', 8)
        value = blob(path+'/value', size)
        if not modern:
            try:
                value.decode('utf-8')
            except UnicodeDecodeError as error:
                raise LayerError('Historical collection entry is not UTF-8') from error
        sizes.add(size)
    available = bounded('/availability/count', 32, MAX_COLLECTIONS)
    if count != available:
        raise LayerError('Collection and availability counts differ')
    for index in range(available):
        blob(f'/availability/{index}', 32)
    boundaries = {'tail_start': start_bit, 'collections_end': reader.position}
    disabled = None
    if modern:
        disabled = tuple(scalar(f'/disabled_heroes/{i}', 32).to_bytes(4, 'big')
                         for i in range(scalar('/disabled_heroes/count', 8)))
    seed = scalar('/init/random_seed', 32)
    scalar('/init/unknown32', 32)
    players, seen_slots, field_values = [], set(), set()
    unknown_player_set_bits, unknown_player_nonzero = 0, 0
    count_players = bounded('/players/count', 5, 16)
    for index in range(count_players):
        path = f'/players/{index}'
        scalar(path+'/unknown32', 32)
        slot = scalar(path+'/slot', 5)
        if slot >= 16 or slot in seen_slots:
            raise LayerError('Invalid or duplicate working-set player slot')
        seen_slots.add(slot)
        toon = Toon(scalar(path+'/toon/region', 8),
                    scalar(path+'/toon/program', 32).to_bytes(4, 'big'),
                    scalar(path+'/toon/realm', 32), scalar(path+'/toon/id', 64))
        if toon.program != b'Hero':
            raise LayerError('Unexpected numeric-toon program in observed profile')
        players.append(Player(slot, toon))
        string_toon(path+'/string_toon')
        scalar(path+'/name_flag', 1)
        scalar(path+'/unknown2bits', 2)
        if scalar(path+'/secondary/present', 1):
            scalar(path+'/secondary/unknown2', 2)
            string_toon(path+'/secondary/toon')
            scalar(path+'/secondary/flag', 1)
        bits = opaque(path+'/unknown_player_block', 198 if modern else 174)
        unknown_player_set_bits += bits
        unknown_player_nonzero += bool(bits)
        if scalar(path+'/optional64/present', 1): opaque(path+'/optional64/value', 64)
        opaque(path+'/unknown_flags4', 4)
        field_values.add(scalar(path+'/community_named_build32', 32))
        if scalar(path+'/collection_choice', 1) == 0:
            opaque(path+'/collection_bits', scalar(path+'/collection_bit_count', 12))
            scalar(path+'/collection_unknown_bool', 1)
        scalar(path+'/silence_flag', 1)
        if modern:
            scalar(path+'/unknown_bool', 1)
            scalar(path+'/voice_silence_flag', 1)
            scalar(path+'/staff_flag', 1)
        if scalar(path+'/party/present', 1): opaque(path+'/party/value', 64)
        if scalar(path+'/tag/present', 1): blob(path+'/tag/value', scalar(path+'/tag/size', 7))
        if modern:
            scalar(path+'/account_level', 32)
            scalar(path+'/boost_flag', 1)
    boundaries['players_end'] = reader.position
    opaque('/end/unknown64', 64)
    if scalar('/end/mode_toon_choice', 1):
        for label, width in (('region', 8), ('program', 32), ('realm', 32), ('ammid', 32), ('unknown32', 32)):
            scalar('/end/mode_toon/'+label, width)
    else:
        opaque('/end/mode_filler16', 16)
    boundaries['mode_end'] = reader.position
    opaque('/end/unknown87', 87)
    for index in range(scalar('/end/a38_count_minus1', 4)+1): opaque(f'/end/a38/{index}', 38)
    scalar('/end/unknown_bool', 1)
    for index in range(scalar('/end/neut_count_minus1', 4)+1): scalar(f'/end/neut/{index}', 32)
    icon_counts = []
    for index in range(scalar('/end/hero_tables/count', 5)):
        path = f'/end/hero_tables/{index}'
        scalar(path+'/unknown32', 32)
        icons = scalar(path+'/icons/count', 11)
        icon_counts.append(icons)
        for icon in range(icons):
            for label in ('hero_fourcc', 'icon_fourcc', 'unknown32'):
                scalar(f'{path}/icons/{icon}/{label}', 32)
        if modern: opaque(path+'/unknown11', 11)
    cstm = scalar('/end/cstm/count', 6)
    for index in range(cstm): scalar(f'/end/cstm/{index}', 32)
    a48 = scalar('/end/a41_or_a48/count', 5)
    for index in range(a48):
        scalar(f'/end/a41_or_a48/{index}/unknown32', 32)
        scalar(f'/end/a41_or_a48/{index}/value', 16 if modern else 9)
    opaque('/end/unknown23', 23)
    scalar('/end/unknown32a', 32)
    opaque('/end/unknown10', 10)
    scalar('/end/unknown32b', 32)
    allheroes = None
    if modern:
        allheroes = scalar('/end/allheroes/count', 10)
        for index in range(allheroes):
            scalar(f'/end/allheroes/{index}/fourcc', 32)
            opaque(f'/end/allheroes/{index}/unknown5', 5)
            opaque(f'/end/allheroes/{index}/unknown128', 128)
        opaque('/end/unknown2', 2)
    boundaries['payload_end'] = reader.position
    padding = len(raw)*8-reader.position
    if not 0 <= padding < 8:
        raise LayerError('Unexpected trailing bytes or truncated tail')
    if padding and scalar('/end/padding', padding):
        raise LayerError('Nonzero EOF alignment padding')
    report = dict(format='hots-battlelobby-tail-audit-v1', profile=profile,
        member_sha256=digest(raw), member_bytes=len(raw), tail_sha256=digest(raw[start_bit//8:]),
        tail_bytes=len(raw)-start_bit//8, boundaries_bits=boundaries, trailing_padding_bits=padding,
        collection_count=count, collection_entry_sizes=sorted(sizes),
        collection_representation='fixed-eight-byte-opaque-identifiers' if modern else 'variable-UTF8-names',
        availability_count=available, availability_bytes=available*32,
        disabled_hero_count=len(disabled) if disabled is not None else None,
        player_count=len(players), player_unknown_block_bits=198 if modern else 174,
        player_unknown_blocks_nonzero=unknown_player_nonzero,
        player_unknown_blocks_set_bits_total=unknown_player_set_bits,
        community_named_build32_distinct_values=sorted(field_values),
        community_named_build32_verified_client_build=False,
        hero_table_count=len(icon_counts), hero_icon_record_count=sum(icon_counts),
        cstm_count=cstm, a41_or_a48_count=a48, allheroes_count=allheroes,
        tokens=len(tokens), complete_eof_covered=True, same_profile_full_member_roundtrip_exact=True,
        private_names_toons_slots_or_ownership_values_emitted=False,
        unknown_semantics_inferred=False, cross_profile_conversion_supported=False,
        replay_modified=False, client_launched=False, playback_or_simulation_validated=False)
    tail = Tail(profile, raw[:start_bit//8], tuple(tokens), tuple(players), seed, disabled,
                digest(raw), len(raw), report)
    if encode_tail(tail) != raw:
        raise LayerError('Tail same-profile reconstruction differs')
    return tail


def summary(tail: Tail) -> dict:
    # JSON-compatible copy prevents a caller changing the model's own report.
    import copy
    return copy.deepcopy(tail.report)


def crosscheck(tail: Tail, details: dict, initdata: dict) -> dict:
    """Compare identities privately; report counts/booleans without their values."""
    from collections import Counter
    def detail_toon(value):
        program = value['m_programId']
        if not isinstance(program, bytes) or len(program) != 4:
            raise LayerError('Expected decoded details FourCC bytes')
        return Toon(value['m_region'], program,
                    value['m_realm'], value['m_id'])
    detailed = [(p['m_workingSetSlotId'], detail_toon(p['m_toon'])) for p in details['m_playerList']]
    detail_slots = {slot:toon for slot,toon in detailed}
    if len(detail_slots) != len(detailed):
        raise LayerError('Duplicate details working-set slot')
    lobby = initdata['m_syncLobbyState']['m_lobbyState']
    desc = initdata['m_syncLobbyState']['m_gameDescription']
    initial = []
    for slot in lobby['m_slots']:
        raw = slot.get('m_toonHandle', b'')
        if not raw: continue
        match = TOON_HANDLE.fullmatch(raw)
        if not match: raise LayerError('Unexpected initData toon-handle format')
        region, program, realm, identifier = match.groups()
        initial.append((slot['m_workingSetSlotId'], Toon(int(region), program, int(realm), int(identifier))))
    init_slots = {slot:toon for slot,toon in initial}
    if len(init_slots) != len(initial): raise LayerError('Duplicate initData working-set slot')
    selected = Counter(p.toon for p in tail.players)
    detail_matches = sum(detail_slots.get(p.slot) == p.toon for p in tail.players)
    init_matches = sum(init_slots.get(p.slot) == p.toon for p in tail.players)
    disabled_equal = None
    if tail.disabled_heroes is not None:
        disabled_equal = list(tail.disabled_heroes) == desc.get('m_disabledHeroList')
    return dict(format='hots-battlelobby-tail-private-crosscheck-v1', players_checked=len(tail.players),
        details_player_count=len(detailed), details_identity_multiset_equal=selected==Counter(t for _,t in detailed),
        details_identity_and_slot_matches=detail_matches,
        all_details_participants_match_tail_by_slot=detail_matches==len(detailed),
        tail_entries_not_present_in_details=len(tail.players)-detail_matches,
        initdata_occupied_slots=len(initial), initdata_identity_multiset_equal=selected==Counter(t for _,t in initial),
        initdata_identity_and_slot_matches=init_matches,
        seed_matches_lobby=tail.random_seed==lobby['m_randomSeed'],
        seed_matches_game_description=tail.random_seed==desc['m_randomValue'],
        disabled_hero_list_equal=disabled_equal, private_identity_values_emitted=False,
        program_id_normalization='tail32-bit FourCC converted to four big-endian bytes equals decoded details FourCC bytes',
        slot_mismatch_repaired=False)


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    from battlelobby_attribute_layer import _read
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('member',type=Path)
    parser.add_argument('--start-bit',type=int,required=True)
    parser.add_argument('--profile',choices=PROFILES,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.report.exists() or args.report.is_symlink() or args.report.suffix.lower()!='.json':
        parser.error('Output must be a new .json report')
    report=summary(decode_tail(_read(args.member),args.start_bit,args.profile))
    with args.report.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(complete_eof_covered=True,exact_member_roundtrip=True,replay_modified=False)))


if __name__=='__main__':
    main()
