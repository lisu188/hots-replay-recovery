"""Project the pinned 41810/98348 Dragon Shire recordings to public talent evidence.

Put the project root and pinned Blizzard heroprotocol package on PYTHONPATH:

    python project_dragon_talent_comparison.py --source ORIGINAL --references REF1 ... REF12 > result.json

The output contains aggregate talent observations, replay hashes and map context.
"""

import argparse
from collections import Counter, defaultdict
from hashlib import file_digest
import json
from pathlib import Path
import sys

from heroprotocol import decoders
from heroprotocol.versions import protocol41810, protocol96477

from mpq_reader import MPQArchive
from talent_choice_audit import audit_talent_choices, SELECTION, SETUP, STAT

SOURCE = 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
REFERENCES = frozenset("""
59bea7829e0ae19e0fc7eccd540c9541589aaafe6c2930ac3b7d5cbfcfa164c7
6050999619a7d6732765025f2bc55b487bc5f1c3f6a511d500c4ad270ce8eed4
6753244ac500b071916b00bf9e498d99a67fd6aa2950e67bd6c46a04cfedf39e
72c43e7e28920acc3866b925768e6e6c5273b303eb455a85925ceb1e1146f2bd
742c87226b179fcb187998c561f160e806d3f4b9648f9f0dd3167466448ed9db
78d20d5f3cbeb85843420e9bc058fa0873d246c74224732e7cdaee5a138bf85a
882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c
889b1d8f2ef029abdc691fce6d52c20489c0cab2fe1220c1003d30608fdcd78e
b1520f5a6950d83deb84356478d6f148ed4eff6939ca524c4a0b632082214c3f
ce9c2b6160f5b6154abe8cbcecae982dc00c61910bee691627c3a57c8c99dc77
eba0a8353d6fd4d19363267f7164b8a9d8a0dfd6f2974583f7403fc49760661c
fc85db148697edec3488605f13591275d3b46b362009089584697249491df76c
""".split())
SCHEMAS = {
    'protocol41810': '879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',
    'protocol96477': 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84',
    'decoders': '17bfb926af0f7f79e18f6299dbae50fc2821c53b229235d4f9c857c7ef3e96b1',
}


