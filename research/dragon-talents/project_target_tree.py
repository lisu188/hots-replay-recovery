"""Compare all original TEN_GREYMANE talent selections with eight pinned 98348 hero files."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


SOURCE_PATH_SHA = '8e96e51618e5d3922dda9d2ecfa88bc4b9461b8ec0cd9bf947374ff696d2e1e9'
CONTROLS_SHA = '0641a634ddf8e0f8915f80e5798024e97d847891c9519be916ffdc38a6ccb395'
DEFAULTS_SHA = 'f39bc54277cec03c773bffb8cb2c183a69b96c75884937937e4d60b04733adad'
# Whole member SHA-256s from observations/collection-license-current-98348.json.
HERO_BY_SHA = {
    'b2ecee56c24e3a6e62c904f066f858dd5fb9fa144c2e17af423320efaf9c69e1': 'Abathur',
    '6e575d1c7e852274480b88e89e06ce993a9b8dd6f7988ccdc57e173c337eb799': 'Anubarak',
    '1e4bc827d905d70772f6e3cd06707b147fa2e8349e94ae9c659b6aa91a79444f': 'Barbarian',
    '0331a785983525abcbd58d95159ce4b12d8652c8a7294967e1231b30f5053064': 'FaerieDragon',
    '78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff': 'Greymane',
    '39cf6954288e32edd73dfed13f82e45ab5f944a54f9f3fa9adaf2aacc7ffc13b': 'Kaelthas',
    '721086138a01ff65659616556ea617c85f968d8bd28ec888fa6397bde0ce113a': 'Nova',
    '8dc1f32eca0299e4007a99ac487bf816ff3a7f8a24e0f3301ea050e3f7b8fd29': 'Tyrande',
}


def read_input(path):
    # All eleven optional/required inputs are smaller than 312 KiB.
    with path.open('rb') as source:
        data = source.read(312 * 1024 + 1)
    if len(data) > 312 * 1024:
        raise ValueError(f'Oversized projection input: {path.name}')
    return data


def pinned(path, expected):
    content = read_input(path)
    if sha256(content).hexdigest() != expected:
        raise ValueError(f'Unexpected contents for {path.name}')
    return content


def read_trees(files):
    trees = {}
    for path in files:
        data = read_input(path)
        digest = sha256(data).hexdigest()
        if digest not in HERO_BY_SHA:
            raise ValueError(f'Unknown 98348 XML member: {path.name}')
        hero = HERO_BY_SHA[digest]
        hero_id = 'Hero' + hero
        if hero_id in trees:
            raise ValueError(f'Duplicate hero file for {hero}')
        catalog = ET.fromstring(data)
        definition, = [node for node in catalog.findall('CHero') if node.get('id') == hero]
        by_name, ordered = {}, []
        for position, choice in enumerate(definition.findall('TalentTreeArray')):
            talent = choice.attrib['Talent']
            if talent in by_name:
                raise ValueError(f'Ambiguous literal row for {hero}: {talent}')
            by_name[talent] = dict(position=position, tier=int(choice.attrib['Tier']),
                                   column=int(choice.attrib['Column']), prerequisites=[
                                       item.attrib['value'] for item in choice.findall('PrerequisiteTalentArray')])
            ordered.append(talent)
        declarations = {node.get('id') for node in catalog.findall('CTalent')}
        trees[hero_id] = (by_name, ordered, declarations)
    if len(trees) != len(HERO_BY_SHA):
        raise ValueError('Expected eight distinct pinned heroes')
    return trees


def project(xml_files, source_path, controls, tier_defaults=None):
    trees = read_trees(xml_files)
    source = json.loads(pinned(source_path, SOURCE_PATH_SHA))['source_talent_path']
    observations = json.loads(pinned(controls, CONTROLS_SHA))['source_observations']
    by_key = {(o['hero_id'], o['index'], o['purchase_name']): o for o in observations}
    levels = {}
    if tier_defaults is not None:
        root = ET.fromstring(pinned(tier_defaults, DEFAULTS_SHA))
        default, = [node for node in root.findall('CHero') if node.attrib == {'default': '1'}]
        levels = {int(row.attrib['Tier']): int(row.attrib['Level']) for row in default.findall('TalentTierArray')}
    cases, counts, multiplicity = [], Counter(), Counter()
    for selection in source:
        hero, index, name = selection['hero'], selection['source_index'], selection['purchase']
        key = hero, index, name
        observation = by_key[key]
        multiplicity[key] += 1
        by_name, ordered, declarations = trees[hero]
        literal = by_name.get(name)
        if literal is None:
            status = 'absent_from_tree'
        elif literal['position'] == index:
            status = 'same_position'
        else:
            status = 'different_position'
        counts[status] += 1
        case = dict(ordinal=selection['game_event_ordinal'], loop=selection['selection_loop'], hero=hero,
                    source_index=index, purchase=name, recorded_prior_level=selection['recorded_prior_level'],
                    literal_name_at_source_index=ordered[index] if index < len(ordered) else None,
                    target_literal=literal, literal_status=status, same_file_CTalent=name in declarations,
                    observed_indices_for_name=observation['target_indices_for_source_name'],
                    observed_names_at_source_index=observation['target_names_at_source_index'])
        if levels and literal is not None:
            case['target_global_default_level'] = levels[literal['tier']]
        cases.append(case)
    if multiplicity != {k: o['count'] for k, o in by_key.items()}:
        raise ValueError('Source selection multiplicities differ from the independently pinned controls table')
    return dict(format='ten-greymane-source-to-98348-literal-trees-v1', source_build=41810, target_build=98348,
                source_path_sha256=SOURCE_PATH_SHA, controls_sha256=CONTROLS_SHA, hero_xml_by_sha256=HERO_BY_SHA,
                global_tier_defaults_sha256=DEFAULTS_SHA if levels else None, source_purchase_counts=dict(counts),
                scope='Positions are zero-based direct CHero XML rows, with observations from twelve Dragon Shire controls. '
                      'Optional global default levels are file-local declarations. Effective rule equivalence, selectable wire indices '
                      'for unobserved talents and playback are unverified.',
                selections=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xml', type=Path, nargs=8, required=True, metavar='HERO_XML')
    parser.add_argument('--source-path', type=Path, required=True)
    parser.add_argument('--controls', type=Path, required=True)
    parser.add_argument('--tier-defaults', type=Path, help='Optional pinned 98348 global HeroData.xml')
    args = parser.parse_args()
    try:
        report = project(args.xml, args.source_path, args.controls, args.tier_defaults)
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    sys.stdout.buffer.write((json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8'))
