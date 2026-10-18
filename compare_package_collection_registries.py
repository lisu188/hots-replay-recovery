"""Bounded static package-registry comparisons; no availability or player values."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re

from collection_license_audit import CollectionError, DEFAULT_LIMITS, _json, _load_observation, _read, write_new_report
from depot_s2mh_wire import decode_verified_header

MAX_HEADERS = 64
MAX_AGGREGATE_BYTES = 16 * 1024 * 1024
MAX_ITEMS = 65535


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ordered_sha(values):
    return sha(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode('utf-8'))


def unique_first(values):
    return list(dict.fromkeys(values))


def registry(root, field):
    if field not in root:
        return None
    values=root[field]
    if not isinstance(values,list) or len(values)>MAX_ITEMS:
        raise CollectionError('Unsupported or oversized package registry array')
    if field==23:
        decoded=[]
        for value in values:
            if not isinstance(value,bytes) or not 1<=len(value)<=256:
                raise CollectionError('Unsupported named package-registry item')
            try:
                name=value.decode('utf-8')
            except UnicodeError as error:
                raise CollectionError('Named package registry is not UTF-8') from error
            # Some historical package registries contain bracketed test names.
            # Compare their exact literals, but never export unmatched strings.
            decoded.append(name)
        return decoded
    if field==24:
        if any(type(value) is not int or not 0<=value<2**64 for value in values):
            raise CollectionError('Numeric package registry must contain unsigned64 values')
        return values
    raise CollectionError('Only package registry fields23/24 are supported')


def comparison(values, target):
    distinct=unique_first(values)
    overlap=set(values)&set(target)
    return {'raw_items':len(values),'distinct_items':len(distinct),
        'raw_ordered_values_sha256':ordered_sha(values),'deduplicated_first_ordered_values_sha256':ordered_sha(distinct),
        'same_set':set(values)==set(target),'deduplicated_first_exact_target_order':distinct==target,
        'package_only_count':len(set(values)-set(target)),'target_only_count':len(set(target)-set(values)),
        'deduplicated_relative_overlap_order_equal':([value for value in distinct if value in overlap]
                                                    ==[value for value in target if value in overlap]),
        'duplicate_item_count':len(values)-len(distinct)}


def load_cases(path):
    validated=_load_observation(path,DEFAULT_LIMITS)
    raw=_read(path,DEFAULT_LIMITS.observation_bytes)
    if sha(raw)!=validated['sha256']:
        raise CollectionError('Catalog-only observation changed during validation')
    observation=_json(raw)
    groups={encoding:[case for case in observation['cases'] if case['encoding']==encoding]
            for encoding in ('utf8-name','big-endian-u64')}
    for encoding,cases in groups.items():
        if not cases or any(case['items']!=cases[0]['items'] for case in cases):
            raise CollectionError('Same-encoding observations do not have identical ordered registries')
    return groups,validated


def analyze(observation_path,handle_manifest_path,original_header_root,cache_scan_path,cache_root):
    groups,validated=load_cases(observation_path)
    old,current=groups['utf8-name'][0]['items'],groups['big-endian-u64'][0]['items']
    manifest_raw,scan_raw=_read(handle_manifest_path,131072),_read(cache_scan_path,131072)
    manifest,scan=_json(manifest_raw),_json(scan_raw)
    original=next(row for row in manifest['results'] if row['id']=='original41810')
    current_manifest=next(row for row in manifest['results'] if row['id']=='current98348')
    old_handles=original['terminal_s2mh_handles']
    wanted_archives=[row['digest'] for row in current_manifest['dependency_prefix_handles']]
    candidates=scan['matching_archive_digest']
    if len(old_handles)!=5 or len(wanted_archives)!=6 or not 1<=len(candidates)<=MAX_HEADERS-5:
        raise CollectionError('Unsupported bounded package set')
    total=0

    def read_header(path,digest):
        nonlocal total
        if not re.fullmatch(r'[0-9a-f]{64}',digest):
            raise CollectionError('Noncanonical content digest')
        raw=_read(path,2*1024*1024)
        total+=len(raw)
        if total>MAX_AGGREGATE_BYTES:
            raise CollectionError('Aggregate package-header bound exceeded')
        root=decode_verified_header(raw,digest)[0]
        identity,archive=root.get(0),root.get(2)
        if (not isinstance(identity,dict) or set(identity)!={0,1}
                or any(type(value) is not int for value in identity.values())
                or not isinstance(archive,bytes) or len(archive)!=40):
            raise CollectionError('Unsupported static package identity')
        row={'header_sha256':digest,'bytes':len(raw),'package_id':identity[0],'package_version':identity[1],
            'archive_type':archive[:4].decode('ascii'),'archive_region':archive[4:8].strip(b'\0 ').decode('ascii'),
            'archive_region_raw_bytes_hex':archive[4:8].hex(),
            'archive_digest':archive[8:].hex(),'field23_present':23 in root,'field24_present':24 in root}
        names,numbers=registry(root,23),registry(root,24)
        row['field23_name_comparison']=comparison(names,old) if names is not None else None
        row['field24_numeric_comparison']=comparison(numbers,current) if numbers is not None else None
        return row,names,numbers

    old_rows,old_lists=[],[]
    for index,handle in enumerate(old_handles):
        digest=handle['digest']
        row,names,numbers=read_header(original_header_root/(digest+'.s2mh'),digest)
        row['source_terminal_handle_index']=index
        row['catalog_name_duplicates']=[{'name':name if name in validated['names'] else None,
                                        'value_sha256':sha(name.encode('utf-8')),
                                        'indexes':[i for i,value in enumerate(names or []) if value==name]}
                                        for name,count in Counter(names or []).items() if count>1]
        old_rows.append(row)
        old_lists.extend(names or [])
    old_aggregate=comparison(old_lists,old)
    old_aggregate['header_registry_fields_concatenated_in_source_terminal_handle_order']=True
    old_aggregate['exact_registry_coverage_proves_player_ownership']=False

    new_rows=[]
    candidate_groups={digest:[] for digest in wanted_archives}
    for source in sorted(candidates,key=lambda row:(row['package_id'],row['package_version'],row['header_sha256'])):
        digest=source['header_sha256']
        row,names,numbers=read_header(cache_root/digest[:2]/digest[2:4]/(digest+'.s2mh'),digest)
        if any(row[key]!=source[key] for key in ('bytes','package_id','package_version','archive_region','archive_digest')):
            raise CollectionError('Cached package differs from prior hash-verified inventory identity')
        if row['archive_digest'] not in candidate_groups:
            raise CollectionError('Unrequested cached archive')
        if numbers is not None:
            row['current_missing_numeric_ids']=sorted(set(current)-set(numbers)) if len(set(current)-set(numbers))<=64 else None
            row['package_only_numeric_ids']=sorted(set(numbers)-set(current)) if len(set(numbers)-set(current))<=64 else None
        new_rows.append(row)
        candidate_groups[row['archive_digest']].append((row,names,numbers))
    combinations=1
    for group in candidate_groups.values():
        if not group:
            raise CollectionError('An expected cached archive group is empty')
        combinations*=len(group)
    if combinations>10000:
        raise CollectionError('Candidate combination bound exceeded')
    exact_sets,exact_orders=0,0
    for combo in itertools.product(*candidate_groups.values()):
        values=[value for _,_,numbers in combo for value in numbers or []]
        distinct=unique_first(values)
        exact_sets+=set(values)==set(current)
        exact_orders+=distinct==current
    return {'format':'hots-static-package-collection-registry-comparison-v1',
        'source_bindings':{'catalog_only_observation_sha256':validated['sha256'],
            'handle_manifest_sha256':sha(manifest_raw),'cache_scan_sha256':sha(scan_raw),
            'source_producer_sha256':sha(Path(__file__).read_bytes())},
        'catalog_observation_cases':validated['cases'],
        'legacy_headers':old_rows,'legacy_aggregate':old_aggregate,
        'legacy_case_order_matches':[{'id':case['id'],'member_sha256':case['member_sha256'],
            'deduplicated_aggregate_exact_order':unique_first(old_lists)==case['items']} for case in groups['utf8-name']],
        'current_cached_headers':new_rows,'candidate_groups':[{'archive_digest':digest,'candidate_count':len(group)}
            for digest,group in candidate_groups.items()],
        'current_candidate_combination_comparison':{'combinations':combinations,'same_numeric_set':exact_sets,
            'deduplicated_first_exact_numeric_order':exact_orders,'dependency_or_region_compatibility_applied':False},
        'header_files_read':len(old_handles)+len(candidates),'header_bytes_read':total,
        'legacy_static_registry_order_binding_established':old_aggregate['deduplicated_first_exact_target_order'],
        'current_authentic_package_registry_binding_established':False,
        'availability_32byte_per_entry_semantics_proven':False,'HyperlinkId_legacy_entitlement_semantics_proven':False,
        'availability_or_player_values_read_or_emitted':False,'raw_headers_exported':False,
        'client_launched':False,'replay_modified':False,'package_selected_for_conversion':False,
        'limitations':['Registry arrays are package-static catalog metadata. Their match does not establish what the separate16-slot32-byte availability records mean.',
            'Legacy root[0][23] byte strings and modern root[0][24] decoded integers remain distinct wire fields.',
            'Cached EU package IDs/versions are not silently equated with current US replay package identities or installed build98348.',
            'All936 cached combinations fail set equality; registry evidence does not select any package or authorize a rewrite.',
            'A complete raw XML License list is not the observed current registry: License1209137 exists in raw currentXML and is absent from the replay registry.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('collection-observation','handle-manifest','original-header-root','cache-scan','cache-root','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error('Output must be new with an existing directory parent')
    report=analyze(args.collection_observation,args.handle_manifest,args.original_header_root,args.cache_scan,args.cache_root)
    write_new_report(report,args.output)
    print(json.dumps({'legacy_exact_order':report['legacy_static_registry_order_binding_established'],
        'current':report['current_candidate_combination_comparison'],'headers':report['header_files_read'],
        'report_sha256':sha(args.output.read_bytes())},sort_keys=True))


if __name__=='__main__':
    main()
