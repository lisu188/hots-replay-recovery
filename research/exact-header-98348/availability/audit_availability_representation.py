"""Read-only availability representation audit; emit counts and booleans only.

Sixteen private cell-position flags are compared with sixteen private lobby
position flags. No per-position flags, cells, masks, account IDs or identities
are returned or serialized. Correlation does not establish ownership semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import json
from math import factorial
from pathlib import Path

from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import crosscheck, decode_tail, digest
from collection_license_audit import _read, write_new_report
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

WORK=Path(__file__).resolve().parents[1]
CASE_LIMIT=15
ROW_LIMIT=65535
REPLAY_LIMIT=5*1024*1024
MEMBER_LIMIT=8*1024*1024
COHORT_SHA='fc6dbc312dac9143bfe450d661f8033a04c2ce4eec51878618e2a517f8faf609'
EU_SHA='413b87f7224b18020b4170542c6db1ee5b970e21936ec975efa5d92260b01464'
ORIGINAL_SHA='e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
R8_SHA='4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
SCHEMA_OLD='879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd'
SCHEMA_CURRENT='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'


@dataclass(frozen=True,repr=False)
class PrivateCase:
    active:tuple[bool,...]=field(repr=False)
    varying:tuple[bool,...]=field(repr=False)
    working:tuple[bool,...]=field(repr=False)
    ordinal:tuple[bool,...]=field(repr=False)
    participants:tuple[bool,...]=field(repr=False)
    alphabet:frozenset[bytes]=field(repr=False)


def _presence(values):
    if not isinstance(values,(set,frozenset)) or any(type(v) is not int or not 0<=v<16 for v in values):
        raise ValueError('Expected a private bounded unique occupied-position set')
    return tuple(index in values for index in range(16))


def position_relation(flags,presence):
    if len(flags)!=16 or len(presence)!=16 or any(type(v) is not bool for v in flags+presence):
        raise ValueError('Expected sixteen private boolean position flags')
    return {
        'positions_checked':16,
        'populated_positions':sum(presence),'unpopulated_positions':16-sum(presence),
        'flagged_populated_positions':sum(flag and present for flag,present in zip(flags,presence)),
        'flagged_unpopulated_positions':sum(flag and not present for flag,present in zip(flags,presence)),
        'unflagged_populated_positions':sum(not flag and present for flag,present in zip(flags,presence)),
        'unflagged_unpopulated_positions':sum(not flag and not present for flag,present in zip(flags,presence)),
        'same_position_flags_equal_population':flags==presence,
        'every_flagged_position_is_populated':all(not flag or present for flag,present in zip(flags,presence)),
    }


def summarize_rows(rows,working,ordinal,participants):
    if not isinstance(rows,(tuple,list)) or not 1<=len(rows)<=ROW_LIMIT or any(type(row) is not bytes or len(row)!=32 for row in rows):
        raise ValueError('Expected bounded nonempty fixed32-byte rows')
    populations={name:_presence(values) for name,values in (('working_set_coordinates',working),('lobby_array_coordinates',ordinal),
        ('details_participant_working_set_coordinates',participants))}
    columns=[{row[index*2:index*2+2] for row in rows} for index in range(16)]
    active=tuple(any(value!=b'\0\0' for value in column) for column in columns)
    varying=tuple(len(column)>1 for column in columns)
    values=set().union(*columns)
    cells=len(rows)*16
    zero_cells=sum(row[index:index+2]==b'\0\0' for row in rows for index in range(0,32,2))
    report={
        'rows':len(rows),'availability_bytes':len(rows)*32,'two_byte_cells':cells,
        'distinct_two_byte_cell_values':len(values),
        'two_observed_values_are_exact_zero_and_all_16_bits_set':values=={b'\0\0',b'\xff\xff'},
        'all_cells_are_zero_or_all_16_bits_set':values<={b'\0\0',b'\xff\xff'},
        'zero_cell_value_present':b'\0\0' in values,
        'nonzero_cell_value_count':len(values-{b'\0\0'}),
        'every_nonzero_cell_value_has_exactly_one_set_bit':bool(values-{b'\0\0'}) and all(int.from_bytes(value,'big').bit_count()==1 for value in values if value!=b'\0\0'),
        'zero_cells':zero_cells,'nonzero_cells':cells-zero_cells,
        'positions_with_any_nonzero_cell':sum(active),'positions_with_more_than_one_cell_value':sum(varying),
        'positions_with_all_cells_zero':sum(column=={b'\0\0'} for column in columns),
        'positions_with_all_cells_all_16_bits_set':sum(column=={b'\xff\xff'} for column in columns),
        'coordinates_have_equal_private_population_flags':populations['working_set_coordinates']==populations['lobby_array_coordinates'],
        'same_position_crosschecks':{name:{'any_nonzero':position_relation(active,presence),
            'varying':position_relation(varying,presence)} for name,presence in populations.items()},
    }
    return report,PrivateCase(active,varying,populations['working_set_coordinates'],populations['lobby_array_coordinates'],
        populations['details_participant_working_set_coordinates'],frozenset(values))


def compatible_bijections(cases,activity,coordinates,*,implication):
    """Exact permanent of private 16x16 compatibility, at most 2**16 DP states."""
    if not 1<=len(cases)<=CASE_LIMIT or activity not in ('active','varying') or coordinates not in ('working','ordinal','participants') or type(implication) is not bool:
        raise ValueError('Invalid bounded permutation query')
    if any(not isinstance(case,PrivateCase) or any(type(values) is not tuple or len(values)!=16 or any(type(value) is not bool for value in values)
        for values in (case.active,case.varying,case.working,case.ordinal,case.participants)) for case in cases):
        raise ValueError('Invalid private position flags')
    masks=[]
    for cell_index in range(16):
        mask=0
        for position in range(16):
            compatible=all((not getattr(case,activity)[cell_index] or getattr(case,coordinates)[position])
                if implication else getattr(case,activity)[cell_index]==getattr(case,coordinates)[position] for case in cases)
            if compatible:mask|=1<<position
        masks.append(mask)
    masks.sort(key=int.bit_count)
    @lru_cache(maxsize=65536)
    def count(used):
        index=used.bit_count()
        if index==16:return 1
        remaining=masks[index]&~used
        total=0
        while remaining:
            candidate=remaining&-remaining
            remaining-=candidate
            total+=count(used|candidate)
        return total
    result=count(0)
    return {'compatible_bijective_permutations':result,'possible_bijective_permutations':factorial(16),
        'compatible_cell_position_pairs':sum(mask.bit_count() for mask in masks),
        'private_compatibility_pairs_checked':16*16*len(cases),
        'identity_permutation_compatible':all(all((not flag or present) if implication else flag==present
            for flag,present in zip(getattr(case,activity),getattr(case,coordinates))) for case in cases)}


def compare_group(cases):
    return {coordinates:{activity:{'equal_population':compatible_bijections(cases,activity,coordinates,implication=False),
                'flagged_implies_populated':compatible_bijections(cases,activity,coordinates,implication=True)}
            for activity in ('active','varying')} for coordinates in ('working','ordinal','participants')}


def cases_and_sources():
    cohort_path=WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json'
    eu_path=WORK/'eu-replay-search-20261018/one-eu-current-reference-binding.json'
    raw=_read(cohort_path,4*1024*1024);eu_raw=_read(eu_path,1024*1024)
    if digest(raw)!=COHORT_SHA or digest(eu_raw)!=EU_SHA:raise ValueError('Pinned source manifests changed')
    refs=json.loads(raw)['references'];eu=json.loads(eu_raw)
    if len(refs)!=12 or eu['data_build']!=98348:raise ValueError('Wrong source cohort')
    cases=[('original41810',WORK/'TEN_GREYMANE_source_41810.StormReplay',ORIGINAL_SHA,False),
        ('published-r8',WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay',R8_SHA,False)]
    for index,ref in enumerate(refs):
        if ref['build']!=98348 or ref['schema_file_sha256']!=SCHEMA_CURRENT or ref['observed_payload_roundtrip'] is not True:
            raise ValueError('US control lacks established provenance')
        path=(WORK/ref['replay_file']).resolve()
        if not path.is_relative_to(WORK.resolve()):raise ValueError('Cohort path escapes task work')
        cases.append((f'current-us-{index+1:02}',path,ref['replay_sha256'],True))
    cases.append(('current-eu-01',WORK/'eu-replay-search-20261018/heroeslounge-27515-g1-20261005.StormReplay',eu['file_sha256'],True))
    if eu['file_sha256']!='a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4' or len(cases)!=15:
        raise ValueError('Unexpected EU control identity')
    return cases,{'cohort_manifest_sha256':digest(raw),'EU_binding_sha256':digest(eu_raw)}


def bounded_member(archive,name):
    entry=archive.get_hash_table_entry(name)
    if entry is None or not 0<=entry.block_table_index<len(archive.block_table):raise ValueError('Missing required MPQ member')
    block=archive.block_table[entry.block_table_index]
    if not 1<=block.size<=MEMBER_LIMIT or not 1<=block.archived_size<=REPLAY_LIMIT:raise ValueError('Member exceeds declared audit bound')
    raw=archive.read_file(name)
    if not isinstance(raw,bytes) or len(raw)!=block.size:raise ValueError('Decoded member size differs')
    return raw


def analyze():
    cases,sources=cases_and_sources()
    reports={};private=[];total_replay_bytes=0;total_member_bytes=0
    for label,path,expected,modern in cases:
        source=_read(path,REPLAY_LIMIT)
        if digest(source)!=expected:raise ValueError('Replay differs from existing provenance')
        total_replay_bytes+=len(source)
        protocol=load_protocol(96477 if modern or label=='published-r8' else 41810)
        expected_schema=SCHEMA_CURRENT if modern or label=='published-r8' else SCHEMA_OLD
        if protocol.recovery_schema_sha256!=expected_schema:raise ValueError('Canonical identity schema differs')
        archive=MPQArchive(path)
        try:
            member=bounded_member(archive,'replay.server.battlelobby')
            details_raw=bounded_member(archive,'replay.details');init_raw=bounded_member(archive,'replay.initData')
            mods=audit_member(member,'observed-11' if modern else 'legacy-10','current-observed' if modern else 'historical-fixed')
            tail=decode_tail(member,mods['terminal_handles_end_bit'],'current-tail' if modern else 'historical-tail')
            details=protocol.decode_replay_details(details_raw);initial=protocol.decode_replay_initdata(init_raw)
            checks=crosscheck(tail,details,initial)
            if (not checks['all_details_participants_match_tail_by_slot'] or not checks['initdata_identity_multiset_equal']
                    or checks['initdata_identity_and_slot_matches']!=checks['players_checked']
                    or not checks['seed_matches_lobby'] or not checks['seed_matches_game_description']
                    or checks['disabled_hero_list_equal'] is False):
                raise ValueError('Private identity/slot/seed crosscheck failed')
            slots=initial['m_syncLobbyState']['m_lobbyState']['m_slots']
            if len(slots)!=16:raise ValueError('Expected exactly sixteen initial lobby positions')
            occupied=[(index,slot['m_workingSetSlotId']) for index,slot in enumerate(slots) if slot.get('m_toonHandle',b'')]
            working={slot for _,slot in occupied};ordinal={index for index,_ in occupied}
            if len(working)!=len(occupied) or working!={player.slot for player in tail.players}:raise ValueError('Occupied working positions differ')
            rows=[token.value for token in tail.tokens if token.path.startswith('/availability/') and token.width is None]
            if len(rows)!=(5418 if modern else 263):raise ValueError('Unexpected availability row count')
            participants={player['m_workingSetSlotId'] for player in details['m_playerList']}
            if len(participants)!=len(details['m_playerList']):raise ValueError('Duplicate details participant position')
            report,private_case=summarize_rows(rows,working,ordinal,participants)
            private.append(private_case)
            member_bytes=len(member)+len(details_raw)+len(init_raw);total_member_bytes+=member_bytes
            reports[label]={'replay_sha256':expected,'replay_bytes':len(source),'battlelobby_member_sha256':digest(member),
                'battlelobby_member_bytes':len(member),'details_member_bytes':len(details_raw),'initdata_member_bytes':len(init_raw),
                'identity_schema_sha256':expected_schema,'complete_tail_EOF_and_same_profile_roundtrip':True,
                'private_details_initdata_identity_slot_seed_crosschecks_passed':True,'representation':report}
        finally:archive.close()
        if digest(_read(path,REPLAY_LIMIT))!=expected:raise ValueError('Replay changed during audit')
    for _,path,expected,_ in cases:
        if digest(_read(path,REPLAY_LIMIT))!=expected:raise ValueError('Replay changed before final receipt')
    return {'format':'hots-availability-private-position-representation-audit-v2',
        'source_producer_sha256':digest(Path(__file__).read_bytes()),'sources':sources,
        'bounds':{'cases':CASE_LIMIT,'rows_per_case':ROW_LIMIT,'replay_file_bytes':REPLAY_LIMIT,
            'declared_decoded_member_bytes':MEMBER_LIMIT,'positions_per_case':16,'bijection_DP_max_states':65536},
        'case_count':len(cases),'total_replay_file_bytes_including_R8_duplicate':total_replay_bytes,
        'total_selected_decoded_member_bytes':total_member_bytes,
        'total_availability_bytes':sum(row['representation']['availability_bytes'] for row in reports.values()),
        'all_cases_exactly_zero_and_all_16_bits_set_cell_alphabet':all(row['representation']['two_observed_values_are_exact_zero_and_all_16_bits_set'] for row in reports.values()),
        'zero_cell_value_present_in_every_case':all(row['representation']['zero_cell_value_present'] for row in reports.values()),
        'every_case_nonzero_cell_alphabet_is_one_one_bit_pattern':all(row['representation']['nonzero_cell_value_count']==1 and row['representation']['every_nonzero_cell_value_has_exactly_one_set_bit'] for row in reports.values()),
        'all_fifteen_cases_have_identical_literal_two_byte_cell_alphabets':all(case.alphabet==private[0].alphabet for case in private),
        'cases':reports,'all16_position_joint_compatibility':{
            'legacy_two_cases':compare_group(private[:2]),'current_thirteen_cases':compare_group(private[2:]),'all_fifteen_cases':compare_group(private)},
        'all_source_replay_digests_unchanged_after_audit':True,
        'cell_values_masks_per_position_flags_slot_IDs_accounts_or_raw_player_values_emitted':False,
        'ownership_semantics_inferred':False,'availability_or_new_license_values_generated':False,
        'raw_header_replay_or_member_written':False,'client_launched':False,
        'optional_selected_loadout_license_anchor_check_performed':False,
        'limitations':[
            'Populated means an initData lobby entry has a nonempty toon handle, privately crosschecked against every tail working-set participant; this includes occupied observers where present.',
            'Working-set coordinates, the sixteen-entry lobby-array order, and details participant working-set positions are checked separately; no equivalence is assumed.',
            'Activity means at least one nonzero cell in a position; varying means more than one observed cell value in that position. Neither label establishes ownership or entitlement semantics.',
            'All sixteen private flags are compared at matching positions and under every compatible bijection, counted by an exact bounded permanent; compatible correlations do not select a semantic permutation.',
            'Original and R8 are two cases of the same source tail, not independent observations.',
            'No loadout anchors, safe defaults, migration rules or missing/new-license availability are derived.',
        ]}


if __name__=='__main__':
    report=analyze();output=Path(__file__).with_name('availability-representation-15-cases-v2.json')
    write_new_report(report,output)
    print(json.dumps({'cases':report['case_count'],'availability_bytes':report['total_availability_bytes'],
        'exact_two_value_alphabet_all_cases':report['all_cases_exactly_zero_and_all_16_bits_set_cell_alphabet'],
        'report_sha256':digest(output.read_bytes())},sort_keys=True))
