"""Two allowlisted image fragments only; no string/address decoding or traversal.

Full-file hash passes are opaque. Selected metadata validation never follows
thread/heap/stack/custom streams. BSN probes use relative format geometry only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import uuid

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
METADATA_LIMIT=64*1024
DUMP_LIMIT=256*1024
ALLOWED=((0x02036E40,1032),(0x020399E0,4))
PRIOR_SHA='a40cde35e02707ff2c484dcc98b2bafa4a86bd30eae1ddf2d6b6fc98f7fb85ea'
DESCRIPTORS_SHA='86fdb4c998ee393a56fa9165af16d472438aee7eb3221610a3eededa366ad27f'
CASE_TIMES=('2022-07-27 22.10.05','2022-07-27 22.11.31','2022-08-09 20.10.37','2022-08-09 20.12.10','2022-08-09 20.13.42')
sha=lambda b:hashlib.sha256(b).hexdigest()

def require(value,message='Bounded approved fragment validation failed'):
    if not value:raise ValueError(message)

def select_ranges(descriptors,image_base,image_size,file_size):
    """Return only exact approved extents, never expose or follow other ranges."""
    selected={}
    for start,length,file_rva in descriptors:
        require(length>0 and start+length<=1<<64 and 0<=file_rva<=file_size and length<=file_size-file_rva)
        if image_base<=start and start+length<=image_base+image_size:
            key=(start-image_base,length)
            if key in ALLOWED:
                require(key not in selected)
                selected[key]=file_rva
    require(set(selected)==set(ALLOWED))
    require(sum(length for _,length in selected)==1036)
    return selected

def read_selected(read_at,selected):
    require(set(selected)==set(ALLOWED))
    result=[]
    for rva,length in ALLOWED:
        # The file location came only from validated MINIDUMP_MEMORY_DESCRIPTOR.
        data=read_at(selected[rva,length],length)
        require(type(data) is bytes and len(data)==length)
        result.append(data)
    return tuple(result)

def type_records_valid(raw,type_offsets,type_start,type_end,count):
    """Source-backed type metadata grammar; never reads/decodes dump strings."""
    materialized=0
    for index,start in enumerate(type_offsets):
        end=type_offsets[index+1] if index+1<count else type_end
        position=start
        def number(width,signed=False):
            nonlocal position
            require(0<=width<=end-position)
            value=int.from_bytes(raw[position:position+width],'big',signed=signed)
            position+=width;return value
        def integer(kind):
            require(0<=kind<=7)
            return number(1<<(kind>>1),not(kind&1))
        def bounds(fixed=False):
            kind=number(1);flags=0 if fixed else number(1)
            low=integer(kind);high=low if fixed else integer(kind)
            return kind,flags,low,high
        header=number(1);kind=header&63
        require(1<=kind<=16)
        children=[];limits=None
        if kind in (1,3,4):
            limits=bounds(bool(header&128))
            if kind==1:children.append(number(4))
        elif kind in (2,9,15):limits=bounds()
        elif kind in (6,7,14):
            limits=bounds();integer_type,flags,low,high=limits
            if header&128:members=high-low+1
            else:
                count_type=number(1);require(count_type<=5)
                members=number(1<<(count_type>>1))
            require(0<=members<=20000)
            materialized+=members;require(materialized<=200000)
            # No need to materialize a dense range. Sparse values are grammar
            # integers only, never treated as addresses or string pointers.
            tags=[] if header&128 else [integer(integer_type) for _ in range(members)]
            if kind!=7 and not header&128:require(len(set(tags))==members)
            if kind in (6,14):children=[number(4) for _ in range(members)]
        elif kind in (11,16):children.append(number(4))
        if limits and limits[2]>limits[3]:
            require(kind in (6,7,14) and header&128 and limits[2]==limits[3]+1)
        require(all(0<=child<count for child in children))
        if position!=end:
            require(index==count-1 and end-position<=3 and raw[position:end]==b'\0'*(end-position))
    return True

def probe_fragment(raw):
    """Bounded heuristic candidates, not an assertion of universal BSN absence.

    A full candidate must fit wholly within ONE selected fragment. The version
    search window1..16 is policy, not a source-proven exhaustive version set.
    No dump-string table entries or strings are followed or decoded.
    """
    require(type(raw) is bytes and len(raw)<=1032)
    facts=[];headers=0;unavailable=0
    for offset in range(max(0,len(raw)-19)):
        version,unknown,count,type_size,dump_size=struct.unpack_from('>5I',raw,offset)
        if not 1<=version<=16 or not 1<=count<=20000 or type_size<count:continue
        headers+=1
        type_start=20+4*count;type_end=type_start+type_size
        # Source constructor supports a no-dump variant exactly at type_end.
        end=type_end if dump_size==0 else type_end+4*count+dump_size
        if end>len(raw)-offset:
            unavailable+=1;continue
        candidate=raw[offset:offset+end]
        try:
            offsets=struct.unpack_from('>'+str(count)+'I',candidate,20)
            require(offsets[0]==type_start and list(offsets)==sorted(set(offsets)))
            require(all(type_start<=p<type_end for p in offsets))
            if dump_size:
                dump_start=type_end+4*count
                dumps=struct.unpack_from('>'+str(count)+'I',candidate,type_end)
                require(all(p==0 or dump_start<=p<end for p in dumps))
            type_records_valid(candidate,offsets,type_start,type_end,count)
        except (ValueError,struct.error):continue
        facts.append({'offset_within_fragment':offset,'framed_bytes':end,'version_word':version,
                      'type_count':count,'type_info_bytes':type_size,'dump_info_bytes':dump_size,
                      'constructor_geometry_and_all_type_records_validated':True,'dump_strings_decoded':False})
    return {'selected_bytes':len(raw),'constructor_shape_header_candidates':headers,
            'header_candidates_requiring_uncaptured_bytes':unavailable,'complete_type_grammar_candidates':facts,
            'complete_type_grammar_candidate_count':len(facts)}

def opaque_hash(path,size,counts):
    h=hashlib.sha256();done=0
    with path.open('rb') as stream:
        initial=os.fstat(stream.fileno());require(initial.st_size==size)
        while done<size:
            data=stream.read(min(16384,size-done));require(data)
            h.update(data);done+=len(data);counts['opaque_full_file_hash_bytes']+=len(data)
        final=os.fstat(stream.fileno())
    require((initial.st_size,initial.st_mtime_ns)==(final.st_size,final.st_mtime_ns))
    return h.hexdigest()

def analyze(root):
    counts=Counter();prior_raw=(WORK/'legacy41810-crash-metadata/five-preserved41810-module-metadata.json').read_bytes()
    descriptor_raw=(WORK/'legacy41810-image-range-feasibility/old41810-image-capture-descriptor-feasibility.json').read_bytes()
    counts['pinned_receipt_bytes']+=len(prior_raw)+len(descriptor_raw)
    require(sha(prior_raw)==PRIOR_SHA and sha(descriptor_raw)==DESCRIPTORS_SHA)
    prior=json.loads(prior_raw);descriptor_report=json.loads(descriptor_raw)
    require(prior['case_count']==descriptor_report['case_count']==5)
    require(prior['all_ten_input_file_digests_unchanged'] and descriptor_report['all_source_dump_hashes_unchanged_and_equal_existing_pins'])
    root=root.resolve(strict=True);rows=[];private_fragments=[]
    for index,(time,reference,descriptor_ref) in enumerate(zip(CASE_TIMES,prior['cases'],descriptor_report['cases'])):
        require(reference['case_id']==descriptor_ref['case_id'] and reference['folder_time_label_only']==time)
        matches=[p for p in root.glob(time+'*B41810 Error') if p.is_dir() and not p.is_symlink()]
        require(len(matches)==1);expected_folder=matches[0]
        path=expected_folder/(expected_folder.name+'.dmp')
        require(path.is_file() and not path.is_symlink())
        size=path.stat().st_size;require(size==reference['dump']['bytes']<=DUMP_LIMIT)
        expected=reference['dump']['sha256_before'];require(expected==reference['dump']['sha256_after']==descriptor_ref['dump_SHA256_before']==descriptor_ref['dump_SHA256_after'])
        require(opaque_hash(path,size,counts)==expected)
        selected_bytes=0
        with path.open('rb') as stream:
            def metadata(offset,length):
                require(type(offset) is int and type(length) is int and 0<=offset<=size and 0<=length<=size-offset)
                require(counts['selected_metadata_bytes']+length<=METADATA_LIMIT)
                stream.seek(offset);data=stream.read(length);require(len(data)==length)
                counts['selected_metadata_bytes']+=length;return data
            header=struct.unpack('<IIIIIIQ',metadata(0,32))
            require(header[0]==0x504d444d and header[1]==reference['dump']['header_version'] and 1<=header[2]<=128)
            directory=[struct.unpack('<III',metadata(header[3]+12*i,12)) for i in range(header[2])]
            require(all(0<=rva<=size and length<=size-rva for _,length,rva in directory))
            modules=[row for row in directory if row[0]==4];memories=[row for row in directory if row[0]==5]
            require(len(modules)==len(memories)==1)
            _,module_size,module_rva=modules[0]
            module_count=struct.unpack('<I',metadata(module_rva,4))[0]
            require(module_count==reference['dump']['module_count'] and 4+108*module_count<=module_size)
            target=reference['dump']['target'];require(target['module_list_ordinal']==0)
            module=metadata(module_rva+4,108)
            base,image_size,checksum,timestamp=struct.unpack_from('<QIII',module)
            require(base==int(target['base_of_image'],16) and image_size==target['size_of_image'] and checksum==target['PE_checksum'] and timestamp==target['PE_timestamp'])
            fixed=struct.unpack_from('<13I',module,24)
            require(fixed[0]==0xfeef04bd)
            require((fixed[2]>>16,fixed[2]&65535,fixed[3]>>16,fixed[3]&65535)==(0,17,0,41810))
            require((fixed[4]>>16,fixed[4]&65535,fixed[5]>>16,fixed[5]&65535)==(0,17,0,41810))
            cv_size,cv_rva=struct.unpack_from('<II',module,76)
            require(24<=cv_size<=8192 and 0<=cv_rva<=size and cv_size<=size-cv_rva)
            cv=metadata(cv_rva,24)
            require(cv[:4]==b'RSDS' and cv[4:20]==uuid.UUID(target['CodeView']['GUID']).bytes_le and struct.unpack_from('<I',cv,20)[0]==target['CodeView']['age_decimal'])
            _,mem_size,mem_rva=memories[0]
            count=struct.unpack('<I',metadata(mem_rva,4))[0]
            require(count==descriptor_ref['memory_range_count']<=2048 and mem_size==4+16*count)
            values=metadata(mem_rva+4,16*count)
            descriptors=[struct.unpack_from('<QII',values,16*i) for i in range(count)]
            selected=select_ranges(descriptors,base,image_size,size)
            def image_read(offset,length):
                nonlocal selected_bytes
                require((offset,length) in {(selected[key],key[1]) for key in ALLOWED})
                require(selected_bytes+length<=1036 and 0<=offset<=size-length)
                stream.seek(offset);data=stream.read(length);require(len(data)==length)
                selected_bytes+=length;counts['selected_pointed_image_bytes']+=length;return data
            fragments=read_selected(image_read,selected)
        require(selected_bytes==1036 and opaque_hash(path,size,counts)==expected)
        private_fragments.append(fragments)
        rows.append({'case_id':reference['case_id'],'dump_bytes':size,'dump_sha256_before_and_after':expected,
                     'header_module_fixed_versions_RSDS_and_descriptors_revalidated':True,'selected_pointed_image_bytes':selected_bytes,
                     'fragments':[{'image_relative_start':rva,'bytes':length,'sha256':sha(data),'probe':probe_fragment(data)}
                                  for (rva,length),data in zip(ALLOWED,fragments)]})
    require(len(rows)==5 and counts['selected_pointed_image_bytes']==5180)
    pairs=[]
    for fragment_index,(rva,length) in enumerate(ALLOWED):
        equal=different=0;differences=[]
        for a in range(5):
            for b in range(a+1,5):
                first,second=private_fragments[a][fragment_index],private_fragments[b][fragment_index]
                same=first==second;equal+=same;different+=not same
                differences.append(sum(x!=y for x,y in zip(first,second)))
        pairs.append({'image_relative_start':rva,'bytes':length,'exact_equal_case_pairs':equal,'different_case_pairs':different,
                      'different_byte_count_min':min(differences),'different_byte_count_max':max(differences),
                      'distinct_fragment_SHA256_count':len({sha(value[fragment_index]) for value in private_fragments})})
    return {'format':'hots-five41810-approved-image-fragment-BSN-probe-v1','producer_sha256':sha(Path(__file__).read_bytes()),
            'pinned_module_receipt_sha256':PRIOR_SHA,'pinned_descriptor_receipt_sha256':DESCRIPTORS_SHA,
            'case_count':len(rows),'cases':rows,'cross_case_fragment_reproducibility':pairs,'read_counts':dict(counts),
            'selected_image_byte_limit_per_case':1036,'selected_metadata_limit_total_bytes':METADATA_LIMIT,
            'complete_constructor_type_grammar_candidates':sum(fragment['probe']['complete_type_grammar_candidate_count'] for row in rows for fragment in row['fragments']),
            'all_five_dump_hashes_unchanged':True,'fragment_strings_addresses_or_pointers_decoded_or_emitted':False,
            'other_pointed_memory_heap_stack_thread_or_custom_data_read_or_decoded':False,
            'static_code_data_or_PE_section_classification_performed':False,'raw_dump_or_fragment_bytes_exported':False,
            'discontinuous_fragments_concatenated_as_a_schema':False,'game_process_debugger_or_native_code_loaded':False,
            'network_or_repo_cloud_writes':False,
            'limits':['Full-file hash passes are opaque; only header/directory/target-module/24-byteRSDS/memory-descriptor metadata are structurally decoded.',
                      'Only the two exact allowed wholly-module image ranges are read as pointed memory. No names or pointer-sized values from those fragments are decoded.',
                      'The version-word1..16 constructor heuristic is bounded and not source-proven exhaustive. No complete candidate is promoted from partial/unavailable bytes.',
                      'No strings, dump-string entries or pointers are followed during candidate probing; complete type grammar facts alone would not prove a named schema.',
                      'No old ClientInfo width, field name, serialization layout or executable section classification follows from this bounded probe.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(args.output.parent.is_dir() and not args.output.exists() and not args.output.is_symlink())
    data=(json.dumps(analyze(args.input_root),indent=2,sort_keys=True)+'\n').encode()
    require(len(data)<=64*1024)
    with args.output.open('xb') as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
