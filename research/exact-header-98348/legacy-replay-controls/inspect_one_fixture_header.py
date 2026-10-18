"""One bounded public fixture header read; full acquisition only on exact41810."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import urllib.request
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;WORK=HERE.parent
sys.path[:0]=[r'C:\Users\andrz\git\hots-replay-recovery',str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from protocol_loader import load_protocol

COMMIT='e45df6beb2bde6bbedd883cf86ea419a4a7868c0'
TREE='12187ed1421c7509aabf87b2408569cee54859d5'
BLOB='6a554be1dd6a51a422ceb630c9ed692c46297284'
LISTED_SIZE=2183482
URL=f'https://raw.githubusercontent.com/ebshimizu/hots-parser/{COMMIT}/test/replays/towers-of-doom.StormReplay'
CAP=4096
SCHEMA='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):raise ValueError('Unexpected redirect refused')

def header(raw,protocol):
    if len(raw)<16:raise ValueError('Truncated MPQ user header')
    magic,size,offset,length=struct.unpack_from('<4s3I',raw)
    if magic!=b'MPQ\x1b' or not 1<=length<=CAP-16 or 16+length>len(raw):raise ValueError('Bounded MPQ user header invalid')
    decoded=protocol.decode_replay_header(raw[16:16+length])
    allowed=('m_flags','m_major','m_minor','m_revision','m_build','m_baseBuild')
    version={k:decoded['m_version'][k] for k in allowed if k in decoded['m_version']}
    if any(type(v) is not int for v in version.values()):raise ValueError('Header version is not scalar')
    data=decoded.get('m_dataBuildNum')
    if data is not None and type(data) is not int:raise ValueError('Header data build invalid')
    root=decoded.get('m_ngdpRootKey')
    if root is not None:
        if not isinstance(root,dict) or type(root.get('m_data')) is not bytes or len(root['m_data'])!=16:raise ValueError('Header NGDP root invalid')
        root=root['m_data'].hex()
    return {'version':version,'data_build':data,'NGDP_root':root,'MPQ_user_header_bytes':length,'MPQ_user_data_size':size,'MPQ_archive_offset':offset}

def main():
    output=HERE/'one-fixture-header-observation.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse existing report')
    private=HERE/'fixture-source-commit.private.json';commit_raw=private.read_bytes();commit=json.loads(commit_raw)
    if commit['sha']!=COMMIT or commit['commit']['tree']['sha']!=TREE:raise ValueError('Pinned immutable commit differs')
    source=json.loads((HERE/'hots-parser-tree.body.json').read_bytes())
    matches=[r for r in source['tree'] if r['path']=='test/replays/towers-of-doom.StormReplay']
    if len(matches)!=1 or matches[0]['sha']!=BLOB or matches[0]['size']!=LISTED_SIZE or source['sha']!=COMMIT:raise ValueError('Pinned fixture listing differs')
    protocol=load_protocol(96477)
    if protocol.recovery_schema_sha256!=SCHEMA:raise ValueError('Official pinned header schema differs')
    opener=urllib.request.build_opener(NoRedirect())
    request=urllib.request.Request(URL,headers={'Range':'bytes=0-4095','Accept-Encoding':'identity','User-Agent':'HotS-offline-recovery-header-probe/1'})
    with opener.open(request,timeout=30) as response:
        status=response.status;content_range=response.headers.get('Content-Range');content_length=response.headers.get('Content-Length');encoding=response.headers.get('Content-Encoding')
        if response.geturl()!=URL or status not in (200,206) or encoding not in (None,'identity'):raise ValueError('Unexpected header transport')
        if status==206:
            match=re.fullmatch(r'bytes 0-(\d+)/(\d+)',content_range or '')
            if not match or int(match[1])!=4095 or int(match[2])!=LISTED_SIZE or content_length!='4096':raise ValueError('Content-Range does not match requested prefix')
        elif content_range is not None or content_length not in (None,str(LISTED_SIZE)):raise ValueError('Unexpected ignored-Range full response')
        prefix=response.read(CAP)
    if len(prefix)!=CAP:raise ValueError('Prefix length differs')
    decoded=header(prefix,protocol);full_record=None
    if decoded['version'].get('m_build')==41810:
        full_path=HERE/'author-fixture-exact41810.private.StormReplay'
        if full_path.exists() or full_path.is_symlink():raise FileExistsError('Refuse existing replay output')
        with opener.open(urllib.request.Request(URL,headers={'Accept-Encoding':'identity'}),timeout=30) as response:
            if response.status!=200 or response.geturl()!=URL or response.headers.get('Content-Encoding') not in (None,'identity'):raise ValueError('Unexpected full fixture response')
            full=response.read(min(3*1024*1024,LISTED_SIZE)+1)
        if len(full)!=LISTED_SIZE or full[:CAP]!=prefix:raise ValueError('Full fixture length/prefix differs')
        blob=hashlib.sha1(f'blob {len(full)}\0'.encode()+full).hexdigest()
        if blob!=BLOB or header(full[:CAP],protocol)!=decoded:raise ValueError('Full fixture Git blob/header differs')
        with full_path.open('xb') as stream:stream.write(full)
        full_record={'bytes':len(full),'sha256':sha(full),'git_blob_sha1_verified':blob,'private_file':full_path.name}
    report={'format':'legacy-public-fixture-header-observation-v1','source_url':URL,'source_commit':COMMIT,'source_commit_tree':TREE,'listed_git_blob_sha1':BLOB,'listed_object_bytes':LISTED_SIZE,
        'source_commit_connector_content_sha256':sha(commit_raw),'source_tree_metadata_sha256':sha((HERE/'hots-parser-tree.body.json').read_bytes()),
        'request':{'Range':'bytes=0-4095','Accept-Encoding':'identity','redirects_allowed':False},
        'response':{'status':status,'content_range':content_range,'content_length':content_length,'content_encoding':encoding,'application_body_bytes_read':len(prefix),'application_read_cap':CAP,'response_closed_after_bounded_read':True,'Range_honored':status==206,'underlying_transport_buffer_bytes_measured':False},
        'header_prefix_sha256':sha(prefix),'header_schema_build':96477,'header_schema_sha256':SCHEMA,'decoded_header_allowlist':decoded,
        'exact41810':decoded['version'].get('m_build')==41810,'full_fixture_acquisition':full_record,
        'whole_fixture_SHA_or_Gitblob_verified':full_record is not None,'raw_prefix_body_saved_or_published':False,
        'raw_players_or_messages_emitted':False,'client_launched':False,'repo_modified':False,'producer_sha256':sha(Path(__file__).read_bytes()),
        'limits':['The bounded prefix identifies the parsed version; its hash is not a full-file Git-blob or SHA256 validation.',
            'The source commit and fixture listing bind the intended immutable path; only an exact41810 result permits the separately guarded full download.']}
    data=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    with output.open('xb') as stream:stream.write(data)
    print(json.dumps({'report_bytes':len(data),'report_sha256':sha(data),'actual_header':decoded,'full_body_saved':full_record is not None}))

if __name__=='__main__':main()
