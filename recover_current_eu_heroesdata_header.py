"""Reproduce one exact advertised EU HeroesData header from explicit local inputs.

This narrow research reproducer performs no acquisition or replay modification.
Only a complete SHA256 match to the fixed, replay-advertised target permits a
header write. The old fields, score shift and registry recipe remain hypotheses
for any other artifact. Raw headers and replays are private local inputs.
"""
from __future__ import annotations
import argparse,hashlib,json,os,stat
from pathlib import Path
from lossless_wire import parse,clone,encode,to_generic
from depot_s2mh_wire import decode_verified_header
from battlelobby_header_attributes import project,localization_indices,localize_package
from project_attribute_nodes import project_nodes
from registry_header_candidates import iter_candidate_vectors,position_candidates
from battlelobby_attribute_layer import _Reader,decode_layer
from battlelobby_tail import decode_tail
from audit_battlelobby_mod_metadata import audit_member
from reference_replay import inspect_reference,checked_archive
from protocol_loader import load_protocol

TARGET='f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0'
SOURCE='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9'
PRIOR='29f66c9eca1844826ad55f63eb8fd32a2d6e74ddb7931a8e835fb951f58e184d'
SCHEMA='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
ROOT='c3b3c8bc82e3a5a62e550fdde9a40c28'
HEADER_LIMIT=512*1024
REPLAY_LIMIT=3*1024*1024

def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(test,message):
    if not test:raise ValueError(message)

def read_bounded(path:Path,limit:int)->bytes:
    path=Path(path);info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink(),'Input must be a regular file')
    require(0<info.st_size<=limit,'Input exceeds its explicit size bound')
    with path.open('rb') as f:raw=f.read(limit+1)
    require(0<len(raw)<=limit,'Input grew beyond its explicit size bound')
    return raw

def new_output(path:Path,suffix:str):
    path=Path(path)
    require(path.suffix.lower()==suffix and path.parent.is_dir(),'Output needs an existing parent and expected suffix')
    if os.path.lexists(path):raise FileExistsError('Refuse existing output')

def save_exact_header(raw:bytes,path:Path,expected_sha256:str)->bool:
    """Digest+independent wire gate, then exclusive creation; no mismatch writes.

    The CLI always supplies TARGET. The explicit digest argument also permits
    small synthetic tests of this filesystem guard, without genuine raw inputs.
    """
    new_output(path,'.s2mh')
    require(type(expected_sha256) is str and len(expected_sha256)==64 and all(c in '0123456789abcdef' for c in expected_sha256),'Expected digest must be canonical SHA256')
    require(type(raw) is bytes and 0<len(raw)<=HEADER_LIMIT,'Header body exceeds bound')
    if sha(raw)!=expected_sha256:return False
    decode_verified_header(raw,expected_sha256)
    with Path(path).open('xb') as f:f.write(raw)
    require(sha(read_bounded(path,HEADER_LIMIT))==expected_sha256,'Saved output verification failed')
    return True

