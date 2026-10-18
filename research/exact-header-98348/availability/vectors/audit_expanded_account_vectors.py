"""Extend the frozen13-case correlation audit with eight existing local controls.

No acquisition or semantic inference is performed. Raw vector/account/position
data stay in RAM. Explicit read accounting includes guard rehashes and every
MPQ file read, including repeated headers/tables. Runtime imports are excluded.
"""
from __future__ import annotations

from collections import Counter
import json
from math import factorial,prod
from pathlib import Path

import audit_repeated_account_vectors as prior
import audit_availability_representation as previous
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import crosscheck,decode_tail,digest
from collection_license_audit import _read,write_new_report
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

WORK=Path(__file__).resolve().parents[1]
MAX_CASES=21
MAX_DISTINCT=40*1024*1024
MAX_READS=180*1024*1024
MAX_AVAILABILITY=8*1024*1024
ROOT='c3b3c8bc82e3a5a62e550fdde9a40c28'
PRIOR_SHA='66fdf4a017ddaf0a8a2b816572a8bdaae6993e0f041632a7d19e3647cbada6ac'
PRIOR_REPORT_SHA='1b0203fe36da7e42e72d4de6062e0ae8cc8dbd745e6af1119d188b1546a83d75'
OTHER_TABLE_SHA='7e13c5f046c79a9ea0db240fd50c04628173568d0e838e6f89b659a744406219'


class Budget:
    def __init__(self,limit=MAX_READS):
        if type(limit) is not int or not 1<=limit<=MAX_READS:raise ValueError('Invalid explicit-read budget')
        self.limit=limit;self.counts=Counter();self.distinct={};self.availability=0
    def reserve(self,size):
        if type(size) is not int or size<0 or sum(self.counts.values())+size>self.limit:
            raise ValueError('Explicit input read budget exceeded')
    def add(self,kind,size):
        self.reserve(size);self.counts[kind]+=size
    def read(self,path,limit,kind='provenance_metadata'):
        size=path.stat().st_size
        self.reserve(min(size,limit)+1)
        raw=_read(path,limit);self.add(kind,len(raw));return raw
    def register(self,path,size):
        key=str(path.resolve())
        if key not in self.distinct:
            if sum(self.distinct.values())+size>MAX_DISTINCT:raise ValueError('Distinct replay-size budget exceeded')
            self.distinct[key]=size
    def add_availability(self,size):
        if size<0 or self.availability+size>MAX_AVAILABILITY:raise ValueError('Availability-byte budget exceeded')
        self.availability+=size


class CountedFile:
    def __init__(self,stream,budget):self.stream=stream;self.budget=budget
    def read(self,size=-1):
        if type(size) is not int or size<0:raise ValueError('Unbounded MPQ read refused')
        self.budget.reserve(size)
        raw=self.stream.read(size);self.budget.add('MPQ_file_reads',len(raw));return raw
    def seek(self,*args):return self.stream.seek(*args)
    def close(self):return self.stream.close()


class CountedArchive(MPQArchive):
    def __init__(self,path,budget):
        self.file=CountedFile(path.open('rb'),budget)
        try:
            self.header=self.read_header();self.hash_table=self.read_table('hash');self.block_table=self.read_table('block')
        except BaseException:
            self.close();raise


