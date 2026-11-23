"""Test the 98348 normal talent-award path against tracker names withheld from the model."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from encoders import encode_tracker_events
from heroprotocol.versions import protocol41810, protocol96477
from mpq_reader import MPQArchive
from project_target_tree import DEFAULTS_SHA, HERO_BY_SHA, pinned, read_trees
from source_talent_path_41810 import _tracker_history
from talent_choice_audit import SELECTION, STAT, _fields
from migrate_replay import SOURCE_SHA256


TARGET_ROOT = 'c3b3c8bc82e3a5a62e550fdde9a40c28'
ROSTER_SHA = 'fc6dbc312dac9143bfe450d661f8033a04c2ce4eec51878618e2a517f8faf609'


def active_tier(levels, occupied, level):
    """Default ascending tier scan. Assumes all tiers enabled and no respec."""
    return next((tier for tier in sorted(levels) if tier not in occupied and levels[tier] <= level), None)


def check_match(replay, expected_sha, xml_files, tier_defaults, include_witnesses=False):
    original = expected_sha == SOURCE_SHA256
    if original and include_witnesses:
        raise ValueError('Target witnesses require a current control replay')
    protocol = protocol41810 if original else protocol96477
    trees = read_trees(xml_files)
    grid = {}
    for hero, (by_name, _, _) in trees.items():
        for name, row in by_name.items():
            cell = (hero, row['tier'], row['column'])
            if cell in grid:
                raise ValueError('Duplicate direct tree cell')
            grid[cell] = name
    default_xml = ET.fromstring(pinned(tier_defaults, DEFAULTS_SHA))
    default, = [node for node in default_xml.findall('CHero') if node.attrib == {'default': '1'}]
    levels = {int(row.attrib['Tier']): int(row.attrib['Level']) for row in default.findall('TalentTierArray')}

    with closing(MPQArchive(replay)) as archive:
        archive.file.seek(0)
        if file_digest(archive.file, 'sha256').hexdigest() != expected_sha:
            raise ValueError('Replay digest mismatch')
        header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        build = 41810 if original else 98348
        if (header['m_version']['m_baseBuild'], header['m_version']['m_build'], header['m_dataBuildNum']) != (build,) * 3:
            raise ValueError('Wrong replay build')
        if not original and header['m_ngdpRootKey']['m_data'].hex() != TARGET_ROOT:
            raise ValueError('Wrong target data root')
        game = archive.read_file('replay.game.events')
        tracker = archive.read_file('replay.tracker.events')
        if not original:
            description = protocol.decode_replay_initdata(archive.read_file('replay.initData'))['m_syncLobbyState']['m_gameDescription']
            context = {key: description[key] for key in ('m_mapFileSyncChecksum', 'm_modFileSyncChecksum')}
        archive.file.seek(0)
        if file_digest(archive.file, 'sha256').hexdigest() != expected_sha:
            raise ValueError('Replay changed during read')

    events = list(protocol.decode_replay_tracker_events(tracker))
    # Identify the scope by prior hero/player setup, without reading purchase names.
    setup, heroes, history, _ = _tracker_history(e for e in events if e.get('m_eventName') != b'TalentChosen')
    held, actual_names = {}, {}
    for event in events:
        if event['_event'] != STAT or event['m_eventName'] != b'TalentChosen':
            continue
        player = _fields(event, 'm_intData')[b'PlayerID']
        spawn, hero = heroes[player]
        clock = event['_gameloop']
        if hero not in trees:
            continue
        if spawn > clock or (player, clock) in held:
            raise ValueError('Ambiguous tracker purchase')
        item, = [pair for pair in event['m_stringData'] if pair['m_key'] == b'PurchaseName']
        actual_names[player, clock] = item.pop('m_value')
        held[player, clock] = item

    occupied = defaultdict(set)
    rows = []
    for ordinal, event in enumerate(protocol.decode_replay_game_events(game)):
        if event['_event'] != SELECTION:
            continue
        clock, index = event['_gameloop'], event['m_index']
        setup_loop, player = setup[event['_userid']['m_userId']]
        spawn, hero = heroes[player]
        if hero not in trees:
            continue
        key = (player, clock + 1)
        if max(setup_loop, spawn) > clock or key not in held:
            raise ValueError('Unpaired selection')
        end = bisect_left(history[player], clock, key=lambda item: item[0])
        if not end:
            raise ValueError('Missing prior recorded level')
        level = history[player][end - 1][1]
        tier = active_tier(levels, occupied[player], level)
        if tier is None:
            raise ValueError('No eligible tier under the stated assumptions')
        occupied[player].add(tier)
        by_name, ordered, _ = trees[hero]

        if original:
            # Assume every preceding historical selection was represented successfully.
            # This yields a necessary tier per choice, not a simulated stock match.
            name = actual_names[key].decode('ascii')
            target = by_name.get(name)
            if target is None:
                status = 'absent'
            elif target['tier'] != tier:
                status = 'requires_tier_change'
            else:
                status = 'same_tier'
            rows.append(dict(ordinal=ordinal, loop=clock, hero=hero, purchase=name, active_tier=tier,
                             target_tier=target['tier'] if target else None, recorded_level=level, status=status))
        else:
            if index >= len(ordered):
                raise ValueError('Observed target index outside the literal tree')
            wire_row = by_name[ordered[index]]
            if wire_row['tier'] != tier:
                raise ValueError('Wire row disagrees with the active tier')
            name = grid[hero, tier, wire_row['column']]
            held[key]['m_value'] = name.encode('ascii')
            if held[key]['m_value'] != actual_names[key]:
                raise ValueError('Reconstructed tracker purchase differs')
            rows.append(dict(loop=clock, hero=hero, purchase=name, tier=tier, column=wire_row['column'], index=index))
        del held[key]
    if held:
        raise ValueError('Unmatched scoped tracker purchases')

    result = dict(replay_sha256=expected_sha, build=build, scoped_awards=len(rows),
                  selections_per_scoped_player=sorted(map(len, occupied.values())),
                  assumption='Ascending enabled default tiers, no respec, prior recorded LevelUp used for UnitLevel.')
    if original:
        counts = Counter(row['status'] for row in rows)
        unique = {(r['hero'], r['purchase'], r['active_tier'], r['status']) for r in rows}
        if len(unique) != len({(hero, name) for hero, name, _, _ in unique}):
            raise ValueError('Conflicting required tier for a historical purchase')
        return dict(result, counts=dict(counts), distinct=dict(Counter(r[3] for r in unique)), selections=rows)
    encoded = encode_tracker_events(events, protocol)
    if encoded != tracker:
        raise ValueError('Reconstructed tracker member differs')
    result.update(context=context, tracker_bytes=len(tracker), tracker_sha256=sha256(encoded).hexdigest(),
                  tracker_events=len(events), whole_member_identical=True, scope_heroes=sorted({r['hero'] for r in rows}))
    if include_witnesses:
        result['witnesses'] = rows
    return result


def study(source, reference_root, roster, xml_files, tier_defaults):
    original = check_match(source, SOURCE_SHA256, xml_files, tier_defaults)
    refs = json.loads(pinned(roster, ROSTER_SHA))['references']
    controls = []
    for ref in refs:
        path = reference_root / ref['replay_file']
        if path.stat().st_size != ref['replay_bytes']:
            raise ValueError('Wrong control size')
        match = check_match(path, ref['replay_sha256'], xml_files, tier_defaults)
        if match['context'] != {'m_mapFileSyncChecksum': 886294905, 'm_modFileSyncChecksum': 13528913}:
            raise ValueError('Unexpected control map or mod')
        controls.append(match)
    return dict(format='active-tier-award-study-v1', source=original, controls=controls,
                roster_sha256=ROSTER_SHA, target_root=TARGET_ROOT, hero_xml_by_sha256=HERO_BY_SHA,
                tier_defaults_sha256=DEFAULTS_SHA, recovered_names=sum(c['scoped_awards'] for c in controls),
                complete_tracker_bytes=sum(c['tracker_bytes'] for c in controls),
                stock_behavior_or_runtime_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--sha256', help='Whole-file SHA-256 for a single replay')
    parser.add_argument('--reference-root', type=Path, help='Directory containing the pinned control replay paths')
    parser.add_argument('--roster', type=Path, help='Pinned expanded-current-catalog-comparison-2026-10-18.json')
    parser.add_argument('--witnesses', action='store_true', help='Include individual current-build awards with no player identifiers')
    parser.add_argument('--xml', type=Path, nargs=8, required=True)
    parser.add_argument('--tier-defaults', type=Path, required=True)
    args = parser.parse_args()
    if args.reference_root is not None and args.roster is not None and args.sha256 is None and not args.witnesses:
        report = study(args.replay, args.reference_root, args.roster, args.xml, args.tier_defaults)
    elif args.reference_root is None and args.roster is None and args.sha256 is not None:
        report = check_match(args.replay, args.sha256, args.xml, args.tier_defaults, include_witnesses=args.witnesses)
    else:
        parser.error('Provide either --sha256 or the pair --reference-root and --roster')
    sys.stdout.buffer.write((json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8'))
