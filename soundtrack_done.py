"""Project TEN's map-intro completion payload with two non-Dragon catalog anchors."""

import json
import re
from contextlib import closing
from hashlib import sha256
from xml.etree import ElementTree

from encoders import encode_game_events as named_encode
from first_sync_game import game
from hero_revive_wire import GATE_MAP
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE


DRAGON = 'MX_Dragonshire_Intro'
SKY = 'MX_SkyTemple_Intro'
CURSED = 'MX_RavensCourt_Intro'
SKY_MAP = '889da151b127b6b5091a26c0395b7787a74cd3f4dea69521512cf027129a009e'
CURSED_MAP = '7751c274aa96c7b58e89c757eeb89e05f28e5c369e463ec6d51bf172681bd3a9'
STOCK = 'f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f'
OLD = 'e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250'
NAME = 'NNet.Game.STriggerSoundtrackDoneEvent'
EVIDENCE = '04a419ae2fed1c29a1a8a7c40d7f7471417a0c585aa3b95eae30e98254b7da65'
PINS = ('6a1d9c02750d0085e20485e26c9df29b22bb4543407eb4117638c9add12b8bdd',
        '932224e3de535d1c316af10e3de92dc722419c74de1cf342b05de2b8a543b1b0',
        '15b6a50e5f1cf96b2bc4b19999d3f5f51171421f07689d4e64cb2973825126ea')
MUSIC = {'MusicArray','IntroMusic','PostGameMusic','CreditsMusic','MatchmakingMusic','BrawlMatchmakingMusic',
         'BrawlMatchFoundMusic','LootScreenMusic','LoopAmbience','ObserverSoundtrack'}


def intro(path, digest):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Unexpected map package')
    with closing(MPQArchive(path)) as archive:
        script = read_member(archive, 'MapScript.galaxy')
    names = re.findall(rb'(?m)^\s*libCore_gv_mAPMapSoundtrack\[0\] = "([A-Za-z0-9_]+)";', script)
    if len(names) != 1:
        raise ValueError('Expected one explicit opening soundtrack')
    return names[0].decode('ascii')


def catalog_models(core, ui, heroes):
    """Relative first appearances in typed fields of three known assets, with two simpler rivals."""
    roots = []
    for path, digest in zip((core,ui,heroes), PINS, strict=True):
        data = path.read_bytes()
        if sha256(data).hexdigest() != digest:
            raise ValueError('Wrong build-98348 catalog asset')
        roots.append(ElementTree.fromstring(data))
    out = {}
    for mode in ('declarations', 'declarations_next', 'ui_declarations_next'):
        names = {}
        def add(value):
            if value:
                names.setdefault(value, len(names))
        for node in roots[0].findall('CSoundtrack'):
            add(node.get('id'))
        if mode == 'ui_declarations_next':
            for node in roots[1].findall('./CGameUI/*'):
                if node.tag in MUSIC:
                    add(node.get('value'))
        for node in roots[2].findall('CSoundtrack'):
            add(node.get('id'))
            if mode != 'declarations':
                for link in node.findall('Next'):
                    add(link.get('value'))
        out[mode] = names
    return out


def observe(path, digest, build):
    protocol, raw = game(path,digest,build)
    with closing(MPQArchive(path)) as archive:
        map_digest = protocol.decode_replay_details(archive.read_file('replay.details'))['m_cacheHandles'][-1][8:].hex()
    rows = []
    offset = previous = 0
    for ordinal,e in enumerate(protocol.decode_replay_game_events(raw)):
        tick = e['_gameloop']
        size, rem = divmod(e['_bits'],8)
        if rem or not size or tick < previous:
            raise ValueError('Invalid physical event')
        if e['_eventid'] == 64:
            if e['_event'] != NAME or set(k for k in e if not k.startswith('_')) != {'m_soundtrack'}:
                raise ValueError('Event 64 changed')
            delta, user, word = tick-previous, e['_userid']['m_userId'], e['m_soundtrack']
            frame = raw[offset:offset+size]
            if named_encode([{**e, '_gameloop':delta}], protocol) != frame:
                raise ValueError('Schema disagrees with physical frame')
            if build == 98348:
                native = GameEvent(delta,user,64,(word,))
                if encode_game_events([native]) != frame or next(iter_game_events(frame)).event != native:
                    raise ValueError('Native codec disagrees with physical frame')
            rows.append((ordinal,tick,delta,user,word))
        previous,offset=tick,offset+size
    if offset != len(raw) or not rows:
        raise ValueError('Missing soundtrack completions or incomplete recording')
    return dict(sha256=digest,build=build,map=map_digest,rows=rows)


def fit(models, anchor_assets, recordings):
    """Compute two cross-map predictions for the Dragon role without using Dragon recordings."""
    anchors = {}
    for role, map_id in ((SKY,SKY_MAP),(CURSED,CURSED_MAP)):
        if intro(anchor_assets[map_id],map_id) != role:
            raise ValueError('Wrong map role')
        words = {row[4] for r in recordings if r['map']==map_id and r['build']==98348 for row in r['rows']}
        if len(words) != 1:
            raise ValueError('Anchor unavailable or ambiguous')
        anchors[role] = words.pop()
    predictions = {mode:{role:word + pos[DRAGON]-pos[role] for role,word in anchors.items()}
                   for mode,pos in models.items()}
    selected = set(predictions['ui_declarations_next'].values())
    if len(selected) != 1:
        raise ValueError('Independent map anchors disagree')
    return selected.pop(), predictions


def project_rows(source_recording, source_map, gate_map, word):
    if (source_recording['sha256']!=SOURCE or source_recording['build']!=41810 or source_recording['map']!=OLD
        or intro(source_map,OLD)!=DRAGON or intro(gate_map,GATE_MAP)!=DRAGON or not 0<=word<65535):
        raise ValueError('Unexpected TEN soundtrack inputs')
    protocol=target_protocol()
    records=[]
    frames=bytearray()
    for ord_,tick,delta,user,original in source_recording['rows']:
        if original != 96:
            raise ValueError('Unexpected source soundtrack')
        named=dict(_event=NAME,_eventid=64,_gameloop=tick,_userid={'m_userId':user},m_soundtrack=word)
        native=GameEvent(delta,user,64,(word,))
        frame=encode_game_events([native])
        if named_encode([{**named,'_gameloop':delta}],protocol)!=frame or next(iter_game_events(frame)).event!=native:
            raise ValueError('Target encoders disagree')
        frames.extend(frame)
        records.append((ord_,named))
    return records, bytes(frames)


def verified_rows(source, source_map, gate_map, evidence):
    """Rebuild source rows under the two-map calibration and its recorded scheduling condition."""
    receipt = json.loads(evidence.read_bytes())
    digest = sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if digest != EVIDENCE:
        raise ValueError('Unexpected soundtrack calibration receipt')
    word = receipt['target_word']
    rows, frames = project_rows(observe(source,SOURCE,41810), source_map, gate_map, word)
    ordinals = [i for i,_ in rows]
    if (ordinals != receipt['ten_original_ordinals'] or len(set(ordinals))!=len(ordinals)
            or sha256(frames).hexdigest()!=receipt['sparse_sha256']):
        raise ValueError('Soundtrack ordinal list or conditional frame stream changed')
    return rows