def assess_extended(controls):
    """Use the frozen algorithms; widen only admission to at most21 controls."""
    if not 2<=len(controls)<=MAX_CASES:raise ValueError('Expanded control count exceeds bound')
    # Pairwise admission against the first case reuses every frozen shape,
    # active-presence, per-case uniqueness and common-column-length guard.
    for control in controls[1:]:prior.validate_controls([controls[0],control])
    pairs=prior.private_pairs(controls);matrix=prior.exact_matrix(controls)
    direct=prior.direct_pair_statistics(controls,pairs,matrix);groups=prior.presence_groups(controls)
    active_count=prod(factorial(len(positions)) for signature,positions in groups.items() if any(signature))
    empty_count=prod(factorial(len(positions)) for signature,positions in groups.items() if not any(signature))
    histogram=Counter();identity_found=False;actual_count=0
    for mapping in prior.iter_active_arrangements(groups):
        actual_count+=1;same_equal=different_equal=0
        for first,a,second,b,same in pairs:
            equal=matrix[first,second][mapping[a],mapping[b]]
            if same:same_equal+=equal
            else:different_equal+=equal
        histogram[same_equal,different_equal]+=1
        if mapping==tuple(range(16)):
            identity_found=True
            if (same_equal!=direct['same_account_across_replays']['exact_vector_pairs'] or
                    different_equal!=direct['different_accounts_across_replays']['exact_vector_pairs']):
                raise ValueError('Expanded identity control differs')
    if actual_count!=active_count or not identity_found:raise ValueError('Expanded arrangement enumeration incomplete')
    account_counts=Counter(account for control in controls for account in control.accounts_by_position.values())
    same_pairs=direct['same_account_across_replays']['vector_pairs'];maximum=max(same for same,_ in histogram)
    return {'control_cases':len(controls),'participant_occurrences':sum(len(control.accounts_by_position) for control in controls),
        'distinct_private_accounts':len(account_counts),'private_accounts_observed_in_multiple_cases':sum(count>1 for count in account_counts.values()),
        'participant_column_vector_bytes':sum(len(control.columns[slot]) for control in controls for slot in control.accounts_by_position),
        'registry_rows_per_vector':len(controls[0].columns[0])//2,'cross_replay_pairs_considered':len(pairs),
        'direct_working_set_position_alignment':direct,
        'presence_constraint_aggregate':{'signature_group_sizes':sorted(len(positions) for positions in groups.values()),
            'always_participant_positions':sum(len(positions) for signature,positions in groups.items() if all(signature)),
            'never_participant_positions':sum(len(positions) for signature,positions in groups.items() if not any(signature)),
            'varying_participation_positions':sum(len(positions) for signature,positions in groups.items() if any(signature) and not all(signature)),
            'all_compatible_position_bijections':active_count*empty_count,'never_participant_permutations_not_enumerated':empty_count,
            'distinct_active_arrangements_enumerated':actual_count,'identity_active_arrangement_checked':identity_found},
        'arrangement_consistency_aggregate':{'histogram':[{'same_account_exact_vector_pairs':same,'different_account_exact_vector_pairs':different,'active_arrangement_count':count}
            for (same,different),count in sorted(histogram.items())],
            'same_account_exact_vector_pairs_min':min(same for same,_ in histogram),'same_account_exact_vector_pairs_max':maximum,
            'active_arrangements_attaining_maximum_same_account_exact_pairs':sum(count for (same,_),count in histogram.items() if same==maximum),
            'active_arrangements_with_every_repeated_account_pair_exact':sum(count for (same,_),count in histogram.items() if same==same_pairs) if same_pairs else None,
            'zero_repeated_account_pairs_would_mean_no_consistency_test':same_pairs==0}}


def profile_checked(path,expected_sha,replay_sha,budget):
    raw=budget.read(path,128*1024)
    if digest(raw)!=expected_sha:raise ValueError('Pinned core profile digest differs')
    profile=json.loads(raw)
    if (profile['file_sha256']!=replay_sha or profile['schema_file_sha256']!=previous.SCHEMA_CURRENT
        or profile['observed_payload_roundtrip'] is not True or profile['schema_build']!=96477):
        raise ValueError('Bound core profile proof differs')
    target=profile['target']
    if target['m_version']['m_build']!=98348 or target['m_version']['m_baseBuild']!=98348 or target['m_dataBuildNum']!=98348:
        raise ValueError('Profile target build differs')
    return raw,profile


