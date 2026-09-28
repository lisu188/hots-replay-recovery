import argparse
import copy
import hashlib
import json
from pathlib import Path

from mpq_reader import MPQArchive
from mpq_patch import patch_replay
from encoders import encode_game_events, encode_header, encode_initdata
import protocol41810 as source_protocol
import protocol43905 as target_protocol

TARGET_BUILD=43905

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('-o','--output',default='work/TEN_GREYMANE_43905.StormReplay')
    args=ap.parse_args()
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    archive=MPQArchive(args.source)

    header=copy.deepcopy(source_protocol.decode_replay_header(archive.header['user_data_header']['content']))
    header['m_version']['m_build']=TARGET_BUILD
    header['m_version']['m_baseBuild']=TARGET_BUILD
    header['m_dataBuildNum']=TARGET_BUILD

    initdata=copy.deepcopy(source_protocol.decode_replay_initdata(archive.read_file('replay.initData')))
    opts=initdata['m_syncLobbyState']['m_gameDescription']['m_gameOptions']
    opts['m_ammId']=None

    events=list(source_protocol.decode_replay_game_events(archive.read_file('replay.game.events')))
    user_options=0
    for event in events:
        if event['_event']=='NNet.Game.SUserOptionsEvent':
            event['m_baseBuildNum']=TARGET_BUILD
            event['m_buildNum']=TARGET_BUILD
            user_options+=1
        if event['_event']=='NNet.Game.SCmdEvent' and event['m_cmdFlags'] >= (1<<24):
            raise ValueError(f'SCmdEvent at loop {event["_gameloop"]} cannot fit build 43905 command flags')

    header_raw=encode_header(header,target_protocol)
    init_raw=encode_initdata(initdata,target_protocol)
    game_raw=encode_game_events(events,target_protocol)

    report=patch_replay(args.source,out,header_raw,{
        'replay.initData':init_raw,
        'replay.game.events':game_raw,
    })

    check=MPQArchive(out)
    decoded_header=target_protocol.decode_replay_header(check.header['user_data_header']['content'])
    decoded_init=target_protocol.decode_replay_initdata(check.read_file('replay.initData'))
    decoded_events=list(target_protocol.decode_replay_game_events(check.read_file('replay.game.events')))
    if decoded_header != header: raise AssertionError('header encode/decode mismatch')
    if decoded_init != initdata: raise AssertionError('initData encode/decode mismatch')
    if decoded_events != events: raise AssertionError('game events encode/decode mismatch')

    result={
        'target_build':TARGET_BUILD,
        'output':str(out),
        'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
        'size':out.stat().st_size,
        'game_events':len(events),
        'user_options_build_fields_updated':user_options,
        'roundtrip_validated':True,
        'mpq_blocks':report,
        'known_limitations':[
            'ngdpRootKey and fixedFileHash still identify the original build-41810 game data',
            'major/minor/revision version fields are intentionally unchanged pending extraction from an authentic build-43905 replay',
            'opaque replay.sync/replay.server.battlelobby/replay.resumable streams are preserved byte-for-byte',
        ],
    }
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
