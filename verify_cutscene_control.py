"""Verify the retail cutscene-frame ID, local UI hookup order and full-history dialog CRC prefix."""

from argparse import ArgumentParser
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import pack, unpack, unpack_from
from xml.etree import ElementTree as ET
from zlib import crc32

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_unit_radii import check, pinned
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned as pin_image


WINDOWS = (
    (0x9f25a0,0x9f2988),(0x970e2e,0x970e46),(0x9f46bb,0x9f46f4),(0x9f48db,0x9f4900),
    (0xd5b826,0xd5b83e),(0xd60af0,0xd60b27),(0x792e91,0x792eac),(0x793ab7,0x793ad2),
    (0xd5c807,0xd5c834),(0x7647ff,0x76480b),(0x1f2d56d,0x1f2d57e),(0x1f376e4,0x1f37701),
    (0x1f381b0,0x1f381c9),(0x203ebd0,0x203ec8e),(0x20914be,0x20914d3),(0x2092350,0x2092361),
    (0x9f29b1,0x9f29d1),(0x9f2d1c,0x9f2d2e),(0x987d5a,0x987e15),(0x9f36ac,0x9f36d2),
)
WINDOW_HASH='14fe56280d1917ec21da5795bbfb54e86d0d8d4030e1565ddfa7ac9d3e4d2380'
LAYOUT='2c871c7e77501a8ec246553c77c0a44b724ffca0ff66bffa18ef5bee9ada698e'
ASSET='632f2a5844e9fa19e7ddf0200f0559c08b2c59321011c256cd8b6c4e7bf33304'
UI='a5ddbe757a93d0019d6d17b430a5b8bf51e2e99783574e0a82a3f04e3bcd5309'
GAME='a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09'
SIGNED='150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791'
CUTSCENES=('OnFireCutsceneFrame','SpecialOverlayCutscene','DeathOverlayCutscene')
UI_SLOTS=('UIInitializeGameUIHandles','NotificationDisplayInitialize','UIInitializeHeroConsole',
          'UIInitializeDamageFlashUI','FullscreenOverlaysInitialize')


