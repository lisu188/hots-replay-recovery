"""Private equality constraints for existing current availability columns.

No vector values/digests, account keys, slot IDs, presence signatures or mapping
permutations are returned. All equality is exact bytes, never a hash surrogate.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from dataclasses import dataclass,field
import itertools
import json
from math import factorial,prod
from pathlib import Path

from audit_availability_representation import cases_and_sources,bounded_member,REPLAY_LIMIT,SCHEMA_CURRENT
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import crosscheck,decode_tail,digest
from collection_license_audit import _read,write_new_report
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

MAX_CASES=13
MAX_ACTIVE_ARRANGEMENTS=4096
ROW_COUNT=5418
BASE_HELPER_SHA='bd8eae93fd8334e6155a691acc3f2785a3d79556828b23f6aaf8c5363b89d65f'


@dataclass(frozen=True,repr=False)
class PrivateControl:
    accounts_by_position:dict=field(repr=False)
    columns:tuple=field(repr=False)


def column_vectors(rows):
    if type(rows) not in (tuple,list) or not 1<=len(rows)<=65535 or any(type(row) is not bytes or len(row)!=32 for row in rows):
        raise ValueError('Expected bounded fixed32-byte availability rows')
    return tuple(b''.join(row[position*2:position*2+2] for row in rows) for position in range(16))


def validate_controls(controls):
    if not 2<=len(controls)<=MAX_CASES:raise ValueError('Expected bounded multiple current controls')
    lengths=set()
    for control in controls:
        if not isinstance(control,PrivateControl) or type(control.accounts_by_position) is not dict or type(control.columns) is not tuple or len(control.columns)!=16:
            raise ValueError('Invalid private control shape')
        if not 1<=len(control.accounts_by_position)<=16 or any(type(slot) is not int or not 0<=slot<16 for slot in control.accounts_by_position):
            raise ValueError('Invalid private participant position')
        identities=list(control.accounts_by_position.values())
        try:unique_count=len(set(identities))
        except TypeError as error:raise ValueError('Private account key is not hashable') from error
        if unique_count!=len(identities):raise ValueError('Same account appears twice in one control')
        if any(type(value) is not bytes or not 2<=len(value)<=2*65535 or len(value)%2 for value in control.columns):
            raise ValueError('Invalid private column size/type')
        if {position for position,column in enumerate(control.columns) if any(column)}!=set(control.accounts_by_position):
            raise ValueError('Private active columns and participant positions differ')
        lengths.update(len(value) for value in control.columns)
    if len(lengths)!=1:raise ValueError('Column registry lengths differ')


def private_pairs(controls):
    pairs=[]
    for first in range(len(controls)):
        for second in range(first+1,len(controls)):
            for first_slot,first_account in controls[first].accounts_by_position.items():
                for second_slot,second_account in controls[second].accounts_by_position.items():
                    pairs.append((first,first_slot,second,second_slot,first_account==second_account))
    return pairs


def exact_matrix(controls):
    """Private exact equality, only participants and only different replay cases."""
    matrix={}
    for first in range(len(controls)):
        for second in range(first+1,len(controls)):
            matrix[first,second]={(a,b):controls[first].columns[a]==controls[second].columns[b]
                for a in controls[first].accounts_by_position for b in controls[second].accounts_by_position}
    return matrix


def mismatch_count(first,second):
    if len(first)!=len(second) or len(first)%2:raise ValueError('Column lengths differ')
    return sum(first[index:index+2]!=second[index:index+2] for index in range(0,len(first),2))


def direct_pair_statistics(controls,pairs,matrix):
    result={}
    for same,label in ((True,'same_account_across_replays'),(False,'different_accounts_across_replays')):
        selected=[pair for pair in pairs if pair[4] is same]
        equal=0;differences=[]
        for first,a,second,b,_ in selected:
            is_equal=matrix[first,second][a,b]
            equal+=is_equal
            if not is_equal:differences.append(mismatch_count(controls[first].columns[a],controls[second].columns[b]))
        result[label]={'vector_pairs':len(selected),'exact_vector_pairs':equal,'different_vector_pairs':len(selected)-equal,
            'differing_pairs_mismatched_registry_rows_min':min(differences) if differences else None,
            'differing_pairs_mismatched_registry_rows_max':max(differences) if differences else None,
            'differing_pairs_total_mismatched_registry_rows':sum(differences)}
    return result


def presence_groups(controls):
    groups=defaultdict(list)
    for position in range(16):
        signature=tuple(position in control.accounts_by_position for control in controls)
        groups[signature].append(position)
    return groups


def iter_active_arrangements(groups,*,cap=MAX_ACTIVE_ARRANGEMENTS):
    if type(cap) is not int or not 1<=cap<=MAX_ACTIVE_ARRANGEMENTS:raise ValueError('Invalid arrangement cap')
    active=[positions for signature,positions in groups.items() if any(signature)]
    count=prod(factorial(len(positions)) for positions in active)
    if count>cap:raise ValueError('All active arrangements exceed cap; no truncation')
    # Never-participant groups remain identity: they cannot change any selected
    # participant column, and are counted separately rather than enumerated.
    for choices in itertools.product(*(itertools.permutations(positions) for positions in active)):
        inverse=list(range(16))
        for positions,choice in zip(active,choices):
            for working_position,cell_position in zip(positions,choice):inverse[working_position]=cell_position
        yield tuple(inverse)


def assess(controls):
    validate_controls(controls)
    pairs=private_pairs(controls);matrix=exact_matrix(controls)
    direct=direct_pair_statistics(controls,pairs,matrix)
    groups=presence_groups(controls)
    active_count=prod(factorial(len(positions)) for signature,positions in groups.items() if any(signature))
    empty_count=prod(factorial(len(positions)) for signature,positions in groups.items() if not any(signature))
    histogram=Counter();identity_found=False;actual_count=0
    for mapping in iter_active_arrangements(groups):
        actual_count+=1
        same_equal=different_equal=0
        for first,a,second,b,same in pairs:
            equal=matrix[first,second][mapping[a],mapping[b]]
            if same:same_equal+=equal
            else:different_equal+=equal
        histogram[same_equal,different_equal]+=1
        if mapping==tuple(range(16)):
            identity_found=True
            if (same_equal!=direct['same_account_across_replays']['exact_vector_pairs'] or
                    different_equal!=direct['different_accounts_across_replays']['exact_vector_pairs']):
                raise ValueError('Identity arrangement control differs')
    if actual_count!=active_count or not identity_found:raise ValueError('Incomplete arrangement enumeration')
    account_counts=Counter(account for control in controls for account in control.accounts_by_position.values())
    same_pairs=direct['same_account_across_replays']['vector_pairs']
    maximum=max(same for same,_ in histogram)
    minimum=min(same for same,_ in histogram)
    return {
        'control_cases':len(controls),'participant_occurrences':sum(len(control.accounts_by_position) for control in controls),
        'distinct_private_accounts':len(account_counts),'private_accounts_observed_in_multiple_cases':sum(count>1 for count in account_counts.values()),
        'participant_column_vector_bytes':sum(len(control.columns[slot]) for control in controls for slot in control.accounts_by_position),
        'registry_rows_per_vector':len(controls[0].columns[0])//2,
        'cross_replay_pairs_considered':len(pairs),'direct_working_set_position_alignment':direct,
        'presence_constraint_aggregate':{
            'signature_group_sizes':sorted(len(positions) for positions in groups.values()),
            'always_participant_positions':sum(len(positions) for signature,positions in groups.items() if all(signature)),
            'never_participant_positions':sum(len(positions) for signature,positions in groups.items() if not any(signature)),
            'varying_participation_positions':sum(len(positions) for signature,positions in groups.items() if any(signature) and not all(signature)),
            'all_compatible_position_bijections':active_count*empty_count,
            'never_participant_permutations_not_enumerated':empty_count,
            'distinct_active_arrangements_enumerated':actual_count,
            'identity_active_arrangement_checked':identity_found,
        },
        'arrangement_consistency_aggregate':{
            'histogram':[{'same_account_exact_vector_pairs':same,'different_account_exact_vector_pairs':different,'active_arrangement_count':count}
                for (same,different),count in sorted(histogram.items())],
            'same_account_exact_vector_pairs_min':minimum,'same_account_exact_vector_pairs_max':maximum,
            'active_arrangements_attaining_maximum_same_account_exact_pairs':sum(count for (same,_),count in histogram.items() if same==maximum),
            'active_arrangements_with_every_repeated_account_pair_exact':sum(count for (same,_),count in histogram.items() if same==same_pairs) if same_pairs else None,
            'zero_repeated_account_pairs_would_mean_no_consistency_test':same_pairs==0,
        },
    }


def analyze():
    helper=Path(__import__('audit_availability_representation').__file__)
    if digest(_read(helper,1024*1024))!=BASE_HELPER_SHA:raise ValueError('Pinned previous audit helper differs')
    cases,sources=cases_and_sources()
    originals={label:digest(_read(path,REPLAY_LIMIT)) for label,path,_,_ in cases}
    if any(originals[label]!=expected for label,_,expected,_ in cases):raise ValueError('Input replay differs before audit')
    protocol=load_protocol(96477)
    if protocol.recovery_schema_sha256!=SCHEMA_CURRENT:raise ValueError('Canonical protocol differs')
    controls=[];provenance=[];registry=None;replay_bytes=member_bytes=availability_bytes=0
    for label,path,expected,modern in cases[2:]:
        if not modern:raise ValueError('Legacy control in current-only comparison')
        archive=MPQArchive(path)
        try:
            raw=bounded_member(archive,'replay.server.battlelobby')
            details_raw=bounded_member(archive,'replay.details');init_raw=bounded_member(archive,'replay.initData')
            mods=audit_member(raw,'observed-11','current-observed')
            tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
            details=protocol.decode_replay_details(details_raw);initial=protocol.decode_replay_initdata(init_raw)
            checks=crosscheck(tail,details,initial)
            if (not checks['all_details_participants_match_tail_by_slot'] or not checks['initdata_identity_multiset_equal']
                    or checks['initdata_identity_and_slot_matches']!=checks['players_checked']
                    or not checks['seed_matches_lobby'] or not checks['seed_matches_game_description']
                    or checks['disabled_hero_list_equal'] is False):raise ValueError('Private identity/position/seed control failed')
            current=[token.value for token in tail.tokens if token.path.startswith('/collections/') and token.path.endswith('/value')]
            if len(current)!=ROW_COUNT or (registry is not None and current!=registry):raise ValueError('Current registry order differs')
            registry=current
            rows=[token.value for token in tail.tokens if token.path.startswith('/availability/') and token.width is None]
            if len(rows)!=ROW_COUNT:raise ValueError('Current availability count differs')
            columns=column_vectors(rows)
            accounts={}
            for participant in details['m_playerList']:
                position=participant['m_workingSetSlotId'];toon=participant['m_toon']
                account=(toon['m_region'],toon['m_programId'],toon['m_realm'],toon['m_id'])
                if position in accounts:raise ValueError('Duplicate details working position')
                accounts[position]=account
            if len(accounts)!=10:raise ValueError('Expected ten details participants')
            active={index for index,column in enumerate(columns) if any(column)}
            if active!=set(accounts):raise ValueError('Presence constraint does not hold in this control')
            controls.append(PrivateControl(accounts,columns))
            size=len(_read(path,REPLAY_LIMIT));replay_bytes+=size
            selected=len(raw)+len(details_raw)+len(init_raw);member_bytes+=selected;availability_bytes+=len(rows)*32
            provenance.append({'id':label,'replay_sha256':expected,'replay_bytes':size,'battlelobby_member_sha256':digest(raw),
                'selected_decoded_member_bytes':selected,'availability_bytes':len(rows)*32,
                'full_tail_roundtrip_and_private_identity_position_seed_crosschecks_passed':True})
        finally:archive.close()
    report=assess(controls)
    for label,path,expected,_ in cases:
        if digest(_read(path,REPLAY_LIMIT))!=expected:raise ValueError('Replay changed during audit')
    return {'format':'hots-current-private-repeated-account-vector-audit-v1','source_producer_sha256':digest(Path(__file__).read_bytes()),
        'previous_audit_helper_sha256':BASE_HELPER_SHA,'source_manifests':sources,'identity_schema_sha256':SCHEMA_CURRENT,
        'controls':provenance,'current_replay_bytes':replay_bytes,'selected_decoded_member_bytes':member_bytes,
        'current_availability_bytes':availability_bytes,'comparison':report,
        'bounds':{'current_controls':MAX_CASES,'registry_rows':ROW_COUNT,'positions':16,'active_arrangements':MAX_ACTIVE_ARRANGEMENTS,
            'cross_replay_pairs_max':MAX_CASES*(MAX_CASES-1)//2*16*16,'replay_file_bytes':REPLAY_LIMIT},
        'all_fifteen_source_replay_digests_unchanged_including_original_R8':True,
        'all_thirteen_current_ordered_registries_exactly_equal':True,
        'vector_values_digests_account_keys_positions_or_mapping_permutations_emitted':False,
        'ownership_semantics_or_unique_semantic_mapping_inferred':False,
        'new_or_missing_license_availability_filled':False,'replay_header_or_member_written':False,
        'client_launched':False,'network_used':False,
        'limitations':[
            'Account equality uses the exact decoded details toon tuple privately after tail/initData identity and working-position crosschecks; no names or account keys are emitted.',
            'Only ten details participants per current replay are included; occupied entries absent from details are excluded.',
            'Each vector contains one exact two-byte cell per item in the same observed5418 registry order. Equality is byte-exact; no vector digests are used.',
            'Every presence-compatible active arrangement is assessed; permutations confined to positions never participating are counted but do not alter any compared vector.',
            'Repeated-account vector consistency and different-account differences are correlations only. Changing assets or other time-dependent state can change a vector; no required-equality semantics or ownership is established.',
            'No mapping is selected or emitted, even if one arrangement has a stronger observed correlation.',
        ]}


if __name__=='__main__':
    report=analyze();output=Path(__file__).with_name('repeated-account-vector-comparison-13-cases-v2.json')
    write_new_report(report,output)
    print(json.dumps({'cases':len(report['controls']),'comparison':report['comparison'],
        'report_sha256':digest(output.read_bytes())},sort_keys=True))
