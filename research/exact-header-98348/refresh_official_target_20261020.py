from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,urllib.request
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise RuntimeError('Manifest redirect refused')
url='https://eu.patch.battle.net/hero/versions'
with urllib.request.build_opener(NoRedirect()).open(url,timeout=30) as response:
 assert response.status==200
 raw=response.read(4097)
assert 0<len(raw)<=4096
lines=raw.decode('utf8').splitlines();header=[x.split('!')[0] for x in lines[0].split('|')]
rows=[dict(zip(header,line.split('|'))) for line in lines[1:] if line and not line.startswith('#')]
eu=[r for r in rows if r['Region']=='eu'];assert len(eu)==1
data={'format':'hots-live-official-target-20261020-v1','source_url':url,
 'checked_at_utc':datetime.now(timezone.utc).isoformat(),'HTTP_status':200,
 'body_bytes':len(raw),'body_sha256':hashlib.sha256(raw).hexdigest(),'EU_public_fields':eu[0],
 'current_target_still_matches_frozen_reference_context':eu[0]['BuildId']=='98348',
 'game_client_launched':False,'raw_replay_or_player_data_used':False,
 'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out=Path(__file__).resolve().parent/'official-target-20261020.json'
assert not out.exists();out.write_bytes((json.dumps(data,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps(data))
