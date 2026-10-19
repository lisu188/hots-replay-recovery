"""Hash-bound saved metadata only: exact startup unit-link coverage.

No replay, PE, old header, dump, network, conversion or personal data access.
Public game unit names/catalog indices and aggregate observation counts only.
"""
from collections import defaultdict
import base64
import hashlib
import json
from pathlib import Path
import os

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
LIMIT = 4*1024*1024
R8_SHA = '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
SCHEMA = 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
ROOT = 'c3b3c8bc82e3a5a62e550fdde9a40c28'
sha = lambda data: hashlib.sha256(data).hexdigest()


class Budget:
    def __init__(self):
        self.bytes = 0
        self.pins = {}
    def read(self, path, expected=None):
        if path.is_symlink():
            raise ValueError('Metadata symlink refused')
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not 1 <= before.st_size <= 512*1024 or self.bytes+before.st_size+1 > LIMIT:
                raise ValueError('Metadata read budget exceeded')
            raw = stream.read(before.st_size+1)
            after = os.fstat(stream.fileno())
        self.bytes += len(raw)
        if len(raw) != before.st_size or before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise ValueError('Metadata changed during read')
        digest = sha(raw)
        if expected is not None and expected != digest:
            raise ValueError('Pinned metadata digest differs')
        if path in self.pins and self.pins[path]['sha256'] != digest:
            raise ValueError('Metadata changed across reads')
        self.pins[path] = {'bytes': len(raw), 'sha256': digest}
        return raw
    def document(self, path, expected=None):
        return json.loads(self.read(path, expected))


def table(inventory):
    result = {}
    for row in inventory['entries']:
        name = row['unit_type']
        if name in result or not name.isascii() or not name:
            raise ValueError('Duplicate or malformed inventory unit type')
        result[name] = {item['link'] for item in row['links']}
        if any(type(link) is not int or not 0 <= link < 65536 for link in result[name]):
            raise ValueError('Malformed catalog link')
    return result


def classify(source, references):
    old = table(source)
    current = defaultdict(set)
    for reference in references:
        for name, links in table(reference).items():
            current[name].update(links)
    reverse_old, reverse_current = defaultdict(set), defaultdict(set)
    for catalog, reverse in ((old, reverse_old), (current, reverse_current)):
        for name, links in catalog.items():
            for link in links:
                reverse[link].add(name)
    pairs, unresolved = [], []
    for name in sorted(old):
        before, after = old[name], current[name]
        if not after:
            reason = 'not_observed_in_current_references'
        elif len(before) != 1 or len(after) != 1:
            reason = 'ambiguous_type_to_link'
        elif len(reverse_old[next(iter(before))]) != 1 or len(reverse_current[next(iter(after))]) != 1:
            reason = 'ambiguous_link_to_type'
        else:
            pairs.append({'unit_type': name, 'before': next(iter(before)), 'after': next(iter(after))})
            continue
        unresolved.append({'unit_type': name, 'source_links': sorted(before), 'target_links': sorted(after), 'reason': reason})
    return pairs, unresolved


def validate_profile(profile, replay_sha):
    target = profile['target']
    version = target['m_version']
    if (profile['file_sha256'] != replay_sha or profile['schema_file_sha256'] != SCHEMA
            or profile['observed_payload_roundtrip'] is not True
            or (version['m_build'],version['m_baseBuild'],target['m_dataBuildNum']) != (98348,98348,98348)
            or base64.b64decode(target['m_ngdpRootKey']['m_data']['$bytes_base64'], validate=True).hex() != ROOT
            or any(profile['streams'][kind]['binary_roundtrip'] is not True for kind in ('game','message','tracker'))):
        raise ValueError('Saved genuine current core profile differs')


