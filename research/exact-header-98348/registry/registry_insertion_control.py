"""Gate RAM-only registry insertion enumeration on an exact XML multiset control."""
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path

from collection_license_audit import _load_observation, DEFAULT_LIMITS, _read, write_new_report
from depot_s2mh_wire import decode_verified_header

MAX_ITEMS=65535
MAX_NEW=9
MAX_CANDIDATES=1024
CACHED_SHA='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9'
PROJECTION_SHA='c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22'
OBSERVATION_SHA='0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def checked(values):
    if (not isinstance(values,(list,tuple)) or len(values)>MAX_ITEMS
            or any(type(value) is not int or not 0<=value<2**64 for value in values)):
        raise ValueError('A bounded unsigned64 integer sequence is required')
    return list(values)


def control(package_values,current_values,xml_license_values,excluded_extra):
    package,current,xml=map(checked,(package_values,current_values,xml_license_values))
    extra=set(checked(list(excluded_extra)))
    if len(current)!=len(set(current)) or not package or not current:
        raise ValueError('Expected nonempty package and unique current registry')
    old_unique=list(dict.fromkeys(package))
    missing=set(current)-set(package)
    if not 1<=len(missing)<=MAX_NEW or set(package)-set(current):
        raise ValueError('Unsupported missing-only registry relationship')
    if old_unique!=[value for value in current if value not in missing]:
        raise ValueError('Existing first-occurrence order changed')
    if extra & set(current):
        raise ValueError('Excluded extras cannot be observed current registry IDs')
    filtered=[value for value in xml if value not in missing and value not in extra]
    package_counter,xml_counter=Counter(package),Counter(filtered)
    exact=package_counter==xml_counter
    missing_counts={value:xml.count(value) for value in sorted(missing)}
    return {'raw_package_count':len(package),'distinct_package_count':len(package_counter),
        'raw_XML_License_count':len(xml),'distinct_XML_License_count':len(set(xml)),
        'filtered_XML_License_count':len(filtered),'filtered_XML_distinct_count':len(xml_counter),
        'exact_multiplicity_control_passed':exact,
        'XML_only_occurrence_differences':dict(xml_counter-package_counter),
        'package_only_occurrence_differences':dict(package_counter-xml_counter),
        'missing_current_ID_XML_occurrences':missing_counts,
        'excluded_nonregistry_XML_occurrences':{value:xml.count(value) for value in sorted(extra)},
        'single_occurrence_insertion_prerequisite_passed':exact and all(count==1 for count in missing_counts.values()),
        'existing_unique_order_control_passed':True}


def iter_insertions(package_values,current_values,xml_license_values,excluded_extra,*,cap=MAX_CANDIDATES):
    """Yield integer tuples only after the exact control; never encode a header."""
    if type(cap) is not int or not 1<=cap<=MAX_CANDIDATES:
        raise ValueError('Candidate cap must be within1..1024')
    package,current=checked(package_values),checked(current_values)
    evidence=control(package,current,xml_license_values,excluded_extra)
    if not evidence['single_occurrence_insertion_prerequisite_passed']:
        raise ValueError('Exact multiplicity/single-occurrence prerequisite failed')
    first={}
    for index,value in enumerate(package):first.setdefault(value,index)
    new=[value for value in current if value not in first]
    intervals=[]
    for value in new:
        position=current.index(value)
        previous=next((entry for entry in reversed(current[:position]) if entry in first),None)
        following=next((entry for entry in current[position+1:] if entry in first),None)
        lower=first[previous]+1 if previous is not None else 0
        upper=first[following] if following is not None else len(package)
        intervals.append(range(lower,upper+1))
    # Consecutive new IDs can share a gap; stable order within that gap is part
    # of the observed first-dedup constraint. Count before constructing tuples.
    choices=[]
    for gaps in itertools.product(*intervals):
        if any(left>right for left,right in zip(gaps,gaps[1:])):continue
        choices.append(gaps)
        if len(choices)>cap:raise ValueError('Candidate space exceeds cap; no truncation is permitted')
    for gaps in choices:
        insertions={}
        for gap,value in zip(gaps,new):insertions.setdefault(gap,[]).append(value)
        candidate=[]
        for gap in range(len(package)+1):
            candidate.extend(insertions.get(gap,()))
            if gap<len(package):candidate.append(package[gap])
        if list(dict.fromkeys(candidate))!=current:
            raise ValueError('Insertion enumeration failed its observed-order postcondition')
        yield tuple(candidate)


