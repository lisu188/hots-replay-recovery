"""Separate read-only native ClientInfo decoder; private values stay in RAM.

This research module leaves the frozen observed-profile auditer untouched.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
WORK=HERE.parent
REPO=Path(r'C:\Users\andrz\git\hots-replay-recovery')
sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps'),str(WORK/'availability-vector-expanded-ready'),str(WORK/'availability-vector-ready'),str(WORK/'availability-representation-ready')]
from battlelobby_attribute_layer import _Reader,_Writer,digest
from battlelobby_tail import decode_tail,crosscheck
from audit_battlelobby_mod_metadata import audit_member
from protocol_loader import load_protocol
import audit_expanded_account_vectors as cohort

@dataclass
class Field:
    path:str
    type_id:int
    start:int
    end:int
    kind:str
    value:object

class NativeDecoder:
    def __init__(self,protocol,raw,start):
        if type(start) is not int or not 0<=start<=len(raw)*8:raise ValueError('Invalid ClientInfo start')
        self.protocol=protocol;self.reader=_Reader(raw);self.reader.position=start
        self.writer=_Writer();self.writer.raw=bytearray(raw[:start//8]);self.writer.position=start//8*8
        if start%8:
            r=_Reader(raw);r.position=start//8*8;self.writer.bits(r.bits(start%8),start%8)
        self.fields=[];self.raw=raw;self.start=start
    def bits(self,n):
        value=self.reader.bits(n);self.writer.bits(value,n);return value
    def blob(self,n):
        value=self.reader.blob(n);self.writer.blob(value);return value
    def decode(self,i,path='',depth=0):
        if depth>64 or len(self.fields)>100000:raise ValueError('Native decode budget exceeded')
        rec=self.protocol.records[i];kind=rec['kind'];start=self.reader.position;value=None
        bounds=rec.get('bounds')
        if kind=='USER':value=self.decode(rec['element_type'],path,depth+1)
        elif kind=='STRUCT':
            value={name:self.decode(c,path+'/'+name,depth+1) for name,c in zip(rec['field_names'],rec['field_types'])}
        elif kind=='CHOICE':
            value=self.bits(bounds['bits'])+bounds['min']
            if value not in rec['tags']:raise ValueError('Native choice tag outside declared fields')
            at=rec['tags'].index(value)
            self.decode(rec['field_types'][at],path+'/'+rec['field_names'][at],depth+1)
        elif kind=='ARRAY':
            value=self.bits(bounds['bits'])+bounds['min']
            if not 0<=value<=min(bounds['max'],32768):raise ValueError('Native array length exceeds bound')
            for j in range(value):self.decode(rec['element_type'],path+'/'+str(j),depth+1)
        elif kind=='OPTIONAL':
            value=self.bits(1)
            if value:self.decode(rec['element_type'],path+'/value',depth+1)
        elif kind in ('ASCII_STRING','STRING','BLOB'):
            width=bounds['bits']+(2 if kind=='STRING' else 0)
            count=self.bits(width)+bounds['min']
            maximum=bounds['max']*(4 if kind=='STRING' else 1)
            if not 0<=count<=min(maximum,4096):raise ValueError('Native byte-string length exceeds bound')
            value=self.blob(count)
            if kind=='ASCII_STRING':value.decode('ascii')
            if kind=='STRING':
                decoded=value.decode('utf-8')
                if not bounds['min']<=len(decoded)<=bounds['max']:raise ValueError('Native UTF8 character count exceeds bounds')
        elif kind=='BIT_ARRAY':
            value=self.bits(bounds['bits'])+bounds['min']
            if not 0<=value<=min(bounds['max'],65536):raise ValueError('Native bit-array length exceeds bound')
            for at in range(0,value,64):self.bits(min(64,value-at))
        elif kind in ('INT','ENUM'):
            value=self.bits(bounds['bits'])+bounds['min']
            if value>bounds['max']:raise ValueError('Native scalar outside bounds')
            if kind=='ENUM' and value not in rec['tags']:raise ValueError('Native enum value absent')
        elif kind in ('BOOL','FOURCC','REAL32','REAL64'):
            value=self.bits({'BOOL':1,'FOURCC':32,'REAL32':32,'REAL64':64}[kind])
        elif kind!='NULL':raise ValueError('Unsupported native kind')
        self.fields.append(Field(path,i,start,self.reader.position,kind,value));return value
    def exact_consumed_bits(self):
        end=self.reader.position;whole=end//8
        if self.writer.position!=end or self.writer.raw[:whole]!=self.raw[:whole]:return False
        return not end%8 or self.writer.raw[whole]==self.raw[whole]&((1<<(end%8))-1)
    def field(self,path,kind=None):
        result=[f for f in self.fields if f.path==path and (kind is None or f.kind==kind)]
        if not result:raise ValueError('Expected native field absent')
        return next((f for f in result if f.kind!='USER'),result[-1])

def token_positions(tail):
    position=len(tail.prefix)*8;result={}
    for token in tail.tokens:
        if token.width is None:position+=(-position)%8
        result[token.path]=position
        position+=token.width if token.width is not None else len(token.value)*8
    if position!=tail.member_bytes*8:raise ValueError('Existing tail token extent differs')
    return result

def native_case(protocol,raw,tail):
    positions=token_positions(tail);rows=[]
    for index,player in enumerate(tail.players):
        path=f'/players/{index}';start=positions[path+'/unknown32'];decoder=NativeDecoder(protocol,raw,start)
        decoder.decode(1768)
        expected_end=positions[f'/players/{index+1}/unknown32'] if index+1<len(tail.players) else tail.report['boundaries_bits']['players_end']
        if decoder.reader.position!=expected_end or not decoder.exact_consumed_bits():raise ValueError('Native ClientInfo end or exact bit reencoding differs')
        anchors={'/m_clientId':'/unknown32','/m_playerScope':'/slot','/m_toonHandle':'/toon/region','/m_toonName':'/string_toon/region',
            '/m_talkerInfo':'/name_flag','/m_talkerInfo/m_id/m_id':'/unknown2bits','/m_talkerNetworkId':'/secondary/present',
            '/m_rating':'/optional64/present','/m_clientBuildVersion/value':'/community_named_build32',
            '/m_sharedPlayerInfo':'/collection_choice','/m_accountNickname':'/tag/present','/m_playerLevel':'/account_level','/m_hasActiveBoost':'/boost_flag'}
        for native,old in anchors.items():
            if decoder.field(native).start!=positions[path+old]:raise ValueError('Native/observed-profile anchor differs')
        if decoder.field('/m_clientId').end-decoder.field('/m_clientId').start!=32 or decoder.field('/m_playerScope').value!=player.slot:raise ValueError('Native client/scope shape differs')
        choice=decoder.field('/m_talkerInfo/m_id/m_id','CHOICE')
        net=decoder.field('/m_talkerNetworkId');voice=decoder.field('/m_voiceSessionId');profile=decoder.field('/m_profileAddress');permissions=decoder.field('/m_relevantPermissions','ARRAY')
        opaque_start=positions[path+'/unknown_player_block/0']
        if not (net.end==voice.start and voice.end==profile.start and profile.end==permissions.start and permissions.end==decoder.field('/m_rating').start):raise ValueError('Native segment is not contiguous')
        observed_bit=_Reader(raw);observed_bit.position=positions[path+'/secondary/present'];first=observed_bit.bits(1)
        rows.append({'choice':choice.value,'first_network_bit':first,'permission_count':permissions.value,
            'native_segment_bits':permissions.end-net.start,'opaque_remaining_bits':permissions.end-opaque_start,
            'opaque_starts_one_bit_inside_network_field':opaque_start==net.start+1,
            'named_widths':[net.end-net.start,voice.end-voice.start,profile.end-profile.start,permissions.end-permissions.start],
            'all_13_known_anchors_equal':True,'full_ClientInfo_reencoding_exact':True})
    return rows

def analyze(protocol):
    from inspect_bsn_schema import BLOB_SHA,EXPECTED
    if digest(protocol.raw)!=BLOB_SHA or protocol.records[1768]['name']!='Battlenet::Client::S2GameDefines::ClientInfo':raise ValueError('Pinned native protocol differs')
    budget=cohort.Budget();specs,guards,sources=cohort.load_specs(budget)
    identity=load_protocol(96477)
    if identity.recovery_schema_sha256!=cohort.previous.SCHEMA_CURRENT:raise ValueError('Pinned protocol differs')
    results=[];totals=[];branch_control=None
    for spec in specs:
        before=budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads')
        if digest(before)!=spec['sha']:raise ValueError('Replay digest differs')
        cohort.profile_checked(spec['profile'],spec['profile_sha'],spec['sha'],budget)
        archive=cohort.CountedArchive(spec['path'],budget)
        try:
            header=identity.decode_replay_header(archive.header['user_data_header']['content'])
            if (header['m_version']['m_build']!=98348 or header['m_version']['m_baseBuild']!=98348 or header['m_dataBuildNum']!=98348 or header['m_ngdpRootKey']['m_data'].hex()!=cohort.ROOT):raise ValueError('Actual replay build/root differs')
            raw=cohort.previous.bounded_member(archive,'replay.server.battlelobby')
            mods=audit_member(raw,'observed-11','current-observed')
            tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
            initial=identity.decode_replay_initdata(archive.read_file('replay.initData'));details=identity.decode_replay_details(archive.read_file('replay.details'))
            checks=crosscheck(tail,details,initial)
            if not checks['all_details_participants_match_tail_by_slot'] or checks['initdata_identity_and_slot_matches']!=len(tail.players) or not checks['initdata_identity_multiset_equal'] or not checks['seed_matches_lobby'] or not checks['seed_matches_game_description']:raise ValueError('Private identity/seed crosscheck differs')
            rows=native_case(protocol,raw,tail);totals+=rows
            if branch_control is None:branch_control=network_branch_control(protocol,raw,tail,mods['terminal_handles_end_bit'])
            results.append({'id':spec['id'],'replay_sha256':spec['sha'],'profile_sha256':spec['profile_sha'],'member_sha256':digest(raw),'players':len(rows),'required_private_crosschecks_passed':True,'all_native_ClientInfo_ends_and_reencoding_exact':True})
        finally:archive.close()
        if digest(budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))!=spec['sha']:raise ValueError('Replay changed')
    for _,path,sha,_ in guards:
        if digest(budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))!=sha:raise ValueError('Legacy guard differs')
    return {'format':'hots-native-ClientInfo-current-binding-v1','source_PE_sha256':EXPECTED,'source_embedded_bytecode_sha256':BLOB_SHA,'source_hashes':{'native_client_layout.py':digest(Path(__file__).read_bytes()),'cohort_loader':digest(Path(cohort.__file__).read_bytes())},
        'current_cases':len(results),'current_player_records':len(totals),'results':results,
        'aggregate':{'TalkerId_choice_histogram':dict(Counter(str(r['choice']) for r in totals)),'first_network_field_bit_histogram':dict(Counter(str(r['first_network_bit']) for r in totals)),
            'relevant_permission_count_histogram':dict(Counter(str(r['permission_count']) for r in totals)),
            'native_segment_bits_histogram':dict(Counter(str(r['native_segment_bits']) for r in totals)),
            'prior_opaque_remaining_bits_histogram':dict(Counter(str(r['opaque_remaining_bits']) for r in totals)),
            'named_width_histogram':[{'widths':list(widths),'records':n} for widths,n in Counter(tuple(r['named_widths']) for r in totals).items()],
            'all_prior_opaque_starts_one_bit_into_network_field':all(r['opaque_starts_one_bit_inside_network_field'] for r in totals),
            'all_13_anchors_match':all(r['all_13_known_anchors_equal'] for r in totals),'all_full_ClientInfo_reencodings_exact':all(r['full_ClientInfo_reencoding_exact'] for r in totals)},
        'single_bit_RAM_network_branch_negative_control':branch_control,
        'input_read_accounting':dict(budget.counts),'input_read_bytes':sum(budget.counts.values()),
        'private_player_values_or_network_identifiers_emitted':False,'game_code_executed_or_loaded':False,'replay_or_member_written':False,
        'old_174_layout_proven':False,'current_32_byte_availability_semantics_proven':False,
        'limits':['Only actual current98348 controls are decoded with this native schema.','Exact reencoding checks structural preservation; independent existing initData/details gates authenticate identity and boundaries.','Static field names do not establish ownership meaning or a legacy-to-current value transformation.']}

def network_branch_control(protocol,raw,tail,start):
    positions=token_positions(tail);at=positions['/players/0/secondary/present']
    if raw[at//8]&(1<<(at%8)):raise ValueError('Positive control does not have observed zero first bit')
    modified=bytearray(raw);modified[at//8]|=1<<(at%8);modified=bytes(modified)
    decoder=NativeDecoder(protocol,modified,positions['/players/0/unknown32']);decoder.decode(1768)
    expected=positions['/players/1/unknown32'] if len(tail.players)>1 else tail.report['boundaries_bits']['players_end']
    if decoder.reader.position!=expected or not decoder.exact_consumed_bits() or not 0<=decoder.field('/m_talkerNetworkId').value<=255:raise ValueError('Native single-bit control differs')
    old_failed=False
    try:decode_tail(modified,start,'current-tail')
    except ValueError:old_failed=True
    if not old_failed:raise ValueError('Observed-profile negative control did not reject')
    return {'body_saved':False,'source_member_sha256':digest(raw),'RAM_mutated_member_sha256':digest(modified),
        'exactly_one_wire_bit_changed':sum((a^b).bit_count() for a,b in zip(raw,modified))==1,
        'changed_only_first_bit_of_native_u8_network_field':True,'native_full_ClientInfo_boundary_and_reencoding_pass':True,
        'prior_observed_tail_decoder_rejects':True,'synthetic_mutation_is_not_an_authentic_replay':True}

if __name__=='__main__':
    from inspect_bsn_schema import analyze as inspect,load_current_PE,write_new
    output=HERE/'native-ClientInfo-current-21case-binding.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse existing report')
    _,protocol=inspect(load_current_PE());print(write_new(output,analyze(protocol)))
