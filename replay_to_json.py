import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from mpq_reader import MPQArchive
import protocol41810 as protocol41810
import protocol43905 as protocol43905

KNOWN_FILES = [
    '(listfile)',
    'replay.details',
    'replay.initData',
    'replay.attributes.events',
    'replay.game.events',
    'replay.message.events',
    'replay.tracker.events',
    'replay.server.battlelobby',
    'replay.smartcam.events',
    'replay.sync.events',
    'replay.resumable.events',
    'replay.load.info',
]

def normalize(v):
    if isinstance(v, bytes):
        try:
            s=v.decode('utf-8')
            if all(c.isprintable() or c in '\r\n\t' for c in s):
                return s
        except UnicodeDecodeError:
            pass
        return {'$bytes_hex': v.hex()}
    if isinstance(v, dict):
        return {str(k): normalize(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)):
        return [normalize(x) for x in v]
    return v

def dump_json(path,obj):
    path.write_text(json.dumps(normalize(obj),ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def dump_jsonl(path,events):
    counter=Counter(); count=0; first=None; last=None
    with path.open('w',encoding='utf-8',newline='\n') as f:
        for event in events:
            n=normalize(event)
            f.write(json.dumps(n,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
            counter[event.get('_event','?')]+=1; count+=1
            if first is None: first=event.get('_gameloop')
            last=event.get('_gameloop')
    return {'count':count,'first_gameloop':first,'last_gameloop':last,'types':dict(sorted(counter.items()))}

def sha256(data): return hashlib.sha256(data).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('replay')
    ap.add_argument('-o','--output',default='decoded/41810')
    args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    replay_path=Path(args.replay)
    archive=MPQArchive(replay_path)

    user_data=archive.header.get('user_data_header',{}).get('content',b'')
    header=protocol41810.decode_replay_header(user_data)
    base_build=header['m_version']['m_baseBuild']
    protocols={41810:protocol41810,43905:protocol43905}
    protocol=protocols.get(base_build)
    if protocol is None:
        raise ValueError(f'Unsupported replay protocol build {base_build}')
    header=protocol.decode_replay_header(user_data)
    details=protocol.decode_replay_details(archive.read_file('replay.details'))
    initdata=protocol.decode_replay_initdata(archive.read_file('replay.initData'))
    attributes=protocol.decode_replay_attributes_events(archive.read_file('replay.attributes.events'))

    dump_json(out/'header.json',header)
    dump_json(out/'details.json',details)
    dump_json(out/'initData.json',initdata)
    dump_json(out/'attributes.events.json',attributes)

    game_stats=dump_jsonl(out/'game.events.jsonl',protocol.decode_replay_game_events(archive.read_file('replay.game.events')))
    message_stats=dump_jsonl(out/'message.events.jsonl',protocol.decode_replay_message_events(archive.read_file('replay.message.events')))
    tracker_stats=dump_jsonl(out/'tracker.events.jsonl',protocol.decode_replay_tracker_events(archive.read_file('replay.tracker.events')))

    files=[]
    listfile=archive.read_file('(listfile)')
    names=[]
    if listfile:
        names=[x.decode('utf-8','replace') for x in listfile.splitlines()]
    for n in dict.fromkeys(names+KNOWN_FILES):
        data=archive.read_file(n)
        if data is not None:
            files.append({'name':n,'size':len(data),'sha256':sha256(data)})

    manifest={
        'format':'hots-replay-json-v1',
        'source':{'name':replay_path.name,'size':replay_path.stat().st_size,'sha256':sha256(replay_path.read_bytes())},
        'protocol_build':header['m_version']['m_baseBuild'],
        'archive':{
            'mpq_offset':archive.header['offset'],
            'format_version':archive.header['format_version'],
            'sector_size_shift':archive.header['sector_size_shift'],
            'files':files,
        },
        'streams':{'game':game_stats,'message':message_stats,'tracker':tracker_stats},
    }
    dump_json(out/'manifest.json',manifest)
    print(json.dumps(manifest['streams'],indent=2))

if __name__=='__main__': main()