def verify_native(executable,section):
    raw=pin_image(executable,PE)
    text=pin_image(section,TEXT)
    check(sha256(b''.join(text[a-TEXT_RVA:b-TEXT_RVA] for a,b in WINDOWS)).hexdigest()==WINDOW_HASH,
          'Unexpected native path')
    for a,b,h in ((0x9f4bf0,0x9f4c24,'c768b02f00a097498c'),(0x9f57f0,0x9f5842,'f5064a82eb6eef4b1e')):
        check(sha256(text[a-TEXT_RVA:b-TEXT_RVA]).hexdigest().startswith(h),'Unexpected native reset')
    nt,=unpack_from('<I',raw,60)
    table=nt+24+unpack_from('<H',raw,nt+20)[0]
    sections=[unpack_from('<III',raw,table+40*i+12) for i in range(unpack_from('<H',raw,nt+6)[0])]
    def read(rva,n):
        pos,=(r+rva-a for a,size,r in sections if a<=rva and rva+n<=a+size)
        return raw[pos:pos+n]
    def reference(rva,op):
        loc=rva-TEXT_RVA
        prefix=bytes.fromhex(op)
        check(text[loc:loc+len(prefix)]==prefix,'Changed machine instruction')
        return rva+len(prefix)+4+unpack_from('<i',text,loc+len(prefix))[0]
    for site,dest in ((0x1f376f9,0x203ebd0),(0x1f381c1,0x203ebd0),(0x792ea7,0xd60af0),
                      (0x793acd,0xd60af0),(0xd5c82f,0x7645e0),(0x764806,0x1f2d540),(0x9f2956,0x9f1600),
                      (0x970e34,0x9f25a0),(0x987dfe,0x9707a0),(0x98987b,0x987d10),
                      (0x97bad4,0x9f4bf0),(0x9871af,0x9f57f0)):
        check(reference(site,'e8')==dest,'Changed call target')
    check(reference(0x203ec83,'e9')==0x13340e0,'Unexpected event submitter')
    check(all(reference(a,op)==0x2f6fbc4 for a,op in ((0x9f46c8,'8b15'),(0x9f46e1,'8905'),
              (0x9f29cb,'8905'),(0x9f2d1c,'8b1d'))),'Different dialog control counter')
    fields=[reference(s,'8b05') for s in (0x9f25b4,0x9f2602,0x9f264c,0x9f2696,0x9f26e0,0x9f272a,
                                         0x9f2774,0x9f27be)]
    fields.extend(reference(s,'443305') for s in (0x9f2805,0x9f284d,0x9f2895,0x9f28dd))
    check(fields==[0x2f6fbc0,0x2f6fbc4,0x2f6fbc8,*range(0x2f6fbe0,0x2f6fc04,4)],'Different CRC order')
    check(reference(0x9f2925,'488b1d')==0x2f6fbd8, 'Different linked suffix')
    global_values=[unpack('<I',read(r,4))[0] for r in fields]
    check(global_values==[1,1,*([0]*10)], 'Different PE initializer values')
    table_words=unpack('<1024I',read(reference(0x9f25ad,'4c8d15'),4096))
    def fold(words):
        state=0xffffffff
        for w in words:
            v=w^state
            state=(table_words[v>>24]^table_words[256+((v>>16)&255)]^
                   table_words[512+((v>>8)&255)]^table_words[768+(v&255)])
        return state^0xffffffff
    for words in (global_values,list(range(12)),[0xa5a5a5a5,0x2345,*range(10)]):
        check(fold(words)==crc32(pack('<12I',*words)), 'Native CRC disagrees with zlib')
    dest=unpack_from('<I',text,0x970e40-TEXT_RVA+2)[0]
    check(dest==0xf0 and (dest-8)//4==58,'Different slot index')
    return dict(native_windows=len(WINDOWS)+2,frame_default_namespace=3,hooked_frame_namespace=2,
                hooked_control_low_bits=16,frame_id_offset='0x1f8',instance_id_offset='0x28',
                full_mode_slot=58,crc_dword_rvas=[hex(v) for v in fields],
                pristine_PE_words=global_values,pristine_words_crc32_without_nodes=f'{fold(global_values):08x}',
                list_head='0x2f6fbd8',per_node='0x9f1600',both_counters_reset_to_one_at=['0x9f4bf0','0x9f57f0'],
                loaded_control_counter_at='0x9f29cb',fast_mode4_world_bit6_clear_slot58=0,
                TEN_published_slot58=None)


def verify_ui(folder,layout,asset,adapted_map):
    ui=pinned(folder/'uilib.galaxy',UI).decode('utf-8-sig').replace('\r\n','\n')
    game=pinned(folder/'gamelib.galaxy',GAME).decode('utf-8-sig')
    frames=ET.fromstring(pinned(layout,LAYOUT))
    scene=ET.fromstring(pinned(asset,ASSET))
    death,=[n for n in frames.iter('Frame') if n.get('name')=='DeathOverlayCutscene']
    check(death.get('type')=='CutsceneFrame' and death.find('File').get('val')=='Cutscenes/GameUI_DeathOverlay.StormCutscene',
          'Unexpected death-overlay asset')
    keys={e.get('name'):[k.get('bookmark') for k in e.iter('Key') if k.get('bookmark')]
          for e in death.findall('Animation')}
    check(keys=={'Start':['Start'],'Stop':['Death']},'Different death animation routes')
    marks={n.get('bookmarkName'):n for n in scene.iter('CCutsceneElementBookmark')}
    check(marks['Loop End'].get('jumpToBookmarkWhenHit')=='Loop Start' and marks['Death End'].get('pauseWhenHit')=='1',
          'Different marker behavior')
    end_node,=scene.iter('CCutsceneNodeEndScene')
    check(len(end_node)==0 and 'libUIUI_gf_FullscreenOverlaysShowHideDeathOverlay(true, lv_deadPlayer);' in game,
          'Unexpected end markers or victim trigger')
    def body(name):
        return re.search(r'bool libUIUI_gt_'+name+r'_Func .*?\n}\n',ui,re.S).group()
    init=body('InitializeUI')
    calls=re.findall(r'TriggerExecute\(libUIUI_gt_(\w+), true, true\);',init)
    check(tuple(calls[:5])==UI_SLOTS,'Different startup order')
    counts={}
    hits={}
    number=0
    for name in UI_SLOTS:
        src=body(name).split('// Actions',1)[1]
        check('Wait(' not in src and 'for (' not in src and src.count('if (')==1,'Unexpected conditional hookup')
        hookups=[l for l in src.splitlines() if 'DialogControlHookup' in l]
        counts[name]=len(hookups)
        for line in hookups:
            number+=1
            if 'c_triggerControlTypeCutscene' in line:
                hits[line.split('"')[-2]]=number
    check(list(counts.values())==[9,23,19,4,6] and hits==dict(zip(CUTSCENES,(47,60,61))),
          'Unexpected prefix ordinals')
    pinned(adapted_map,SIGNED)
    with closing(MPQArchive(adapted_map)) as archive:
        members=read_member(archive,'(listfile)').decode().splitlines()
        check(not any(p.lower().endswith(('.stormlayout','.stormcutscene')) for p in members),
              'Adapted map contains a UI asset override')
        script=read_member(archive,'MapScript.galaxy').decode('utf-8-sig')
        check('DeathOverlayCutscene' not in script and 'FullscreenOverlaysShowHideDeathOverlay' not in script,
              'Adapted map explicitly changes the death overlay')
    return dict(ui_hookup_calls_by_trigger=counts,one_based_authored_cutscene_calls=hits,
                death_asset_end_marker_elements=0,death_end_bookmark_pauses=True,loop_end_jumps_to_loop_start=True,
                signed_map_sha256=SIGNED,signed_map_contains_ui_asset_override=False,
                counter_before_first_ui_hookup=None,target_death_frame_control_id=None)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    for name in ('executable','section','scripts','layout','asset','adapted_map'):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    print(json.dumps(dict(native=verify_native(args.executable,args.section),
                          ui=verify_ui(args.scripts,args.layout,args.asset,args.adapted_map)),indent=2))