def load_specs(budget):
    # This bounded helper reads two small pinned manifests. Account its exact
    # metadata bytes even though the already reviewed helper performs the reads.
    cases,sources=previous.cases_and_sources()
    for relative in ('reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json','eu-replay-search-20261018/one-eu-current-reference-binding.json'):
        budget.add('provenance_metadata', (WORK/relative).stat().st_size)
    cohort=json.loads(budget.read(WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json',4*1024*1024))
    specs=[]
    for index,(label,path,sha,modern) in enumerate(cases[2:]):
        if index<12:
            row=cohort['references'][index];profile=WORK/row['profile_file'];profile_sha=row['profile_file_sha256']
        else:
            binding=json.loads(budget.read(WORK/'eu-replay-search-20261018/one-eu-current-reference-binding.json',1024*1024))
            profile=WORK/'eu-replay-search-20261018'/binding['profile_file'];profile_sha=binding['profile_sha256']
        specs.append({'id':label,'path':path,'sha':sha,'profile':profile,'profile_sha':profile_sha,'extra':False})
    table_path=WORK/'replay-search-20261018/crossmap-catalog-observation-eight.json';table_raw=budget.read(table_path,1024*1024)
    if digest(table_raw)!=OTHER_TABLE_SHA:raise ValueError('Pinned eight-control source table differs')
    rows=json.loads(table_raw)['references']
    if len(rows)!=8:raise ValueError('Expected exactly eight prior acquired controls')
    for row in rows:
        if row['build']!=98348 or row['root']!=ROOT or row['schema_sha256']!=previous.SCHEMA_CURRENT or row['core_stream_roundtrips_exact'] is not True:
            raise ValueError('Eight-control proof differs')
        path=(WORK/'replay-search-20261018'/row['replay_file']).resolve()
        if not path.is_relative_to((WORK/'replay-search-20261018').resolve()) or path.suffix!='.StormReplay':raise ValueError('Candidate source path escapes narrow tree')
        specs.append({'id':row['id'],'path':path,'sha':row['replay_sha256'],'bytes':row['replay_bytes'],
            'profile':Path(str(path)+'.profile.v2.json'),'profile_sha':row['profile_sha256'],'extra':True})
    if len(specs)!=21 or len({row['sha'] for row in specs})!=21:raise ValueError('Duplicate or wrong-sized current cohort')
    sources['eight_other_map_catalog_table_sha256']=OTHER_TABLE_SHA
    return specs,cases[:2],sources


def analyze():
    budget=Budget()
    if digest(budget.read(Path(prior.__file__),1024*1024))!=PRIOR_SHA:raise ValueError('Frozen13-case producer differs')
    if digest(budget.read(Path(previous.__file__),1024*1024))!=prior.BASE_HELPER_SHA:raise ValueError('Frozen15-case helper differs')
    prior_path=WORK/'availability-vector-ready/repeated-account-vector-comparison-13-cases-v2.json'
    prior_raw=budget.read(prior_path,1024*1024)
    if digest(prior_raw)!=PRIOR_REPORT_SHA:raise ValueError('Frozen13-case report differs')
    specs,legacy_guards,sources=load_specs(budget)
    failures=[];eligible=[];guards=[]
    for label,path,sha,_ in legacy_guards:
        raw=budget.read(path,previous.REPLAY_LIMIT,'guard_rehash_reads')
        budget.register(path,len(raw))
        if digest(raw)!=sha:raise ValueError('Original/R8 guard differs')
        guards.append((path,sha))
    for spec in specs:
        try:
            raw=budget.read(spec['path'],previous.REPLAY_LIMIT,'guard_rehash_reads');budget.register(spec['path'],len(raw))
            if digest(raw)!=spec['sha'] or ('bytes' in spec and len(raw)!=spec['bytes']):raise ValueError('Pinned replay differs')
            eligible.append(spec);guards.append((spec['path'],spec['sha']))
        except (OSError,ValueError):
            if not spec['extra']:raise
            failures.append({'id':spec['id'],'stage':'existing_local_source_or_digest','raw_error_or_private_values_emitted':False})
    protocol=load_protocol(96477)
    if protocol.recovery_schema_sha256!=previous.SCHEMA_CURRENT:raise ValueError('Canonical identity schema differs')
    controls=[];records=[];registry=None;member_total=0
    for spec in eligible:
        stage='bound_core_profile'
        try:
            profile_raw,profile=profile_checked(spec['profile'],spec['profile_sha'],spec['sha'],budget)
            archive=CountedArchive(spec['path'],budget)
            try:
                stage='actual_header_build_root'
                header=protocol.decode_replay_header(archive.header['user_data_header']['content'])
                if (header['m_version']['m_build']!=98348 or header['m_version']['m_baseBuild']!=98348 or header['m_dataBuildNum']!=98348
                    or header['m_ngdpRootKey']['m_data'].hex()!=ROOT):raise ValueError('Actual header build/root differs')
                stage='full_mod_tail_and_private_crosschecks'
                raw=previous.bounded_member(archive,'replay.server.battlelobby')
                details_raw=previous.bounded_member(archive,'replay.details');init_raw=previous.bounded_member(archive,'replay.initData')
                mods=audit_member(raw,'observed-11','current-observed')
                tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
                details=protocol.decode_replay_details(details_raw);initial=protocol.decode_replay_initdata(init_raw)
                checks=crosscheck(tail,details,initial)
                if (not checks['all_details_participants_match_tail_by_slot'] or not checks['initdata_identity_multiset_equal']
                    or checks['initdata_identity_and_slot_matches']!=checks['players_checked'] or not checks['seed_matches_lobby']
                    or not checks['seed_matches_game_description'] or checks['disabled_hero_list_equal'] is False):raise ValueError('Private crosscheck differs')
                stage='exact_registry_and_participant_columns'
                keys=[token.value for token in tail.tokens if token.path.startswith('/collections/') and token.path.endswith('/value')]
                if len(keys)!=prior.ROW_COUNT or (registry is not None and keys!=registry):raise ValueError('Registry order differs')
                registry=keys
                rows=[token.value for token in tail.tokens if token.path.startswith('/availability/') and token.width is None]
                if len(rows)!=prior.ROW_COUNT:raise ValueError('Availability row count differs')
                columns=prior.column_vectors(rows);accounts={}
                for participant in details['m_playerList']:
                    position=participant['m_workingSetSlotId'];toon=participant['m_toon']
                    if position in accounts:raise ValueError('Duplicate participant position')
                    accounts[position]=(toon['m_region'],toon['m_programId'],toon['m_realm'],toon['m_id'])
                if len(accounts)!=10:raise ValueError('Wrong current participant count')
                control=prior.PrivateControl(accounts,columns)
                prior.validate_controls([controls[0],control] if controls else [control,control])
                budget.add_availability(len(rows)*32);controls.append(control)
                selected=len(raw)+len(details_raw)+len(init_raw);member_total+=selected
                records.append({'id':spec['id'],'replay_sha256':spec['sha'],'profile_sha256':digest(profile_raw),
                    'actual_build_base_data':98348,'actual_root':ROOT,'schema_sha256':previous.SCHEMA_CURRENT,
                    'existing_profile_core_roundtrip_bound_to_replay':True,'fresh_core_stream_decode_performed':False,
                    'fresh_full_mod_tail_roundtrip_and_private_crosschecks_passed':True,'availability_bytes':len(rows)*32,
                    'selected_decoded_member_bytes':selected})
            finally:archive.close()
        except (OSError,ValueError,KeyError,TypeError):
            if not spec['extra']:raise
            failures.append({'id':spec['id'],'stage':stage,'raw_error_or_private_values_emitted':False})
    if len(controls)<13:raise ValueError('Base cohort incomplete')
    reproduced=assess_extended(controls[:13])
    if reproduced!=json.loads(prior_raw)['comparison']:raise ValueError('Expanded algorithm does not reproduce frozen13-case values')
    comparison=assess_extended(controls)
    for path,sha in guards:
        if digest(budget.read(path,previous.REPLAY_LIMIT,'guard_rehash_reads'))!=sha:raise ValueError('Source changed after expanded audit')
    return {'format':'hots-expanded-current-private-vector-audit-v1','source_producer_sha256':digest(Path(__file__).read_bytes()),
        'frozen13_case_producer_sha256':PRIOR_SHA,'frozen13_case_report_sha256':PRIOR_REPORT_SHA,
        'source_manifests':sources,'attempted_existing_current_controls':21,'admitted_current_controls':len(controls),
        'admitted_additional_controls':len(controls)-13,'existing_source_or_decode_failure_count':len(failures),
        'failure_stage_counts':dict(Counter(row['stage'] for row in failures)),'failures':failures,
        'network_acquisition_attempts':0,'network_acquisition_failures':0,
        'controls':records,'comparison':comparison,'frozen13_case_comparison_reproduced_exactly':True,
        'all_admitted_current_ordered5418_registries_exactly_equal':True,
        'bounds':{'current_cases':MAX_CASES,'distinct_replay_input_bytes':MAX_DISTINCT,'explicit_analysis_input_reads':MAX_READS,
            'decoded_availability_bytes':MAX_AVAILABILITY,'active_arrangements':prior.MAX_ACTIVE_ARRANGEMENTS},
        'actual_reads':{'distinct_replay_input_files_including_original_R8_guards':len(budget.distinct),
            'distinct_replay_input_bytes_including_original_R8_guards':sum(budget.distinct.values()),
            'explicit_analysis_input_read_bytes':sum(budget.counts.values()),'read_byte_categories':dict(budget.counts),
            'decoded_availability_bytes':budget.availability,'selected_decoded_member_bytes':member_total,
            'accounting_scope':'All explicit metadata reads, replay guard reads and every inherited MPQ file read, including overlapping header/table reads; runtime executable/import filesystem reads are excluded.'},
        'all_admitted_and_original_R8_source_digests_unchanged':True,
        'private_vectors_hashes_toons_slots_presence_signatures_or_mapping_permutations_emitted':False,
        'ownership_or_unique_semantic_mapping_inferred':False,'availability_values_generated':False,
        'replay_header_or_member_written':False,'client_launched':False,'network_used':False,'repo_modified':False,
        'limitations':[
            'Existing profile digests bind prior full core checks. This run freshly checks build/root, full mod/tail roundtrip, exact registry order and private identity/slot/seed consistency; it does not rerun core event decoding.',
            'Eight already acquired other-map references are the only additional candidates; source/decode rejections are counted without raw errors or private values.',
            'Vector equality and repeated-account consistency are format correlations, not ownership/entitlement semantics or a required-equality rule.',
            'No participant-to-cell mapping, account key, vector digest, raw cells or candidate permutation is emitted or selected.',
            'The historical15-case and frozen13-case reports are preserved. Original/R8 files are guard-hashed only.',
        ]}


if __name__=='__main__':
    report=analyze();output=Path(__file__).with_name('expanded-vector-comparison-up-to21-cases.json')
    write_new_report(report,output)
    print(json.dumps({'admitted':report['admitted_current_controls'],'failures':report['existing_source_or_decode_failure_count'],
        'comparison':report['comparison'],'reads':report['actual_reads'],'report_sha256':digest(output.read_bytes())},sort_keys=True))
