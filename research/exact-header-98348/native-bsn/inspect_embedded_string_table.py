"""Bounded byte-only string-table boundary and concrete reference research."""
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
WORK=HERE.parent
MAX_SPAN=2*1024*1024
TARGETS=(('m_clientLicensesList',43426603),('m_mapNamespace',43476303))
PARSER=WORK/'native-serialization-98348/inspect_native_serialization_labels.py'
PARSER_SHA='4c43053e77a9ee4997ab972f6d039f31e1e92902c5e58d514aa90b0af4bdb523'
BAD=re.compile(rb'[^\x00\x20-\x7e]')
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def ascii_nul_span(raw,anchor,cap=MAX_SPAN):
    if type(raw) is not bytes or type(anchor) is not int or not 0<=anchor<len(raw):raise ValueError('Invalid span input')
    if type(cap) is not int or not 1<=cap<=MAX_SPAN or BAD.fullmatch(raw[anchor:anchor+1]):raise ValueError('Invalid cap/anchor byte')
    a=max(0,anchor-cap);b=min(len(raw),anchor+cap+1)
    left=list(BAD.finditer(raw,a,anchor))
    start=left[-1].end() if left else a
    right=BAD.search(raw,anchor,b)
    end=right.start() if right else b
    if (not left and a>0) or (right is None and b<len(raw)) or end-start>cap:raise ValueError('Actual maximal boundaries exceed cap')
    if start and not BAD.fullmatch(raw[start-1:start]):raise ValueError('Left maximal boundary unproven')
    if end<len(raw) and not BAD.fullmatch(raw[end:end+1]):raise ValueError('Right maximal boundary unproven')
    return start,end

def cstrings(raw,start,end):
    if not 0<=start<end<=len(raw) or end-start>MAX_SPAN or BAD.search(raw,start,end):raise ValueError('Invalid string-table span')
    result=[]
    for match in re.finditer(rb'[^\x00]+',raw[start:end]):
        if len(result)>=65536:raise ValueError('String count exceeds bound')
        a=start+match.start();b=start+match.end()
        result.append((a,b,raw[a:b]))
    return result

def occurrences(raw,needle,cap=128):
    result=[];pos=0
    while True:
        at=raw.find(needle,pos)
        if at<0:break
        if len(result)>=cap:raise ValueError('Reference byte-match cap exceeded')
        result.append(at);pos=at+1
    return result

