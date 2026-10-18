"""Compare two authenticated cached static arrays without choosing a replacement."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from collection_license_audit import _read, write_new_report
from depot_s2mh_wire import decode_verified_header

OLDER_SHA='29f66c9eca1844826ad55f63eb8fd32a2d6e74ddb7931a8e835fb951f58e184d'
NEWER_SHA='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def analyze():
    cache=Path(r'C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
    def read(digest):
        raw=_read(cache/digest[:2]/digest[2:4]/(digest+'.s2mh'),2*1024*1024)
        root=decode_verified_header(raw,digest)[0]
        values=root[24]
        if not isinstance(values,list) or len(values)>65535 or any(type(x) is not int or not 0<=x<2**64 for x in values):
            raise ValueError('Unexpected bounded integer registry')
        return root[0],values
    older_identity,older=read(OLDER_SHA);newer_identity,newer=read(NEWER_SHA)
    observation_path=Path(r'C:/Users/andrz/git/hots-replay-recovery/observations/collection-identities-2026-10-18.json')
    observation_raw=_read(observation_path,1024*1024)
    if sha(observation_raw)!='0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9':
        raise ValueError('Pinned current catalog-only observation differs')
    current=next(c['items'] for c in json.loads(observation_raw)['cases'] if c['encoding']=='big-endian-u64')
    added,removed=set(newer)-set(older),set(older)-set(newer)
    filtered=[x for x in newer if x not in added]
    index,greedy_deletions=0,[]
    for position,value in enumerate(older):
        if index<len(filtered) and value==filtered[index]:index+=1
        else:greedy_deletions.append({'older_raw_index':position,'value':value})
    missing=set(current)-set(newer)
    return {'format':'hots-authenticated-historical-registry-delta-v1',
        'source_producer_sha256':sha(Path(__file__).read_bytes()),
        'older':{'header_sha256':OLDER_SHA,'package_id':older_identity[0],'package_version':older_identity[1],
                 'raw_count':len(older),'distinct_count':len(set(older))},
        'newer':{'header_sha256':NEWER_SHA,'package_id':newer_identity[0],'package_version':newer_identity[1],
                 'raw_count':len(newer),'distinct_count':len(set(newer))},
        'current_catalog_observation_sha256':sha(observation_raw),'current_registry_count':len(current),
        'newly_added_unique_IDs':sorted(added),'removed_unique_IDs':sorted(removed),
        'newer_only_occurrence_differences':dict(Counter(newer)-Counter(older)),
        'older_only_occurrence_differences':dict(Counter(older)-Counter(newer)),
        'raw_count_delta':len(newer)-len(older),
        'simple_eight_ID_insertion_positive_control_passed':False,
        'remove_all_new_IDs_from_newer_equals_older_raw':filtered==older,
        'remove_all_new_IDs_from_newer_is_exact_older_subsequence':index==len(filtered),
        'one_greedy_subsequence_alignment_deletions':greedy_deletions if index==len(filtered) else None,
        'greedy_alignment_is_unique_or_semantic_removal_mapping':False,
        'older_newer_unique_union_equals_current_registry':set(older)|set(newer)==set(current),
        'all_current_missing9_IDs_were_in_older':missing<=set(older),
        'current_missing9_occurrences_in_older':{value:older.count(value) for value in sorted(missing)},
        'current_missing9_all_exactly_once_in_authenticated_older':all(older.count(value)==1 for value in missing),
        'future_raw5497_count_established':False,'future_registry_or_header_authenticated':False,
        'candidate_vectors_or_header_bytes_emitted':False,'client_launched':False,'replay_modified':False,
        'limitations':['The raw+8 count change comprises20new unique IDs, removal of9old IDs and3duplicate10975occurrences. It is not an eight-insertion positive control.',
            'All9 IDs absent from65662 but present in current replay registry exist once in65661; this is direct historical multiplicity evidence, not a current-header proof.',
            'A greedy exact subsequence alignment is diagnostic and is not claimed unique or to establish catalog removal semantics.',
            'The unchanged-source XML multiplicity control remains failed. No declaration is filtered to force equality.']}


if __name__=='__main__':
    report=analyze();output=Path(__file__).with_name('historical-registry-65661-to-65662-delta.json')
    write_new_report(report,output)
    print(json.dumps({'new_unique':len(report['newly_added_unique_IDs']),'removed_unique':len(report['removed_unique_IDs']),
        'simple_insertion_control':False,'missing9_previously_once':report['current_missing9_all_exactly_once_in_authenticated_older'],
        'report_sha256':sha(output.read_bytes())},sort_keys=True))
