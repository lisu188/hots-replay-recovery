"""Byte-only, one-file PE research. Never execute/map/load the inspected image."""
import collections
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
IMAGE=Path('C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe')
EXPECTED_SHA='efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
MAX_IMAGE=512*1024*1024
MAX_REPORT=256*1024
WORDS=re.compile(r'replay|battle.?lobby|licen[cs]e|reward|collection|serializ|availability|player|map_?namespace',re.I)
SAFE_LABEL=re.compile(r'[A-Za-z0-9_@?$:.<>(), \[\]*=+!~-]{4,192}\Z')
ASCII_RUNS=re.compile(rb'[\x20-\x7e]{4,2048}')
UTF16_RUNS=re.compile(rb'(?:[\x20-\x7e]\x00){4,2048}')
sha=lambda b:hashlib.sha256(b).hexdigest()

def require(condition,message):
    if not condition:raise ValueError(message)

class PE:
    def __init__(self,raw):
        self.raw=raw
        require(raw[:2]==b'MZ' and len(raw)>0x100,'DOS header differs')
        pe=self.u32(0x3c)
        require(pe+24<=len(raw) and raw[pe:pe+4]==b'PE\0\0','PE header differs')
        self.machine,self.nsections,self.timestamp=struct.unpack_from('<HHI',raw,pe+4)
        optional_size=self.u16(pe+20);optional=pe+24
        require(self.machine==0x8664 and self.u16(optional)==0x20b,'Expected AMD64 PE32+')
        require(0<self.nsections<=64 and optional_size>=240,'Optional/section bound differs')
        self.imagebase=self.u64(optional+24);self.sizeofimage=self.u32(optional+56)
        self.headersize=self.u32(optional+60);self.sections=[]
        self.resource_rva,self.resource_size=struct.unpack_from('<II',raw,optional+112+2*8)
        for i in range(self.nsections):
            pos=optional+optional_size+i*40
            require(pos+40<=len(raw),'Section header truncated')
            name=raw[pos:pos+8].rstrip(b'\0').decode('ascii','strict')
            virtual_size,rva,size,offset=struct.unpack_from('<IIII',raw,pos+8)
            flags=self.u32(pos+36)
            require(offset+size<=len(raw),'Section exceeds bounded image')
            self.sections.append({'name':name,'rva':rva,'virtual_size':virtual_size,'raw_size':size,'raw_offset':offset,'characteristics':flags})
    def u16(self,p):return struct.unpack_from('<H',self.raw,p)[0]
    def u32(self,p):return struct.unpack_from('<I',self.raw,p)[0]
    def u64(self,p):return struct.unpack_from('<Q',self.raw,p)[0]
    def section_at(self,p):
        return next((s for s in self.sections if s['raw_offset']<=p<s['raw_offset']+s['raw_size']),None)
    def location(self,p):
        s=self.section_at(p)
        return {'file_offset':p,'section':s['name'] if s else None,
                'rva':s['rva']+p-s['raw_offset'] if s else p if p<self.headersize else None}
    def rva_offset(self,rva):
        for s in self.sections:
            if s['rva']<=rva<s['rva']+s['raw_size']:return s['raw_offset']+rva-s['rva']
        if 0<=rva<self.headersize:return rva
        raise ValueError('RVA has no physical bytes')
    def version(self):
        root=self.rva_offset(self.resource_rva)
        limit=root+self.resource_size
        require(limit<=len(self.raw) and self.resource_size<=16*1024*1024,'Resource bound differs')
        def entries(offset):
            pos=root+offset
            require(root<=pos and pos+16<=limit,'Resource directory outside section')
            count=self.u16(pos+12)+self.u16(pos+14)
            require(count<=4096 and pos+16+8*count<=limit,'Resource count exceeds bound')
            return [struct.unpack_from('<II',self.raw,pos+16+8*i) for i in range(count)]
        rows=[value for name,value in entries(0) if name==16]
        require(len(rows)==1 and rows[0]&0x80000000,'Version resource not unique')
        pending=[(rows[0]&0x7fffffff,0)];leaves=[]
        while pending:
            offset,depth=pending.pop();require(depth<=4,'Version directory depth exceeds bound')
            for _,value in entries(offset):
                if value&0x80000000:pending.append((value&0x7fffffff,depth+1))
                else:
                    pos=root+value;require(pos+16<=limit,'Version leaf outside resource')
                    rva,size=struct.unpack_from('<II',self.raw,pos)
                    require(size<=65536,'Version value exceeds64KiB')
                    filepos=self.rva_offset(rva);leaves.append(self.raw[filepos:filepos+size])
        require(0<len(leaves)<=8,'Version leaf count differs')
        versions=[]
        for blob in leaves:
            strings={};fixed=None;nodes=0
            def node(pos,end,depth):
                nonlocal fixed,nodes
                nodes+=1;require(nodes<=1024 and depth<=8 and pos+6<=end,'Version node bound differs')
                length,value_len,kind=struct.unpack_from('<HHH',blob,pos)
                require(length>=6 and pos+length<=end,'Version node length differs')
                stop=pos+length;k=pos+6;chars=[]
                while True:
                    require(k+2<=stop and len(chars)<128,'Version key malformed')
                    code=struct.unpack_from('<H',blob,k)[0];k+=2
                    if code==0:break
                    chars.append(chr(code))
                key=''.join(chars);v=(k+3)&~3
                value_bytes=value_len*(2 if kind==1 else 1)
                require(v+value_bytes<=stop,'Version value truncated')
                if key=='VS_VERSION_INFO':
                    require(value_bytes==52,'Fixed version size differs')
                    values=struct.unpack_from('<13I',blob,v)
                    require(values[0]==0xfeef04bd,'Fixed version signature differs')
                    fixed={'file_version_words':[values[2]>>16,values[2]&65535,values[3]>>16,values[3]&65535],
                           'product_version_words':[values[4]>>16,values[4]&65535,values[5]>>16,values[5]&65535]}
                elif key in ('FileVersion','ProductVersion','OriginalFilename','FileDescription','ProductName','CompanyName'):
                    require(kind==1 and value_bytes<=512,'String version value differs')
                    value=blob[v:v+value_bytes].decode('utf-16le').rstrip('\0')
                    require(all(32<=ord(x)<127 for x in value),'Nonpublic version text outside allowlist')
                    strings[key]=value
                child=(v+value_bytes+3)&~3
                while child+6<=stop:
                    child_len=struct.unpack_from('<H',blob,child)[0]
                    if not child_len:break
                    node(child,stop,depth+1);child=(child+child_len+3)&~3
            node(0,len(blob),0)
            require(fixed is not None,'Fixed version absent')
            versions.append({'fixed':fixed,'strings':strings})
        return versions