def sha(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def read_complete(data, decoder_class, protocol, type_id):
    reader = decoder_class(data, protocol.typeinfos)
    result = reader.instance(type_id)
    reader.byte_align()
    if not reader.done():
        raise ValueError('Trailing metadata bytes')
    return result


def relevant(stream, kinds):
    rows = []
    count = 0
    for event in stream:
        count += 1
        if event['_event'] in kinds:
            rows.append(event)
    return rows, count


def observe(path, replay_hash, build):
    protocol = protocol41810 if build == 41810 else protocol96477
    archive = MPQArchive(path)
    try:
        header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        if (header['m_version']['m_build'], header['m_version']['m_baseBuild']) != (build, build):
            raise ValueError('Unexpected replay build')
        details = read_complete(archive.read_file('replay.details'), decoders.VersionedDecoder,
                                protocol, protocol.game_details_typeid)
        init = read_complete(archive.read_file('replay.initData'), decoders.BitPackedDecoder,
                             protocol, protocol.replay_initdata_typeid)
        description = init['m_syncLobbyState']['m_gameDescription']
        context = {
            'build': build, 'base_build': header['m_version']['m_baseBuild'],
            'map_title': details['m_title'].decode('utf-8'),
            'map_file_checksum': description['m_mapFileSyncChecksum'],
            'mod_file_checksum': description['m_modFileSyncChecksum'],
        }
        expected_sums = (759447839, 3522231966) if build == 41810 else (886294905, 13528913)
        if context['map_title'] != 'Dragon Shire' or (context['map_file_checksum'], context['mod_file_checksum']) != expected_sums:
            raise ValueError('Unexpected map/mod context')
        if build == 98348:
            context.update(data_build=header['m_dataBuildNum'], root_key=header['m_ngdpRootKey']['m_data'].hex())
            if context['data_build'] != build or context['root_key'] != 'c3b3c8bc82e3a5a62e550fdde9a40c28':
                raise ValueError('Unexpected target data build/root')
        game, game_count = relevant(protocol.decode_replay_game_events(archive.read_file('replay.game.events')), {SELECTION})
        tracker, tracker_count = relevant(protocol.decode_replay_tracker_events(archive.read_file('replay.tracker.events')), {STAT, SETUP})
        report = audit_talent_choices(game, tracker)
        archive.file.seek(0)
        if file_digest(archive.file, 'sha256').hexdigest() != replay_hash:
            raise ValueError('Archive changed while decoding')
    finally:
        archive.close()
    pairs = report['unique_one_loop_pairs']
    if pairs != report['selection_events'] or pairs != report['tracker_purchase_events']:
        raise ValueError('Expected complete one-to-one selection/purchase coverage')
    stats = {
        'replay_sha256': replay_hash, 'game_events': game_count, 'tracker_events': tracker_count,
        'selections': report['selection_events'], 'tracker_purchases': report['tracker_purchase_events'],
        'paired_purchases': pairs,
    }
    return context, stats, report['observations']


def compare(source, reference_paths):
    for module in (protocol41810, protocol96477, decoders):
        if sha(Path(module.__file__)) != SCHEMAS[module.__name__.rsplit('.', 1)[-1]]:
            raise ValueError('Unexpected heroprotocol schema or decoder source')
    if sha(source) != SOURCE:
        raise ValueError('Unexpected original replay')
    references = {sha(path): path for path in reference_paths}
    if len(reference_paths) != len(REFERENCES) or references.keys() != REFERENCES:
        raise ValueError('Expected the twelve distinct pinned reference recordings')
    context, original, rows = observe(source, SOURCE, 41810)
    target_context = None
    controls = []
    by_index = defaultdict(set)
    by_name = defaultdict(set)
    for replay_hash, path in sorted(references.items()):
        current, reference, observations = observe(path, replay_hash, 98348)
        if target_context is not None and target_context != current:
            raise ValueError('Inconsistent reference map/mod contexts')
        target_context = current
        controls.append(reference)
        for row in observations:
            by_index[row['hero_id'], row['index']].add(row['purchase_name'])
            by_name[row['hero_id'], row['purchase_name']].add(row['index'])
    counts = Counter()
    projected = []
    for row in rows:
        hero, name, index = row['hero_id'], row['purchase_name'], row['index']
        names = sorted(by_index[hero, index])
        indices = sorted(by_name[hero, name])
        if not names:
            state = 'target_index_unobserved'
        elif name not in names:
            state = 'different_name_at_index'
        elif len(names) == 1:
            state = 'same_name_at_index'
        else:
            state = 'mixed_names_at_index'
        counts[state] += row['count']
        projected.append({**row, 'comparison': state, 'target_names_at_source_index': names,
                          'target_indices_for_source_name': indices})
    return {
        'format': 'dragon-shire-observed-talent-comparison-v1',
        'source_context': context, 'reference_context': target_context, 'source': original,
        'references': controls, 'upstream_source_sha256': SCHEMAS,
        'game_tracker_schemas': {'source': 41810, 'references': 96477},
        'association': 'Unique same-player tracker purchase exactly one loop after selection, with prior explicit user/player setup and recorded hero.',
        'scope': 'Two independently decoded recordings may associate different labels with the same hero/index. Matching names or indices do not establish equivalent mechanics or an admissible replacement.',
        'source_purchase_counts': dict(sorted(counts.items())), 'source_observations': projected,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--references', type=Path, nargs=12, required=True)
    args = parser.parse_args()
    sys.stdout.buffer.write((json.dumps(compare(args.source, args.references), sort_keys=True, indent=2) + '\n').encode('utf-8'))