def _observed_reference(path:Path):
    initial=read_bounded(path,REPLAY_LIMIT)
    profile=inspect_reference(path,96477,98348)
    require(profile['file_sha256']==sha(initial) and profile['file_bytes']==len(initial),'Reference changed during inspection')
    require(profile['schema_file_sha256']==SCHEMA,'Pinned Blizzard schema differs')
    target=profile['target'];v=target['m_version']
    require(v['m_build']==v['m_baseBuild']==target['m_dataBuildNum']==98348,'Reference build/base/data must all be98348')
    require(target['m_ngdpRootKey']['m_data'].hex()==ROOT,'Reference root differs')
    p=load_protocol(96477);a=checked_archive(path)
    try:
        details=p.decode_replay_details(a.read_file('replay.details'))
        raw=a.read_file('replay.server.battlelobby')
    finally:a.close()
    require({x['m_toon']['m_region'] for x in details['m_playerList']}=={2},'Reference participants must explicitly beEU')
    require(sha(read_bounded(path,REPLAY_LIMIT))==profile['file_sha256'],'Reference changed during context read')
    mods=audit_member(raw,'observed-11','current-observed')
    identities=[]
    for entry in mods['entries']:
        r=_Reader(raw);r.position=entry['start_bit'];identities.append((r.bits(32),r.bits(32)))
    matches=[i for i,value in enumerate(identities) if value==(169992,65663)]
    require(len(matches)==1,'Expected exactly one advertised target package')
    index=matches[0];r=_Reader(raw);r.position=mods['mod_metadata_end_bit']
    handles=[r.blob(40) for _ in range(r.bits(6))]
    require(index<len(handles) and handles[index][:4]==b's2mh' and handles[index][4:8].strip(b'\0')==b'EU' and handles[index][8:]==bytes.fromhex(TARGET),'Exact target EUhandle is not advertised')
    tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
    registry=[int.from_bytes(x.value,'big') for x in tail.tokens if x.path.startswith('/collections/') and x.path.endswith('/value')]
    require(len(registry)==len(set(registry))==5418,'Expected exact-size distinct current registry')
    return profile,raw,index,registry

