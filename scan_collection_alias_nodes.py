"""Project exact legacy-name XML nodes; never infer aliases or write a replay.

The CLI requires every XML file from the pinned98348 extraction inventory.
scan_subset() is a separate research helper which never claims completeness.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from collection_license_audit import (CollectionError, DEFAULT_LIMITS, VERSION_TOKEN,
    _inventory, _json, _metadata_versions, _output_preflight, _parse_xml, _read,
    _selected_field, _string, write_new_report)
from plan_collection_candidates import LICENSE_LIMIT, LICENSE_SHA256, VERSION, plan


@dataclass(frozen=True)
class EvidencePolicy:
    projection_sha256: str = LICENSE_SHA256
    xml_files: int = 5575
    legacy_names: int = 263
    unresolved_names: int = 207
    current_ids: int = 5418


@dataclass(frozen=True)
class ScanLimits:
    matches: int = 50000
    matches_per_file: int = 10000
    related_fields: int = 50000
    related_fields_per_record: int = 128
    node_path_characters: int = 4096
    unit_declarations: int = 1024
    unit_fields: int = 8192
    unit_fields_per_record: int = 128
    report_bytes: int = 16 * 1024 * 1024


POLICY = EvidencePolicy()
LIMITS = ScanLimits()
RELATED = {'License', 'RequiredRewardArray', 'AttributeId', 'DisplayModel', 'VariationArray'}
ALIAS_WORD = re.compile(r'legacy|alias|migrat|conversion|oldreward|olditem|previous|deprecated|rename', re.I)
UNIT_QUERIES = ('NovaHoloCloneCloaked', 'NovaHoloClone', 'AbathurEvolvedMonstrosity',
                'TownCannonTowerL2Standalone')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _inputs(projection, observation, policy):
    # The reviewed planner validates the exact projection digest, version/build
    # provenance, allowlisted catalog-only observation and recomputed candidates.
    planned = plan(Path(projection), Path(observation), expected_sha256=policy.projection_sha256)
    raw = _read(Path(projection), LICENSE_LIMIT)
    if _sha(raw) != policy.projection_sha256:
        raise CollectionError('Projection changed during validation')
    data = _json(raw)
    counts = planned['counts']
    if (counts['legacy_names'], counts['unresolved_names'], counts['current_observed_ids']) != (
            policy.legacy_names, policy.unresolved_names, policy.current_ids):
        raise CollectionError('Projection collection scope differs from the expected policy')
    unresolved = {row['legacy_name'] for row in planned['candidates']
                  if len(row['observed_license_candidates']) != 1}
    if len(unresolved) != policy.unresolved_names:
        raise CollectionError('Unresolved-name count differs from the expected scope')
    xml, metadata = {}, {}
    for source in data['source_files']:
        target = xml if source['kind'] == 'XML' else metadata
        path = source['path']
        if source['kind'] == 'XML' and Path(path).suffix.lower() != '.xml':
            raise CollectionError('Projected XML has an unsupported filename')
        if source['kind'] == 'hdp.info' and Path(path).name.lower() != 'hdp.info':
            raise CollectionError('Projected metadata has an unsupported filename')
        target[path] = source
    if len(xml) != policy.xml_files or data['counts']['xml_files'] != len(xml):
        raise CollectionError('Projected XML inventory count differs from the expected policy')
    all_paths = list(xml) + list(metadata)
    if len({path.casefold() for path in all_paths}) != len(all_paths):
        raise CollectionError('Case-colliding projected paths are unsupported')
    metadata_rows = {row['path']: row for row in data['version_binding']['metadata']}
    if set(metadata_rows) != set(metadata):
        raise CollectionError('Projected version metadata inventory differs')
    for path, source in metadata.items():
        row = metadata_rows[path]
        if (row['bytes'], row['sha256']) != (source['bytes'], source['sha256']):
            raise CollectionError('Projected metadata descriptor differs from its binding')
    if sum(row['bytes'] for row in data['source_files']) != data['counts']['source_bytes']:
        raise CollectionError('Projected aggregate source bytes differ')
    return data, unresolved, xml, metadata, planned


def _fresh_log(path):
    raw = _read(Path(path), DEFAULT_LIMITS.version_log_bytes)
    try:
        versions = sorted(set(VERSION_TOKEN.findall(raw.decode('utf-8-sig'))))
    except UnicodeError as error:
        raise CollectionError('Live version log must be UTF-8') from error
    if versions != [VERSION]:
        raise CollectionError('Fresh live log does not exclusively identify98348')
    return {'bytes': len(raw), 'sha256': _sha(raw), 'observed_versions': versions}


def _role(owner, tag, attrs, matched_attribute, *, record_identity):
    kind = owner['kind']
    if (kind.startswith(('CModel', 'CActor', 'CLight', 'CSound'))
            or tag in {'DisplayModel', 'Model', 'Models', 'ModelGroups'}
            or (tag == 'ReplacementArray' and attrs.get('Catalog') in {'Model', 'Actor', 'Sound'})):
        return 'visual-or-audio-asset-reference'
    if record_identity and matched_attribute == 'id':
        return 'reward-record-identity' if kind.startswith('CReward') else 'catalog-record-identity'
    if kind.startswith('CReward') and ALIAS_WORD.search(tag):
        return 'named-reward-alias-or-migration-field-unverified'
    if tag == 'RequiredRewardArray':
        return 'direct-reward-reference'
    return 'unclassified-exact-literal-reference'


def _nodes(raw, relative, names, limits, budget):
    """DTD/depth/element gates run before this bounded streaming projection."""
    matches, related_owners, frames, child_counts = [], [], [], []
    owner, owner_locator, owner_matches, related = None, None, [], []
    root_tag, root_owner = None, None
    file_count = 0

    def node_path():
        result = '/'.join(frames)
        if len(result) > limits.node_path_characters:
            raise CollectionError('XML node-path bound exceeded')
        return result

    def add(attribute, value, element, record_identity):
        nonlocal file_count
        file_count += 1
        budget['matches'] += 1
        if file_count > limits.matches_per_file or budget['matches'] > limits.matches:
            raise CollectionError('Exact-match node budget exceeded')
        matches.append({'file': relative, 'owner': dict(owner), 'owner_node_path': owner_locator,
                        'node_path': node_path(), 'attribute_name': attribute, 'matched_value': value,
                        'role': _role(owner, _local(element.tag), element.attrib, attribute,
                                      record_identity=record_identity),
                        'alias_or_entitlement_mapping_proven': False})
        owner_matches.append(len(matches) - 1)

    def finish_owner():
        if owner_matches and related:
            related_owners.append({'file': relative, 'owner': dict(owner), 'owner_node_path': owner_locator,
                                   'matching_node_indexes_within_file': list(owner_matches),
                                   'direct_fields': list(related),
                                   'inheritance_or_cross_record_join_performed': False})

    for event, element in ET.iterparse(io.BytesIO(raw), events=('start', 'end')):
        if event == 'start':
            tag = _local(element.tag)
            _string(element.tag, DEFAULT_LIMITS)
            ordinal = child_counts[-1] if child_counts else 0
            if child_counts:
                child_counts[-1] += 1
            frames.append(element.tag + '[' + str(ordinal) + ']')
            child_counts.append(0)
            depth = len(frames)
            if depth == 1:
                root_tag = tag
            if depth == 1 or (root_tag == 'Catalog' and depth == 2):
                owner = {'kind': tag, 'id': element.attrib.get('id')}
                if owner['id'] is not None:
                    _string(owner['id'], DEFAULT_LIMITS, empty=True)
                owner_locator = node_path()
                owner_matches, related = [], []
                if depth == 1:
                    root_owner = dict(owner)
            record_identity = depth == (2 if root_tag == 'Catalog' else 1)
            for key, value in sorted(element.attrib.items()):
                if value in names:
                    _string(key, DEFAULT_LIMITS)
                    add(key, value, element, record_identity)
        else:
            depth, tag = len(frames), _local(element.tag)
            record_identity = depth == (2 if root_tag == 'Catalog' else 1)
            # Text must match the whole literal value. No whitespace, case or
            # substring normalization is applied to manufacture a match.
            if element.text in names:
                add('#text', element.text, element, record_identity)
            direct_depth = 3 if root_tag == 'Catalog' else 2
            related_owner = owner['kind'] in {'CSkin', 'CMount'} or owner['kind'].startswith('CReward')
            if depth == direct_depth and related_owner and tag in RELATED:
                budget['related'] += 1
                if len(related) >= limits.related_fields_per_record or budget['related'] > limits.related_fields:
                    raise CollectionError('Related-field node budget exceeded')
                related.append({'node_path': node_path(), 'tag': tag,
                                'field': _selected_field(element, DEFAULT_LIMITS)})
            if depth == (2 if root_tag == 'Catalog' else 1):
                finish_owner()
                if root_tag == 'Catalog' and depth == 2:
                    owner, owner_locator, owner_matches, related = dict(root_owner), frames[0], [], []
            # A record's tail belongs to the Catalog parent, so project it only
            # after closing that owner's related-field group. Other child tails
            # remain part of their enclosing record. Neither kind is ignored.
            if element.tail in names:
                add('#tail', element.tail, element, False)
            # Leave only empty child shells so _selected_field can still detect
            # unsupported nested field content. No raw subtree is retained.
            element.clear()
            frames.pop()
            child_counts.pop()
    return matches, related_owners


def _inventory_digest(rows):
    projected = [{'path': path, 'bytes': row['bytes'], 'sha256': row['sha256']}
                 for path, row in sorted(rows.items())]
    return _sha(json.dumps(projected, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def _unit_field(element):
    """Project named direct unit scalar fields; never evaluate catalog aliases."""
    allowed = {'Link', 'value', 'index', 'removed'}
    attributes = {key: _string(value, DEFAULT_LIMITS, empty=True)
                  for key, value in element.attrib.items() if key in allowed}
    unknown = sorted(set(element.attrib) - allowed)
    for key in unknown:
        _string(key, DEFAULT_LIMITS)
    reasons = []
    if unknown:
        reasons.append('unsupported_attributes')
    if list(element) or (element.text or '').strip():
        reasons.append('nested_or_text_field_content_not_interpreted')
    if 'index' in attributes:
        reasons.append('indexed_array_operation_not_resolved')
    if 'removed' in attributes:
        reasons.append('removal_operation_not_resolved')
    if not any(key in attributes for key in ('Link', 'value')):
        reasons.append('missing_Link_or_value')
    if any('##' in value for value in attributes.values()):
        reasons.append('template_not_resolved')
    return {'attributes': attributes, 'unsupported_attribute_names': unknown,
            'unresolved': reasons, 'field_semantics_resolved': False}


def _unit_nodes(raw, relative, descriptor, limits, budget):
    # The same raw bytes have already passed digest, DTD and parser-shape gates.
    # This pass is independent of the 207 legacy collection-name matches.
    result, depth, root_tag, owner, child_ordinal = [], 0, None, None, -1
    for event, element in ET.iterparse(io.BytesIO(raw), events=('start', 'end')):
        tag = _local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 1:
                root_tag = tag
            elif depth == 2:
                child_ordinal += 1
                if root_tag == 'Catalog' and tag == 'CUnit' and element.get('id') in UNIT_QUERIES:
                    budget['unit_declarations'] += 1
                    if budget['unit_declarations'] > limits.unit_declarations:
                        raise CollectionError('Unit declaration budget exceeded')
                    owner = {'file': relative, 'bytes': descriptor['bytes'], 'sha256': descriptor['sha256'],
                             'kind': 'CUnit', 'id': element.get('id'),
                             'parent': element.get('parent'), 'default': element.get('default'),
                             'catalog_child_ordinal': child_ordinal, 'direct_fields': [],
                             'inheritance_or_alias_resolution_performed': False}
                    for value in (owner['parent'], owner['default']):
                        if value is not None:
                            _string(value, DEFAULT_LIMITS, empty=True)
        else:
            if depth == 3 and owner is not None and tag in {'BehaviorArray', 'UnitAlias'}:
                budget['unit_fields'] += 1
                if (len(owner['direct_fields']) >= limits.unit_fields_per_record
                        or budget['unit_fields'] > limits.unit_fields):
                    raise CollectionError('Unit direct-field budget exceeded')
                owner['direct_fields'].append({'tag': tag, 'field': _unit_field(element)})
            if depth == 2:
                if owner is not None:
                    result.append(owner)
                    owner = None
            element.clear()
            depth -= 1
    return result


def _scan(files, data, names, expected_xml, planned, *, complete, log, metadata, limits):
    if len(files) > len(expected_xml):
        raise CollectionError('Scanned XML count exceeds the projected inventory')
    matches, related, units, checked, total, declarations, fields = [], [], [], {}, 0, 0, [0]
    budget = {'matches': 0, 'related': 0, 'unit_declarations': 0, 'unit_fields': 0}
    for relative, path in sorted(files.items()):
        if relative not in expected_xml:
            raise CollectionError('Unprojected XML input is unsupported')
        expected = expected_xml[relative]
        raw = _read(Path(path), DEFAULT_LIMITS.xml_file_bytes)
        total += len(raw)
        if total > DEFAULT_LIMITS.total_source_bytes:
            raise CollectionError('Aggregate XML byte bound exceeded')
        if len(raw) != expected['bytes'] or _sha(raw) != expected['sha256']:
            raise CollectionError('Raw XML digest or byte size differs from pinned98348 inventory')
        metrics = _parse_xml(raw, relative, DEFAULT_LIMITS, [], fields)
        if any(metrics[key] != expected[key] for key in ('xml_root', 'xml_elements', 'tracked_declarations')):
            raise CollectionError('Raw XML shape differs from the projected source descriptor')
        declarations += metrics['tracked_declarations']
        if declarations > DEFAULT_LIMITS.declarations:
            raise CollectionError('Aggregate declaration count bound exceeded')
        observed, direct = _nodes(raw, relative, names, limits, budget)
        matches.extend(observed)
        related.extend(direct)
        units.extend(_unit_nodes(raw, relative, expected, limits, budget))
        checked[relative] = expected
    if complete and set(checked) != set(expected_xml):
        raise CollectionError('Complete scan is missing projected XML')
    seen = {row['matched_value'] for row in matches}
    matched_files = sorted({row['file'] for row in matches})
    return {'format': 'hots-exact-current-legacy-name-xml-node-scan-v1', 'target_version': VERSION,
            'scope': 'complete-pinned-XML-inventory' if complete else 'subset-pinned-XML-file-digests-only',
            'projection_sha256': planned['licenses_sha256'],
            'collection_observation_sha256': planned['collection_observation_sha256'],
            'unresolved_names': sorted(names), 'expected_xml_files': len(expected_xml), 'scanned_xml_files': len(checked),
            'scanned_xml_bytes': total, 'expected_xml_inventory_sha256': _inventory_digest(expected_xml),
            'scanned_xml_inventory_sha256': _inventory_digest(checked),
            'all_projected_XML_files_exact_digest_verified': complete,
            'complete_absence_scope_established': complete,
            'fresh_version_log': log, 'fresh_extracted_metadata': metadata,
            'projection_version_binding': data['version_binding'],
            'matched_file_provenance': [{'path': path, 'bytes': expected_xml[path]['bytes'], 'sha256': expected_xml[path]['sha256']}
                                        for path in matched_files],
            'match_count': len(matches), 'match_role_counts': dict(Counter(row['role'] for row in matches)),
            'names_seen_in_scanned_files': sorted(seen), 'names_not_seen_in_scanned_files': sorted(names - seen),
            'matches': matches, 'related_owning_record_fields': related,
            'unit_identity_queries': {
                'queries': list(UNIT_QUERIES), 'direct_Catalog_CUnit_declarations': units,
                'results': [{'id': name, 'declaration_count': sum(row['id'] == name for row in units),
                             'not_seen_in_scanned_XML': not any(row['id'] == name for row in units),
                             'absent_from_all_projected_XML': (not any(row['id'] == name for row in units)) if complete else None}
                            for name in UNIT_QUERIES],
                'complete_pinned_XML_inventory_verified': complete,
                'numeric_unit_links_or_replacements_inferred': False,
                'inheritance_catalog_order_or_UnitAlias_semantics_resolved': False},
            'aliases_registered': False, 'entitlement_or_ownership_mapping_proven': False,
            'inheritance_or_catalog_load_order_resolved': False, 'replay_modified': False, 'client_launched': False,
            'contains_player_ownership_or_identity_data': False, 'raw_XML_exported': False,
            'limitations': ['Every match is an exact whole attribute, element text or tail-text value; names embedded in paths, substrings or differently cased text are not matches.',
                            'Visual/model/audio references and reward record IDs are classified separately from named alias/migration fields. Classification is not semantic proof.',
                            'Related scalar fields belong to the same owning record only; no cross-record, inheritance, template or reward/license join is performed.',
                            'Absence means no exact literal in the scanned XML scope. It says nothing about encoded, constructed, binary or server-side aliases.',
                            'Fresh hdp.info timestamps can differ from the original metadata digest; Version/IsPtr and metadata paths are checked, and fresh digests are retained.',
                            'Subset reports never establish full inventory coverage or global absence.']}


def scan_complete(root, projection, observation, version_log, *, policy=POLICY, limits=LIMITS):
    data, names, xml, expected_metadata, planned = _inputs(projection, observation, policy)
    log = _fresh_log(version_log)
    inventory, _ = _inventory(Path(root), DEFAULT_LIMITS)
    actual_xml = {relative: path for relative, path in inventory if path.suffix.lower() == '.xml'}
    actual_metadata = {relative: path for relative, path in inventory if path.name.lower() == 'hdp.info'}
    if set(actual_xml) != set(xml) or set(actual_metadata) != set(expected_metadata):
        raise CollectionError('Extracted XML/metadata inventory differs from the pinned projection')
    metadata = []
    for relative, path in sorted(actual_metadata.items()):
        raw = _read(path, DEFAULT_LIMITS.metadata_bytes)
        if _metadata_versions(raw, DEFAULT_LIMITS) != [VERSION]:
            raise CollectionError('Fresh extracted metadata has the wrong live version')
        metadata.append({'path': relative, 'bytes': len(raw), 'sha256': _sha(raw),
                         'version_field': 'Version', 'is_ptr': False, 'observed_version_strings': [VERSION]})
    return _scan(actual_xml, data, names, xml, planned, complete=True, log=log, metadata=metadata, limits=limits)


def scan_subset(files, projection, observation, *, policy=POLICY, limits=LIMITS):
    """Research only; maps projected relative paths to local small raw XML files."""
    data, names, xml, _, planned = _inputs(projection, observation, policy)
    if not isinstance(files, dict) or not files or len(files) > len(xml):
        raise CollectionError('A bounded nonempty subset mapping is required')
    return _scan(files, data, names, xml, planned, complete=False, log=None, metadata=[], limits=limits)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'projection', 'collection-observation', 'version-log', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _output_preflight(args.output, args.root)
        report = scan_complete(args.root, args.projection, args.collection_observation, args.version_log)
        from dataclasses import replace
        write_new_report(report, args.output, limits=replace(DEFAULT_LIMITS, report_bytes=LIMITS.report_bytes))
    except (CollectionError, OSError) as error:
        print('Alias-node scan failed: ' + (str(error) if isinstance(error, CollectionError) else type(error).__name__), file=sys.stderr)
        return 1
    print(json.dumps({'scanned_xml_files': report['scanned_xml_files'], 'exact_matches': report['match_count'],
                      'matched_names': len(report['names_seen_in_scanned_files']),
                      'complete_pinned_inventory_verified': True, 'alias_mapping_proven': False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
