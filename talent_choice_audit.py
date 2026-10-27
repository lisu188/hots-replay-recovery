"""Read-only, fixed-offset talent observations from already decoded events.

Input decoding/build provenance is the caller's responsibility. These joins
describe recorded observations; they do not define talent tiers, establish
causality, authorize index migration, or prove rule/playback equivalence.
Only aggregate hero/talent identifiers are returned, never player identities.
"""

from collections import Counter, defaultdict
import re

SELECTION = 'NNet.Game.SHeroTalentTreeSelectedEvent'
SETUP = 'NNet.Replay.Tracker.SPlayerSetupEvent'
STAT = 'NNet.Replay.Tracker.SStatGameEvent'


def _uint(value, label, positive=False):
    if type(value) is not int or not int(positive) <= value <= 0xffffffff:
        raise ValueError('invalid ' + label)
    return value


def _identifier(value):
    if type(value) is bytes:
        try:
            value = value.decode('ascii')
        except UnicodeDecodeError:
            raise ValueError('invalid hero/talent identifier') from None
    if type(value) is not str or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,255}', value) is None:
        raise ValueError('invalid hero/talent identifier')
    return value


def _fields(event, name):
    result = {}
    for item in event.get(name) or []:
        key = item['m_key']
        if key in result:
            raise ValueError('duplicate tracker stat key')
        result[key] = item['m_value']
    return result


def audit_talent_choices(game_events, tracker_events):
    """Observe unique same-player purchases exactly one loop after selection.

    Repeated keys on either side remain unpaired. User/player setup must be
    explicit and one-to-one. A stable Hero identifier must have been recorded
    by selection time. No nearest-time, user+1, array-order or tier inference.
    Irrelevant decoded events are ignored. Inputs are never modified.
    """
    setup, player_users, heroes = {}, {}, {}
    purchases = []
    for event in tracker_events:
        kind = event['_event']
        if kind == SETUP:
            user = event.get('m_userId')
            if user is None:
                continue
            user = _uint(user, 'user ID')
            player = _uint(event['m_playerId'], 'player ID', positive=True)
            tick = _uint(event['_gameloop'], 'setup loop')
            if user in setup or player in player_users:
                raise ValueError('ambiguous user/player setup')
            setup[user], player_users[player] = (player, tick), user
        elif kind == STAT and event['m_eventName'] in (b'PlayerSpawned', b'TalentChosen'):
            integers, strings = _fields(event, 'm_intData'), _fields(event, 'm_stringData')
            player = _uint(integers[b'PlayerID'], 'player ID', positive=True)
            tick = _uint(event['_gameloop'], 'stat loop')
            if event['m_eventName'] == b'PlayerSpawned':
                hero = _identifier(strings[b'Hero'])
                if player in heroes and heroes[player][0] != hero:
                    raise ValueError('conflicting recorded hero identity')
                previous = heroes.get(player, (hero, tick))[1]
                heroes[player] = (hero, min(previous, tick))
            else:
                purchases.append((player, tick, _identifier(strings[b'PurchaseName'])))

    selections, unmapped, missing_hero = [], 0, 0
    for event in game_events:
        if event['_event'] != SELECTION:
            continue
        payload = {key: value for key, value in event.items() if not key.startswith('_')}
        if set(payload) != {'m_index'}:
            raise ValueError('unexpected talent selection payload')
        index = _uint(payload['m_index'], 'talent index')
        tick = _uint(event['_gameloop'], 'selection loop')
        user = _uint(event['_userid']['m_userId'], 'user ID')
        if user not in setup or setup[user][1] > tick:
            unmapped += 1
            continue
        player = setup[user][0]
        hero = heroes.get(player)
        if hero is None or hero[1] > tick:
            missing_hero += 1
            hero = None
        selections.append((player, tick, index, hero[0] if hero else None))

    selection_counts = Counter((player, tick) for player, tick, _, _ in selections)
    by_purchase = defaultdict(list)
    for position, (player, tick, name) in enumerate(purchases):
        by_purchase[player, tick].append((position, name))
    observations, used, paired = Counter(), set(), 0
    for player, tick, index, hero in selections:
        candidates = by_purchase.get((player, tick + 1), ())
        if hero is not None and selection_counts[player, tick] == 1 and len(candidates) == 1:
            position, name = candidates[0]
            used.add(position)
            paired += 1
            observations[hero, index, name] += 1
    return {
        'format': 'fixed-one-loop-talent-observations-v1',
        'selection_events': len(selections) + unmapped,
        'selection_events_user_unmapped': unmapped,
        'mapped_selections_without_prior_hero': missing_hero,
        'tracker_purchase_events': len(purchases),
        'unique_one_loop_pairs': paired,
        'unpaired_selection_events': len(selections) + unmapped - paired,
        'unpaired_tracker_purchases': len(purchases) - len(used),
        'fixed_offset_single_candidate_counts': {
            str(offset): sum(len(by_purchase.get((player, tick + offset), ())) == 1
                             for player, tick, _, _ in selections)
            for offset in range(-2, 3)
        },
        'observations': [
            {'hero_id': hero, 'index': index, 'purchase_name': name, 'count': count}
            for (hero, index, name), count in sorted(observations.items())
        ],
        'index_semantics_or_rule_equivalence_proven': False,
        'replay_or_sync_written': False,
    }


def compare_observed_names(source, target):
    """Compare aggregate name sets only where hero and numeric index overlap.

    Reports unequal strings, not removed talents or a safe replacement index.
    Map, mod and build context must remain attached by the caller.
    """
    def table(report):
        result = defaultdict(set)
        for row in report['observations']:
            result[row['hero_id'], row['index']].add(row['purchase_name'])
        return result
    old, new = table(source), table(target)
    return [
        {'hero_id': hero, 'index': index,
         'source_purchase_names': sorted(old[hero, index]),
         'target_purchase_names': sorted(new[hero, index]),
         'name_sets_equal': old[hero, index] == new[hero, index]}
        for hero, index in sorted(old.keys() & new.keys())
    ]