def main():
    out=HERE/'embedded-string-table-boundaries-98348.json'
    if out.exists():raise FileExistsError('Refuse existing report')
    assert sha(PARSER.read_bytes())==PARSER_SHA
    spec=importlib.util.spec_from_file_location('pinned_static_PE',PARSER)
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    assert not parser.IMAGE.is_symlink()
    with parser.IMAGE.open('rb') as f:
        before=os.fstat(f.fileno());assert before.st_size==53573840<=512*1024*1024
        raw=f.read(512*1024*1024+1);after=os.fstat(f.fileno())
    assert len(raw)==before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
    assert sha(raw)==parser.EXPECTED_SHA
    pe=parser.PE(raw)
    spans={}
    for name,offset in TARGETS:
        assert raw[offset:offset+len(name)+1]==name.encode()+b'\0'
        start,end=ascii_nul_span(raw,offset)
        spans.setdefault((start,end),[]).append((name,offset))
    results=[]
    for (start,end),targets in spans.items():
        strings=cstrings(raw,start,end)
        assert strings
        all_terminated=all(raw[b:b+1]==b'\0' for _,b,_ in strings)
        assert len(strings)==len(set(a for a,_,_ in strings))
        lookup={a:(index,b,value) for index,(a,b,value) in enumerate(strings)}
        target_rows=[]
        for name,p in targets:
            index,b,value=lookup[p];assert value==name.encode()
            target_rows.append({'label':name,'location':pe.location(p),'relative_to_maximal_span_start':p-start,
                                'nonempty_token_index_zero_based':index,'NUL_terminated':raw[b]==0})
        def safe_token(row):
            a,b,value=row
            label=value.decode('ascii')
            return {'location':pe.location(a),'relative_offset':a-start,'bytes':len(value),
                    'safe_label':label if parser.SAFE_LABEL.fullmatch(label) else None,'NUL_terminated':raw[b:b+1]==b'\0'}
        prefix_start=max(0,(start-64)&~3);suffix_start=(end+3)&~3
        prefix=[{'file_offset':p,'u32_le':struct.unpack_from('<I',raw,p)[0]} for p in range(prefix_start,start-3,4)]
        suffix=[{'file_offset':p,'u32_le':struct.unpack_from('<I',raw,p)[0]} for p in range(suffix_start,min(len(raw)-3,suffix_start+64),4)]
        candidates=[]
        base_locations=[('maximal_ASCII_or_NUL_span_start',start),('first_nonempty_token',strings[0][0])]
        bnet=next((a for a,_,value in strings if value.startswith(b'Battlenet::')),None)
        if bnet is not None:base_locations.append(('first_Battlenet_name_in_span',bnet))
        seen=set()
        for kind,base in base_locations:
            if base in seen:continue
            seen.add(base);loc=pe.location(base)
            matches={}
            for form,needle in (('absolute_VA_u64',struct.pack('<Q',pe.imagebase+loc['rva'])),
                                ('image_RVA_u32',struct.pack('<I',loc['rva']))):
                matches[form]=[pe.location(p) for p in occurrences(raw,needle)]
            candidates.append({'base_hypothesis':kind,'location':loc,'raw_integer_byte_matches':matches})
        # A concrete offset-array probe: at least eight exact consecutive token starts.
        # No lone integer match is interpreted as an index/reference.
        sequence_probes=[]
        sample_indices=sorted(set([0]+[max(0,lookup[p][0]-4) for _,p in targets]))
        for index in sample_indices:
            selection=strings[index:index+8]
            if len(selection)!=8:continue
            offsets=[a-start for a,_,_ in selection]
            needle=struct.pack('<8I',*offsets)
            hits=occurrences(raw,needle,16)
            # Negative control changes the order while preserving the scalar set.
            wrong=struct.pack('<8I',*(offsets[1:]+offsets[:1]))
            wrong_hits=occurrences(raw,wrong,16)
            sequence_probes.append({'first_nonempty_token_index':index,'entries':8,
                'relative_to':'maximal_span_start','exact_consecutive_u32_offset_sequence_matches':[pe.location(p) for p in hits],
                'rotated_sequence_negative_matches':[pe.location(p) for p in wrong_hits],
                'individual_scalar_matches_not_claimed_as_references':True})
        numeric_matches=[]
        quantities={'span_bytes':end-start,'nonempty_token_count':len(strings),'NUL_byte_count':raw[start:end].count(0)}
        for side,words in (('prefix',prefix),('suffix',suffix)):
            for word in words:
                for meaning,value in quantities.items():
                    if word['u32_le']==value:numeric_matches.append({'side':side,**word,'equals_measured':meaning})
        results.append({'maximal_span_start':pe.location(start),'maximal_span_end_exclusive':pe.location(end),
            'span_bytes':end-start,'span_sha256':sha(raw[start:end]),'both_boundaries_reached_inside_2MiB_cap':True,
            'preceding_boundary_byte':raw[start-1] if start else None,'following_boundary_byte':raw[end] if end<len(raw) else None,
            'all_span_bytes_are_NUL_or_printable_ASCII':True,'all_nonempty_tokens_have_NUL_terminators':all_terminated,
            'nonempty_token_count':len(strings),'distinct_nonempty_token_count':len({value for _,_,value in strings}),
            'NUL_byte_count':quantities['NUL_byte_count'],'target_tokens':target_rows,
            'first_eight_token_summaries':[safe_token(row) for row in strings[:8]],
            'last_eight_token_summaries':[safe_token(row) for row in strings[-8:]],
            'prefix_aligned_u32_words':prefix,'suffix_aligned_u32_words':suffix,'boundary_numeric_quantity_matches':numeric_matches,
            'candidate_base_pointer_byte_matches':candidates,'ordered_offset_array_probes':sequence_probes,
            'true_runtime_table_base_or_reference_format_established':False})
    final=parser.IMAGE.stat();assert final.st_size==before.st_size and final.st_mtime_ns==before.st_mtime_ns
    report={'format':'hots-native-maximal-NUL-string-span-research-v1','producer_sha256':sha(Path(__file__).read_bytes()),
        'PE_parser_source_sha256':PARSER_SHA,'source_PE_sha256':sha(raw),'source_PE_bytes':len(raw),
        'this_operation_PE_read_passes':1,'this_operation_PE_bytes_read':len(raw),
        'maximum_span_bytes':MAX_SPAN,'requested_anchors':[{'name':n,'file_offset':p} for n,p in TARGETS],
        'distinct_maximal_spans':len(results),'results':results,'source_size_and_mtime_unchanged':True,
        'game_or_client_image_executed_or_loaded':False,'debugger_disassembler_or_process_used':False,
        'raw_binary_or_complete_string_table_dump_saved':False,'new_network_requests':0,'repo_modified':False,
        'layout_174_198_or_availability32B_semantics_proven':False,'new_header_candidate':False,
        'limitations':['A maximal printable/NUL span proves physical bounds and C-string segmentation only.',
            'Leading/trailing printable bytes or NUL padding can belong to adjacent data; an actual runtime string-table base is not inferred.',
            'Raw pointer-pattern and exact offset-array probes are data observations, not code crossreferences or semantic use proof.',
            'No complete typed-schema grammar or serializer widths are established unless a separate validated container is identified.']}
    encoded=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode();assert len(encoded)<=256*1024
    with out.open('xb') as f:f.write(encoded)
    print(json.dumps({'report_sha256':sha(encoded),'report_bytes':len(encoded),'distinct_spans':len(results),
                      'span_bytes':[row['span_bytes'] for row in results],'tokens':[row['nonempty_token_count'] for row in results]}))

if __name__=='__main__':main()
