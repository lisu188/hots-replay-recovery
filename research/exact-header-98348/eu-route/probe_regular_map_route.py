"""Bounded primary-page discovery for a current EU regular-map replay.

Private HTML is scratch only. Public output projects dates/maps/observed URLs only.
One execution fetches only explicitly selected URLs already linked by saved pages.
"""
import argparse
import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.request

from inspect_lounge_page import BASE, Redirect, checked

MAX_PAGES=10
MAX_TOTAL=2*1024*1024
LEDGER=BASE/'regular-map-route-ledger.json'


def inspect(raw):
    text=raw.decode('utf-8')
    clean=' '.join(html.unescape(re.sub('<[^>]*>',' ',text)).split())
    date=re.search(r'Scheduled for (\d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{2} \(UTC [^)]*\))',clean)
    parts=re.split(r'<div class="tab-pane[^\"]*" id="game(\d+)" role="tabpanel">',text)
    games=[]
    for i in range(1,len(parts),2):
        body=parts[i+1]
        link=re.search(r'href="([^\"]+\.stormreplay)"',body,re.I)
        name=re.search(r'<span class="badge badge-info">([^<]+)</span>',body)
        games.append({'game_id':int(parts[i]),'map':html.unescape(name.group(1)) if name else None,
                      'replay_url':checked(html.unescape(link.group(1))) if link else None})
    return {'match_ids':list(dict.fromkeys(int(v) for v in re.findall(r'match/view/(\d+)',text))),
            'scheduled':date.group(1) if date else None,'games':games,
            'replay_link_count':len(re.findall(r'href="[^\"]+\.stormreplay"',text,re.I))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not re.fullmatch('[a-z0-9-]{1,70}',args.label):raise ValueError('Unsafe label')
    url=checked(args.url)
    sources=[]
    for path in BASE.glob('*.private.html'):
        if path.stat().st_size>MAX_TOTAL:continue
        if url in html.unescape(path.read_text(encoding='utf8')):
            sources.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    if not sources:raise ValueError('URL was not linked by an existing saved primary page')
    ledger=json.loads(LEDGER.read_bytes()) if LEDGER.exists() else {'format':'hots-bounded-current-eu-regular-map-route-v1','maximum_HTML_pages':MAX_PAGES,'maximum_aggregate_HTML_bytes':MAX_TOTAL,'pages':[],'replays_downloaded':0}
    if any(row['url']==url for row in ledger['pages']):raise ValueError('No duplicate request')
    remaining=MAX_TOTAL-sum(row['bytes'] for row in ledger['pages'])
    if len(ledger['pages'])>=MAX_PAGES or remaining<1:raise ValueError('Page budget exhausted')
    dest=BASE/(args.label+'.private.html')
    if dest.exists():raise FileExistsError(dest)
    with urllib.request.build_opener(Redirect).open(urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/offline-bounded-public-reference','Accept-Encoding':'identity'}),timeout=25) as response:
        if response.status!=200 or response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('Unexpected HTTP response')
        length=response.headers.get('Content-Length')
        if length is not None and (not length.isdecimal() or int(length)>remaining):raise ValueError('Page exceeds aggregate budget')
        raw=response.read(remaining+1)
        if len(raw)>remaining or (length is not None and len(raw)!=int(length)):raise ValueError('Oversize or truncated page')
        final=checked(response.url)
    with dest.open('xb') as stream:stream.write(raw)
    row={'url':url,'final_url':final,'status':200,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
         'acquired_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved_private_HTML':dest.name,
         'observed_link_sources':sources,'parsed':inspect(raw)}
    ledger['pages'].append(row)
    LEDGER.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'url':url,'bytes':len(raw),'total_pages':len(ledger['pages']),
        'total_bytes':sum(row['bytes'] for row in ledger['pages']),'parsed':row['parsed']},sort_keys=True))


if __name__=='__main__':main()
