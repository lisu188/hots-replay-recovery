"""Independent old control, pinned official core and unchanged tail checks."""
from collections import Counter
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import traceback
sys.dont_write_bytecode=True
WORK=Path(__file__).resolve().parent;HERE=WORK/'legacy-39445-control'
REPO=Path(r'C:\Users\andrz\git\hots-replay-recovery')
sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from battlelobby_attribute_layer import _read,digest,ORIGINAL_SHA256,decode_layer,encode_layer
from audit_battlelobby_mod_metadata import audit_metadata
from battlelobby_tail import decode_tail,crosscheck
from reference_replay import checked_archive,native,SortedVersionedEncoder
from migrate_replay import SemanticDecoder,SemanticEncoder,decode_events,encode_events
from encoders import encode_header,encode_tracker_events

FULL='32803cf56e4377a18ea74c908af3d840637faeb7803aaca943f8807ade70ba87'
SOURCE=HERE/'htc39445.private.StormReplay'
GUARDS=[(WORK/'TEN_GREYMANE_source_41810.StormReplay',ORIGINAL_SHA256),(WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay','4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19')]
SCHEMA_BLOB='457c6234946e71c9883fdffecb9ef923f7f19cee'
def canonical_protocol():
    source=WORK/'heroprotocol/heroprotocol/versions/protocol39445.py';raw=_read(source);normalized=raw.replace(b'\r\n',b'\n')
    if hashlib.sha1(f'blob {len(normalized)}\0'.encode()+normalized).hexdigest()!=SCHEMA_BLOB:raise ValueError('Canonical upstream39445 Git blob differs')
    target=HERE/'protocol39445.canonical-private.py'
    if target.exists():
        if _read(target)!=normalized:raise ValueError('Existing canonical schema differs')
    else:
        with target.open('xb') as stream:stream.write(normalized)
    spec=importlib.util.spec_from_file_location('_authenticated_protocol39445',target);p=importlib.util.module_from_spec(spec);sys.modules[spec.name]=p;spec.loader.exec_module(p)
    return p,{'upstream_commit':'9af3ea7150f1a8acb53464c92519a9bbcc7a3594','Git_blob_sha1':SCHEMA_BLOB,'source_raw_sha256':digest(raw),'canonical_LF_sha256':digest(normalized),'canonical_bytes':len(normalized),'normalization':'CRLF-to-LF only; canonical bytes match upstream Git blob'}

def failure(stage,error):
    frames=traceback.extract_tb(error.__traceback__)
    return {'status':'failed','stage':stage,'exception_class':type(error).__name__,
        'stack':[{'file':Path(f.filename).name,'function':f.name,'line':f.lineno} for f in frames[-5:]],'exception_values_or_message_emitted':False}

def analyze():
    for path,expected in GUARDS:
        if digest(_read(path))!=expected:raise ValueError('Source/R8 guard differs')
    raw=_read(SOURCE)
    if len(raw)!=652332 or digest(raw)!=FULL or hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!='8ff1b28c5b07e2d48425dcd097072f2953e94ef9':raise ValueError('Full control digest differs')
    p,schema=canonical_protocol();archive=checked_archive(SOURCE);results={};details=initial=None;mods=None;tail=None
    try:
        if any(b.size>8*1024*1024 for b in archive.block_table) or sum(b.size for b in archive.block_table)>32*1024*1024:raise ValueError('Archive decoded budget exceeded')
        header_raw=archive.header['user_data_header']['content'];header=p.decode_replay_header(header_raw)
        if (header['m_version']['m_build']!=39445 or header['m_version']['m_baseBuild']!=39445 or header['m_dataBuildNum']!=39445 or header['m_ngdpRootKey']['m_data'].hex()!='b3959e128489be464b4ef50eb6259480'):raise ValueError('Actual old header differs')
        try:
            if encode_header(header,p)!=header_raw:raise ValueError('Header roundtrip differs')
            results['header']={'status':'passed','sha256':digest(header_raw),'binary_roundtrip':True}
        except Exception as exc:results['header']=failure('header_roundtrip',exc)
        for kind in ('details','initData'):
            data=archive.read_file('replay.'+kind)
            try:
                if kind=='details':
                    details=p.decode_replay_details(data);encoder=SortedVersionedEncoder(p.typeinfos);encoder.instance(p.game_details_typeid,details)
                else:
                    initial=SemanticDecoder(data,p.typeinfos).instance(p.replay_initdata_typeid);encoder=SemanticEncoder(p.typeinfos);encoder.instance(p.replay_initdata_typeid,initial)
                    if native(initial)!=native(p.decode_replay_initdata(data)):raise ValueError('Official/semantic initData differs')
                if encoder.getvalue()!=data:raise ValueError('Metadata roundtrip differs')
                results[kind]={'status':'passed','bytes':len(data),'sha256':digest(data),'binary_roundtrip':True}
            except Exception as exc:results[kind]=failure(kind,exc)
        for kind in ('game','message','tracker'):
            data=archive.read_file(f'replay.{kind}.events')
            try:
                events=list(itertools.islice(decode_events(data,p,kind),250001))
                if len(events)>250000:raise ValueError('Event budget exceeded')
                official=getattr(p,f'decode_replay_{kind}_events')(data);sentinel=object()
                for first,second in itertools.zip_longest(events,official,fillvalue=sentinel):
                    if first is sentinel or second is sentinel or native(first)!=native(second):raise ValueError('Official/semantic events differ')
                encoded=encode_tracker_events(events,p) if kind=='tracker' else encode_events(events,p,kind)
                if encoded!=data:raise ValueError('Event stream roundtrip differs')
                results[kind]={'status':'passed','bytes':len(data),'sha256':digest(data),'event_count':len(events),'official_semantic_payloads_equal':True,'binary_roundtrip':True}
                if kind=='game':
                    options=[{k:e[k] for k in ('m_buildNum','m_baseBuildNum','m_versionFlags')} for e in events if e['_event']=='NNet.Game.SUserOptionsEvent']
                    results[kind]['UserOptions_builds']=sorted({x['m_buildNum'] for x in options});results[kind]['UserOptions_match_header']=bool(options) and all(x['m_buildNum']==39445 and x['m_baseBuildNum']==39445 for x in options)
            except Exception as exc:results[kind]=failure(kind,exc)
        battle=archive.read_file('replay.server.battlelobby');stage='attribute_layer_legacy10'
        try:
            layer=decode_layer(battle,'legacy-10')
            if encode_layer(layer,'legacy-10')!=battle:raise ValueError('Attribute roundtrip differs')
            stage='historical_mod_metadata';mods=audit_metadata(battle,dict(layer.boundaries)['locale_handles_end'],'historical-fixed')
            stage='unchanged_historical_tail';tail=decode_tail(battle,mods['terminal_handles_end_bit'],'historical-tail')
            checks=crosscheck(tail,details,initial)
            if not checks['all_details_participants_match_tail_by_slot'] or checks['initdata_identity_and_slot_matches']!=len(tail.players):raise ValueError('Tail identities differ')
            results['battlelobby']={'status':'passed','member_sha256':digest(battle),'players':len(tail.players),'private_crosschecks_passed':True,'full_tail_roundtrip_and_EOF':True}
        except Exception as exc:
            results['battlelobby']=failure(stage,exc);results['battlelobby']['member_sha256']=digest(battle)
            if mods is not None:results['battlelobby'].update(attribute_and_mod_metadata_passed=True,terminal_handles_end_bit=mods['terminal_handles_end_bit'])
    finally:archive.close()
    if digest(_read(SOURCE))!=FULL:raise ValueError('Control changed during analysis')
    for path,expected in GUARDS:
        if digest(_read(path))!=expected:raise ValueError('Source/R8 changed during analysis')
    return {'format':'authenticated39445-control-core-and-historical-layout-v1','fixture_sha256':FULL,'schema':schema,'actual_header_version':header['m_version'],
        'actual_header_data_build':header['m_dataBuildNum'],'actual_header_NGDP_root':header['m_ngdpRootKey']['m_data'].hex(),'results':results,
        'original_R8_before_after_guards_pass':True,'source_files':{'producer':digest(Path(__file__).read_bytes())},
        'existing_parser_profiles_modified':False,'raw_player_or_messages_emitted':False,'replay_written_or_converted':False,'client_launched':False,
        'old41810_schema_or_full_migration_proven':False}

if __name__=='__main__':
    output=HERE/'39445-core-and-unchanged-tail-observation.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse existing report')
    data=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    if len(data)>64*1024:raise ValueError('Report exceeds bound')
    with output.open('xb') as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':digest(data)}))
