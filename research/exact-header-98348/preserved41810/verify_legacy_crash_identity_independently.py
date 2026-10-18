"""Independent first-module metadata check using documented minidump records."""
from pathlib import Path, PureWindowsPath
import hashlib
import json
import struct
import uuid

WORK=Path(__file__).resolve().parent
BASE=Path(r'C:\Users\andrz\OneDrive\Dokumenty\Heroes of the Storm\GameLogs')
RECORD=WORK/'legacy41810-crash-metadata/five-preserved41810-module-metadata.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
report_raw=RECORD.read_bytes()
assert sha(report_raw)=='a40cde35e02707ff2c484dcc98b2bafa4a86bd30eae1ddf2d6b6fc98f7fb85ea'
report=json.loads(report_raw)
folders=sorted(path for path in BASE.iterdir() if path.is_dir() and 'B41810 Error' in path.name)
assert len(folders)==len(report['cases'])==5
metadata_reads=hash_reads=0

def opaque_hash(path):
    global hash_reads
    size=path.stat().st_size;assert 0<size<256*1024
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while piece:=stream.read(16384):h.update(piece);hash_reads+=len(piece)
    return h.hexdigest()

for folder,row in zip(folders,report['cases']):
    dump=next(folder.glob('*.dmp'));error=next(p for p in folder.glob('*Error.txt'))
    assert opaque_hash(dump)==row['dump']['sha256_before']
    assert opaque_hash(error)==row['Error_text']['sha256_before']
    size=dump.stat().st_size
    with dump.open('rb') as stream:
        def at(offset,count):
            global metadata_reads
            assert 0<=offset<=size and 0<=count<=size-offset and count<=16384
            stream.seek(offset);data=stream.read(count);assert len(data)==count
            metadata_reads+=count;return data
        header=at(0,32);assert header[:4]==b'MDMP'
        _,_,streams,directory,_,_,_=struct.unpack('<IIIIIIQ',header)
        assert 0<streams<=128
        entries=[struct.unpack('<III',at(directory+index*12,12)) for index in range(streams)]
        modules=[entry for entry in entries if entry[0]==4];assert len(modules)==1
        _,length,rva=modules[0]
        count=struct.unpack('<I',at(rva,4))[0];assert 0<count<=1024 and 4+108*count<=length
        # All frozen cases identify the target as module zero. Independently
        # check that declared module, without reading other module identities.
        module=at(rva+4,108)
        imagebase,imagesize,checksum,timestamp,name_rva=struct.unpack_from('<QIIII',module)
        n=struct.unpack('<I',at(name_rva,4))[0];assert n%2==0 and n<=8192
        name=at(name_rva+4,n).decode('utf-16-le')
        assert PureWindowsPath(name).name=='HeroesOfTheStorm_x64.exe' and 'Base41810' in name
        version=struct.unpack_from('<13I',module,24);assert version[0]==0xfeef04bd
        words=lambda a,b:[a>>16,a&65535,b>>16,b&65535]
        assert words(version[2],version[3])==words(version[4],version[5])==[0,17,0,41810]
        cvsize,cvrva=struct.unpack_from('<II',module,76);assert 24<cvsize<=8192
        cv=at(cvrva,cvsize);assert cv[:4]==b'RSDS'
        guid=str(uuid.UUID(bytes_le=cv[4:20])).upper();age=struct.unpack_from('<I',cv,20)[0]
        pdb=PureWindowsPath(cv[24:].split(b'\0',1)[0].decode('utf-8')).name
        target=row['dump']['target']
        assert (imagesize,checksum,timestamp)==(89478144,45759189,1458935250)
        assert (imagesize,checksum,timestamp)==(target['size_of_image'],target['PE_checksum'],target['PE_timestamp'])
        assert guid==target['CodeView']['GUID']=='7BF26548-FE37-4F3F-94F0-218512BDB807'
        assert age==target['CodeView']['age_decimal']==49 and pdb=='HeroesOfTheStorm_x64.pdb'
    with error.open('rb') as stream:
        head=[]
        for _ in range(45):
            value=stream.readline(4097);assert len(value)<=4096
            metadata_reads+=len(value);head.append(value)
    text=b''.join(head).decode('utf-8-sig')
    assert all(value in text for value in ['B41810','Heroes.17','x86_64','e_errorIdStreaming','NGDP:E_DATA_ERROR'])
    assert row['Error_text']['static_error_message'] in text
    assert opaque_hash(dump)==row['dump']['sha256_after'] and opaque_hash(error)==row['Error_text']['sha256_after']

result={'format':'hots-preserved41810-crash-root-independent-structure-review-v1',
    'review_source_sha256':sha(Path(__file__).read_bytes()),'reviewed_report_sha256':sha(report_raw),
    'independently_verified_cases':5,'documented_header_and_first_module_record_layout_used':True,
    'full_file_hash_pass_bytes':hash_reads,'selected_metadata_read_bytes':metadata_reads,
    'all_module_version_image_identity_and_RSDS_fields_reproduced':True,
    'all_first45line_Error_static_claims_verified':True,'all10_input_hashes_unchanged':True,
    'complete_executable_or_PDB_SHA_established':False,'historical_CASC_root_or_BuildConfig_established':False,
    'other_module_identities_or_memory_streams_decoded':False,'Variables_or_NGDP_read':False,
    'network_requests':0,'client_or_debugger_launched':False,'raw_source_paths_or_memory_published':False,
    'material_findings':[],
    'primary_layout_sources':[
        'https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_header',
        'https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_module',
        'https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_module_list'],
    'limits':['Only module zero is independently decoded, after validating the frozen target ordinal; no non-target module names are read.',
        'Historical executable metadata is not an authenticated historical content manifest or full executable body.',
        'The generic streaming error identifies neither a failed CDN object nor its underlying cause.']}
dest=WORK/'legacy41810-crash-independent-review';dest.mkdir(exist_ok=False)
path=dest/'root-preserved41810-crash-independent-review.json'
with path.open('xb') as handle:handle.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'cases_verified':5,'report_sha256':sha(path.read_bytes()),'hash_reads':hash_reads,'metadata_reads':metadata_reads}))
