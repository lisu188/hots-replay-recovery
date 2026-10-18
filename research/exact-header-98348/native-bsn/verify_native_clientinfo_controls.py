"""Research reproduction of portable native codec on the frozen21 controls.

Paths locate the existing local research corpus only. No PE, client, network,
replay writes or raw participant output is used.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;WORK=HERE.parent
REPO=Path(r'C:\Users\andrz\git\hots-replay-recovery')
sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps'),str(WORK/'availability-vector-expanded-ready'),str(WORK/'availability-vector-ready'),str(WORK/'availability-representation-ready')]
_spec=importlib.util.spec_from_file_location('_verified_local_native_clientinfo',HERE/'native_clientinfo.py')
_native=importlib.util.module_from_spec(_spec);sys.modules[_spec.name]=_native;_spec.loader.exec_module(_native)
audit_current_client_infos=_native.audit_current_client_infos
SCHEMA_SHA256=_native.SCHEMA_SHA256
from battlelobby_attribute_layer import digest
from battlelobby_tail import decode_tail,crosscheck
from audit_battlelobby_mod_metadata import audit_member
from protocol_loader import load_protocol
import audit_expanded_account_vectors as cohort

def analyze():
    budget=cohort.Budget();specs,guards,sources=cohort.load_specs(budget)
    identity=load_protocol(96477)
    if identity.recovery_schema_sha256!=cohort.previous.SCHEMA_CURRENT:raise ValueError('Pinned identity schema differs')
    results=[]
    for spec in specs:
        before=budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads')
        if digest(before)!=spec['sha']:raise ValueError('Replay digest differs')
        cohort.profile_checked(spec['profile'],spec['profile_sha'],spec['sha'],budget)
        archive=cohort.CountedArchive(spec['path'],budget)
        try:
            header=identity.decode_replay_header(archive.header['user_data_header']['content'])
            if (header['m_version']['m_build']!=98348 or header['m_version']['m_baseBuild']!=98348 or header['m_dataBuildNum']!=98348 or header['m_ngdpRootKey']['m_data'].hex()!=cohort.ROOT):raise ValueError('Actual current header differs')
            raw=cohort.previous.bounded_member(archive,'replay.server.battlelobby');mods=audit_member(raw,'observed-11','current-observed')
            tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
            initial=identity.decode_replay_initdata(archive.read_file('replay.initData'));details=identity.decode_replay_details(archive.read_file('replay.details'))
            checks=crosscheck(tail,details,initial)
            if not checks['all_details_participants_match_tail_by_slot'] or checks['initdata_identity_and_slot_matches']!=len(tail.players) or not checks['initdata_identity_multiset_equal'] or not checks['seed_matches_lobby'] or not checks['seed_matches_game_description']:raise ValueError('Private crosscheck differs')
            facts=audit_current_client_infos(raw,tail)
            results.append({'id':spec['id'],'replay_sha256':spec['sha'],'profile_sha256':spec['profile_sha'],'member_sha256':digest(raw),'facts':facts,'private_crosschecks_passed':True})
        finally:archive.close()
        if digest(budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))!=spec['sha']:raise ValueError('Replay changed')
    for _,path,sha,_ in guards:
        if digest(budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))!=sha:raise ValueError('Legacy source guard differs')
    return {'format':'hots-portable-native-ClientInfo-21control-verification-v1','cases':len(results),'players':sum(r['facts']['players_checked'] for r in results),
        'schema_sha256':SCHEMA_SHA256,'source_hashes':{n:digest((HERE/n).read_bytes()) for n in ('native_clientinfo.py','test_native_clientinfo.py','verify_native_clientinfo_controls.py')},
        'results':results,'read_accounting':dict(budget.counts),'source_schema_file_read_each_player':True,'native_module_loaded_by_exact_local_source_path':True,
        'no_PE_or_client_loading':True,'replay_or_member_written':False,'private_values_emitted':False,'old174_layout_or_availability_semantics_claimed':False}

if __name__=='__main__':
    output=HERE/'portable-native-clientinfo-21control-verification.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse existing output')
    raw=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    if len(raw)>256*1024:raise ValueError('Report exceeds bound')
    with output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'bytes':len(raw),'sha256':digest(raw)}))
