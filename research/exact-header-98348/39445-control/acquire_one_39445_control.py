"""Acquire only the explicitly authorized pinned39445 public control."""
import hashlib
import json
from pathlib import Path
import urllib.request
HERE=Path(__file__).resolve().parent/'legacy-39445-control'
URL='https://raw.githubusercontent.com/HeroesToolChest/Heroes.StormReplayParser/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Tests/Heroes.StormReplayParser.Tests/Replays/TowersofDoom1_39445.StormR'
SIZE=652332
BLOB='8ff1b28c5b07e2d48425dcd097072f2953e94ef9'
PREFIX='9663ddd305fdbd6564b26f32f8ac7bb434f8a727a5a4be026abeb2bc42e815b6'
sha=lambda data:hashlib.sha256(data).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):raise ValueError('Unexpected redirect refused')
def main():
    HERE.mkdir(exist_ok=True);path=HERE/'htc39445.private.StormReplay';output=HERE/'39445-full-acquisition.json'
    if any(p.exists() or p.is_symlink() for p in (path,output)):raise FileExistsError('Refuse existing outputs')
    request=urllib.request.Request(URL,headers={'Range':f'bytes=0-{SIZE-1}','Accept-Encoding':'identity','User-Agent':'HotS-offline-recovery-old-control/1'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=30) as response:
        status=response.status;length=response.headers.get('Content-Length');crange=response.headers.get('Content-Range');encoding=response.headers.get('Content-Encoding');etag=response.headers.get('ETag')
        if response.geturl()!=URL or status not in (200,206) or encoding not in (None,'identity') or length!=str(SIZE):raise ValueError('Unexpected full control response')
        if status==206 and crange!=f'bytes 0-{SIZE-1}/{SIZE}':raise ValueError('Unexpected full-range boundaries')
        if status==200 and crange is not None:raise ValueError('Unexpected full-response range')
        raw=response.read(SIZE+1)
    if len(raw)!=SIZE or sha(raw[:4096])!=PREFIX:raise ValueError('Pinned length/prefix differs')
    git=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if git!=BLOB:raise ValueError('Pinned full Git blob differs')
    with path.open('xb') as stream:stream.write(raw)
    report={'format':'authorized39445-public-fixture-acquisition-v1','source_url':URL,'source_commit':'d381dd9c273205c0fd7ac402c75eef98c6fa6c78',
        'bytes':len(raw),'sha256':sha(raw),'verified_git_blob_sha1':git,'verified_prefix4096_sha256':PREFIX,
        'HTTP':{'status':status,'content_range':crange,'content_length':length,'ETag':etag,'content_encoding':encoding,'application_read_cap':SIZE+1,'application_body_bytes':len(raw),'response_closed':True,'redirects_allowed':False},
        'private_file':path.name,'raw_fixture_for_publication':False,'players_or_messages_emitted':False,'client_launched':False,'producer_sha256':sha(Path(__file__).read_bytes())}
    data=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    with output.open('xb') as stream:stream.write(data)
    print(json.dumps({'bytes':len(raw),'full_sha256':sha(raw),'report_sha256':sha(data)}))
if __name__=='__main__':main()