def category(label):
    low=label.lower()
    if 'mapnamespace' in low or 'map_namespace' in low:return 'map-namespace-label'
    if low.startswith('replay.') or 'battlelobby' in low or 'battle_lobby' in low:return 'replay-stream-or-battlelobby-label'
    if label.startswith('.?A') or label.startswith('??_R'):
        return 'MSVC-RTTI-type-name-candidate'
    if re.fullmatch(r'CReward[A-Za-z0-9_]*',label):return 'reward-catalog-type-label'
    if label.startswith(('m_','s_')):return 'field-spelling-candidate'
    if 'serializ' in low:return 'serialization-word-label'
    return 'other-target-keyword-label'

def main():
    output=HERE/'native-serialization-labels-98348.json'
    require(not output.exists(),'Refuse existing research report')
    require(not IMAGE.is_symlink(),'Refuse final image symlink')
    with IMAGE.open('rb') as f:
        before=os.fstat(f.fileno())
        require(stat.S_ISREG(before.st_mode) and 0<before.st_size<=MAX_IMAGE,'Image exceeds single-file bound')
        raw=f.read(MAX_IMAGE+1);after=os.fstat(f.fileno())
    require(len(raw)==before.st_size<=MAX_IMAGE and before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns,'Image changed or exceeded bounded read')
    require(sha(raw)==EXPECTED_SHA,'Recorded Base98348 image SHA differs')
    pe=PE(raw);versions=pe.version()
    require(any(v['strings'].get('FileVersion')=='2.57.0.98348' for v in versions),'Actual string FileVersion differs')
    matched=[];counts=collections.Counter();excluded=collections.Counter()
    for encoding,pattern in (('ASCII',ASCII_RUNS),('UTF-16LE',UTF16_RUNS)):
        for match in pattern.finditer(raw):
            b=match.group();label=b.decode('ascii' if encoding=='ASCII' else 'utf-16le')
            if not WORDS.search(label):continue
            loc=pe.location(match.start())
            if not SAFE_LABEL.fullmatch(label):excluded['non-label-or-long-'+encoding]+=1;continue
            if loc['section'] is None:excluded['outside-PE-section-'+encoding]+=1;continue
            c=category(label);counts[c]+=1
            matched.append({'label':label,'encoding':encoding,'category':c,**loc})
    priority={'map-namespace-label':0,'replay-stream-or-battlelobby-label':0,'MSVC-RTTI-type-name-candidate':1,'field-spelling-candidate':2,
              'serialization-word-label':3,'reward-catalog-type-label':4,'other-target-keyword-label':5}
    caps={'map-namespace-label':48,'replay-stream-or-battlelobby-label':64,'MSVC-RTTI-type-name-candidate':112,'field-spelling-candidate':48,
          'serialization-word-label':48,'reward-catalog-type-label':48,'other-target-keyword-label':48}
    selected=[];saved=collections.Counter()
    for row in sorted(matched,key=lambda row:(priority[row['category']],row['file_offset'])):
        c=row['category']
        if len(selected)>=320 or saved[c]>=caps[c]:continue
        selected.append(row);saved[c]+=1
    # Data-only RTTI structure candidates; no virtual function is invoked.
    rtti=[]
    rdata=[s for s in pe.sections if s['name']=='.rdata']
    if len(rdata)==1:
        rd=rdata[0];view=raw[rd['raw_offset']:rd['raw_offset']+rd['raw_size']]
        for row in selected:
            if row['category']!='MSVC-RTTI-type-name-candidate' or not row['label'].startswith('.?A'):continue
            descriptor_offset=row['file_offset']-16
            loc=pe.location(descriptor_offset)
            if loc['rva'] is None or descriptor_offset<0:continue
            key=struct.pack('<I',loc['rva'])
            start=0;valid=[]
            while len(valid)<4:
                found=view.find(key,start)
                if found<0:break
                start=found+1;pos=rd['raw_offset']+found-12
                if pos<rd['raw_offset'] or pos+24>rd['raw_offset']+rd['raw_size']:continue
                signature,offset,cd_offset,type_rva,hierarchy_rva,self_rva=struct.unpack_from('<6I',raw,pos)
                actual=pe.location(pos)
                if signature!=1 or self_rva!=actual['rva'] or type_rva!=loc['rva']:continue
                try:pe.rva_offset(hierarchy_rva)
                except ValueError:continue
                valid.append({'complete_object_locator':actual,'type_descriptor_rva':type_rva,'class_hierarchy_rva':hierarchy_rva,
                              'offset_in_complete_object':offset,'constructor_displacement_offset':cd_offset})
            if valid:rtti.append({'type_label':row['label'],'name_location':{k:row[k] for k in ('file_offset','rva','section')},'validated_data_structure_candidates':valid})
            if len(rtti)>=32:break
    # Exact RIP-relative byte forms only. Instruction boundaries are NOT proven.
    # These hints are never treated as decoded code crossreferences or semantics.
    target_by_rva={row['rva']:row for row in selected if row['rva'] is not None}
    hints=[]
    forms=re.compile(rb'[\x48\x4c][\x8b\x8d][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',re.S)
    for s in pe.sections:
        if not s['characteristics']&0x20000000:continue
        view=raw[s['raw_offset']:s['raw_offset']+s['raw_size']]
        for match in forms.finditer(view):
            target=s['rva']+match.start()+7+struct.unpack_from('<i',match.group(),3)[0]
            if target not in target_by_rva:continue
            if len(hints)<64:
                hints.append({'target_label':target_by_rva[target]['label'],'target_rva':target,
                              'candidate_site':pe.location(s['raw_offset']+match.start()),
                              'classification':'raw-RIP-relative-LEA-or-MOV-byte-form-boundary-unvalidated'})
    final=IMAGE.stat();require(final.st_size==before.st_size and final.st_mtime_ns==before.st_mtime_ns,'Source metadata changed during analysis')
    report={'format':'hots-native-serialization-label-research-v1','producer_sha256':sha(Path(__file__).read_bytes()),
        'source':{'path':str(IMAGE),'bytes':len(raw),'sha256':sha(raw),'PE_machine':hex(pe.machine),'PE32plus':True,
                  'PE_timestamp':pe.timestamp,'image_base':pe.imagebase,'size_of_image':pe.sizeofimage,'version_resources':versions,
                  'single_bounded_PE_read':True,'source_size_and_mtime_unchanged':True},
        'sections':pe.sections,'target_terms':['replay','battlelobby','player','license','reward','collection','serialization','availability','MapNamespace'],
        'safe_label_counts':dict(sorted(counts.items())),'saved_label_counts':dict(sorted(saved.items())),
        'excluded_non_label_counts':dict(sorted(excluded.items())),'selected_label_limit':320,
        'selected_labels_are_truncated':len(selected)<len(matched),'selected_labels':selected,
        'RTTI_data_structure_candidates':rtti,'raw_RIP_relative_byte_hints':hints,
        'existing_disassembler_detection':{'Python_modules':{m:importlib.util.find_spec(m) is not None for m in ('pefile','capstone','iced_x86','lief','yara')},
                                            'PATH_tools':{m:shutil.which(m) for m in ('llvm-objdump','objdump','dumpbin')},
                                            'Ghidra_directories_present':[str(p) for p in (Path('C:/tools/ghidra_12.0.4_PUBLIC'),Path('C:/tools/Ghidra')) if p.is_dir()],
                                            'Ghidra_or_headless_analysis_invoked':False},
        'code_instructions_decoded':False,'instruction_boundaries_proven':False,'serializer_field_semantics_proven':False,
        'old174_to_new198_mapping_proven':False,'availability32byte_record_meaning_proven':False,
        'game_image_executed_or_loaded':False,'game_or_client_DLL_loaded':False,'debugger_process_or_injection_used':False,
        'binary_copy_or_disassembly_dump_saved':False,'new_network_requests':0,'repo_modified':False,
        'limitations':['String presence and even an RTTI data relationship do not establish a serializer or field layout.',
            'Reward catalog type/property names are separated from possible serialization labels; neither alone binds the opaque fields.',
            'No disassembler was installed. Raw opcode byte forms are unvalidated hints, not established instruction crossreferences.',
            'Only allowlisted short static labels are emitted; paths, arbitrary format strings and longer/non-label text are excluded.',
            'No old-build executable comparison, game execution, player-data interpretation or replay rewrite is performed.']}
    encoded=(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode()
    require(len(encoded)<=MAX_REPORT,'Compact research report exceeds256KiB')
    with output.open('xb') as f:f.write(encoded)
    print(json.dumps({'report_sha256':sha(encoded),'report_bytes':len(encoded),'source_bytes':len(raw),
                      'selected_labels':len(selected),'RTTI_candidates':len(rtti),'unvalidated_RIP_hints':len(hints),
                      'version':versions[0]['strings'].get('FileVersion')}))

if __name__=='__main__':main()
