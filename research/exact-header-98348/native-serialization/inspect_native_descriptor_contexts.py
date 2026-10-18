"""One additional byte-only PE pass; descriptor context union capped at64KiB."""
import hashlib
import importlib.util
import json
import os
import re
import struct
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('static_pe_parser',HERE/'inspect_native_serialization_labels.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
IMAGE=module.IMAGE
sha=lambda b:hashlib.sha256(b).hexdigest()
TARGETS=('m_licenseInstance','m_licenseCatalog','m_clientLicensesList','m_mapNamespace')
IDENTIFIER=re.compile(rb'[A-Za-z_][A-Za-z0-9_.]{0,127}\Z')

def varint(b,pos,end):
    value=0
    for shift in range(0,70,7):
        if pos>=end:raise ValueError('truncated varint')
        c=b[pos];pos+=1;value|=(c&127)<<shift
        if not c&128:return value,pos
    raise ValueError('varint exceeds64bits')

def wire(b,start,end):
    if not start<end or end-start>65536:raise ValueError('message bound')
    fields=[];pos=start
    while pos<end:
        key,pos=varint(b,pos,end);number,kind=key>>3,key&7
        if not number or len(fields)>=4096:raise ValueError('field bound')
        if kind==0:value,pos=varint(b,pos,end)
        elif kind in (1,5):
            n=8 if kind==1 else 4
            if pos+n>end:raise ValueError('truncated fixed')
            value=b[pos:pos+n];pos+=n
        elif kind==2:
            n,pos=varint(b,pos,end)
            if n>end-pos:raise ValueError('truncated blob')
            value=b[pos:pos+n];pos+=n
        else:raise ValueError('unsupported wire kind')
        fields.append((number,kind,value))
    return fields

def field_descriptor(blob):
    fields=wire(blob,0,len(blob));seen={}
    for number,kind,value in fields:
        if number in seen:raise ValueError('duplicate descriptor field')
        if number not in {1,2,3,4,5,6,7,8,9,10,17}:raise ValueError('unknown descriptor field')
        seen[number]=(kind,value)
    if not {1,3,4,5}<=set(seen):raise ValueError('missing field descriptor keys')
    if seen[1][0]!=2 or not IDENTIFIER.fullmatch(seen[1][1]):raise ValueError('invalid field name')
    if any(seen[k][0]!=0 for k in (3,4,5)):raise ValueError('descriptor enum wire mismatch')
    if not 1<=seen[3][1]<(1<<29) or seen[4][1] not in (1,2,3) or not 1<=seen[5][1]<=18:raise ValueError('descriptor enums differ')
    if 6 in seen and (seen[6][0]!=2 or not IDENTIFIER.fullmatch(seen[6][1])):raise ValueError('invalid type name')
    result={'name':seen[1][1].decode(),'number':seen[3][1],'label_enum':seen[4][1],'type_enum':seen[5][1]}
    if 6 in seen:result['type_name']=seen[6][1].decode()
    return result

def framed_payloads(raw,start,end,payload_start):
    for pos in range(max(start,payload_start-6),payload_start):
        try:
            key,p=varint(raw,pos,payload_start)
            if key&7!=2:continue
            size,p=varint(raw,p,payload_start)
            if p!=payload_start or not 0<size<=end-p:continue
            yield pos,key>>3,p,p+size
        except ValueError:continue

def main():
    output=HERE/'native-descriptor-contexts-98348.json'
    if output.exists():raise FileExistsError('Refuse existing context report')
    initial_report=json.loads((HERE/'native-serialization-labels-98348.json').read_bytes())
    initial_source=(HERE/'inspect_native_serialization_labels.py').read_bytes()
    assert sha(initial_source)==initial_report['producer_sha256']
    with IMAGE.open('rb') as f:
        before=os.fstat(f.fileno());assert before.st_size==53573840<=512*1024*1024
        raw=f.read(512*1024*1024+1);after=os.fstat(f.fileno())
    assert len(raw)==before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
    assert sha(raw)==module.EXPECTED_SHA
    pe=module.PE(raw)
    occurrences=[]
    for term in TARGETS:
        position=0;found=[]
        while True:
            p=raw.find(term.encode(),position)
            if p<0:break
            found.append(p);position=p+len(term)
            assert len(found)<=16
        occurrences.extend((term,p) for p in found)
    assert len(occurrences)<=24
    intervals=sorted((max(0,p-1024),min(len(raw),p+2048)) for _,p in occurrences)
    merged=[]
    for start,end in intervals:
        if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
        else:merged.append([start,end])
    context_bytes=sum(end-start for start,end in merged);assert context_bytes<=65536
    rows=[];container_candidates={}
    for term,p in occurrences:
        start,end=next((s,e) for s,e in merged if s<=p<e)
        labels=[]
        for match in re.finditer(rb'[\x20-\x7e]{4,256}',raw[start:end]):
            value=match.group().decode()
            if module.SAFE_LABEL.fullmatch(value):
                off=start+match.start();labels.append({'label':value,**pe.location(off)})
        nearby=sorted(labels,key=lambda row:abs(row['file_offset']-p))[:32]
        row={'target':term,**pe.location(p),'neighbor_label_window_start':start,'neighbor_label_window_end':end,
             'nearest_allowlisted_labels':sorted(nearby,key=lambda row:row['file_offset']),
             'protobuf_name_key_length_prefix_matches':raw[p-2:p]==bytes((10,len(term)))}
        descriptors=[]
        if row['protobuf_name_key_length_prefix_matches']:
            for frame,key,a,b in framed_payloads(raw,start,end,p-2):
                try:desc=field_descriptor(raw[a:b])
                except ValueError:continue
                if desc['name']==term:
                    descriptors.append({'enclosing_field_number':key,'field_descriptor_start':a,'field_descriptor_end':b,
                                        'complete_contiguous_payload_sha256':sha(raw[a:b]),'descriptor':desc})
        row['complete_protobuf_FieldDescriptorProto_candidates']=descriptors
        # Look only inside the bounded contexts for complete framed DescriptorProto.
        for match in re.finditer(rb'\x0a[\x01-\x7f][A-Za-z_]',raw[start:end]):
            candidate=start+match.start()
            for frame,key,a,b in framed_payloads(raw,start,end,candidate):
                if not a<=p<b:continue
                try:
                    fields=wire(raw,a,b);names=[v for n,k,v in fields if n==1 and k==2]
                    if len(names)!=1 or not IDENTIFIER.fullmatch(names[0]):continue
                    body=[field_descriptor(v) for n,k,v in fields if n==2 and k==2]
                    if not body or len(body)>128 or not any(d['name']==term for d in body):continue
                    if len({d['name'] for d in body})!=len(body) or len({d['number'] for d in body})!=len(body):continue
                    container_candidates[(a,b)]={'message_name':names[0].decode(),'start':a,'end':b,'outer_field_number':key,
                        'payload_sha256':sha(raw[a:b]),'complete_FieldDescriptorProto_children':body,
                        'classification':'protobuf-compatible-contiguous-DescriptorProto-candidate'}
                except ValueError:continue
        rows.append(row)
    final=IMAGE.stat();assert final.st_size==before.st_size and final.st_mtime_ns==before.st_mtime_ns
    report={'format':'hots-native-bounded-descriptor-context-research-v1','producer_sha256':sha(Path(__file__).read_bytes()),
        'PE_parser_source_sha256':sha(initial_source),'initial_report_sha256':sha((HERE/'native-serialization-labels-98348.json').read_bytes()),
        'source_PE_sha256':sha(raw),'source_PE_bytes':len(raw),'additional_PE_byte_read_passes':1,
        'total_PE_read_passes_for_this_research':2,'cumulative_PE_bytes_read':2*len(raw),
        'source_size_and_mtime_unchanged':True,'context_union_bytes':context_bytes,'maximum_context_union_bytes':65536,
        'contexts_are_label_metadata_only_no_raw_body_dump':True,'target_occurrences':rows,
        'complete_protobuf_DescriptorProto_candidates':list(container_candidates.values()),
        'game_or_client_code_executed_or_loaded':False,'disassembler_or_debugger_used':False,'new_network_requests':0,
        'replay_modified':False,'new_header_candidate':False,'opaque174_to198_or_32byte_layout_bound':False,
        'limitations':['A protobuf-compatible field/message grammar needs complete-container/type-context verification before attribution.',
            'Nearby labels alone do not establish shared type membership or a connection to replay.server.battlelobby.',
            'No code crossreference, serialization bit width, account value or missing MapNamespace value is inferred.']}
    encoded=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode();assert len(encoded)<=256*1024
    with output.open('xb') as f:f.write(encoded)
    print(json.dumps({'report_sha256':sha(encoded),'report_bytes':len(encoded),'context_bytes':context_bytes,
                      'occurrences':len(rows),'complete_message_candidates':len(container_candidates),
                      'complete_field_candidates':sum(len(r['complete_protobuf_FieldDescriptorProto_candidates']) for r in rows)}))

if __name__=='__main__':main()
