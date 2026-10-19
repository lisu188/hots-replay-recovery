"""Bounded original/R8 source lifecycle checks; emit public unit types/counts.

Archives are read into RAM once, never changed. No messages, player identities,
packed tags, positions, user IDs or complete events are written.
"""
from collections import Counter, defaultdict
from io import BytesIO
import itertools
import json
from pathlib import Path
import hashlib
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0] = [str(REPO), str(WORK/'heroprotocol'), str(WORK/'python-deps')]
from catalog_diagnostics import UnitTimeline, link_fields
from command_identity_audit import analyse as command_contexts
from encoders import encode_tracker_events
from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import native
from repair_unit_tags import references

NAMES = ('AbathurEvolvedMonstrosity', 'NovaHoloCloneCloaked', 'TownCannonTowerL2Standalone',
         'TownCannonTowerDead', 'TownCannonTowerL2', 'TownCannonTowerL3')
PREFIX = 'NNet.Replay.Tracker.'
ORIGINAL = WORK/'TEN_GREYMANE_source_41810.StormReplay'
R8 = WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay'
ORIGINAL_SHA = 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
R8_SHA = '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
SCHEMAS = {41810:'879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',
           96477:'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'}
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_source(path, expected):
    require(not path.is_symlink(), 'Replay symlink refused')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(1 <= before.st_size <= 3*1024*1024, 'Replay source size exceeds cap')
        raw = stream.read(before.st_size+1)
        after = os.fstat(stream.fileno())
    require(len(raw) == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
            and sha(raw) == expected, 'Replay digest/stat differs')
    return raw, before


class RAMArchive(MPQArchive):
    def __init__(self, raw):
        self.file = BytesIO(raw)
        self.header = self.read_header()
        self.hash_table = self.read_table('hash')
        self.block_table = self.read_table('block')


def occurrence(loops):
    return {'count': len(loops), 'first_gameloop': min(loops) if loops else None,
            'last_gameloop': max(loops) if loops else None}


def summarize(game, tracker, shift):
    timeline = UnitTimeline(tracker)
    events = {name: defaultdict(list) for name in NAMES}
    tags = {name: set() for name in NAMES}
    transitions = {name: Counter() for name in NAMES}
    states = {}
    for row in tracker:
        kind = row['_event']
        if kind not in {PREFIX+name for name in ('SUnitBornEvent','SUnitInitEvent','SUnitDiedEvent','SUnitRevivedEvent','SUnitTypeChangeEvent')}:
            continue
        pair = (row['m_unitTagIndex'],row['m_unitTagRecycle'])
        previous, alive = states.get(pair, (None, False))
        current = previous
        loop = row['_gameloop']
        if 'm_unitTypeName' in row:
            current = row['m_unitTypeName'].decode('ascii')
            if previous in NAMES and current != previous:
                events[previous]['type_change_away'].append(loop)
                transitions[previous][current] += 1
        if kind in (PREFIX+'SUnitBornEvent',PREFIX+'SUnitInitEvent',PREFIX+'SUnitTypeChangeEvent'):
            if current in NAMES:
                events[current][kind[len(PREFIX):]].append(loop)
                tags[current].add(pair)
        if kind in (PREFIX+'SUnitBornEvent',PREFIX+'SUnitInitEvent',PREFIX+'SUnitRevivedEvent'):
            alive = True
            if current in NAMES and kind == PREFIX+'SUnitRevivedEvent':
                events[current]['SUnitRevivedEvent'].append(loop)
                tags[current].add(pair)
        elif kind == PREFIX+'SUnitDiedEvent':
            if current in NAMES:
                events[current]['SUnitDiedEvent_while_last_recorded_type'].append(loop)
            alive = False
        states[pair] = (current, alive)
    classified_links = {name: defaultdict(list) for name in NAMES}
    link_sets = {name: Counter() for name in NAMES}
    for field in link_fields(game):
        matches = [timeline.lookup(tag, field.gameloop, shift) for tag in field.tags]
        names = {name for name, reason in matches if reason == 'known_alive'}
        if len(names) != 1 or any(reason != 'known_alive' for name, reason in matches):
            continue
        name = next(iter(names))
        if name not in NAMES:
            continue
        event = game[field.event_index]['_event'].split('.')[-1]
        classified_links[name][event].append(field.gameloop)
        link_sets[name][field.link] += 1
    tag_refs = {name: defaultdict(list) for name in NAMES}
    for index, path, parent, key, tag in references(game):
        event = game[index]
        name, reason = timeline.lookup(tag, event['_gameloop'], shift)
        if name in NAMES and reason == 'known_alive':
            tag_refs[name][event['_event'].split('.')[-1]].append(event['_gameloop'])
    context_summary, trace = command_contexts(game, tracker, shift)
    require(context_summary['commands'] == 4558, 'Frozen command count differs')
    selected = {name: [] for name in NAMES}
    for row in trace:
        name = row['selected_unit_type_candidate']
        if name in NAMES:
            selected[name].append(row['gameloop'])
    result = []
    for name in NAMES:
        result.append({'unit_type': name, 'distinct_recorded_unit_lifecycles': len(tags[name]),
            'tracker_lifecycle_events': {kind: occurrence(loops) for kind, loops in sorted(events[name].items())},
            'recorded_type_changes_away_to': dict(sorted(transitions[name].items())),
            'catalog_link_fields_by_game_event': {kind: occurrence(loops) for kind, loops in sorted(classified_links[name].items())},
            'observed_source_catalog_link_counts': dict(sorted(link_sets[name].items())),
            'known_alive_game_tag_references_by_event': {kind: occurrence(loops) for kind, loops in sorted(tag_refs[name].items())},
            'commands_with_single_selected_type_agreeing_under_both_masks': occurrence(selected[name]),
            'selected_context_proves_executing_caster': False})
    return result


