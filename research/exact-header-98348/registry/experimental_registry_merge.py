"""Explicit RAM-only hypothesis: unchanged65662 plus nine historical singleton IDs.

No XML multiset equality is claimed. No header encoder or file writer is here.
Only a complete advertised f644 header SHA may authenticate any assembly.
"""
from pathlib import Path
import hashlib
import json

from collection_license_audit import DEFAULT_LIMITS, _load_observation, _read, write_new_report
from depot_s2mh_wire import decode_verified_header
from registry_insertion_control import checked

BASE_SHA='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9'
PRIOR_SHA='29f66c9eca1844826ad55f63eb8fd32a2d6e74ddb7931a8e835fb951f58e184d'
OBSERVATION_SHA='0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9'
EXPECTED_TARGET_SHA='f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0'
MAX_NEW=9
MAX_CANDIDATES=1024


def position_candidates(base_values,current_values,prior_values,*,cap=MAX_CANDIDATES):
    base,current,prior=map(checked,(base_values,current_values,prior_values))
    if type(cap) is not int or not 1<=cap<=MAX_CANDIDATES:
        raise ValueError('Position tuple cap must be within1..1024')
    if not base or len(current)!=len(set(current)) or set(base)-set(current):
        raise ValueError('Expected a nonempty missing-only relationship and unique current keys')
    first={}
    for index,value in enumerate(base):first.setdefault(value,index)
    new=[value for value in current if value not in first]
    if not 1<=len(new)<=MAX_NEW or any(prior.count(value)!=1 for value in new):
        raise ValueError('Every proposed singleton must occur exactly once in authenticated prior data')
    if list(dict.fromkeys(base))!=[value for value in current if value in first]:
        raise ValueError('Existing first-occurrence order differs')
    intervals=[]
    for index,value in enumerate(current):
        if value in first:continue
        previous=next((item for item in reversed(current[:index]) if item in first),None)
        following=next((item for item in current[index+1:] if item in first),None)
        lower=first[previous]+1 if previous is not None else 0
        upper=first[following] if following is not None else len(base)
        intervals.append({'id':value,'current_unique_index':index,'lower_gap':lower,'upper_gap':upper,
                          'prior_raw_index':prior.index(value),
                          'prior_immediate_previous_id':prior[prior.index(value)-1] if prior.index(value)>0 else None,
                          'prior_immediate_next_id':prior[prior.index(value)+1] if prior.index(value)+1<len(prior) else None})
    tuples=[]
    visited=0
    def visit(index,prefix):
        nonlocal visited
        visited+=1
        if visited>MAX_NEW*cap+MAX_NEW+1:
            raise ValueError('Bounded position-search node budget exceeded')
        if index==len(intervals):
            tuples.append(tuple(prefix))
            if len(tuples)>cap:
                raise ValueError('Candidate position space exceeds cap; no truncation')
            return
        item=intervals[index]
        lower=max(item['lower_gap'],prefix[-1] if prefix else 0)
        for gap in range(lower,item['upper_gap']+1):
            visit(index+1,prefix+[gap])
    visit(0,[])
    return {'new_ids_in_current_order':new,'intervals':intervals,'position_tuples':tuples,
            'position_tuple_count':len(tuples),'search_nodes':visited,
            'raw_candidate_count_HYPOTHESIS':len(base)+len(new),
            'XML_multiplicity_control_used_or_passed':False,
            'current_registry_multiplicity_proven':False,'full_header_SHA_only_acceptance':EXPECTED_TARGET_SHA}


def iter_candidate_vectors(base_values,current_values,prior_values,*,cap=MAX_CANDIDATES):
    """Yield (unshifted original-array gap tuple, integer registry tuple) in RAM."""
    base,current=checked(base_values),checked(current_values)
    metadata=position_candidates(base,current,prior_values,cap=cap)
    new=metadata['new_ids_in_current_order']
    for gaps in metadata['position_tuples']:
        insertions={}
        for gap,value in zip(gaps,new):insertions.setdefault(gap,[]).append(value)
        result=[]
        for gap in range(len(base)+1):
            result.extend(insertions.get(gap,()))
            if gap<len(base):result.append(base[gap])
        if (list(dict.fromkeys(result))!=current or [value for value in result if value not in set(new)]!=base
                or any(result.count(value)!=1 for value in new)):
            raise ValueError('RAM-only hypothesis failed its sequence postconditions')
        yield gaps,tuple(result)


def load_actual_inputs():
    cache=Path(r'C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
    def read(sha):
        raw=_read(cache/sha[:2]/sha[2:4]/(sha+'.s2mh'),2*1024*1024)
        return decode_verified_header(raw,sha)[0][24]
    path=Path(r'C:/Users/andrz/git/hots-replay-recovery/observations/collection-identities-2026-10-18.json')
    validated=_load_observation(path,DEFAULT_LIMITS)
    raw=_read(path,DEFAULT_LIMITS.observation_bytes)
    if hashlib.sha256(raw).hexdigest()!=OBSERVATION_SHA or validated['sha256']!=OBSERVATION_SHA:
        raise ValueError('Pinned catalog-only observation differs')
    current=next(case['items'] for case in json.loads(raw)['cases'] if case['encoding']=='big-endian-u64')
    return read(BASE_SHA),current,read(PRIOR_SHA)


if __name__=='__main__':
    base,current,prior=load_actual_inputs()
    metadata=position_candidates(base,current,prior)
    # Check each RAM vector, releasing it before the next; no body is saved.
    checked_count=sum(1 for _ in iter_candidate_vectors(base,current,prior))
    metadata.update(format='hots-EXPERIMENTAL-registry-position-hypothesis-v1',
        source_producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        base_header_sha256=BASE_SHA,prior_header_sha256=PRIOR_SHA,collection_observation_sha256=OBSERVATION_SHA,
        actual_RAM_vector_postconditions_checked=checked_count,
        XML_multiplicity_control_remains_failed=True,
        registry_body_header_or_replay_written=False,authentic_target_header_obtained=False,
        client_launched=False,player_values_read_or_emitted=False,
        limitations=['This is the explicitly authorized unchanged65662+one occurrence per9historically observed IDs hypothesis.',
            'The failed rawXML multiplicity control is not repaired or overridden by this model.',
            'Raw5497 length and duplicate multiplicities are hypotheses; only an exact complete advertised f644SHA may authenticate assembled bytes.',
            'Position tuples are gaps BEFORE the original5488-array element; all indices are unshifted. Gaps may equal len(base).',
            'Two alternatives are retained even if prior neighboring literals favor one. No header or registry body is written.'])
    output=Path(__file__).with_name('EXPERIMENTAL-registry-insertion-position-metadata.json')
    write_new_report(metadata,output)
    print(json.dumps({'position_tuples':metadata['position_tuples'],'new_ids':metadata['new_ids_in_current_order'],
        'count':metadata['position_tuple_count'],'raw_length_HYPOTHESIS':metadata['raw_candidate_count_HYPOTHESIS'],
        'report_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},sort_keys=True))
