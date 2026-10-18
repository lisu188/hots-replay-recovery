"""Recompute the bounded metadata-only legacy fixture search receipt offline."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
INPUTS={
 'barrett-tree.body.json':('4d97eb614648650baa9a9b6789fe37c31b40025c',39),
 'htc-tree.body.json':('d381dd9c273205c0fd7ac402c75eef98c6fa6c78',183),
 'hots-parser-tree.body.json':('e45df6beb2bde6bbedd883cf86ea419a4a7868c0',16),
}
URLS={
 'barrett-tree.body.json':'https://api.github.com/repos/barrett777/Heroes.ReplayParser/git/trees/master?recursive=1',
 'htc-tree.body.json':'https://api.github.com/repos/HeroesToolChest/Heroes.StormReplayParser/git/trees/main?recursive=1',
 'hots-parser-tree.body.json':'https://api.github.com/repos/ebshimizu/hots-parser/git/trees/master?recursive=1',
 'exact-build-fixture-code-search.body.json':'https://api.github.com/search/code?q=41810%20StormReplay%20-filename%3Aprotocol41810.py&per_page=8',
}
sha=lambda data:hashlib.sha256(data).hexdigest()
def analyze():
    sources=[];trees={}
    for name,(expected,count) in INPUTS.items():
        raw=(HERE/name).read_bytes()
        if len(raw)>512*1024:raise ValueError('Source metadata exceeds bound')
        data=json.loads(raw)
        if data['sha']!=expected or len(data['tree'])!=count or data['truncated'] is not False:raise ValueError('Complete pinned source tree differs')
        rows=data['tree'];replays=[r for r in rows if r['type']=='blob' and r['path'].lower().endswith(('.stormreplay','.stormr'))]
        trees[name]={'tree_sha':expected,'entries':count,'truncated':False,'replay_paths':len(replays),'unique_replay_blobs':len({r['sha'] for r in replays}),
            'test_replay_paths':sum(r['path'].startswith('Tests/') for r in replays),'paths_containing_exact_build':sum('41810' in r['path'] for r in rows),
            'replay_candidates':[{'path':r['path'],'git_blob_sha1':r['sha'],'listed_bytes':r['size'],'header_downloaded_or_build_verified':False} for r in replays]}
        sources.append({'file':name,'url':URLS[name],'connector_content_utf8_bytes':len(raw),'connector_content_utf8_sha256':sha(raw)})
    name='exact-build-fixture-code-search.body.json';raw=(HERE/name).read_bytes();search=json.loads(raw)
    if search!={'total_count':0,'incomplete_results':False,'items':[]}:raise ValueError('Frozen exact fixture search differs')
    sources.append({'file':name,'url':URLS[name],'connector_content_utf8_bytes':len(raw),'connector_content_utf8_sha256':sha(raw)})
    return {'format':'hots-legacy-fixture-bounded-search-v1','target_build':41810,'target_version':'0.17.0.41810',
        'source_operation_cap':8,'source_attempts_used':8,'successful_GitHub_metadata_operations':4,'web_search_queries':2,'Firecrawl_requests_blocked_before_search':2,
        'operations':[
            {'number':1,'tool':'Firecrawl.search','query':'"41810" "StormReplay" -protocol41810.py','outcome':'402_insufficient_credits_request_not_run'},
            {'number':2,'tool':'Firecrawl.search','query':'Heroes ReplayParser test fixtures 2016 StormReplay github','outcome':'402_insufficient_credits_request_not_run'},
            {'number':3,'url':URLS['barrett-tree.body.json'],'outcome':'complete39_entry_author_owned_tree_no_replay_fixtures'},
            {'number':4,'url':URLS['htc-tree.body.json'],'outcome':'complete183_entry_author_owned_tree_no_exact41810_path'},
            {'number':5,'tool':'web.search_query','query':'"41810" replay','domains':['github.com'],'outcome':'No qualifying HotS fixture result in returned web results; unrelated GitHub issue-number matches.'},
            {'number':6,'tool':'web.search_query','query':'"41810" "fixtures"','domains':['github.com'],'outcome':'No qualifying HotS fixture result in returned web results; not an exhaustive absence claim.'},
            {'number':7,'url':URLS['hots-parser-tree.body.json'],'outcome':'complete16_entry_author_owned_tree_one_unversioned_replay_fixture'},
            {'number':8,'url':URLS[name],'outcome':'zero_indexed_code_results_incomplete_false'}],
        'frozen_sources':sources,'tree_projections':trees,
        'outcome':{'exact41810_fixture_listing_found':False,'new_replays_or_headers_downloaded':0,'new_replay_header_builds_verified':0,
            'candidate_bodies_downloaded':0,'client_or_PDB_downloaded':False,'client_launched':False,'private_player_values_emitted':False,'repo_modified':False},
        'scope_limits':['Repository trees bind only these observed current trees, not every branch or historical commit.',
            'Build39445 is only a fixture filename label here. Its body/header was not acquired or verified.',
            'The unversioned towers-of-doom fixture is2183482listed bytes; no build/date inference or eligibility was made.',
            'There are22 HTC replay paths but20 unique blobs:20 test paths plus2 benchmark duplicates.',
            'No dated tournament archive was admitted and no guessed old-client or generated-protocol acquisition was used.',
            'Connector content hashes bind saved UTF8 text; raw HTTP transport byte counts and web-search envelopes were not exposed.',
            'Stopped after8 initial attempts. Finding no exact41810listing here does not establish global absence.'],
        'producer_sha256':sha(Path(__file__).read_bytes())}

if __name__=='__main__':
    output=HERE/'legacy-fixture-eight-operation-ledger.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse existing report')
    raw=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    if len(raw)>128*1024:raise ValueError('Compact report exceeds limit')
    with output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'bytes':len(raw),'sha256':sha(raw)}))