def analyze():
    raw_original, original_stat = read_source(ORIGINAL, ORIGINAL_SHA)
    raw_r8, r8_stat = read_source(R8, R8_SHA)
    total_disk = len(raw_original)+len(raw_r8)
    require(total_disk+len(raw_original) <= 4*1024*1024, 'Aggregate replay read budget would exceed4MiB')
    results = []
    for label, raw, version, shift, build in (('original41810',raw_original,41810,18,41810),('R8',raw_r8,96477,22,98285)):
        protocol = load_protocol(version)
        require(protocol.recovery_schema_sha256 == SCHEMAS[version], 'Pinned official schema differs')
        archive = RAMArchive(raw)
        try:
            header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
            require(header['m_version']['m_build'] == build, 'Executable build differs')
            streams, stream_facts = {}, {}
            for kind, cap in (('game',150000),('tracker',10000)):
                block = archive.get_hash_table_entry('replay.'+kind+'.events')
                require(block is not None and archive.block_table[block.block_table_index].size <= 8*1024*1024,
                        'Decoded stream size exceeds bound')
                payload = archive.read_file('replay.'+kind+'.events')
                decoded = list(itertools.islice(decode_events(payload,protocol,kind),cap+1))
                require(len(decoded) <= cap, 'Decoded event budget exceeded')
                encoded = encode_tracker_events(decoded,protocol) if kind == 'tracker' else encode_events(decoded,protocol,kind)
                require(encoded == payload, 'Observed event stream roundtrip differs')
                official = getattr(protocol,'decode_replay_'+kind+'_events')(payload)
                sentinel = object()
                require(all(first is not sentinel and second is not sentinel and native(first) == native(second)
                            for first,second in itertools.zip_longest(decoded,official,fillvalue=sentinel)),
                        'Official/semantic decoded payload differs')
                streams[kind] = decoded
                stream_facts[kind] = {'events': len(decoded), 'sha256': sha(payload),
                                     'byte_roundtrip_exact': True, 'official_semantic_equal': True}
            require(len(streams['game']) == 104257 and len(streams['tracker']) == 6614, 'Frozen event counts differ')
            facts = summarize(streams['game'], streams['tracker'], shift)
            results.append({'id':label,'replay_sha256':sha(raw),'declared_build':build,
                'canonical_official_schema_sha256':SCHEMAS[version],'packed_tag_shift':shift,
                'streams':stream_facts,'unit_type_observations':facts})
        finally:
            archive.close()
    require(results[0]['unit_type_observations'] == results[1]['unit_type_observations'],
            'Original/R8 targeted type lifecycle/reference statistics differ')
    checked_original, _ = read_source(ORIGINAL, ORIGINAL_SHA)
    total_disk += len(checked_original)
    require(checked_original == raw_original and sha(raw_r8) == R8_SHA, 'Source/R8 RAM guard differs')
    final_r8 = R8.stat()
    require(final_r8.st_size == r8_stat.st_size and final_r8.st_mtime_ns == r8_stat.st_mtime_ns,
            'R8 disk stat changed during analysis')
    sources = {}
    for name in ('catalog_diagnostics.py','command_identity_audit.py','repair_unit_tags.py','migrate_replay.py','encoders.py','protocol_loader.py'):
        body = (REPO/name).read_bytes()
        require(len(body) <= 256*1024, 'Source provenance body cap exceeded')
        sources[name] = sha(body)
    sources['producer'] = sha(Path(__file__).read_bytes())
    return {'format':'hots-original-R8-targeted-unobserved-unit-lifecycle-review-v1',
        'results':results,'targeted_original_R8_statistics_equal':True,'source_hashes':sources,
        'replay_disk_bytes_read':total_disk,'replay_disk_byte_cap':4*1024*1024,
        'original_full_disk_SHA256_before_and_after':True,
        'R8_full_disk_SHA256_read_once_then_unchanged_stat_and_RAM_SHA256_after':True,
        'R8_second_disk_SHA256_reread_performed':False,
        'messages_PE_headers_dumps_network_reads':0,'raw_identity_tags_positions_player_or_event_values_emitted':False,
        'replay_or_catalog_modified':False,'current_target_links_or_aliases_guessed':False,
        'limits':['Recorded tracker names and known-alive references establish source usage only, not current native catalog identities.',
            'Command target snapshots and selected-unit context are distinguished; selection is not proof of the executing caster.',
            'A source old-link collision across tracker names does not authorize collapsing those names or assigning one current global replacement.']}


if __name__ == '__main__':
    output = HERE/'source-unobserved-unit-lifecycles.json'
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refuse existing lifecycle report')
    data = (json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    if len(data) > 64*1024:
        raise ValueError('Lifecycle report exceeds cap')
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
