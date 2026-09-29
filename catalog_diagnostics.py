from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from migrate_replay import write_json
from reference_replay import inspect_reference
from repair_unit_tags import components, read_streams, u32

R6_SHA256 = '0613acfcdcda173be31a7dbf4b31a985d62304a35547da18b235256738c22f0c'
REFERENCES = {
    '05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75': 'Braxis Holdout',
    '5a7b05f4a75bc229dbbd74e6cc09e3b411129fc731874cfaa9217432fb85e7dc': 'Dragon Shire',
}
PREFIX = 'NNet.Replay.Tracker.'


@dataclass(frozen=True)
class LinkField:
    event_index: int
    gameloop: int
    path: tuple
    link: int
    tags: tuple[int, ...]


def link_fields(game: list[dict]):
    for index, event in enumerate(game):
        loop = u32(event['_gameloop'])
        if event['_event'] == 'NNet.Game.SSelectionDeltaEvent':
            delta = event['m_delta']
            tags = delta['m_addUnitTags']
            offset = 0
            for ordinal, group in enumerate(delta['m_addSubgroups']):
                count = u32(group['m_count'])
                if not count or count > len(tags) - offset:
                    raise ValueError('Selection group count disagrees with unit tags')
                link = u32(group['m_unitLink'])
                if link >= 65536:
                    raise ValueError('Catalog unit link exceeds its serialized width')
                selected = tuple(u32(t) for t in tags[offset:offset + count])
                yield LinkField(index, loop, ('m_delta', 'm_addSubgroups', ordinal, 'm_unitLink'), link, selected)
                offset += count
            if offset != len(tags):
                raise ValueError('Selection unit tags have no group')
        path = None
        if event['_event'] == 'NNet.Game.SCmdEvent' and 'TargetUnit' in event.get('m_data', {}):
            path = ('m_data', 'TargetUnit')
        elif event['_event'] == 'NNet.Game.SCmdUpdateTargetUnitEvent':
            path = ('m_target',)
        if path:
            node = event
            for part in path:
                node = node[part]
            link = u32(node['m_snapshotUnitLink'])
            if link >= 65536:
                raise ValueError('Catalog unit link exceeds its serialized width')
            yield LinkField(index, loop, path + ('m_snapshotUnitLink',), link, (u32(node['m_tag']),))


class UnitTimeline:
    def __init__(self, tracker: list[dict]):
        self.history = defaultdict(list)
        last_loop = -1
        states = {}
        for event in tracker:
            loop = u32(event['_gameloop'])
            if loop < last_loop:
                raise ValueError('Tracker must be chronological')
            last_loop = loop
            name = event['_event']
            if name not in {PREFIX + x for x in ('SUnitBornEvent', 'SUnitInitEvent', 'SUnitDiedEvent', 'SUnitRevivedEvent', 'SUnitTypeChangeEvent')}:
                continue
            key = (u32(event['m_unitTagIndex']), u32(event['m_unitTagRecycle']))
            prior_type, alive = states.get(key, (None, False))
            if name in (PREFIX + 'SUnitBornEvent', PREFIX + 'SUnitInitEvent', PREFIX + 'SUnitTypeChangeEvent'):
                raw = event['m_unitTypeName']
                if not isinstance(raw, bytes) or not raw or len(raw) > 256:
                    raise ValueError('Invalid tracker unit type')
                prior_type = raw.decode('ascii')
            if name in (PREFIX + 'SUnitBornEvent', PREFIX + 'SUnitInitEvent', PREFIX + 'SUnitRevivedEvent'):
                alive = True
            elif name == PREFIX + 'SUnitDiedEvent':
                alive = False
            states[key] = (prior_type, alive)
            self.history[key].append((loop, prior_type if alive else None))
        self.times = {key: [value[0] for value in rows] for key, rows in self.history.items()}

    def lookup(self, tag: int, loop: int, shift: int = 22) -> tuple[str | None, str]:
        key = components(tag, shift)
        u32(loop)
        if tag in (0, 0xffffffff):
            return None, 'sentinel'
        times = self.times.get(key, [])
        position = bisect.bisect_right(times, loop) - 1
        if position < 0:
            return None, 'no_prior_identity'
        if times[position] == loop:
            return None, 'same_tick_transition'
        name = self.history[key][position][1]
        return (name, 'known_alive') if name else (None, 'dead_or_unknown')


