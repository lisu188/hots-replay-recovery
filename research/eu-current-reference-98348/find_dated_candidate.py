"""Inspect only match IDs linked by already saved official standings pages."""
import datetime, hashlib, html, json, re, time, urllib.request
from pathlib import Path
from inspect_lounge_page import BASE, LIMIT, Redirect, checked

opener=urllib.request.build_opener(Redirect)
ids=set()
for p in BASE.glob('offseason-*.private.html'):
    ids.update(re.findall(r'match/view/(\d+)',p.read_text(encoding='utf8')))
results=[]
for mid in sorted(ids,key=int):
    file=BASE/f'match-{mid}.private.html'
    url=checked(f'https://heroeslounge.gg/match/view/{mid}')
    fetched=not file.exists()
    if fetched:
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/offline-reference-research'}),timeout=30) as r:
            checked(r.url); raw=r.read(LIMIT+1)
            if len(raw)>LIMIT: raise ValueError('page too large')
        file.write_bytes(raw)
        time.sleep(1)
    else:raw=file.read_bytes()
    text=raw.decode('utf8')
    clean=' '.join(html.unescape(re.sub('<[^>]*>',' ',text)).split())
    date=re.search(r'Scheduled for (\d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{2} \(UTC [^)]*\))',clean)
    date=date.group(1) if date else None
    parts=re.split(r'<div class="tab-pane[^\"]*" id="game(\d+)" role="tabpanel">',text)
    games=[]
    for i in range(1,len(parts),2):
        body=parts[i+1]
        link=re.search(r'href="([^\"]+\.stormreplay)"',body,re.I)
        map_name=re.search(r'<span class="badge badge-info">([^<]+)</span>',body)
        games.append({'game':int(parts[i]),'map':html.unescape(map_name.group(1)) if map_name else None,'replay_url':checked(html.unescape(link.group(1))) if link else None})
    result={'match_id':int(mid),'url':url,'html_bytes':len(raw),'html_sha256':hashlib.sha256(raw).hexdigest(),'scheduled':date,'games':games}
    results.append(result)
    print(json.dumps({'id':mid,'scheduled':date,'games':[{k:v for k,v in g.items() if k!='replay_url'} for g in games]}),flush=True)
    if date and 'Oct 2026' in date and any(g['replay_url'] for g in games):
        print('OCTOBER_CANDIDATE_FOUND',flush=True)
        break
out=BASE/'dated-match-discovery.json'
with out.open('x',encoding='utf8') as f:json.dump({'source':'official linked offseason standings only','results':results},f,indent=2);f.write('\n')
