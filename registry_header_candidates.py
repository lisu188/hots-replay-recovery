"""Bounded RAM registry insertion hypotheses for exact-header hash testing.

Every proposed key needs one authenticated historical occurrence. Sequence
invariants and caps do not authenticate target multiplicity; complete target
header SHA256 comparison remains the acceptance rule. No I/O is performed.
"""
MAX_ITEMS=65535
MAX_NEW=9
MAX_CANDIDATES=1024
EXPECTED_TARGET_SHA='f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0'

def checked(values):
    if (not isinstance(values,(list,tuple)) or len(values)>MAX_ITEMS
            or any(type(value) is not int or not 0<=value<2**64 for value in values)):
        raise ValueError('A bounded unsigned64 integer sequence is required')
    return list(values)


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
