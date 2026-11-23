"""Match original Dragon Shire authored camps to the 41810 tracker and capture outcomes."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from xml.etree import ElementTree

from dragon_startup_births import MECHANICS_SHA, region_contains, xy
from encoders import encode_tracker_events
from heroprotocol.versions import protocol41810
from mpq_reader import MPQArchive

SOURCE = 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
MAP = 'e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def typed_data(event, key, name):
    (value,) = [r['m_value'] for r in event[key] if r['m_key'] == name.encode()]
    return value


def unit_key(e):
    return e['m_unitTagIndex'],e['m_unitTagRecycle']


def analyze(replay, old_map, current_library):
    for path, expected in ((replay,SOURCE), (old_map,MAP), (current_library,MECHANICS_SHA)):
        require(sha256(path.read_bytes()).hexdigest() == expected, 'Unexpected input SHA-256')
    with closing(MPQArchive(replay)) as a:
        header = protocol41810.decode_replay_header(a.header['user_data_header']['content'])
        handles=protocol41810.decode_replay_details(a.read_file('replay.details'))['m_cacheHandles']
        require(header['m_version']['m_build']==41810 and handles[-1][8:].hex()==MAP, 'Wrong source')
        wire = a.read_file('replay.tracker.events')
    with closing(MPQArchive(old_map)) as a:
        names = a.read_file('(listfile)').decode().splitlines()
        script_names = [r for r in names if r.lower().endswith('.galaxy')]
        require(script_names == ['MapScript.galaxy'], 'Unexpected packaged Galaxy scripts')
        xml = ElementTree.fromstring(a.read_file('Objects'))
        regions = {int(n.attrib['id']): n for n in ElementTree.fromstring(a.read_file('Regions')).findall('region')}
        preload = a.read_file('Preload.xml')
        script = a.read_file(script_names[0]).decode('utf-8-sig')
    require('include "TriggerLibs/MapMechanicsLib"' in script and b'CampOwnershipFlag' in preload,
            'Historical map metadata')
    old_flags = [n for n in xml.findall('ObjectUnit') if n.attrib['UnitType']=='CampOwnershipFlag']
    sconces = [n for n in xml.findall('ObjectUnit') if n.attrib['UnitType']=='LootBannerSconce']
    points = {int(n.attrib['Id']): xy(n) for n in xml.findall('ObjectPoint')}
    blocks = script.split('lv_junglecamp += 1;')[1:]
    require(len(old_flags) == len(blocks) == 5 and not sconces, 'Stock flags')
    tracker = list(protocol41810.decode_replay_tracker_events(wire))
    require(encode_tracker_events(tracker,protocol41810) == wire, 'Source tracker round-trip')
    statutes = defaultdict(list)
    births = defaultdict(list)
    owners = defaultdict(list)
    for e in tracker:
        if e['_event'].endswith('.SStatGameEvent'):
            statutes[e['m_eventName'].decode()].append(e)
        elif e['_event'].endswith('.SUnitBornEvent'):
            births[e['m_unitTypeName'].decode()].append(e)
        elif e['_event'].endswith('.SUnitOwnerChangeEvent'):
            owners[unit_key(e)].append((e['_gameloop'], e['m_controlPlayerId'],e['m_upkeepPlayerId']))
    (gate,) = statutes['GatesOpen']
    require(len(statutes['JungleCampInit']) == len(blocks), 'Original camp init count')
    camp_keys = {r for r in statutes if 'camp' in r.lower() or 'merc' in r.lower() or 'jungle' in r.lower()}
    camps = []
    used_flags = set()
    seen_laner_ids = set()
    captains = [points[int(re.findall(r'lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\)',b)[0])]
                for b in blocks]
    def near(point, index):
        distances=[(x-point[0])**2+(y-point[1])**2 for x,y in captains]
        smallest=min(distances)
        return distances.count(smallest)==1 and distances[index-1]==smallest and smallest<=8**2

    for i,block in enumerate(blocks,1):
        (point,) = re.findall(r'lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\)',block)
        (region,) = re.findall(r'lv_mapDataDefenderLeashRegion = RegionFromId\((\d+)\)',block)
        (kind,) = re.findall(r'lv_mapDataCampDefenderType = libMapM_ge_JungleCampDefenderTypes_(\w+);',block)
        pos, area = points[int(point)], regions[int(region)]
        (flag,) = [f for f in old_flags if near(xy(f),i)]
        try:
            flag_region='inside' if region_contains(area,xy(flag)) else 'outside'
        except ValueError as error:
            if str(error)!='Ambiguous diamond geometry': raise
            flag_region='uncertain_diamond_shape'
        require(flag.attrib['Id'] not in used_flags, 'Flag shared between camps')
        used_flags.add(flag.attrib['Id'])
        def unit_at(name,pos):
            (unit,) = [e for e in births[name] if (e['m_x'],e['m_y']) == tuple(map(math.floor,pos))]
            return unit
        flag_event = unit_at('CampOwnershipFlag',xy(flag))
        beacon = unit_at('TownMercCampCaptureBeacon',pos)
        icon = unit_at('JungleCampIconUnitTeamColor',pos)
        (init,)=[e for e in statutes['JungleCampInit'] if typed_data(e,'m_intData','CampID')==i]
        require(tuple(typed_data(init,'m_fixedData',f'Position{k}') for k in 'XY')==tuple(v*4096 for v in pos),
                'CampID does not match map point')
        require(flag_event['_gameloop'] == beacon['_gameloop'] == init['_gameloop'] == 0, 'Startup timing')
        changes=owners[unit_key(flag_event)]
        require((icon['_gameloop'],15,15) in changes, 'First hostile owner transition')
        defenders = [e for n,es in births.items() if n.startswith('MercDefender') for e in es
                     if near((e['m_x'],e['m_y']),i)]
        initial_loop=min(e['_gameloop'] for e in defenders)
        first=Counter(e['m_unitTypeName'].decode() for e in defenders if e['_gameloop']==initial_loop)
        captured = []
        for e in statutes['JungleCampCapture']:
            if typed_data(e,'m_intData','CampID') != i:
                continue
            loop=e['_gameloop']
            raw_team=typed_data(e,'m_fixedData','TeamID')
            require(raw_team in (4096,8192),'Unexpected TeamID')
            team=raw_team//4096
            owner=10+team
            stat_type=typed_data(e,'m_stringData','CampType').decode()
            require(stat_type == {'SiegeGiants':'Siege Camp','Knights':'Bruiser Camp'}[kind], 'CampType')
            require((loop,owner,owner) in changes and (loop,owner,owner) in owners[unit_key(icon)],
                    'Captured flag/icon owner mismatch')
            owner_loops = [t for t,c,u in owners[unit_key(beacon)] if c==u==owner and t<=loop]
            beacon_delta=loop-max(owner_loops)
            laners = [u for n,es in births.items() if n.startswith('MercLaner') for u in es if u['_gameloop']==loop]
            require(all(u['m_controlPlayerId']==u['m_upkeepPlayerId']==owner for u in laners), 'Laner team')
            require(all(near((u['m_x'],u['m_y']),i) for u in laners), 'Laner outside this camp')
            require(not seen_laner_ids.intersection(unit_key(u) for u in laners), 'Laner double attribution')
            seen_laner_ids.update(unit_key(u) for u in laners)
            composition=Counter(u['m_unitTypeName'].decode() for u in laners)
            expected_comp=({'MercLanerSiegeGiant':2} if kind=='SiegeGiants' else
                           {'MercLanerMeleeKnight':3,'MercLanerRangedMage':1})
            require(composition==expected_comp, 'Unexpected capture wave')
            captured.append(dict(loop=loop, team=team, beacon_owner_change_loops_before=beacon_delta))
        camps.append(dict(id=i,kind=kind,point_id=int(point),region_id=int(region),authored_flag_id=int(flag.attrib['Id']),
                          flag_region_test=flag_region,
                          original_init_loop=init['_gameloop'], flag_tag=list(unit_key(flag_event)),
                          capture_beacon_tag=list(unit_key(beacon)), icon_birth_loop=icon['_gameloop'],
                          first_defenders_loop=initial_loop, first_defender_composition=dict(sorted(first.items())),
                          capture_events=captured))
    require(len(seen_laner_ids) == sum(len(es) for k,es in births.items() if k.startswith('MercLaner')),
            'Unaccounted laner birth')
    return dict(source_replay_sha256=SOURCE, source_map_sha256=MAP, current_mechanics_sha256=MECHANICS_SHA,
                source_tracker_bytes=len(wire), source_tracker_sha256=sha256(wire).hexdigest(),
                source_tracker_reencoded_byte_equal=True, original_map_galaxy_members=script_names,
                historical_map_includes_external_map_mechanics=True, original_preloads_legacy_flag=True,
                exact_historical_library_implementation_recovered=False, gates_open_loop=gate['_gameloop'],
                camp_named_stats={k:len(statutes[k]) for k in sorted(camp_keys)}, all_laner_births=len(seen_laner_ids),
                source_camps=camps, notes='At each recorded capture the legacy flag and icon both change to team '
                'owner 11/12; every captured wave is born within eight map units of its unique nearest camp '
                'point, on that loop, with that owner.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('replay','map','current-library','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    data=(json.dumps(analyze(args.replay,args.map,args.current_library),indent=2)+'\n').encode()
    if args.output.exists():
        require(args.output.read_bytes()==data, 'Existing output differs')
    else:
        with args.output.open('xb') as stream: stream.write(data)
    print(len(data), sha256(data).hexdigest())


if __name__=='__main__':
    main()
