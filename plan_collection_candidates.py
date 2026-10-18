"""Plan exact-name/direct-License candidates from hash-bound static evidence.

No replay, raw XML, player identity or ownership input is accepted. Candidate
declarations do not resolve effective catalog order, inheritance or aliases.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from collection_license_audit import (CollectionError, DEFAULT_LIMITS, SELECTED_FIELDS,
    _comparison, _json, _load_observation, _read, _string, _u64)

VERSION = '2.57.0.98348'
BUILD_CONFIG = 'a64c9b7ebf1c6a811ffefad97865ed80'
LICENSE_SHA256 = 'c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22'
LICENSE_LIMIT = 16 * 1024 * 1024
REPORT_LIMIT = 4 * 1024 * 1024
TOP = {'format', 'version_binding', 'generation_provenance', 'collection_observation',
    'counts', 'source_files', 'declarations', 'direct_comparison', 'limitations',
    'catalog_load_order_resolved', 'catalog_inheritance_resolved',
    'legacy_to_current_mapping_proven', 'client_playback_validated',
    'replay_modified', 'raw_xml_exported'}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise CollectionError('Expected a canonical SHA256')
    return value


def _strings(value):
    if type(value) is not list or len(value) > 64:
        raise CollectionError('Expected a bounded unique reason list')
    for item in value:
        _string(item, DEFAULT_LIMITS)
    if len(value) != len(set(value)): raise CollectionError('Duplicate reason or attribute name')
    return value


def _number(value, maximum):
    _u64(value)
    if value > maximum:
        raise CollectionError('Static projection numeric bound exceeded')
    return value


def _path(value):
    _string(value, DEFAULT_LIMITS)
    if not value.startswith('mods/') or '\\' in value or any(x in ('', '.', '..') for x in value.split('/')):
        raise CollectionError('Expected a relative extracted mods path')
    return value


def _binding(data):
    if type(data) is not dict or set(data) != TOP or data['format'] != 'hots-direct-collection-license-declarations-v1':
        raise CollectionError('Unsupported static license projection schema')
    for flag in ('catalog_load_order_resolved', 'catalog_inheritance_resolved',
                 'legacy_to_current_mapping_proven', 'client_playback_validated', 'replay_modified', 'raw_xml_exported'):
        if data[flag] is not False:
            raise CollectionError('Input claims unsupported semantics or exports')
    value = data['version_binding']
    if type(value) is not dict or set(value) != {'status','expected_version','version_log','matching_hdp_info_files','metadata'}:
        raise CollectionError('Malformed version binding')
    if value['status'] != 'version-log-and-extracted-metadata-match' or value['expected_version'] != VERSION:
        raise CollectionError('Projection is unbound or has the wrong live build')
    log = value['version_log']
    if type(log) is not dict or set(log) != {'bytes','sha256','observed_versions'} or log['observed_versions'] != [VERSION]:
        raise CollectionError('Version log does not bind the expected build')
    _digest(log['sha256']); _number(log['bytes'], DEFAULT_LIMITS.version_log_bytes)
    metadata = value['metadata']
    if type(metadata) is not list or not 1 <= len(metadata) <= 16 or value['matching_hdp_info_files'] != len(metadata) or type(value['matching_hdp_info_files']) is not int:
        raise CollectionError('Extracted version metadata count differs')
    for item in metadata:
        if type(item) is not dict or set(item) != {'path','bytes','sha256','version_field','is_ptr','observed_version_strings'}:
            raise CollectionError('Malformed extracted version metadata')
        if item['version_field'] != 'Version' or item['is_ptr'] is not False or item['observed_version_strings'] != [VERSION]:
            raise CollectionError('Extracted metadata is not the expected live build')
        _path(item['path']); _digest(item['sha256']); _number(item['bytes'], DEFAULT_LIMITS.metadata_bytes)
    generation = data['generation_provenance']
    expected = {'collector_sha256','expected_build_config','extractor_archive_sha256','extractor_release','github_run_id','official_manifest_sha256','repository_commit','workflow_url'}
    if type(generation) is not dict or set(generation) != expected or generation['expected_build_config'] != BUILD_CONFIG:
        raise CollectionError('Collector provenance lacks the expected build configuration')
    for key in ('collector_sha256','extractor_archive_sha256','official_manifest_sha256'):
        _digest(generation[key])
    for key in ('extractor_release','github_run_id','repository_commit','workflow_url'):
        _string(generation[key], DEFAULT_LIMITS)


def _declarations(data):
    rows = data['declarations']
    if type(rows) is not list or not 1 <= len(rows) <= DEFAULT_LIMITS.declarations:
        raise CollectionError('Declaration count bound exceeded')
    selected = 0
    for index, row in enumerate(rows):
        required = {'declaration_index','default','fields','id','parent','source','type','unresolved','xml_child_ordinal'}
        if type(row) is not dict or not required <= set(row) or set(row)-required-{'other_attribute_names'}:
            raise CollectionError('Unexpected declaration schema')
        if type(row['declaration_index']) is not int or row['declaration_index'] != index:
            raise CollectionError('Duplicate or noncanonical declaration index')
        _path(row['source']); _number(row['xml_child_ordinal'], DEFAULT_LIMITS.xml_elements_per_file)
        _string(row['type'], DEFAULT_LIMITS); _strings(row['unresolved'])
        if not (row['type'].startswith('CReward') or row['type'] in {'CHero','CSkin','CMount'}):
            raise CollectionError('Unsupported declaration kind')
        for key in ('id','parent','default'):
            if row[key] is not None: _string(row[key], DEFAULT_LIMITS, empty=True)
        if 'other_attribute_names' in row: _strings(row['other_attribute_names'])
        if type(row['fields']) is not dict or set(row['fields'])-SELECTED_FIELDS:
            raise CollectionError('Unexpected selected field')
        for name, fields in row['fields'].items():
            if type(fields) is not list: raise CollectionError('Expected selected field array')
            selected += len(fields)
            if selected > DEFAULT_LIMITS.selected_fields: raise CollectionError('Selected field bound exceeded')
            for field in fields:
                if type(field) is not dict or not {'attributes','direct_literal_candidate','unresolved'} <= set(field) or set(field)-{'attributes','direct_literal_candidate','unresolved','numeric_value','unsupported_attribute_names'}:
                    raise CollectionError('Unexpected direct declaration field schema')
                reasons = _strings(field['unresolved'])
                if type(field['direct_literal_candidate']) is not bool or field['direct_literal_candidate'] != (not reasons):
                    raise CollectionError('Direct-literal flag disagrees with unresolved reasons')
                attrs = field['attributes']
                if type(attrs) is not dict or set(attrs)-{'value','index','removed'}:
                    raise CollectionError('Unsupported projected field attributes')
                for value in attrs.values(): _string(value, DEFAULT_LIMITS, empty=True)
                if 'unsupported_attribute_names' in field: _strings(field['unsupported_attribute_names'])
                if 'numeric_value' in field:
                    number = _u64(field['numeric_value'])
                    if name not in {'License','ProductId'} or not re.fullmatch('[0-9]+', attrs.get('value','')) or int(attrs['value']) != number:
                        raise CollectionError('Numeric field disagrees with its literal declaration')
                if field['direct_literal_candidate']:
                    if 'value' not in attrs or '##' in attrs['value'] or 'index' in attrs or 'removed' in attrs or field.get('unsupported_attribute_names'):
                        raise CollectionError('Unsupported field cannot be a direct literal')
                    if name in {'License','ProductId'} and 'numeric_value' not in field:
                        raise CollectionError('Numeric literal lacks its bounded value')
    counts = data['counts']
    limits = dict(tree_entries=DEFAULT_LIMITS.tree_entries,source_files=DEFAULT_LIMITS.tree_entries,
        xml_files=DEFAULT_LIMITS.xml_files,source_bytes=DEFAULT_LIMITS.total_source_bytes,
        tracked_declarations=DEFAULT_LIMITS.declarations,selected_fields=DEFAULT_LIMITS.selected_fields)
    if type(counts) is not dict or set(counts) != set(limits): raise CollectionError('Unexpected source count schema')
    for key, limit in limits.items(): _number(counts[key], limit)
    if counts['tracked_declarations'] != len(rows) or counts['selected_fields'] != selected:
        raise CollectionError('Declaration or field counts differ')
    sources = data['source_files']
    if type(sources) is not list or len(sources) != counts['source_files']:
        raise CollectionError('Source-file count differs')
    source_paths = set()
    for source in sources:
        keys = {'path','bytes','sha256','kind'}
        if type(source) is not dict or type(source.get('kind')) is not str or source['kind'] not in {'XML','hdp.info'}:
            raise CollectionError('Malformed source-file descriptor')
        if source['kind'] == 'XML': keys |= {'xml_root','xml_elements','tracked_declarations'}
        if set(source) != keys: raise CollectionError('Unexpected source-file descriptor fields')
        path = _path(source['path']); _digest(source['sha256']); _number(source['bytes'], DEFAULT_LIMITS.xml_file_bytes)
        if source['kind'] == 'XML':
            _string(source['xml_root'], DEFAULT_LIMITS)
            _number(source['xml_elements'], DEFAULT_LIMITS.xml_elements_per_file)
            _number(source['tracked_declarations'], DEFAULT_LIMITS.declarations)
        if path in source_paths: raise CollectionError('Duplicate extracted source path')
        source_paths.add(path)
    if any(row['source'] not in source_paths for row in rows): raise CollectionError('Declaration refers to an unlisted source file')
    if any(item['path'] not in source_paths for item in data['version_binding']['metadata']):
        raise CollectionError('Version metadata source is absent')
    return rows


def plan(licenses: Path, observation_path: Path, *, expected_sha256: str = LICENSE_SHA256) -> dict:
    raw = _read(Path(licenses), LICENSE_LIMIT)
    if _sha(raw) != _digest(expected_sha256): raise CollectionError('Static license projection SHA256 differs')
    data = _json(raw)
    _binding(data)
    rows = _declarations(data)
    observation = _load_observation(Path(observation_path), DEFAULT_LIMITS)
    bound = {key:observation[key] for key in ('bytes','sha256','format','cases')}
    if data['collection_observation'] != bound: raise CollectionError('Catalog-only collection observation binding differs')
    if any(case['count'] != case['distinct_items'] for case in observation['cases']):
        raise CollectionError('Duplicate collection keys are outside candidate-planning scope')
    comparison = _comparison([dict(row, unresolved=list(row['unresolved'])) for row in rows], observation)
    if comparison != data['direct_comparison']: raise CollectionError('Stored direct comparison differs from declarations')
    rewards = defaultdict(list)
    for row in rows:
        if row['type'].startswith('CReward') and row['id']: rewards[row['id']].append(row)
    collisions = {row['numeric_id'] for row in comparison['license_product_namespace_collisions']}
    duplicate_licenses = set(comparison['duplicate_direct_license_declarations'])
    duplicate_records = {index for row in comparison['duplicate_record_identities'] for index in row['declaration_indexes']}
    candidates, shared = [], defaultdict(list)
    for name in sorted(observation['names']):
        records = rewards[name]
        numeric = sorted({item['numeric_value'] for row in records if row['default'] is None
            for item in row['fields'].get('License',[]) if item['direct_literal_candidate'] and 'numeric_value' in item})
        current = sorted(set(numeric) & observation['numbers'])
        reasons = sorted({reason for row in records for reason in row['unresolved']})
        # Reinforce syntactic parent/default blockers independently of stored labels.
        if any(row['parent'] is not None for row in records): reasons = sorted(set(reasons)|{'parent_inheritance_not_resolved'})
        if any(row['default'] is not None for row in records): reasons = sorted(set(reasons)|{'default_declaration_not_resolved'})
        if any(row['declaration_index'] in duplicate_records for row in records):
            reasons = sorted(set(reasons)|{'duplicate_record_identity_catalog_order_not_resolved'})
        status = ('no-exact-reward-record' if not records else 'no-observed-literal-license' if not current else
                  'multiple-observed-literal-licenses' if len(current)>1 else 'single-observed-literal-license')
        item = dict(legacy_name=name,status=status,observed_license_candidates=current,
            direct_license_candidates=numeric,reward_declaration_indexes=[r['declaration_index'] for r in records],
            reward_types=sorted({r['type'] for r in records}),declaration_sources=sorted({r['source'] for r in records}),
            declaration_unresolved_reasons=reasons,one_candidate_without_record_reasons=len(current)==1 and not reasons,
            license_field_unresolved_reasons=sorted({reason for row in records for field in row['fields'].get('License',[]) for reason in field['unresolved']}),
            numeric_product_namespace_collisions=sorted(set(current)&collisions),
            license_values_with_multiple_reward_declarations=[value for value in current if str(value) in duplicate_licenses],
            alias_or_effective_mapping_proven=False)
        if len(current)==1: shared[current[0]].append(name)
        candidates.append(item)
    for item in candidates:
        item['other_legacy_names_sharing_candidate'] = sorted(name for value in item['observed_license_candidates'] for name in shared[value] if name != item['legacy_name'])
    single = [item for item in candidates if len(item['observed_license_candidates'])==1]
    return dict(format='hots-collection-candidate-plan-v1',target_version=VERSION,
        licenses_sha256=_sha(raw),collection_observation_sha256=observation['sha256'],
        counts=dict(legacy_names=len(candidates),current_observed_ids=len(observation['numbers']),
            single_observed_license_candidates=len(single),single_without_record_reasons=sum(x['one_candidate_without_record_reasons'] for x in single),
            single_with_record_reasons=sum(bool(x['declaration_unresolved_reasons']) for x in single),
            unresolved_names=len(candidates)-len(single),
            unresolved_status_counts=dict(Counter(x['status'] for x in candidates if len(x['observed_license_candidates'])!=1))),
        candidates=candidates,contains_player_ownership_or_identity_data=False,
        aliases_registered=False,effective_catalog_mapping_proven=False,whole_collection_conversion_eligible=False,
        replay_modified=False,client_launched=False,
        limitations=['Exact-name literal candidates only; source ordinals are not runtime catalog indexes.',
            'License, ProductId and HyperlinkId remain separate namespaces; collisions do not establish aliases.',
            'Catalog order, inheritance, defaults, templates, availability and entitlement conversion remain unresolved.'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--licenses',type=Path,required=True)
    parser.add_argument('--collection-observation',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink() or args.output.suffix.lower()!='.json': parser.error('Output must be a new .json report')
    result=plan(args.licenses,args.collection_observation)
    raw=(json.dumps(result,indent=2)+'\n').encode('utf-8')
    if len(raw)>REPORT_LIMIT: raise CollectionError('Candidate report bound exceeded')
    with args.output.open('xb') as stream: stream.write(raw)
    print(json.dumps(result['counts'],sort_keys=True))


if __name__=='__main__': main()