def assemble(source_raw:bytes,prior_raw:bytes,reference:Path):
    require(sha(source_raw)==SOURCE and sha(prior_raw)==PRIOR,'Pinned source header digests differ')
    source=parse(source_raw);prior=parse(prior_raw)
    require(encode(source)==source_raw and encode(prior)==prior_raw,'Lossless source controls failed')
    profile,raw,package_index,current=_observed_reference(reference)
    base=to_generic(source.field(0).field(24));historical=to_generic(prior.field(0).field(24))
    position=position_candidates(base,current,historical,cap=2)
    require(position['position_tuple_count']==2,'The narrow recipe requires exactly two registry choices')
    layer=decode_layer(raw,'observed-11');tokens={x.path:x.value for x in layer.tokens}
    observed={tuple(x[0][k] for k in (0,1)):x for x in project(raw,'observed-11').attributes}
    original_attrs=to_generic(source.field(0).field(5))
    attrs=localize_package([observed[tuple(x[0][k] for k in (0,1))] for x in original_attrs],package_index)
    require(len(attrs)==14 and sum(len(x[1]) for x in attrs)==5165 and max(localization_indices(attrs))==5122,'Observed attribute projection differs from the narrow recipe')
    attribute_node=project_nodes(source.field(0).field(5),attrs)
    locales={tokens[f'/locales/{i}/fourcc'].to_bytes(4,'big'):tokens[f'/locales/{i}/handles/{package_index}'] for i in range(tokens['/locales/count'])}
    require(len(locales)==12 and all(len(v)==40 and v[:4]==b's2ml' and v[4:8].strip(b'\0')==b'EU' for v in locales.values()),'Expected12observed EUlocalehandles')
    new_ids=position['new_ids_in_current_order'];witness={}
    for node in prior.field(0).field(24).value:
        if node.value in new_ids:
            require(node.value not in witness,'Historical singleton is not unique');witness[node.value]=node
    require(set(witness)==set(new_ids),'Historical singleton witness is incomplete')
    attempts=[];accepted=None
    for number,(gaps,registry) in enumerate(iter_candidate_vectors(base,current,historical,cap=2),1):
        candidate=clone(source);h=candidate.field(0)
        require(to_generic(h.field(0))=={0:169992,1:65662},'Source identity differs');h.field(0).field(1).value=65663
        h.set_field(5,clone(attribute_node))
        for array in (h.field(4).field(8),h.field(8)):
            require(len(array.value)==12,'Source locale table differs')
            for loc in array.value:
                handles=loc.field(1);name=loc.field(0).value
                require(name in locales and handles.tag==0 and len(handles.value)==1 and handles.value[0].tag==2,'Source locale wire shape differs')
                handles.value[0].value=locales[name]
        shifted=[]
        for record in h.field(7).value:
            for key in (record.field(2).field(0),record.field(2).field(1)):
                require(key.tag==4,'Field7optional shape differs')
                if key.value is not None and key.value.field(2).value:
                    index=key.value.field(2);shifted.append(index.value);index.value+=9
        require(sorted(shifted)==list(range(5114,5213)),'Field7exact99sourceindex control differs')
        insertions={}
        for gap,value in zip(gaps,new_ids):insertions.setdefault(gap,[]).append(value)
        old_nodes=source.field(0).field(24).value;nodes=[]
        for gap in range(len(old_nodes)+1):
            nodes.extend(clone(witness[value]) for value in insertions.get(gap,()))
            if gap<len(old_nodes):nodes.append(clone(old_nodes[gap]))
        h.field(24).value=nodes
        require(tuple(to_generic(h.field(24)))==registry and len(registry)==5497,'Registry vector postcondition failed')
        body=encode(candidate);require(0<len(body)<=HEADER_LIMIT,'Candidate exceeds header bound')
        digest=sha(body);match=digest==TARGET
        if match:
            require(accepted is None,'More than one target candidate')
            generic=decode_verified_header(body,TARGET)
            require(to_generic(candidate)==generic and generic[0][0]=={0:169992,1:65663} and generic[0][5]==attrs and generic[0][24]==list(registry),'Independent accepted-header postcondition failed')
            accepted=body
        attempts.append({'candidate':number,'original_array_insertion_gaps':list(gaps),'bytes':len(body),'sha256':digest,'matches_advertised_target':match,'mismatching_candidate_written':False})
    require(len(attempts)==2 and encode(source)==source_raw and encode(prior)==prior_raw,'Bounded source preservation control failed')
    report={'format':'hots-portable-exact-current-EU-header-reproduction-v1','inputs':{'source_header_sha256':SOURCE,'prior_header_sha256':PRIOR,'reference_replay_sha256':profile['file_sha256'],'reference_bytes':profile['file_bytes'],'schema_sha256':SCHEMA,'build_base_data':98348,'root_md5':ROOT,'explicit_participant_region':2,'target_package_index':package_index},'target_sha256':TARGET,'attempts':attempts,'exact_current_header_recovered':accepted is not None,'independent_complete_wire_decode_on_match':accepted is not None,'current_14_attribute_definitions_and_12_locales_observed':True,'recipe_hypotheses_accepted_only_by_exact_full_SHA':['Allother65662fieldsunchanged','Field7+9shift','Ninehistoricalsingletonregistryinsertions'],'changed_path_groups':['root/0/0/1','root/0/4/8/*/1/0','root/0/5','root/0/7/*/2/{0,1}/2','root/0/8/*/1/0','root/0/24'],'raw_header_or_player_values_in_report':False,'network_used':False,'replay_modified':False,'client_launched':False,'simulation_or_conversion_proven':False}
    return report,accepted

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source-header','prior-header','reference-replay','output','report'):ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        new_output(args.output,'.s2mh');new_output(args.report,'.json')
        outputs={args.output.resolve(),args.report.resolve()};inputs={args.source_header.resolve(),args.prior_header.resolve(),args.reference_replay.resolve()}
        require(len(outputs)==2 and not outputs&inputs,'Output paths overlap inputs')
        report,body=assemble(read_bounded(args.source_header,HEADER_LIMIT),read_bounded(args.prior_header,HEADER_LIMIT),args.reference_replay)
        report['output_written']=save_exact_header(body,args.output,TARGET) if body is not None else False
        report['producer_sha256']=sha(Path(__file__).read_bytes())
        with args.report.open('x',encoding='utf8',newline='\n') as f:json.dump(report,f,indent=2);f.write('\n')
        print(json.dumps({'exact_target_recovered':report['exact_current_header_recovered'],'output_written':report['output_written'],'report_sha256':sha(args.report.read_bytes())}))
        return 0 if body is not None else 2
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__}));return 1

if __name__=='__main__':raise SystemExit(main())
