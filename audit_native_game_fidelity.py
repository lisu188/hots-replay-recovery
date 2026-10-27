"""Read-only reconstruction audit of original41810 -> existing R8 game values.

This audits the exact existing recipe, including its unproved assumptions. It
never returns converted bytes, writes a replay, or certifies semantic fidelity.
Official schemas and the independent legacy decoder are checked before use;
the candidate side and value serialization use the pinned native codec.
"""
import ast
from collections import Counter, defaultdict
import copy
import hashlib
from pathlib import Path

from native_game_events import Choice, GameEvent, encode_game_events, iter_game_events

SOURCE_GAME_SHA256 = 'ea69dd77edd02f3ed2c42a2def1faab6dc4d0eb46da291c44f76bfb49a65eed6'
R8_GAME_SHA256 = '31df2ab80eeeb56bc543ea0744f75d4d2ec6a5c337b1f38f04ef90d169dab2f0'
SCHEMA_PINS = {
    41810: '879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',
    96477: 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84',
}
FLAG_RECIPE = {0x100: 0x100, 0x10a: 0x10a, 0x10100: 0x8100,
               0x100100: 0x80100, 0x100108: 0x80108,
               0x110108: 0x88108, 0x200100: 0x100100}
PREFIX = 'NNet.Game.'


