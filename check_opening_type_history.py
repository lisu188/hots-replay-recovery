"""Measure tracker-visible opening type changes through loop 64 in TEN and 24 build-98348 recordings."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

import first_sync_game
from camp_owner_wire import HISTORICAL_SCHEMA_SHA, TARGET_SCHEMA_SHA
from mpq_reader import MPQArchive
from opening_unit_radii import check
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol


def observe(path, sha, build):
    check(sha256(path.read_bytes()).hexdigest() == sha, 'Replay hash differs')
    protocol = load_protocol(41810 if build == 41810 else 96477)
    check(protocol.recovery_schema_sha256 == (HISTORICAL_SCHEMA_SHA if build==41810 else TARGET_SCHEMA_SHA),
          'Tracker schema differs')
    with closing(MPQArchive(path)) as archive:
        header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        v = header['m_version']
        check((v['m_build'],v['m_baseBuild'],header['m_dataBuildNum']) == (build,)*3,'Replay build differs')
        data = archive.read_file('replay.tracker.events')
    keys, before = set(), []
    for event in protocol.decode_replay_tracker_events(data):
        loop, kind = event['_gameloop'], event['_eventid']
        if loop > 64:
            break
        if kind in (1,2,4,6):
            tag = (event['m_unitTagIndex'], event['m_unitTagRecycle'])
            if loop == 0 and kind in (1,6):
                check(tag not in keys, 'Duplicate loop-zero birth or init')
                keys.add(tag)
            elif kind == 4:
                before.append(tag)
    else:
        raise ValueError('Tracker ended before the first sync boundary')
    check(bool(keys), 'Missing opening units')
    return Counter(opening_units=len(keys),type_changes=sum(t in keys for t in before),
                   all_type_changes=len(before),recordings=1)


def check_history(source, manifest):
    reference = Path(first_sync_game.__file__).parent/'observations'/'first-sync-game.json'
    pins = {r['replay_sha256'] for r in json.loads(reference.read_bytes())['references']}
    cases = json.loads(manifest.read_bytes())
    check(len(pins) == 24 and pins <= cases.keys(), 'Reference cohort differs')
    original = observe(source,SOURCE,41810)
    target = Counter()
    for sha in sorted(pins):
        entry = cases[sha]
        target.update(observe(Path(entry['path'] if isinstance(entry,dict) else entry),sha,98348))
    return {'through_loop':64, 'original':dict(original), 'target':dict(target),
            'observes_shared_type_pointer_at_first_insertion':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('manifest',type=Path)
    args = parser.parse_args()
    print(json.dumps(check_history(args.source,args.manifest),indent=2))
