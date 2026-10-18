"""One-fixture read-only community-schema1 diagnostic, not a profile patch."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
sys.dont_write_bytecode=True
WORK=Path(__file__).resolve().parent;HERE=WORK/'legacy-39445-control'
sys.path[:0]=[r'C:\Users\andrz\git\hots-replay-recovery',str(WORK/'heroprotocol'),str(WORK/'python-deps'),str(WORK)]
from battlelobby_attribute_layer import _read,_Reader,_Writer,digest,decode_layer
from audit_battlelobby_mod_metadata import audit_metadata
from battlelobby_tail import Toon,Player,crosscheck
from reference_replay import checked_archive
from inspect_39445_control import canonical_protocol,FULL,SOURCE,GUARDS,failure

class Wire:
    def __init__(self,raw,start):
        if start%8:raise ValueError('Byte-aligned metadata end required')
        self.r=_Reader(raw);self.r.position=start;self.w=_Writer();self.w.blob(raw[:start//8]);self.ops=0
    def bits(self,n):
        self.ops+=1
        if self.ops>100000:raise ValueError('Field budget exceeded')
        value=self.r.bits(n);self.w.bits(value,n);return value
    def blob(self,n):
        self.ops+=1
        if self.ops>100000 or not 0<=n<=8*1024*1024:raise ValueError('Blob budget exceeded')
        value=self.r.blob(n);self.w.blob(value);return value
    def opaque(self,n):
        for at in range(0,n,64):self.bits(min(64,n-at))
    def count(self,n,cap):
        value=self.bits(n)
        if value>cap:raise ValueError('Count exceeds diagnostic bound')
        return value
    def string_toon(self):
        region=self.bits(8);program=self.bits(32);realm=self.bits(32);name=self.blob(self.bits(7)+2)
        return region,program,realm,name

def diagnose(raw,start,details,initial):
    wire=Wire(raw,start);read=wire.bits
    collections=wire.count(32,65535)
    for _ in range(collections):wire.blob(read(8)).decode('utf-8')
    available=wire.count(32,65535)
    if available!=collections:raise ValueError('Registry/matrix counts differ')
    for _ in range(available):wire.blob(32)
    seed=read(32);read(32);player_count=wire.count(5,16)
    if not player_count:raise ValueError('No players')
    native_path=WORK/'native-client-codec-ready/native_clientinfo.py'
    spec=importlib.util.spec_from_file_location('_schema1_native_prefix',native_path);native=importlib.util.module_from_spec(spec);sys.modules[spec.name]=native;spec.loader.exec_module(native)
    schema=native._schema(WORK/'native-client-codec-ready/native_clientinfo_schema_98348.json');root=schema.records[1768]
    rows=[];players=[];slots=set()
    for _ in range(player_count):
        player_start=wire.r.position;client=read(32);slot=read(5)
        if slot>=16 or slot in slots:raise ValueError('Invalid/duplicate schema1 slot')
        slots.add(slot);toon=Toon(read(8),read(32).to_bytes(4,'big'),read(32),read(64));players.append(Player(slot,toon))
        wire.string_toon();read(1);choice=read(2);secondary=read(1)
        if secondary:read(2);wire.string_toon();read(1)
        opaque_start=wire.r.position
        named=native._Decoder(schema,raw,player_start)
        for name,child in zip(root['field_names'][:5],root['field_types'][:5]):named.decode(child,'/'+name)
        typed={f.path:f for f in named.fields if f.kind!='USER'};native_toon=typed['/m_toonHandle'].value
        prefix_exact=(named.reader.position==opaque_start-1 and typed['/m_clientId'].value==client and typed['/m_playerScope'].value==slot and
            (native_toon['m_region'],native_toon['m_programId'],native_toon['m_realm'],native_toon['m_id'])==(toon.region,int.from_bytes(toon.program,'big'),toon.realm,toon.identifier))
        candidate=_Reader(raw);candidate.position=opaque_start-1
        for width in (8,64,32,64):candidate.bits(width)
        count_at=candidate.position;count7=candidate.bits(7)
        wire.opaque(174);rating_at=wire.r.position;rating=read(1)
        if rating:wire.opaque(64)
        flags=[read(1) for _ in range(4)];build=read(32)
        if read(1)==0:wire.opaque(read(12));read(1)
        read(1)
        # Pinned1.txt has no party-optional field. Existing historical-tail is
        # deliberately unmodified and its earlier failure remains separate.
        if read(1):wire.blob(read(7))
        candidate.position=count_at;count31=candidate.bits(31)
        rows.append({'prefix_match':prefix_exact,'choice':choice,'secondary':secondary,'count7':count7,'candidate7_boundary':candidate.position-24==rating_at,
            'candidate31_payload_physically_impossible':candidate.position+96*count31>len(raw)*8,'rating':rating,'flags':tuple(flags),'build32':build})
    players_end=wire.r.position
    wire.opaque(64)
    if read(1):
        for width in (8,32,32,32,32):read(width)
    else:wire.opaque(16)
    wire.opaque(87)
    for _ in range(read(4)+1):wire.opaque(38)
    read(1)
    for _ in range(read(4)+1):read(32)
    for _ in range(wire.count(5,31)):
        read(32)
        for _ in range(wire.count(11,2047)):read(32);read(32);read(32)
    for _ in range(wire.count(6,63)):read(32)
    for _ in range(wire.count(5,31)):read(32);read(9)
    wire.opaque(23);read(32);wire.opaque(10);read(32)
    padding=len(raw)*8-wire.r.position
    if not 0<=padding<8 or (padding and read(padding)):raise ValueError('Schema1 EOF/padding differs')
    if bytes(wire.w.raw)!=raw:raise ValueError('Schema1 member reconstruction differs')
    checks=crosscheck(SimpleNamespace(players=players,random_seed=seed,disabled_heroes=None),details,initial)
    if not checks['all_details_participants_match_tail_by_slot'] or checks['initdata_identity_and_slot_matches']!=player_count or not checks['initdata_identity_multiset_equal'] or not checks['seed_matches_lobby'] or not checks['seed_matches_game_description']:raise ValueError('Independent private identity/seed gate differs')
    return {'status':'passed','collection_count':collections,'players':player_count,'players_end_bit':players_end,'full_schema1_EOF_and_member_reencoding_exact':True,
        'required_private_identity_seed_gates_passed':True,'native_current_first5_prefix_matches':sum(r['prefix_match'] for r in rows),
        'choice2_histogram':dict(Counter(str(r['choice']) for r in rows)),'previous_secondary_presence_histogram':dict(Counter(str(r['secondary']) for r in rows)),
        'candidate7_count_histogram':dict(Counter(str(r['count7']) for r in rows)),'candidate7_175bit_boundary_matches':sum(r['candidate7_boundary'] for r in rows),
        'candidate31_permission_payload_physically_impossible_records':sum(r['candidate31_payload_physically_impossible'] for r in rows),
        'post_block_optional64_histogram':dict(Counter(str(r['rating']) for r in rows)),
        'post_rating_flags_histogram':[{'flags':list(f),'records':n} for f,n in Counter(r['flags'] for r in rows).items()],
        'community_build32_values_at_source1_anchor':sorted({r['build32'] for r in rows}),'community_build32_matches_header39445_records':sum(r['build32']==39445 for r in rows)}

def analyze():
    for path,expected in GUARDS:
        if digest(_read(path))!=expected:raise ValueError('Original/R8 guard differs')
    s1=WORK/'independent-parser/historical-schemas/1.txt';s2=WORK/'independent-parser/historical-schemas/2.txt'
    first=_read(s1);second=_read(s2)
    if digest(first)!='237a5d48d353fd7ccc2021ba881abe3cfdd40a079a0bc5acfed4a1459dde41b1' or digest(second)!='e33f5cc20afe17476908df1cfb01198f9cb16b5fa9d919c40a05efad9b08b9f1':raise ValueError('Historical primary snapshots differ')
    a=first.decode().splitlines();b=second.decode().splitlines();extra='      m_PartyInfo: Optional:1 of (array [:0 + 64] of bit)'
    if a!=[line for line in b if line!=extra] or b.count(extra)!=1:raise ValueError('Expected exact schema1/2 difference is not unique')
    if digest(_read(SOURCE))!=FULL:raise ValueError('Old control differs')
    p,schema=canonical_protocol();archive=checked_archive(SOURCE)
    try:
        raw=archive.read_file('replay.server.battlelobby');layer=decode_layer(raw,'legacy-10');mods=audit_metadata(raw,dict(layer.boundaries)['locale_handles_end'],'historical-fixed')
        details=p.decode_replay_details(archive.read_file('replay.details'));initial=p.decode_replay_initdata(archive.read_file('replay.initData'))
        result=diagnose(raw,mods['terminal_handles_end_bit'],details,initial)
    finally:archive.close()
    if digest(_read(SOURCE))!=FULL:raise ValueError('Old control changed during diagnostic')
    for path,expected in GUARDS:
        if digest(_read(path))!=expected:raise ValueError('Original/R8 changed')
    return {'format':'39445-schema1-specific-readonly-player-diagnostic-v1','fixture_sha256':FULL,'member_sha256':digest(raw),'result':result,
        'source1_sha256':digest(first),'source2_sha256':digest(second),'source_commit':'85625327fd5623368410e5270a7eeb4869b40af9',
        'source1_vs2_only_difference':'schema1 omits per-player party optional64','producer_sha256':digest(Path(__file__).read_bytes()),
        'native_reader_sha256':digest((WORK/'native-client-codec-ready/native_clientinfo.py').read_bytes()),
        'native_selected_schema_sha256':digest((WORK/'native-client-codec-ready/native_clientinfo_schema_98348.json').read_bytes()),
        'original_R8_guards_preserved':True,'existing_parser_or_profile_modified':False,'raw_player_values_emitted':False,'client_launched':False,
        'unchanged_historical_tail_failure_superseded':False,'old41810_schema_or_conversion_rule_proven':False,
        'limits':['This separate diagnostic applies only the pinned community schema1 to this exact public39445 fixture.',
            'Current-native first5 fields are tested as a prefix hypothesis, not authenticated historical field semantics.',
            'A structurally aligned community build32 remains a source observation; no ownership or migration interpretation follows.']}

if __name__=='__main__':
    output=HERE/'39445-schema1-player-diagnostic-v2.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse existing report')
    data=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    if len(data)>32*1024:raise ValueError('Report exceeds bound')
    with output.open('xb') as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':digest(data)}))