def analyze():
    budget = Budget()
    startup = budget.document(REPO/'observations/startup-interval-r8-2026-09-29.json')
    old_anchors = budget.document(REPO/'observations/runtime-catalog-reference-anchors.json')
    expanded = budget.document(REPO/'observations/expanded-current-catalog-comparison-2026-10-18.json')
    cross = budget.document(REPO/'observations/current-crossmap-eight-catalog-observation-2026-10-18.json')
    budget.read(REPO/'audit_startup_interval.py')
    budget.read(REPO/'catalog_diagnostics.py')
    budget.read(REPO/'repair_unit_tags.py')
    budget.read(Path(__file__))
    if startup['candidate_sha256'] != R8_SHA or expanded['source']['replay_sha256'] != R8_SHA or cross['source_replay_sha256'] != R8_SHA:
        raise ValueError('Source checkpoint binding differs')
    source = budget.document(WORK/expanded['source']['inventory_file'], expanded['source']['inventory_file_sha256'])
    references = []
    for index, row in enumerate(expanded['references']):
        inventory = budget.document(WORK/row['inventory_file'], row['inventory_file_sha256'])
        profile = budget.document(WORK/row['profile_file'], row['profile_file_sha256'])
        validate_profile(profile, row['replay_sha256'])
        references.append({'id': 'dragon-'+str(index+1).zfill(2), 'map': 'Dragon Shire',
            'replay_sha256': row['replay_sha256'], 'inventory_sha256': row['inventory_file_sha256'],
            'inventory': inventory, 'selected_hero_names': []})
    for row in cross['references']:
        path = WORK/'replay-search-20261018'/row['replay_file']
        inventory = budget.document(path.with_name(path.name+'.inventory.v2.json'), row['inventory_sha256'])
        profile = budget.document(path.with_name(path.name+'.profile.v2.json'), row['profile_sha256'])
        validate_profile(profile, row['replay_sha256'])
        references.append({'id': row['id'], 'map': row['map'], 'replay_sha256': row['replay_sha256'],
            'inventory_sha256': row['inventory_sha256'], 'inventory': inventory,
            'selected_hero_names': row['selected_hero_names']})
    if len(references) != 20:
        raise ValueError('Expected twelve Dragon plus eight other-map catalog inventories')
    pairs, unresolved = classify(source, [row['inventory'] for row in references])
    if pairs != cross['candidate_mapping']['observed_pairs'] or unresolved != cross['candidate_mapping']['unresolved']:
        raise ValueError('Fresh saved-inventory recomputation differs from published comparison')
    early = [row for row in source['early_fields'] if row['gameloop'] < 64]
    if len(early) != 4:
        raise ValueError('Unexpected startup catalog field count')
    startup_rows = []
    for field, recorded in zip(early, startup['catalog_fields_in_interval']):
        if (field['classification'] != 'known_alive' or field['tracker_types'] != [recorded['tracker_type']]
                or (field['event_index'],field['gameloop'],field['catalog_link']) !=
                   (recorded['event_index'],recorded['gameloop'],recorded['recorded_catalog_link'])):
            raise ValueError('Exact early tracker/selection evidence differs')
        name = field['tracker_types'][0]
        pair = next(row for row in pairs if row['unit_type'] == name)
        if pair['before'] != field['catalog_link']:
            raise ValueError('Source startup link differs from combined candidate')
        evidence = []
        for reference in references:
            for row in reference['inventory']['entries']:
                if row['unit_type'] == name:
                    for item in row['links']:
                        evidence.append({'id': reference['id'], 'map': reference['map'],
                            'replay_sha256': reference['replay_sha256'], 'inventory_sha256': reference['inventory_sha256'],
                            'catalog_link': item['link'], 'classified_field_count': item['fields'],
                            'same_target_map': reference['map'] == 'Dragon Shire'})
        startup_rows.append({'event_index': field['event_index'], 'gameloop': field['gameloop'],
            'tracker_unit_type': name, 'source_catalog_link': field['catalog_link'],
            'recorded_identity_classification': 'known_alive_strictly_before_event',
            'historical_98285_anchor': old_anchors['unit_anchors'].get(name),
            'current_98348_observed_candidate': pair['after'],
            'same_map_current_anchor_observed': any(row['same_target_map'] for row in evidence),
            'current_observation_evidence': evidence})
    remaining_rows = []
    for unresolved_row in unresolved:
        family = 'Abathur' if 'Abathur' in unresolved_row['unit_type'] else 'Nova' if 'Nova' in unresolved_row['unit_type'] else None
        corresponding_hero_seen = [ref['id'] for ref in references if family in ref['selected_hero_names']] if family else []
        remaining_rows.append({**unresolved_row, 'hero_roster_context_only': corresponding_hero_seen,
            'hero_roster_establishes_specific_spawn_type_or_catalog_link': False})
    # All metadata are checked once more, within the same aggregate budget.
    for path, pin in list(budget.pins.items()):
        budget.read(path, pin['sha256'])
    return {'format': 'hots-startup-catalog-current-coverage-review-v1',
        'source_replay_sha256': R8_SHA, 'startup_interval': {'start_inclusive': 0, 'stop_exclusive': 64},
        'startup_fields': startup_rows, 'historical_NULL_anchor_fields_now_observed': 2,
        'current_observed_candidates_for_startup_fields': 4, 'startup_fields_with_same_map_current_anchor': 3,
        'target_context': {'build_base_data': 98348, 'root': ROOT, 'same_map': 'Dragon Shire'},
        'saved_catalog_controls_checked': 20, 'same_map_controls': 12, 'other_map_controls': 8,
        'recomputed_combined_pair_count': len(pairs), 'recomputed_combined_unresolved_count': len(unresolved),
        'remaining_full_match_unresolved_types': remaining_rows,
        'decoder_registry_failure_identified': False,
        'conclusion': 'The old two startup NULL anchors were limited98285 reference coverage. Both exact recorded tracker types already have hash-bound unambiguous same-map98348 observations. No new donor or guessed hero/morph alias is needed for those two fields. Kaelthas has a current other-map candidate only.',
        'method': 'Selection subgroup unit tags join to chronological tracker lifecycle state using repaired packed-tagshift22. Only alive identities strictly before the event tick are admitted; same-tick transitions/dead/unknown/mixed groups are excluded. This is recorded identity evidence, not new engine live allocation.',
        'metadata_input_inventory': [{'path': path.relative_to(WORK).as_posix() if path.is_relative_to(WORK)
             else 'repo/'+path.relative_to(REPO).as_posix(), **pin} for path, pin in budget.pins.items()],
        'metadata_bytes_read_including_before_after_checks': budget.bytes,
        'replay_PE_old_header_dump_network_reads': 0, 'personal_or_raw_replay_values_emitted': False,
        'catalog_values_or_replay_modified': False, 'automatic_migration_or_runtime_equivalence_proven': False,
        'limits': ['Saved core profiles and catalog inventories are hash-bound; raw replay bodies were not reread in this metadata review.',
            'These20 saved catalog inventories are not a fresh catalog inventory for the21st EU ARAM control; no global21-file absence claim is made.',
            'A selected hero is not evidence that a specific summon, clone, morph or building state produced a usable catalog-link observation.',
            'Cross-map observed agreement remains a candidate and does not prove current Dragon Kaelthas or general map independence.',
            'The six full-match unresolved types are separate from the four startup fields. Ambiguous tower aliases must not be collapsed.']}


if __name__ == '__main__':
    output = HERE/'startup-catalog-current-coverage-review.json'
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refuse existing review report')
    data = (json.dumps(analyze(), indent=2, sort_keys=True)+'\n').encode()
    if len(data) > 64*1024:
        raise ValueError('Review report exceeds cap')
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': sha(data)}))
