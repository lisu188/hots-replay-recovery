"""Sanitized exact package binding for the one public EU replay; no player data emitted."""
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO),str(BASE.parent/'heroprotocol'),str(BASE.parent/'python-deps')]
from reference_replay import checked_archive
from protocol_loader import load_protocol
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_attribute_layer import _Reader
from dependency_audit import cache_handle
from mod_data_audit import dependency_prefix
from battlelobby_tail import decode_tail,crosscheck

path=BASE/'heroeslounge-27515-g1-20261005.StormReplay'
profile_path=path.with_suffix('.profile.json')
profile=json.loads(profile_path.read_bytes())
assert hashlib.sha256(path.read_bytes()).hexdigest()==profile['file_sha256']
p=load_protocol(96477)
a=checked_archive(path)
try:
    header=p.decode_replay_header(a.header['user_data_header']['content'])
    details=p.decode_replay_details(a.read_file('replay.details'))
    initial=p.decode_replay_initdata(a.read_file('replay.initData'))
    raw=a.read_file('replay.server.battlelobby')
finally:a.close()
assert header['m_version']['m_build']==header['m_version']['m_baseBuild']==header['m_dataBuildNum']==98348
assert header['m_ngdpRootKey']['m_data'].hex()=='c3b3c8bc82e3a5a62e550fdde9a40c28'
regions=sorted({x['m_toon']['m_region'] for x in details['m_playerList']})
assert regions==[2]
mods=audit_member(raw,'observed-11','current-observed')
tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
tail_check=crosscheck(tail,details,initial)
r=_Reader(raw);r.position=mods['mod_metadata_end_bit']
n=r.bits(6);terminal=[cache_handle(r.blob(40)) for _ in range(n)]
assert r.position==mods['terminal_handles_end_bit']
assert {x['region'] for x in terminal}=={'EU'}
entries=[]
for entry in mods['entries']:
    r=_Reader(raw);r.position=entry['start_bit']
    mod_id,version=r.bits(32),r.bits(32)
    for width in (16,16,24,7,15,2,74):r.bits(width)
    count=r.bits(6)
    caches=[cache_handle(r.blob(40)) for _ in range(count)]
    r.bits(1)
    string_region=r.bits(8);r.bits(32);string_realm=r.bits(32)
    r.blob(r.bits(7)+2)
    toon_region=r.bits(8);r.bits(32);toon_realm=r.bits(32);r.bits(64)
    r.position=entry['end_bit']-32-entry['dependency_count']*64-6
    assert r.bits(6)==entry['dependency_count']
    deps=[{'mod_id':r.bits(32),'version':r.bits(32)} for _ in range(entry['dependency_count'])]
    assert r.bits(32)==entry['final_unknown_filler_value']
    assert r.position==entry['end_bit']
    entries.append({'index':entry['index'],'mod_id':mod_id,'version':version,'creator_string_toon_region':string_region,'creator_string_toon_realm':string_realm,'creator_toon_region':toon_region,'creator_toon_realm':toon_realm,'visual_cache_handles':caches,'dependency_version_pairs':deps,'terminal_s2mh_handle':terminal[entry['index']]})
assert {x['creator_toon_region'] for x in entries}=={2}
prefix=[cache_handle(bytes.fromhex(x)) for x in dependency_prefix(raw)['handles']]
details_handles=[cache_handle(x) for x in details['m_cacheHandles']]
init_handles=[cache_handle(x) for x in initial['m_syncLobbyState']['m_gameDescription']['m_cacheHandles']]
assert details_handles==init_handles==prefix
cache_root=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
cache_matches=[]
for item in terminal:
    f=cache_root/item['relative_path']
    if f.exists():
        blob=f.read_bytes()
        cache_matches.append({'digest':item['digest'],'file_bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'matches_handle':hashlib.sha256(blob).hexdigest()==item['digest']})
    else:cache_matches.append({'digest':item['digest'],'present_at_exact_cache_path':False})
result={'format':'hots-public-eu-reference-binding-v1','file':path.name,'file_sha256':profile['file_sha256'],'file_bytes':profile['file_bytes'],'profile_file':profile_path.name,'profile_sha256':hashlib.sha256(profile_path.read_bytes()).hexdigest(),'declared_version':header['m_version'],'data_build':header['m_dataBuildNum'],'root_md5':header['m_ngdpRootKey']['m_data'].hex(),'map_title':details['m_title'].decode('utf8'),'details_player_region_set':regions,'details_player_count':len(details['m_playerList']),'prefix_handles':prefix,'details_init_prefix_handles_identical_in_order':True,'mod_metadata':mods,'mod_package_bindings':entries,'tail_report':tail.report,'tail_crosscheck':tail_check,'exact_terminal_header_cache_probes':cache_matches,'region_inferred_from_organization':False,'raw_player_or_chat_data_emitted':False,'replay_modified':False,'client_launched':False,'simulation_compatibility_proven':False}
out=BASE/'one-eu-current-reference-binding.json'
with out.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'map':result['map_title'],'build':result['data_build'],'root':result['root_md5'],'details_regions':regions,'terminal_regions':sorted({x['region'] for x in terminal}),'mods':[{'id':x['mod_id'],'version':x['version'],'header':x['terminal_s2mh_handle']['digest']} for x in entries],'exact_cache_present':sum(x.get('matches_handle',False) for x in cache_matches),'tail_crosscheck':tail_check,'report_sha256':hashlib.sha256(out.read_bytes()).hexdigest()},indent=2))