def inventory(game: list[dict], tracker: list[dict], shift: int = 22) -> dict:
    timeline = UnitTimeline(tracker)
    hits = defaultdict(Counter)
    units = defaultdict(set)
    excluded = Counter()
    total = 0
    early = []
    for field in link_fields(game):
        total += 1
        matches = [timeline.lookup(tag, field.gameloop, shift) for tag in field.tags]
        names = {name for name, _ in matches if name is not None}
        if any(name is None for name, _ in matches):
            reason = ','.join(sorted({reason for name, reason in matches if name is None}))
            excluded[reason] += 1
        elif len(names) != 1:
            reason = 'mixed_unit_types_in_subgroup'
            excluded[reason] += 1
        else:
            name = names.pop()
            hits[name][field.link] += 1
            units[(name, field.link)].update(field.tags)
            reason = 'known_alive'
        if field.gameloop <= 80:
            early.append({'event_index': field.event_index, 'gameloop': field.gameloop,
                          'path': list(field.path), 'catalog_link': field.link,
                          'tracker_types': sorted({name for name, _ in matches if name}), 'classification': reason})
    entries = []
    for name in sorted(hits):
        entries.append({'unit_type': name, 'links': [{'link': link, 'fields': count,
                         'distinct_unit_instances': len(units[(name, link)])}
                         for link, count in sorted(hits[name].items())]})
    return {'fields_total': total, 'fields_classified': sum(sum(c.values()) for c in hits.values()),
            'excluded_fields': dict(sorted(excluded.items())), 'entries': entries, 'early_fields': early,
            'lifecycle_policy': 'Use only known alive types strictly before the event tick; never look into the future.'}


def propose_mapping(source: dict, references: list[dict]) -> dict:
    def table(value):
        result = defaultdict(set)
        for item in value['entries']:
            for row in item['links']:
                result[item['unit_type']].add(u32(row['link']))
        return result
    old = table(source)
    new = defaultdict(set)
    for reference in references:
        for name, links in table(reference).items():
            new[name].update(links)
    old_reverse, new_reverse = defaultdict(set), defaultdict(set)
    for catalog, reverse in ((old, old_reverse), (new, new_reverse)):
        for name, links in catalog.items():
            for link in links:
                reverse[link].add(name)
    pairs, unresolved = [], []
    for name in sorted(old):
        before, after = old[name], new.get(name, set())
        reason = None
        if not after:
            reason = 'not_observed_in_current_references'
        elif len(before) != 1 or len(after) != 1:
            reason = 'ambiguous_type_to_link'
        elif len(old_reverse[next(iter(before))]) != 1 or len(new_reverse[next(iter(after))]) != 1:
            reason = 'ambiguous_link_to_type'
        if reason:
            unresolved.append({'unit_type': name, 'source_links': sorted(before), 'target_links': sorted(after), 'reason': reason})
        else:
            pairs.append({'unit_type': name, 'before': next(iter(before)), 'after': next(iter(after))})
    return {'observed_pairs': pairs, 'unresolved': unresolved, 'complete_catalog': False,
            'cross_map_catalog_independence_proven': False, 'automatically_applied': False}


def initial_objects(tracker: list[dict]) -> dict:
    result = defaultdict(list)
    for event in tracker:
        if event['_gameloop'] == 0 and event['_event'] == PREFIX + 'SUnitBornEvent':
            key = (event['m_unitTypeName'].decode('ascii'), event['m_controlPlayerId'],
                   event['m_upkeepPlayerId'], event['m_x'], event['m_y'])
            result[key].append({'index': u32(event['m_unitTagIndex']), 'recycle': u32(event['m_unitTagRecycle'])})
    if not result:
        raise ValueError('No initial tracker objects')
    return result