def _tag(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('invalid source unit tag')
    if value in (0, 0xffffffff):
        return value
    index, recycle = value >> 18, value & ((1 << 18) - 1)
    if index >= 1 << 10:
        raise ValueError('unit tag index cannot fit target layout')
    result = (index << 22) | recycle
    if result in (0, 0xffffffff):
        raise ValueError('unit tag introduces sentinel')
    return result


def _recipe_payload(name, value, counts):
    """Reconstruct recorded R8 assumptions, not an approved general converter."""
    value = copy.deepcopy(value)
    def tag(parent, key):
        before = parent[key]
        if before is None:
            return
        parent[key] = _tag(before)
        counts['unit_tag_references_checked'] += 1
        counts['unit_tag_values_changed'] += parent[key] != before
    if name == PREFIX + 'SUserOptionsEvent':
        for key in ('m_buildNum', 'm_baseBuildNum'):
            if type(value[key]) is not int or value[key] != 41810:
                raise ValueError('unexpected original user-options build')
            value[key] = 98285
            counts['user_option_build_fields_changed'] += 1
    elif name == PREFIX + 'SCmdEvent':
        if 'm_vector' in value:
            raise ValueError('source already has a command vector')
        value['m_vector'] = None
        counts['assumed_absent_command_vectors_added'] += 1
        flags = value['m_cmdFlags']
        if type(flags) is not int or not 0 <= flags < 1 << 26:
            raise ValueError('invalid original command flags')
        value['m_cmdFlags'] = FLAG_RECIPE.get(flags, flags)
        counts['command_flags_changed'] += value['m_cmdFlags'] != flags
        if 'TargetUnit' in value['m_data']:
            tag(value['m_data']['TargetUnit'], 'm_tag')
        tag(value, 'm_otherUnit')
    elif name == PREFIX + 'SCmdUpdateTargetUnitEvent':
        tag(value['m_target'], 'm_tag')
    elif name == PREFIX + 'SUnitClickEvent':
        tag(value, 'm_unitTag')
    elif name == PREFIX + 'SSelectionDeltaEvent':
        tags = value['m_delta']['m_addUnitTags']
        for i in range(len(tags)):
            tag(tags, i)
    elif name == PREFIX + 'STriggerDialogControlEvent':
        data = value['m_eventData']
        if 'MouseButton' in data:
            if set(data) != {'MouseButton'} or type(data['MouseButton']) is not int:
                raise ValueError('unexpected legacy mouse choice')
            value['m_eventData'] = {'MouseEvent': {'m_button': data['MouseButton'], 'm_metaKeyFlags': 0}}
            counts['assumed_zero_mouse_modifier_fields_added'] += 1
    return value


def _anonymous(value, types, type_id, depth=0):
    if depth > 64:
        raise ValueError('projection depth budget')
    kind, args = types[type_id]
    if kind == '_struct':
        if type(value) is not dict or set(value) != {n for n, c, t in args[0]}:
            raise ValueError('projection STRUCT shape')
        return tuple(_anonymous(value[n], types, c, depth + 1) for n, c, t in args[0])
    if kind == '_choice':
        if type(value) is not dict or len(value) != 1:
            raise ValueError('projection CHOICE shape')
        name = next(iter(value))
        pairs = [(tag, c) for tag, (n, c) in args[1].items() if n == name]
        if len(pairs) != 1:
            raise ValueError('projection CHOICE name')
        tag, child = pairs[0]
        return Choice(tag, _anonymous(value[name], types, child, depth + 1))
    if kind == '_optional':
        return None if value is None else _anonymous(value, types, args[0], depth + 1)
    if kind == '_array':
        if type(value) is not list:
            raise ValueError('projection ARRAY type')
        return tuple(_anonymous(v, types, args[1], depth + 1) for v in value)
    return value


def _schema(build):
    from protocol_loader import load_protocol
    module = load_protocol(build)
    raw = Path(module.__file__).read_bytes()
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != SCHEMA_PINS[build]:
        raise ValueError('official schema pin')
    # Use fresh AST literals, not potentially shared mutable module tables.
    tree = ast.parse(raw)
    result = {}
    wanted = {'typeinfos', 'game_event_types', 'svaruint32_typeid', 'replay_userid_typeid', 'game_eventid_typeid'}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    if target.id in result:
                        raise ValueError('duplicate schema assignment')
                    result[target.id] = ast.literal_eval(node.value)
    if set(result) != wanted:
        raise ValueError('incomplete official schema')
    return result


def audit_game_fidelity(source_member, R8_member):
    """Audit only the two exact preserved game members; returns safe aggregates.

    Requires the project's pinned Blizzard/heroprotocol checkout/dependency.
    The old decoder is independent of the candidate native codec. Equal output
    establishes recipe accounting, not the truth of the recipe's assumptions.
    """
    for raw, size, digest in ((source_member, 1146911, SOURCE_GAME_SHA256),
                              (R8_member, 1148436, R8_GAME_SHA256)):
        if type(raw) is not bytes or len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('exact preserved game members required')
    from heroprotocol import decoders
    decoder_raw = Path(decoders.__file__).read_bytes()
    if hashlib.sha256(decoder_raw).hexdigest() != '17bfb926af0f7f79e18f6299dbae50fc2821c53b229235d4f9c857c7ef3e96b1':
        raise ValueError('independent legacy decoder pin')
    old, current = _schema(41810), _schema(96477)
    reader = decoders.BitPackedDecoder(source_member, old['typeinfos'])
    actual = iter(iter_game_events(R8_member))
    counts = Counter()
    flag_pairs = Counter()
    def reconstructed_events():
        while not reader.done():
            index = counts['events']
            delta = reader.instance(old['svaruint32_typeid'])
            user = reader.instance(old['replay_userid_typeid'])
            event_id = reader.instance(old['game_eventid_typeid'])
            if event_id not in old['game_event_types'] or event_id not in current['game_event_types']:
                raise ValueError('unmapped original event ID')
            old_type, name = old['game_event_types'][event_id]
            new_type, new_name = current['game_event_types'][event_id]
            if new_name != name:
                raise ValueError('event name/ID mapping changed')
            payload = reader.instance(old_type)
            reader.byte_align()
            changed = _recipe_payload(name, payload, counts)
            if name == PREFIX + 'SCmdEvent':
                flag_pairs[payload['m_cmdFlags'], changed['m_cmdFlags']] += 1
            expected = GameEvent(next(iter(delta.values())), user['m_userId'], event_id,
                                 _anonymous(changed, current['typeinfos'], new_type))
            try:
                observed = next(actual).event
            except StopIteration:
                raise ValueError('R8 has fewer events') from None
            if expected != observed:
                raise ValueError('unaccounted R8 event difference at index%d' % index)
            counts['events'] += 1
            yield expected
        if next(actual, None) is not None:
            raise ValueError('R8 has additional events')
    rebuilt = encode_game_events(reconstructed_events())
    if rebuilt != R8_member or counts['events'] != 104257:
        raise ValueError('native recipe reconstruction differs')
    by_target = defaultdict(list)
    for (before, after), count in sorted(flag_pairs.items()):
        by_target[after].append({'source_flags': before, 'count': count, 'changed': before != after})
    collisions = [{'R8_flags': target, 'contributors': rows, 'commands': sum(r['count'] for r in rows)}
                  for target, rows in sorted(by_target.items()) if len(rows) > 1]
    return {'format': 'native-source-to-R8-game-fidelity-audit-v1', 'recipe_accounting_passed': True,
            'source_member_sha256': SOURCE_GAME_SHA256, 'R8_member_sha256': R8_GAME_SHA256,
            'schema_SHA256': SCHEMA_PINS, 'counts': dict(sorted(counts.items())),
            'all_event_order_deltas_userids_and_IDs_preserved': True,
            'all_payload_differences_accounted_by_explicit_existing_recipe': True,
            'native_value_writer_reconstructs_whole_R8_member_exactly': True,
            'command_flag_pairs': [{'source_flags': a, 'R8_flags': b, 'count': n} for (a, b), n in sorted(flag_pairs.items())],
            'noninjective_flag_targets': collisions, 'flag_inverse_requires_source_or_per_event_audit': bool(collisions),
            'assumptions_authenticated_as_historical_semantics': False,
            'unproved_recipe_assumptions': ['Historical command-flag bit meanings and untouched16-command case.',
                                          'Absent command vectors and zero mouse modifiers.',
                                          'Runtime unit-instance identities despite recorded index/recycle preservation.'],
            'new_replay_or_member_returned_or_written': False, 'native_target_executed': False,
            'full_upgrade_complete': False}
