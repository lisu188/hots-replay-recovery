"""Project the bounded primary-source lookup, excluding team/player/timeline text."""
from pathlib import Path
import datetime
import hashlib
import json
import re

BASE=Path(__file__).resolve().parent


def main():
    ledger_path=BASE/'regular-map-route-ledger.json'
    raw=ledger_path.read_bytes()
    ledger=json.loads(raw)
    if len(ledger['pages'])!=5 or sum(row['bytes'] for row in ledger['pages'])!=242128:
        raise ValueError('Unexpected bounded discovery inventory')
    pages=[]
    for division,row in enumerate(ledger['pages'],1):
        if row['url']!='https://heroeslounge.gg/eu-season-31/division-'+str(division):
            raise ValueError('Unexpected source page')
        body=(BASE/row['saved_private_HTML']).read_bytes()
        if len(body)!=row['bytes'] or hashlib.sha256(body).hexdigest()!=row['sha256']:
            raise ValueError('Saved source changed')
        text=body.decode('utf8')
        table=re.search(r'<table\b[^>]*>.*?</table>',text,re.S).group(0)
        match_counts=[int(value) for value in re.findall(r'<td><a href="https://heroeslounge\.gg/team/view/[^\"]+"[^>]*>.*?</a></td>\s*<td>(\d+)</td>',table,re.S)]
        if not match_counts or any(match_counts):
            raise ValueError('Empty or nonzero standings counts require new assessment')
        if row['parsed']['match_ids'] or row['parsed']['games'] or row['parsed']['replay_link_count']:
            raise ValueError('A newly available match requires direct inspection')
        pages.append({'url':row['url'],'http_status':row['status'],'bytes':row['bytes'],'sha256':row['sha256'],
            'acquired_at_utc':row['acquired_at_utc'],'standings_rows':len(match_counts),
            'all_standings_match_counts_zero':True,'observed_match_view_links':0,'observed_replay_links':0})
    report={
        'format':'hots-bounded-current-eu-dragon-source-outcome-v1',
        'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'request_helper_sha256':hashlib.sha256((BASE/'probe_regular_map_route.py').read_bytes()).hexdigest(),
        'private_request_ledger_sha256':hashlib.sha256(raw).hexdigest(),
        'sources':pages,'HTML_pages_downloaded':len(pages),'HTML_bytes_downloaded':sum(row['bytes'] for row in pages),
        'caps':{'HTML_pages':10,'aggregate_HTML_bytes':2097152,'replay_files':1,'replay_bytes':5242880},
        'replay_files_downloaded':0,'current_EU_Dragon_Shire_candidate_admitted':False,
        'existing_saved_source_context':{
            'current_control_match_url':'https://heroeslounge.gg/match/view/27515',
            'current_control_primary_page_date':'05 Oct 2026 19:00 (UTC +00:00)',
            'current_control_map':'Lost Cavern',
            'saved_other_match_primary_map_names':['Silver City','Lost Cavern','Braxis Outpost'],
            'saved_offseason_pages':'offseason30-31 groups A/B/C',
        },
        'next_bounded_route':'A completed regular-map match on the linked EU season31 division pages would supply a direct map-filtered replay URL. These five observed pages currently contain no match links and every standings match count is zero.',
        'limitations':[
            'No claim is made that current EU Dragon Shire replays do not exist; this is only the result of the five exact primary pages and previously saved source context.',
            'Map/date filtering would only select a candidate; its actual replay build, map, region and package handles would still need binary verification.',
            'No random match IDs or unlisted upload paths were requested. No new replay was downloaded and no client was launched.',
            'Team names, timeline contents, player identities, raw HTML and private replay/header bytes are not projected.',
        ],
    }
    output=BASE/'current-eu-dragon-route-bounded-outcome.json'
    with output.open('x',encoding='utf8',newline='\n') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'standings_rows':[row['standings_rows'] for row in pages],
        'pages':len(pages),'HTML_bytes':sum(row['bytes'] for row in pages),'replays_downloaded':0},sort_keys=True))


if __name__=='__main__':main()
