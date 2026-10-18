"""Derive diagnostic source edges; never register aliases or convert ownership."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from collection_license_audit import _read, write_new_report
from plan_collection_candidates import plan


REPO = Path(r'C:/Users/andrz/git/hots-replay-recovery')
REPORT_SHA = 'bfbc51bb4c5270cfc13ba5199821795ae4e9dfea9d2ef114a2ba954c5e274bfc'
LICENSE_SHA = 'c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22'
REWARD_KIND = {'CSkin': 'CRewardSkin', 'CMount': 'CRewardMount'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def measure(repo=REPO):
    report_path = repo/'observations/collection-alias-nodes-current-98348.json'
    license_path = repo/'observations/collection-license-current-98348.json'
    observation_path = repo/'observations/collection-identities-2026-10-18.json'
    report_raw, license_raw, observation_raw = (_read(report_path,1024*1024),
        _read(license_path,16*1024*1024), _read(observation_path,1024*1024))
    if digest(report_raw)!=REPORT_SHA or digest(license_raw)!=LICENSE_SHA:
        raise ValueError('Published source report digest differs')
    report, licenses, observation = map(json.loads,(report_raw,license_raw,observation_raw))
    planned=plan(license_path,observation_path)
    assert report['collection_observation_sha256']==digest(observation_raw)==planned['collection_observation_sha256']
    assert report['complete_absence_scope_established'] is True and report['scanned_xml_files']==5575
    assert report['projection_sha256']==LICENSE_SHA
    current_sets=[set(case['items']) for case in observation['cases'] if case['encoding']=='big-endian-u64']
    assert current_sets and all(items==current_sets[0] for items in current_sets) and len(current_sets[0])==5418
    current=current_sets[0]
    records=licenses['declarations']
    sources={row['path']:row for row in licenses['source_files']}
    exact_index=defaultdict(list)
    global_identity_index=defaultdict(list)
    parent_index=defaultdict(list)
    global_license_index=defaultdict(list)
    for record in records:
        exact_index[(record['source'],record['type'],record['id'])].append(record)
        global_identity_index[(record['type'],record['id'])].append(record)
        if record['parent'] is not None:
            parent_index[(record['type'],record['parent'])].append(record)
        if record['type'].startswith('CReward') and record['id'] and '##' not in record['id'] and record['default'] is None:
            for field_index,field in enumerate(record['fields'].get('License',[])):
                if field['direct_literal_candidate']:
                    global_license_index[field['numeric_value']].append((record,field_index))

    def record_ref(record):
        source=sources[record['source']]
        return {'projection_declaration_index':record['declaration_index'], 'source':record['source'],
            'source_bytes':source['bytes'], 'source_sha256':source['sha256'],
            'xml_child_ordinal':record['xml_child_ordinal'], 'type':record['type'], 'id':record['id'],
            'parent':record['parent'], 'default':record['default'], 'unresolved':record['unresolved']}

    def license_refs(record):
        result=[]
        for index,field in enumerate(record['fields'].get('License',[])):
            if field['direct_literal_candidate']:
                value=field['numeric_value']
                occurrences=global_license_index[value]
                result.append({'License_field_index':index,'value':value,'member_of_observed_5418':value in current,
                    'global_reward_declarations_with_same_direct_License':len({r['declaration_index'] for r,_ in occurrences}),
                    'global_direct_License_field_occurrences':len(occurrences)})
        return result

    def audit_global_identities(references):
        # Global identity ignores source paths. Preserve every declaration and
        # its flags, even when a same-file syntactic join selected only one.
        referenced_indexes={record['projection_declaration_index'] for record in references}
        identities=[]
        for kind,identifier in sorted({(record['type'],record['id']) for record in references}):
            declarations=global_identity_index[(kind,identifier)]
            identities.append({'type':kind,'id':identifier,'global_declaration_count':len(declarations),
                'distinct_source_file_count':len({record['source'] for record in declarations}),
                'all_global_declarations':[dict(record_ref(record),selected_fields=record['fields'],
                    other_attribute_names=record.get('other_attribute_names',[])) for record in declarations],
                'effective_catalog_identity_resolved':False})
        return {'referenced_projection_declarations':len(referenced_indexes),
            'distinct_type_identities':len(identities),
            'global_declaration_count':sum(row['global_declaration_count'] for row in identities),
            'identities_with_multiple_global_declarations':sum(row['global_declaration_count']>1 for row in identities),
            'identities_declared_in_multiple_source_files':sum(row['distinct_source_file_count']>1 for row in identities),
            'all_global_identities':identities}

    def reward_edges(loadout):
        edges=[]
        for field_index,field in enumerate(loadout['fields'].get('RequiredRewardArray',[])):
            if not field['direct_literal_candidate']:
                continue
            reward_id=field['attributes']['value']
            targets=exact_index[(loadout['source'],REWARD_KIND[loadout['type']],reward_id)]
            edges.append({'loadout':record_ref(loadout), 'RequiredRewardArray_field_index':field_index,
                'RequiredRewardArray_literal':reward_id, 'typed_same_file_reward_target_count':len(targets),
                'typed_same_file_reward_targets':[{'record':record_ref(target),'direct_License':license_refs(target)} for target in targets],
                'syntactic_edge_only':True})
        return edges

    def values(edges):
        return [license_ref['value'] for edge in edges for target in edge['typed_same_file_reward_targets']
                for license_ref in target['direct_License']]

    anchors=defaultdict(list)
    for index,match in enumerate(report['matches']):
        if match['role']=='visual-or-audio-asset-reference' and match['owner']['kind'] in REWARD_KIND:
            key=(match['file'],match['owner_node_path'],match['owner']['kind'],match['owner']['id'],match['matched_value'])
            anchors[key].append(index)
    families=[]
    for (source,node_path,kind,identifier,old_name),match_indexes in sorted(anchors.items()):
        owner_records=exact_index[(source,kind,identifier)]
        ordinal=int(node_path.split('/')[-1].rsplit('[',1)[1][:-1])
        physical=[record for record in owner_records if record['xml_child_ordinal']==ordinal]
        assert len(physical)==1
        owner=physical[0]
        direct=reward_edges(owner)
        same_id_rewards=exact_index[(source,REWARD_KIND[kind],identifier)]
        children=parent_index[(kind,identifier)]
        all_edges=[edge for child in children for edge in reward_edges(child)]
        colocated=[edge for edge in all_edges if edge['loadout']['source']==source]
        all_values,local_values=values(all_edges),values(colocated)
        families.append({'legacy_literal':old_name,'owner':record_ref(owner),'owner_node_path':node_path,
            'source_alias_scan_match_indexes':match_indexes,
            'same_exact_owner_record_identity_count_in_file':len(owner_records),
            'same_exact_owner_record_identity_count_all_files':sum(record['type']==kind and record['id']==identifier for record in records),
            'same_owner_direct_reward_edges':direct,
            'same_file_same_id_typed_reward_records':[{'record':record_ref(record),'direct_License':license_refs(record)} for record in same_id_rewards],
            'explicit_parent_literal_children_all_files':[record_ref(child) for child in children],
            'one_hop_parent_family_reward_edges_all_files':all_edges,
            'same_file_one_hop_License_values':local_values,
            'all_file_one_hop_License_values':all_values,
            'distinct_all_file_candidate_Licenses':sorted(set(all_values)),
            'all_candidates_in_observed_5418':all(value in current for value in all_values),
            'repeated_License_edge_values':len(all_values)-len(set(all_values)),
            'legacy_alias_or_ownership_mapping_proven':False})

    hyperlinks=[]
    for index,match in enumerate(report['matches']):
        if match['owner']['kind'] not in REWARD_KIND or not match['node_path'].split('/')[-1].startswith('HyperlinkId['):
            continue
        ordinal=int(match['owner_node_path'].split('/')[-1].rsplit('[',1)[1][:-1])
        owners=[record for record in exact_index[(match['file'],match['owner']['kind'],match['owner']['id'])]
                if record['xml_child_ordinal']==ordinal]
        assert len(owners)==1
        owner=owners[0]
        links=reward_edges(owner)
        if links:
            hyperlinks.append({'legacy_literal':match['matched_value'],'matching_field':'HyperlinkId',
                'source_alias_scan_match_index':index,'node_path':match['node_path'],'owner':record_ref(owner),
                'same_owner_direct_reward_edges':links,'distinct_candidate_Licenses':sorted(set(values(links))),
                'legacy_alias_or_ownership_mapping_proven':False})

    all_values=[value for row in families for value in row['all_file_one_hop_License_values']]
    all_edges=[edge for row in families for edge in row['one_hop_parent_family_reward_edges_all_files']]
    license_rows=[item for edge in all_edges for target in edge['typed_same_file_reward_targets'] for item in target['direct_License']]
    global_audit={
        'visual_parent_children':audit_global_identities([child for row in families for child in row['explicit_parent_literal_children_all_files']]),
        'visual_typed_reward_targets':audit_global_identities([target['record'] for edge in all_edges for target in edge['typed_same_file_reward_targets']]),
        'HyperlinkId_owners':audit_global_identities([row['owner'] for row in hyperlinks]),
        'HyperlinkId_typed_reward_targets':audit_global_identities([target['record'] for row in hyperlinks
            for edge in row['same_owner_direct_reward_edges'] for target in edge['typed_same_file_reward_targets']])}
    output={'format':'hots-diagnostic-visual-family-and-HyperlinkId-reward-edges-v2',
        'source_bindings':{'alias_scan_sha256':REPORT_SHA,'alias_scan_commit':'ccb25a17ed3728b3be71c9a61e23e7804bb7dc6b',
            'license_projection_sha256':LICENSE_SHA,'collection_observation_sha256':digest(observation_raw),
            'scanner_sha256':report['generation_provenance']['scanner_sha256'],
            'workflow_url':report['generation_provenance']['workflow_url'],
            'xml_inventory_sha256':report['scanned_xml_inventory_sha256'],
            'reproduction_helper_sha256':digest(Path(__file__).read_bytes())},
        'preserved_exact_reward_candidate_counts':planned['counts'],
        'counts':{'visual_loadout_match_occurrences':sum(len(rows) for rows in anchors.values()),
            'visual_loadout_owners':len(families),'visual_legacy_names':len({row['legacy_literal'] for row in families}),
            'owner_kinds':dict(Counter(row['owner']['type'] for row in families)),
            'strict_same_owner_direct_reward_edge_count':sum(len(row['same_owner_direct_reward_edges']) for row in families),
            'same_file_same_owner_id_reward_declarations':sum(len(row['same_file_same_id_typed_reward_records']) for row in families),
            'same_file_one_hop_singleton_names':sum(len(set(row['same_file_one_hop_License_values']))==1 for row in families),
            'all_file_parent_child_declarations':sum(len(row['explicit_parent_literal_children_all_files']) for row in families),
            'all_file_License_edge_occurrences':len(all_values),'all_file_distinct_License_values':len(set(all_values)),
            'all_file_singleton_names':sum(len(row['distinct_all_file_candidate_Licenses'])==1 for row in families),
            'all_file_multi_License_names':sum(len(row['distinct_all_file_candidate_Licenses'])>1 for row in families),
            'all_file_no_License_names':sum(not row['distinct_all_file_candidate_Licenses'] for row in families),
            'candidate_set_size_distribution':dict(Counter(len(row['distinct_all_file_candidate_Licenses']) for row in families)),
            'all_candidate_Licenses_in_observed_5418':all(row['member_of_observed_5418'] for row in license_rows),
            'children_with_unresolved_parent_records':sum(bool(child['unresolved']) for row in families for child in row['explicit_parent_literal_children_all_files']),
            'reward_targets_with_unresolved_record_flags':sum(bool(target['record']['unresolved']) for edge in all_edges for target in edge['typed_same_file_reward_targets']),
            'duplicate_visual_owner_identity_anchors':sum(row['same_exact_owner_record_identity_count_all_files']>1 for row in families),
            'file_scoped_duplicate_child_record_identities':len(all_edges)-len({(edge['loadout']['source'],edge['loadout']['type'],edge['loadout']['id']) for edge in all_edges}),
            'global_child_type_identities_with_multiple_declarations':global_audit['visual_parent_children']['identities_with_multiple_global_declarations'],
            'global_typed_reward_target_identities_with_multiple_declarations':global_audit['visual_typed_reward_targets']['identities_with_multiple_global_declarations'],
            'global_HyperlinkId_owner_identities_with_multiple_declarations':global_audit['HyperlinkId_owners']['identities_with_multiple_global_declarations'],
            'global_HyperlinkId_reward_target_identities_with_multiple_declarations':global_audit['HyperlinkId_typed_reward_targets']['identities_with_multiple_global_declarations'],
            'multi_target_typed_same_file_reward_joins':sum(edge['typed_same_file_reward_target_count']>1 for edge in all_edges),
            'duplicate_License_edge_values':len(all_values)-len(set(all_values)),
            'candidate_License_values_with_global_reward_declaration_duplicates':len({row['value'] for row in license_rows if row['global_reward_declarations_with_same_direct_License']>1}),
            'HyperlinkId_same_owner_direct_reward_chains':len(hyperlinks),
            'additional_verified_legacy_mappings':0,'remaining_unresolved_names':207},
        'visual_parent_families':families,'HyperlinkId_candidate_chains':hyperlinks,
        'global_type_id_declaration_audit':global_audit,
        'legacy_aliases_registered':False,'ownership_or_entitlement_mapping_proven':False,'replay_modified':False,
        'contains_player_data':False,'raw_XML_exported':False,
        'limitations':['Visual asset equality restricts a current skin/mount family; it does not establish reward identity or legacy ownership migration.',
            'Parent edges are literal child.parent == matched owner.id comparisons. No inherited field, catalog ordering or override is evaluated.',
            'Same-file singleton counts are reported to expose their false uniqueness: variants in other files give multiple direct current Licenses for every family.',
            'HyperlinkId remains a distinct current field; the report does not promote it to a proven legacy alias.',
            'Only literal RequiredRewardArray fields and typed same-file CRewardSkin/CRewardMount records are joined. Duplicate records/fields remain represented.',
            'Global type/id audits inspect every projected declaration, independent of source file. Even globally unique literal records do not establish effective catalog identity or load order.',
            'The existing56 exact reward-name candidates remain unchanged; all207 previously unresolved names remain unresolved for conversion.']}
    return output


def main():
    result=measure()
    output=Path('work/alias-scan-ready/visual-family-and-hyperlink-candidate-edges-v2.json')
    write_new_report(result,output)
    print(json.dumps({'report_sha256':digest(output.read_bytes()),'counts':result['counts']},sort_keys=True))


if __name__=='__main__':
    main()
