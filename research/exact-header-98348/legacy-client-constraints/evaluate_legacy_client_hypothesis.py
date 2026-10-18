"""Read-only narrow count7/count31 hypothesis checks; no value conversion."""
from collections import Counter
import json
import importlib.util
from pathlib import Path
import sys
sys.dont_write_bytecode=True
WORK=Path(__file__).resolve().parent
sys.path[:0]=[r'C:\Users\andrz\git\hots-replay-recovery',str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from battlelobby_attribute_layer import _Reader,_Writer,_read,digest,ORIGINAL_SHA256
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import decode_tail,crosscheck
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
CASES=[('original41810',WORK/'TEN_GREYMANE_source_41810.StormReplay',ORIGINAL_SHA256,41810),
    ('R8',WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay','4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19',96477)]
SCHEMAS={41810:'879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',96477:'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'}

def positions(tail):
    at=len(tail.prefix)*8;result={}
    for token in tail.tokens:
        if token.width is None:at+=(-at)%8
        result[token.path]=at;at+=token.width if token.width is not None else len(token.value)*8
    if at!=tail.member_bytes*8:raise ValueError('Token extent differs')
    return result

def evaluate():
    native_path=WORK/'native-client-codec-ready/native_clientinfo.py'
    spec=importlib.util.spec_from_file_location('_constraint_native_clientinfo',native_path)
    native=importlib.util.module_from_spec(spec);sys.modules[spec.name]=native;spec.loader.exec_module(native)
    schema=native._schema(WORK/'native-client-codec-ready/native_clientinfo_schema_98348.json')
    root=schema.records[1768]
    results=[];private_rows=[]
    for name,path,expected,build in CASES:
        if digest(_read(path))!=expected:raise ValueError('Pinned replay differs')
        protocol=load_protocol(build)
        if protocol.recovery_schema_sha256!=SCHEMAS[build]:raise ValueError('Pinned schema differs')
        archive=MPQArchive(path)
        try:
            header=protocol.decode_replay_header(archive.header['user_data_header']['content'])
            raw=archive.read_file('replay.server.battlelobby')
            if len(raw)>8*1024*1024:raise ValueError('Member exceeds bound')
            mods=audit_member(raw,'legacy-10','historical-fixed');tail=decode_tail(raw,mods['terminal_handles_end_bit'],'historical-tail')
            details=protocol.decode_replay_details(archive.read_file('replay.details'));initial=protocol.decode_replay_initdata(archive.read_file('replay.initData'))
            gate=crosscheck(tail,details,initial)
            if not gate['all_details_participants_match_tail_by_slot'] or gate['initdata_identity_and_slot_matches']!=len(tail.players) or not gate['initdata_identity_multiset_equal'] or not gate['seed_matches_lobby'] or not gate['seed_matches_game_description']:raise ValueError('Private identity/seed gate differs')
            pos=positions(tail);rows=[];tokenmap={t.path:t for t in tail.tokens}
            for index,player in enumerate(tail.players):
                prefix=f'/players/{index}';old_block=pos[prefix+'/unknown_player_block/0'];candidate_start=old_block-1;end=pos[prefix+'/optional64/present']
                if pos.get(prefix+'/secondary/flag')!=candidate_start:raise ValueError('Exact preceding secondary flag anchor absent')
                named=native._Decoder(schema,raw,pos[prefix+'/unknown32'])
                for field,child in zip(root['field_names'][:5],root['field_types'][:5]):named.decode(child,'/'+field)
                typed={f.path:f for f in named.fields if f.kind!='USER'}
                writer=_Writer();writer.position=pos[prefix+'/unknown32']//8*8;writer.raw=bytearray(raw[:writer.position//8])
                remainder=pos[prefix+'/unknown32']%8
                if remainder:
                    fragment=_Reader(raw);fragment.position=writer.position;writer.bits(fragment.bits(remainder),remainder)
                for token in named.tokens:
                    if token.width is None:writer.blob(token.value)
                    else:writer.bits(token.value,token.width)
                last=named.reader.position;whole=last//8
                reencoded=writer.position==last and writer.raw[:whole]==raw[:whole] and (last%8==0 or writer.raw[whole]==raw[whole]&((1<<(last%8))-1))
                toon=typed['/m_toonHandle'].value
                prefix_match=(reencoded and named.reader.position==candidate_start and
                    typed['/m_clientId'].start_bit==pos[prefix+'/unknown32'] and
                    typed['/m_playerScope'].value==player.slot and
                    (toon['m_region'],toon['m_programId'],toon['m_realm'],toon['m_id'])==(player.toon.region,int.from_bytes(player.toon.program,'big'),player.toon.realm,player.toon.identifier))
                r=_Reader(raw);r.position=candidate_start
                values=[r.bits(n) for n in (8,64,32,64)];count_at=r.position;count7=r.bits(7)
                after7=r.position;rating_at=after7;rating_present=r.bits(1)
                if rating_present:r.bits(64)
                flags_at=r.position;flags=[r.bits(1) for _ in range(4)];build_at=r.position;declared_build=r.bits(32)
                r.position=count_at;count31=r.bits(31)
                current_end=r.position+96*count31
                actual_build=tokenmap[prefix+'/community_named_build32'].value
                rows.append({'choice2':tokenmap[prefix+'/unknown2bits'].value,'secondary_flag':tokenmap[prefix+'/secondary/present'].value,
                    'native_first5_prefix_ends_exactly_before175':prefix_match,
                    'count7':count7,'count31':count31,'physical31_impossible':current_end>len(raw)*8,
                    'span175_exact':old_block==candidate_start+1 and after7==end and end-candidate_start==175,
                    'rating_anchor_exact':rating_at==pos[prefix+'/optional64/present'],
                    'flags_anchor_exact':flags_at==pos[prefix+'/unknown_flags4/0'],
                    'build_anchor_exact':build_at==pos[prefix+'/community_named_build32'] and declared_build==actual_build,
                    'flags':tuple(flags),'rating_present':rating_present,'declared_build':declared_build,
                    'build_matches_auth_header':declared_build==header['m_version']['m_build'],
                    'private_slices':tuple(values)})
            private_rows.append(rows)
            results.append({'id':name,'replay_sha256':expected,'member_sha256':digest(raw),'players':len(rows),'header_build':header['m_version']['m_build'],
                'required_private_crosschecks_passed':True,'choice2_histogram':dict(Counter(str(x['choice2']) for x in rows)),
                'previous_secondary_flag_histogram':dict(Counter(str(x['secondary_flag']) for x in rows)),
                'candidate7_count_histogram':dict(Counter(str(x['count7']) for x in rows)),
                'candidate7_all_175bit_boundaries_exact':all(x['span175_exact'] for x in rows),
                'current_native_first5_named_fields_prefix_complete_match':all(x['native_first5_prefix_ends_exactly_before175'] for x in rows),
                'candidate7_rating_flags_and_build_anchors_exact':all(x['rating_anchor_exact'] and x['flags_anchor_exact'] and x['build_anchor_exact'] for x in rows),
                'four_post_rating_flag_histogram':[{'flags':list(flags),'records':count} for flags,count in Counter(x['flags'] for x in rows).items()],
                'rating_optional_flag_histogram':dict(Counter(str(x['rating_present']) for x in rows)),
                'actual_observed_community_build32_values':sorted({tokenmap[f'/players/{i}/community_named_build32'].value for i in range(len(rows))}),
                'community_build32_matches_auth_header_records':sum(x['build_matches_auth_header'] for x in rows),
                'candidate31_all_counts_nonzero':all(x['count31']>0 for x in rows),
                'candidate31_permission_payload_exceeds_remaining_member_records':sum(x['physical31_impossible'] for x in rows)})
        finally:archive.close()
        if digest(_read(path))!=expected:raise ValueError('Replay changed during read')
    return {'format':'legacy-ClientInfo-narrow-candidate-constraint-v1','results':results,
        'source_hashes':{'producer':digest(Path(__file__).read_bytes()),'native_reader':digest(native_path.read_bytes()),
            'native_selected_schema':digest((WORK/'native-client-codec-ready/native_clientinfo_schema_98348.json').read_bytes()),
            'prior_historical_schema2':digest((WORK/'independent-parser/historical-schemas/2.txt').read_bytes())},
        'original_R8_candidate_slices_identical_in_order':[(r['private_slices'],r['count7'],r['flags'],r['declared_build']) for r in private_rows[0]]==[(r['private_slices'],r['count7'],r['flags'],r['declared_build']) for r in private_rows[1]],
        'private_network_profile_or_account_values_emitted':False,'replay_or_profile_modified':False,
        'replay_header_or_client_build_semantics_reconciled':False,'old_ClientInfo_schema_authenticated':False,'old_to_current_conversion_rule_established':False,
        'interpretation':'Only count7 and count31 are tested. Current-named first5-field prefix reencoding and alignment are exact on these source bytes, including endpoint branch1. Candidate7 remains structurally consistent; candidate31 cannot fit even within the remaining physical member. Structural alignment does not authenticate old field names, optional semantics or a conversion rule.64541 remains a source observation, not a verified old client build.'}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):raise FileExistsError('Refuse existing report')
    data=(json.dumps(evaluate(),indent=2,sort_keys=True)+'\n').encode()
    if len(data)>16*1024:raise ValueError('Concise report limit exceeded')
    if args.output is None:print(data.decode(),end='')
    else:
        with args.output.open('xb') as stream:stream.write(data)
        print(json.dumps({'bytes':len(data),'sha256':digest(data)}))
