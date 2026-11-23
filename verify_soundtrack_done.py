"""Verify cross-map calibration and validate TEN's conditional frames against independent codecs."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

import first_sync_game
from native_game_events import PROFILE, _profile
from predict_camp_captures import SOURCE, CONTROLS
from soundtrack_done import CURSED, CURSED_MAP, DRAGON, OLD, SKY, SKY_MAP, STOCK, catalog_models, fit, intro, observe, project_rows
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


def native(exe, decoded):
    image, code = pinned(exe,PE),pinned(decoded,TEXT)
    windows=((0x769360,0x769371,'3c5dc230e81535026a4c4dae'),(0x77bbe0,0x77bce8,'b188fc724eb540f0f4ff2352'),
             (0x77abd0,0x77abed,'1c7d8be09b3cadc1876c8ccd'),(0xc28198,0xc281b3,'bcb818bf1eff2f790acedb79'),
             (0x5e0e10,0x5e0e4c,'48eeef4df8a174dcfa8cbf27'),(0xa8f730,0xa8f76f,'ee1a572ed1a94f9ad9d998a8'),
             (0xc27f4f,0xc27f84,'979e168c81f243914f4c181e'))
    if any(not sha256(code[a-TEXT_RVA:b-TEXT_RVA]).hexdigest().startswith(h) for a,b,h in windows):
        raise ValueError('Changed native soundtrack implementation')
    nt, = unpack_from('<I',image,60)
    start=nt+24+unpack_from('<H',image,nt+20)[0]
    sections=[unpack_from('<III',image,start+i*40+12) for i in range(unpack_from('<H',image,nt+6)[0])]
    def u32(rva):
        ofs,=[p+rva-b for b,n,p in sections if b<=rva and rva+4<=b+n]
        return unpack_from('<I',image,ofs)[0]
    root = u32(0x27bec00)
    types,roots=_profile(PROFILE)
    if (root!=490 or roots[64]!=root or types[root]['field_types']!=[491] or types[491]['element_type']!=3
            or types[3]['bounds']['min']!=0 or types[3]['bounds']['max']!=0xffffffff
            or u32(0x26eeed0+6*4)!=0x30040 or unpack_from('<I',code,0xc286d8+6*4-TEXT_RVA)[0]!=0xc28198):
        raise ValueError('Event/codec/listener binding changed')
    return dict(build=98348,pe_sha256=PE[1],text_sha256=TEXT[1],native_event_root=root,payload='uint32',
                producer_object_link_bits=16,absent_link=65535,listener_table_offset=0x228,pending_kind=4,
                checks_pending_and_reported_catalog_link=True)


def audit_one(args):
    return observe(*args)


def verify(args):
    facts=native(args.exe,args.text)
    scripts=((args.soundlib,'d59cddc1401cb067ed269e8c9f86fd0dd0e9ddb9309b0b6b505a643bddeb671e'),
             (args.heroeslib,'15f0314a1c48a0391e76e22360847e7ef0c91b12a29da15d79453045c175a683'))
    for path,h in scripts:
        if sha256(path.read_bytes()).hexdigest()!=h:
            raise ValueError('Wrong installed Galaxy library')
    lib=args.soundlib.read_text(encoding='utf-8-sig')
    actions=['lv_soundtrack = libCore_gv_mAPMapSoundtrack[0];','SoundtrackPlay(PlayerGroupAll(), c_soundtrackCategoryMusic, lv_soundtrack,',
             'SoundtrackWait(lv_soundtrack);']
    if lib.count('SoundtrackWait(')!=1 or any(lib.count(a)!=1 for a in actions) or [lib.index(a) for a in actions]!=sorted(lib.index(a) for a in actions):
        raise ValueError('Opening playback/wait binding differs')
    refs=Path(first_sync_game.__file__).resolve().parent/'observations/first-sync-game.json'
    expected={SOURCE:41810,**{h:41810 for h in CONTROLS},**{r['replay_sha256']:98348 for r in json.loads(refs.read_bytes())['references']}}
    paths=json.loads(args.recordings.read_bytes())
    if set(paths)!=set(expected) or len(paths)!=28:
        raise ValueError('Wrong recording cohort')
    with ProcessPoolExecutor(args.jobs) as pool:
        all_rows=list(pool.map(audit_one,[(Path(p),h,expected[h]) for h,p in sorted(paths.items())]))
    maps={r['map']:args.depot/r['map'][:2]/r['map'][2:4]/(r['map']+'.s2ma') for r in all_rows}
    roles={h:intro(p,h) for h,p in maps.items()}
    models=catalog_models(args.core,args.ui,args.heroes)
    anchors=[r for r in all_rows if r['build']==98348 and r['map'] in (SKY_MAP,CURSED_MAP)]
    word,predictions=fit(models,maps,anchors)
    held=[r for r in all_rows if r['build']==98348 and r['map']==STOCK]
    if roles[STOCK]!=DRAGON or len(held)!=15 or any(v[4]!=word for r in held for v in r['rows']):
        raise ValueError('Stock Dragon Shire disagrees with held-out projection')
    old=[r for r in all_rows if r['build']==41810]
    if any(r['map']!=OLD or any(v[4]!=96 for v in r['rows']) for r in old):
        raise ValueError('Unexpected historical observations')
    ten,=[r for r in old if r['sha256']==SOURCE]
    rows,frames=project_rows(ten,maps[OLD],args.gate,word)
    if args.frames:
        with args.frames.open('xb') as stream: stream.write(frames)
    if args.rows:
        with args.rows.open('x') as stream: json.dump(rows,stream,separators=(',',':'))
    counts=[]
    for b,h in sorted({(r['build'],r['map']) for r in all_rows}):
        group=[r for r in all_rows if r['build']==b and r['map']==h]
        words=Counter(row[4] for r in group for row in r['rows'])
        counts.append(dict(build=b,map_sha256=h,role=roles[h],recordings=len(group),word_counts=words))
    return dict(native=facts,map_roles=counts,relative_ranks={k:{role:v[role] for role in (SKY,DRAGON,CURSED)} for k,v in models.items()},
                predictions_from_non_dragon_maps=predictions,target_word=word,old_word=96,other_map_calibration_recordings=len(anchors),
                held_out_stock_dragon_recordings=len(held),held_out_stock_dragon_rows=sum(len(r['rows']) for r in held),
                ten_original_ordinals=[i for i,_ in rows],ten_conditional_frames=len(rows),sparse_bytes=len(frames),
                sparse_sha256=sha256(frames).hexdigest(),first_original_loop=rows[0][1]['_gameloop'],
                original_user_and_cadence_retained=True,complete_catalog_loader_recovered=False,target_reporting_schedule_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('recordings','depot','gate','core','ui','heroes','soundlib','heroeslib','exe','text'):
        p.add_argument(field,type=Path)
    p.add_argument('--frames',type=Path)
    p.add_argument('--rows',type=Path)
    p.add_argument('--jobs',type=int,default=3)
    print(json.dumps(verify(p.parse_args()),indent=2))
