"""Fetch one small documented BlizzTrack history response; never a CDN object."""
from pathlib import Path
import datetime,hashlib,json,re,sys,urllib.error,urllib.request
from urllib.parse import urlsplit,parse_qs

HERE=Path(__file__).resolve().parent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def main():
    url,label=sys.argv[1:]
    p=urlsplit(url)
    if p.scheme!='https' or p.netloc!='blizztrack.com' or not re.fullmatch(r'/api/manifest/hero/(seqn|versions)',p.path) or p.fragment:
        raise ValueError('Only documented hero history API is allowed')
    query=parse_qs(p.query)
    if set(query)-{'file','page','limit','seqn'}:raise ValueError('Undocumented query parameter')
    if not re.fullmatch('[a-z0-9-]{1,60}',label):raise ValueError('Invalid scratch label')
    report_path=HERE/(label+'.request.json');body_path=HERE/(label+'.body.json')
    if report_path.exists() or body_path.exists():raise FileExistsError('No overwrite or duplicate request')
    result={'url':url,'requested_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'maximum_bytes':131072,'redirects_followed':0}
    try:
        with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/primary-legacy-build-history','Accept-Encoding':'identity'}),timeout=15) as response:
            result['http_status']=response.status
            if response.status!=200 or response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('Unexpected response')
            length=response.headers.get('Content-Length')
            if length is not None and (not length.isdecimal() or int(length)>131072):raise ValueError('Oversize source response')
            raw=response.read(131073)
            if len(raw)>131072:raise ValueError('Oversize source response')
            parsed=json.loads(raw)
            result.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            with body_path.open('xb') as stream:stream.write(raw)
            print(json.dumps({'response':parsed,'evidence':result},indent=2))
    except urllib.error.HTTPError as error:
        result.update(http_status=error.code,error_type='HTTPError');error.close();print(json.dumps(result))
    except (urllib.error.URLError,ValueError,TimeoutError,OSError) as error:
        result['error_type']=type(error).__name__;print(json.dumps(result))
    with report_path.open('x',encoding='utf8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')


if __name__=='__main__':main()
