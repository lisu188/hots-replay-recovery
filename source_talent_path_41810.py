"""Recover TEN_GREYMANE's erased source talent indices from recorded purchase names."""

import argparse
from bisect import bisect_left
from collections import defaultdict
from contextlib import closing
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sys

from migrate_replay import SOURCE_SHA256, decode_events, encode_events, protocol
from mpq_reader import MPQArchive
from talent_choice_audit import SELECTION, SETUP, STAT, _fields


CATALOG_SHA256 = 'aaf264de6c3e31ce4bee1b1a5d658d695036393e4077e539630dd553698e9bbb'


def _tracker_history(events):
    setup, players, heroes, purchases = {}, set(), {}, {}
    levels = defaultdict(list)
    for event in events:
        kind, tick = event['_event'], event['_gameloop']
        if kind == SETUP and event['m_userId'] is not None:
            user, player = event['m_userId'], event['m_playerId']
            if user in setup or player in players:
                raise ValueError('Ambiguous user/player setup')
            setup[user] = (tick, player)
            players.add(player)
        if kind != STAT or event['m_eventName'] not in (b'PlayerSpawned', b'LevelUp', b'TalentChosen'):
            continue
        ints = _fields(event, 'm_intData')
        player = ints[b'PlayerID']
        if event['m_eventName'] == b'LevelUp':
            level = ints[b'Level']
            history = levels[player]
            if history and (tick <= history[-1][0] or level <= history[-1][1]):
                raise ValueError('Ambiguous level history')
            history.append((tick, level))
        elif event['m_eventName'] == b'PlayerSpawned':
            hero = _fields(event, 'm_stringData')[b'Hero'].decode('ascii')
            first = heroes.setdefault(player, (tick, hero))
            if first[1] != hero:
                raise ValueError('Conflicting hero identity')
        else:
            if (player, tick) in purchases:
                raise ValueError('Ambiguous recorded purchase')
            purchases[player, tick] = _fields(event, 'm_stringData')[b'PurchaseName'].decode('ascii')
    return setup, heroes, levels, purchases


def _source_catalog_lookup(catalog, hero_ids):
    # The exporter grouped choices by level after sorting by Tier and Column.
    # Treat this order as a hypothesis until the reconstructed member matches.
    result = {}
    for hero in catalog:
        hero_id = 'Hero' + hero['id']
        if hero_id not in hero_ids:
            continue
        if hero_id in result:
            raise ValueError('Duplicate historical hero')
        by_name = {}
        for level in sorted(hero['talents'], key=int):
            for option in hero['talents'][level]:
                name = option['id']
                if name in by_name:
                    raise ValueError('Ambiguous talent name for ' + hero_id)
                by_name[name] = (len(by_name), int(level), option.get('prerequisite'))
        result[hero_id] = by_name
    return result


def restore_talent_indices(masked_game, tracker, catalog):
    """Return game events with source indices restored and anonymous selection evidence.

    Talent selections must contain only event metadata. Track each player's
    prerequisites independently, including when two players use the same hero.
    All selections and tracker purchases must pair exactly once.
    """
    setup, heroes, levels, purchases = _tracker_history(tracker)
    lookup = _source_catalog_lookup(catalog, {hero for _, hero in heroes.values()})
    previous = defaultdict(dict)
    restored, path = [], []
    last_tick = -1
    for ordinal, event in enumerate(masked_game):
        tick = event['_gameloop']
        if tick < last_tick:
            raise ValueError('Game events out of order')
        last_tick = tick
        if event['_event'] == SELECTION:
            if any(not key.startswith('_') for key in event):
                raise ValueError('Erase the source selection payload before recovery')
            setup_tick, player = setup[event['_userid']['m_userId']]
            spawn, hero = heroes[player]
            if max(setup_tick, spawn) > tick:
                raise ValueError('Selection precedes its player or hero identity')
            name = purchases.pop((player, tick + 1), None)
            if name is None or name not in lookup.get(hero, {}):
                raise ValueError('Selection lacks a unique next-loop purchase in the historical catalog')
            index, required_level, prerequisite = lookup[hero][name]
            history = levels[player]
            end = bisect_left(history, tick, key=lambda row: row[0])
            if end == 0 or history[end - 1][1] < required_level:
                raise ValueError('No sufficient recorded level strictly before selection')
            if prerequisite is not None and previous[player].get(prerequisite, tick) >= tick:
                raise ValueError('Missing strictly earlier same-player prerequisite')
            previous[player][name] = tick + 1
            path.append(dict(game_event_ordinal=ordinal, selection_loop=tick, hero=hero,
                             purchase=name, source_index=index, catalog_level=required_level,
                             recorded_prior_level=history[end - 1][1], prerequisite=prerequisite))
            event = {**event, 'm_index': index}
        restored.append(event)
    if purchases:
        raise ValueError('Unpaired tracker purchases')
    return restored, path


def recover(source, catalog_file):
    catalog_bytes = Path(catalog_file).read_bytes()
    if sha256(catalog_bytes).hexdigest() != CATALOG_SHA256:
        raise ValueError('Expected the pinned build-41810 historical catalog')
    with Path(source).open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != SOURCE_SHA256:
            raise ValueError('Expected the preserved TEN_GREYMANE replay')
    source_protocol = protocol(41810, local=True)
    with closing(MPQArchive(source)) as archive:
        game_bytes = archive.read_file('replay.game.events')
        tracker_bytes = archive.read_file('replay.tracker.events')
        archive.file.seek(0)
        if file_digest(archive.file, 'sha256').hexdigest() != SOURCE_SHA256:
            raise ValueError('Source replay changed during extraction')
    game = list(decode_events(game_bytes, source_protocol, 'game'))
    for event in game:
        if event['_event'] == SELECTION:
            del event['m_index']
    tracker = decode_events(tracker_bytes, source_protocol, 'tracker')
    restored, path = restore_talent_indices(game, tracker, json.loads(catalog_bytes))
    rebuilt = encode_events(restored, source_protocol, 'game')
    if rebuilt != game_bytes:
        raise ValueError('Reconstructed source game member differs from the original')
    return dict(format='source-talent-path-41810-v1', source_sha256=SOURCE_SHA256,
                catalog_sha256=CATALOG_SHA256, game_member_bytes=len(rebuilt),
                game_member_sha256=sha256(rebuilt).hexdigest(), game_events=len(game),
                game_member_byte_equal=True, source_selections_restored=len(path),
                declared_prerequisites_observed=sum(row['prerequisite'] is not None for row in path),
                source_talent_path=path, target_rule_equivalence_verified=False)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source', required=True, type=Path)
    cli.add_argument('--catalog', required=True, type=Path)
    args = cli.parse_args()
    result = recover(args.source, args.catalog)
    sys.stdout.buffer.write((json.dumps(result, indent=2, sort_keys=True) + '\n').encode('utf-8'))
