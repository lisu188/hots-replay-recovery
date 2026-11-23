"""Measure physical icon and flag tracker rows around Dragon Shire camp capture statistics."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree
import json
import re

from camp_owner_wire import FIELDS, capture_stats, frame_bytes, read_tracker
from first_sound_timing import verify_manifest
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE, MAP
from opening_sound_roles import STOCK


def need(check, message):
    if not check: raise ValueError(message)


def locations(path, build):
    need(sha256(path.read_bytes()).hexdigest()=={41810:MAP,98348:STOCK}[build],"Wrong map")
    banner_type = {41810:b"CampOwnershipFlag",98348:b"LootBannerSconce"}[build]
    with closing(MPQArchive(path)) as archive:
        objects = ElementTree.fromstring(read_member(archive,"Objects"))
        script = read_member(archive,"MapScript.galaxy").decode("utf-8-sig")
    coords = lambda obj: tuple(Decimal(x) for x in obj.attrib["Position"].split(",")[:2])
    points = {int(obj.attrib["Id"]):coords(obj) for obj in objects.findall("ObjectPoint")}
    banners = [coords(obj) for obj in objects.findall("ObjectUnit") if obj.get("UnitType")==banner_type.decode()]
    ids = [int(m) for m in re.findall(r'\.lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\);',script)]
    need(ids==[244,252,245,253,178],"Unknown camp order")
    out = {}
    for camp,pid in enumerate(ids,1):
        beacon = points[pid]
        banner, = [pos for pos in banners if sum((a-b)**2 for a,b in zip(pos,beacon)) <= 8**2]
        out[camp]={"beacon":(b"TownMercCampCaptureBeacon",tuple(map(int,beacon))),
                   "icon":(b"JungleCampIconUnitTeamColor",tuple(map(int,beacon))),
                   "flag":(banner_type,tuple(map(int,banner)))}
    return out


def case(path, sha, build, positions):
    need(sha256(path.read_bytes()).hexdigest()==sha,"Wrong replay")
    p, raw, horizon = read_tracker(path,build)
    rows = list(p.decode_replay_tracker_events(raw))
    tags = {}
    def identity(row):
        return row.get("m_unitTagIndex"),row.get("m_unitTagRecycle")
    for camp, anchors in positions.items():
        tags[camp]={}
        for role,(unit,point) in anchors.items():
            born,=[r for r in rows if r["_eventid"]==1 and r["m_unitTypeName"]==unit and (r["m_x"],r["m_y"])==point
                   and (role=="icon" or r["_gameloop"]==0)]
            tags[camp][role]=identity(born)
    all_keys=set(k for group in tags.values() for k in group.values())
    need(len(all_keys)==15,"Repeated full tag")
    need(not any(r["_eventid"]==2 and identity(r) in all_keys for r in rows),"Camp actor died")
    stats = [(i,*next(capture_stats([r]))) for i,r in enumerate(rows) if r.get("m_eventName")==b"JungleCampCapture"]
    owners = defaultdict(list)
    offset=0
    previous=0
    for i,r in enumerate(rows):
        size=r["_bits"]//8
        need(r["_bits"]==size*8,"Unaligned frame")
        if r["_eventid"]==3 and identity(r) in all_keys:
            need(frame_bytes(r,previous,p)==raw[offset:offset+size],"Physical frame differs")
            owners[identity(r)].append((i,r["_gameloop"],r["m_controlPlayerId"],r["m_upkeepPlayerId"]))
        previous=r["_gameloop"]
        offset+=size
    need(offset==len(raw),"Undecoded tracker suffix")
    observations=[]
    for j,(ordinal,tick,camp,team) in enumerate(stats):
        actors=tags[camp]
        point,=[v for v in owners[actors["beacon"]] if v[1:]==(tick-1,10+team,10+team)]
        transitions={}
        for role in ("icon","flag"):
            transitions[role]=[v for v in owners[actors[role]] if v[1]==tick]
        following=next((t for _,t,c,_ in stats[j+1:] if c==camp),horizon+1)
        candidates=[v for v in owners[actors["flag"]] if tick<v[1]<following and (1<=v[2]<=10 or 1<=v[3]<=10)]
        observations.append(dict(stat_ordinal=ordinal,loop=tick,camp=camp,team=team,beacon_ordinal=point[0],
                                 icon_changes=transitions["icon"],flag_changes=transitions["flag"],
                                 personal_later_changes=candidates,cover_through_plus8=tick+8<=horizon))
    return dict(sha256=sha,build=build,tags=tags,captures=observations)


def summary(rows):
    out={}
    for label, group in (("ten",[r for r in rows if r["sha256"]==SOURCE]),
                         ("held_out_41810",[r for r in rows if r["sha256"]!=SOURCE and r["build"]==41810]),
                         ("stock_98348",[r for r in rows if r["build"]==98348])):
        counts=Counter()
        delays=Counter()
        for record in group:
            for c in record["captures"]:
                counts["captures"]+=1
                a, f, o = c["icon_changes"],c["flag_changes"],c["stat_ordinal"]
                team=[10+c["team"]]*2
                if len(a)==len(f)==1 and list(a[0][2:])==list(f[0][2:])==team:
                    counts["icon_flag_team_pair"]+=1
                    counts["icon_then_flag_then_stat"] += a[0][0] < f[0][0] < o
                    counts["three_frames_physically_adjacent"] += [a[0][0],f[0][0]]==[o-2,o-1]
                personal=c["personal_later_changes"]
                counts["complete_plus8_window"]+=c["cover_through_plus8"]
                counts["captures_with_personal_plus8"]+=any(e[1]==c["loop"]+8 for e in personal)
                counts["personal_after_capture"]+=len(personal)
                for _,t,owner,upkeep in personal:
                    delays[t-c["loop"]]+=1
                    counts["personal_control_equals_upkeep"]+=owner==upkeep
        out[label]=dict(recordings=len(group),counts=dict(counts),personal_change_lag_histogram=dict(sorted(delays.items())))
    return out


def verify(manifest,evidence,old_map,new_map):
    paths={h:Path(path) for path,h,_ in verify_manifest(json.loads(manifest.read_bytes()))}
    doc=json.loads(evidence.read_bytes())
    need(sha256(json.dumps(doc,sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
         =="1b571c891d5b5646c21d39e6552af48b1b98926d4b0b948c556ae19408600a94","Wrong exact stock cohort")
    results=[]
    for field,build,map_path in (("old_replays",41810,old_map),("target_controls",98348,new_map)):
        anchors=locations(map_path,build)
        for record in doc[field]:
            sha=record["sha256"]
            results.append(case(paths[sha],sha,build,anchors))
    return dict(summary=summary(results),cases=results)


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    for field in ("manifest","evidence","old_map","new_map"):
        parser.add_argument(field,type=Path)
    print(json.dumps(verify(**vars(parser.parse_args())),separators=(",",":")))