def analyze():
    repo=Path(r'C:/Users/andrz/git/hots-replay-recovery')
    work=Path(__file__).resolve().parents[1]
    cache=Path(r'C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
    package_raw=_read(cache/CACHED_SHA[:2]/CACHED_SHA[2:4]/(CACHED_SHA+'.s2mh'),2*1024*1024)
    root=decode_verified_header(package_raw,CACHED_SHA)[0]
    package=root[24]
    projection_raw=_read(repo/'observations/collection-license-current-98348.json',16*1024*1024)
    observation_path=repo/'observations/collection-identities-2026-10-18.json'
    validated=_load_observation(observation_path,DEFAULT_LIMITS)
    observation_raw=_read(observation_path,DEFAULT_LIMITS.observation_bytes)
    if sha(projection_raw)!=PROJECTION_SHA or sha(observation_raw)!=OBSERVATION_SHA or validated['sha256']!=OBSERVATION_SHA:
        raise ValueError('Pinned projection or catalog-only observation differs')
    projection,observation=json.loads(projection_raw),json.loads(observation_raw)
    current=next(case['items'] for case in observation['cases'] if case['encoding']=='big-endian-u64')
    sources={row['path']:row for row in projection['source_files']}
    fields=[(record,index,field) for record in projection['declarations'] if record['type'].startswith('CReward')
            for index,field in enumerate(record['fields'].get('License',[])) if field['direct_literal_candidate']]
    all_values=[field['numeric_value'] for _,_,field in fields]
    concrete_values=[field['numeric_value'] for record,_,field in fields
                     if record['id'] and '##' not in record['id'] and record['default'] is None]
    scopes={'all_direct_CReward_License_fields':control(package,current,all_values,{1209137}),
            'concrete_nondefault_direct_CReward_License_fields':control(package,current,concrete_values,{1209137})}
    mismatches=set(scopes['all_direct_CReward_License_fields']['XML_only_occurrence_differences'])
    mismatch_records=[]
    for record,index,field in fields:
        if field['numeric_value'] in mismatches:
            descriptor=sources[record['source']]
            mismatch_records.append({'record':record,'License_field_index':index,
                'source_bytes':descriptor['bytes'],'source_sha256':descriptor['sha256']})
    refused=False
    try:
        next(iter_insertions(package,current,all_values,{1209137}))
    except ValueError:
        refused=True
    if not refused:raise ValueError('Unexpected positive control: review before any enumeration')
    return {'format':'hots-registry-multiplicity-control-and-insertion-refusal-v1',
        'cached_header_sha256':CACHED_SHA,'cached_package_id':root[0][0],'cached_package_version':root[0][1],
        'missing_authentic_header_sha256':'f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0',
        'current_XML_projection_sha256':PROJECTION_SHA,'collection_observation_sha256':OBSERVATION_SHA,
        'source_producer_sha256':sha(Path(__file__).read_bytes()),'scopes':scopes,
        'all_mismatching_XML_declarations_and_flags':mismatch_records,
        'insertion_enumeration_status':'not-attempted-exact-multiplicity-control-failed',
        'candidate_vectors_generated':0,'candidate_space_size_established':None,
        'assumed_raw_current5497_count_established':False,'single_occurrence_assumption_supported':False,
        'iterator_API_available_but_actual_prerequisite_refused':True,'candidate_cap':MAX_CANDIDATES,
        'raw_header_or_replay_written':False,'client_launched':False,'private_player_values_read_or_emitted':False,
        'limitations':['All9 new observedIDs have one direct currentXML License occurrence, but the full unchanged-license multiplicity control fails.',
            'The3 extra XML occurrences across2 existingIDs are retained with every declaration; no arbitrary duplicate, override or unloaded-file filter is applied.',
            'Zero generated vectors means prerequisite refusal, not proof that the hypothetical insertion space is empty.',
            'The iterator returns integer vectors only. It does not encode, patch, sign, save or authenticate package headers.',
            'Any future candidate remains a hypothesis until the full advertised f644 content-addressed SHA matches.']}


if __name__=='__main__':
    result=analyze();output=Path(__file__).with_name('registry-multiplicity-control-negative.json')
    write_new_report(result,output)
    print(json.dumps({'control_passed':result['scopes']['all_direct_CReward_License_fields']['exact_multiplicity_control_passed'],
        'differences':result['scopes']['all_direct_CReward_License_fields']['XML_only_occurrence_differences'],
        'candidate_vectors_generated':0,'report_sha256':sha(output.read_bytes())},sort_keys=True))
