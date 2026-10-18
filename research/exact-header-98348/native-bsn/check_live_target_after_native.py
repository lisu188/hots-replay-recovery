from pathlib import Path
import datetime
import hashlib
import json
import urllib.request

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Redirect refused')

URL='https://eu.patch.battle.net/hero/versions'
opener=urllib.request.build_opener(NoRedirect())
request=urllib.request.Request(URL,headers={'User-Agent':'hots-replay-recovery-offline-target-check/1','Accept-Encoding':'identity'})
with opener.open(request,timeout=20) as response:
    assert response.status==200 and response.geturl()==URL
    assert response.headers.get('Content-Encoding','identity')=='identity'
    raw=response.read(65537);assert len(raw)<=65536
text=raw.decode('utf-8-sig');lines=text.splitlines()
columns=[part.split('!',1)[0] for part in lines[0].split('|')]
rows=[dict(zip(columns,line.split('|'))) for line in lines[1:] if line and not line.startswith('#')]
eu=[row for row in rows if row.get('Region')=='eu'];assert len(eu)==1
target=eu[0]
result={'format':'hots-live-official-target-after-native-research-v1','source_url':URL,
    'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'HTTP_status':200,
    'body_bytes':len(raw),'body_sha256':hashlib.sha256(raw).hexdigest(),'EU_public_fields':target,
    'current_target_still_matches_frozen_reference_context':target.get('VersionsName')=='2.57.0.98348'
        and target.get('BuildConfig')=='a64c9b7ebf1c6a811ffefad97865ed80',
    'game_client_launched':False,'raw_replay_or_player_data_used':False}
path=Path(__file__).resolve().parent/'official-target-after-native-research.json'
with path.open('xb') as output:output.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps(result))