def compare_initial(source: list[dict], reference: list[dict]) -> dict:
    old, new = initial_objects(source), initial_objects(reference)
    common, ambiguous = [], []
    for key in sorted(old.keys() & new.keys()):
        row = {'descriptor': list(key), 'source': old[key], 'reference': new[key]}
        (common if len(old[key]) == len(new[key]) == 1 else ambiguous).append(row)
    def difference(a, b):
        return [{'descriptor': list(k), 'instances': a[k]} for k in sorted(a.keys() - b.keys())]
    return {'source_objects': sum(map(len, old.values())), 'reference_objects': sum(map(len, new.values())),
            'exact_unique_matches': common, 'ambiguous_matches': ambiguous,
            'source_only': difference(old, new), 'reference_only': difference(new, old),
            'index_offset_counts': dict(sorted(Counter(str(row['reference'][0]['index'] - row['source'][0]['index'])
                                                       for row in common).items())),
            'runtime_mapping_proven': False, 'applied_to_replay': False}


def commands(game: list[dict]) -> dict:
    flags = Counter()
    abilities = Counter()
    early = []
    for index, event in enumerate(game):
        if event['_event'] != 'NNet.Game.SCmdEvent':
            continue
        flag = u32(event['m_cmdFlags'])
        ability = event.get('m_abil')
        if ability:
            abilities[u32(ability['m_abilLink'])] += 1
        if ability is None and set(event['m_data']) == {'TargetPoint'}:
            flags[flag] += 1
        if event['_gameloop'] <= 80:
            early.append({'event_index': index, 'gameloop': event['_gameloop'], 'flags': hex(flag),
                          'ability_link': None if not ability else ability['m_abilLink'],
                          'target_kind': next(iter(event['m_data']))})
    return {'implicit_target_point_flags': {hex(flag): count for flag, count in sorted(flags.items())},
            'explicit_ability_links': {str(link): count for link, count in sorted(abilities.items())},
            'early_commands': early, 'ability_or_flag_mapping_applied': False}


def analyze(source: Path, references: list[Path]) -> dict:
    source = Path(source)
    if hashlib.sha256(source.read_bytes()).hexdigest() != R6_SHA256:
        raise ValueError('Expected immutable R6 source')
    profiles = {}
    streams = {}
    for path in [source, *map(Path, references)]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in profiles or (path != source and digest not in REFERENCES):
            raise ValueError('Duplicate or unreviewed input')
        profile = inspect_reference(path, 96477, 98285)
        game, tracker = read_streams(path)
        profiles[digest] = {'file_sha256': digest, 'declared_build': 98285,
                            'observed_payload_roundtrip': profile['observed_payload_roundtrip'],
                            'unit_catalog': inventory(game, tracker), 'commands': commands(game)}
        streams[digest] = tracker
    if set(profiles) != {R6_SHA256, *REFERENCES}:
        raise ValueError('Both original current reference recordings are required')
    ordered_refs = [profiles[d] for d in sorted(REFERENCES)]
    result = {'format': 'hots-catalog-diagnostics-v1', 'source': profiles[R6_SHA256],
              'references': ordered_refs,
              'proposed_unit_mapping': propose_mapping(profiles[R6_SHA256]['unit_catalog'], [r['unit_catalog'] for r in ordered_refs]),
              'initial_dragon_objects': compare_initial(streams[R6_SHA256], streams[next(d for d, title in REFERENCES.items() if title == 'Dragon Shire')]),
              'replay_modified': False, 'client_playback_validated': False,
              'limitations': ['Observed catalog numbers do not establish live object allocation or simulation equivalence.',
                              'Equal command shapes are not proof of equal command-flag meanings.',
                              'Reference recordings contain different rosters and game modes.',
                              'The screenshot time does not establish the first divergent simulation tick.']}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('references', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = analyze(args.source, args.references)
    write_json(args.output, result)
    print(json.dumps({'observed_pairs': len(result['proposed_unit_mapping']['observed_pairs']),
                      'unresolved_types': len(result['proposed_unit_mapping']['unresolved']),
                      'replay_modified': False}, indent=2))
