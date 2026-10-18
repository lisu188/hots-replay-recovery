"""Reproduce a bounded primary-source research receipt without any network.

Reads cached prior observations, a tool-returned public commit/search evidence
projection and the current tail source. Never reads replay or player bytes.
"""
from pathlib import Path
import hashlib
import json

from collection_license_audit import _read, write_new_report

BASE = Path(__file__).resolve().parent
WORK = BASE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('Bounded player-block source evidence differs')


def analyze():
    evidence_raw = _read(BASE/'new-primary-call-evidence.json', 128*1024)
    evidence = json.loads(evidence_raw)
    require(evidence['actual_new_primary_calls'] == evidence['maximum_new_primary_calls'] == 8)
    calls = {row['id']: row for row in evidence['calls']}
    require(set(calls) == set(range(1, 9)))
    prior_rows = []
    prior_documents = {}
    for name in ('player-opaque-additional-primary-investigation.json',
                 'player-opaque-174-to-198-primary-source-comparison.json',
                 'player-opaque-block-forensic-summary.json'):
        raw = _read(WORK/name, 1024*1024)
        prior_rows.append({'file': name, 'bytes': len(raw), 'sha256': sha(raw)})
        prior_documents[name] = json.loads(raw)
    previous = prior_documents['player-opaque-additional-primary-investigation.json']
    previous_searches = previous['bounded_indexed_searches']
    require(previous['prior_289_representation_group_correlations_not_repeated'])
    require(len(previous['new_primary_source_review']) == 11)
    comparison = prior_documents['player-opaque-174-to-198-primary-source-comparison.json']
    require(comparison['version_list']['original41810_schema'] == 2)
    require(comparison['version_list']['last_listed_schema2_build'] == 43259)
    require(comparison['version_list']['first_listed_schema3_build'] == 43481)
    require(comparison['schema2_to_schema3_only_player_record_declaration_change_is_opaque_width'])
    tail_raw = _read(REPO/'battlelobby_tail.py', 128*1024)
    tail_source = tail_raw.decode('utf-8')
    marker = "bits = opaque(path+'/unknown_player_block', 198 if modern else 174)"
    require(marker in tail_source)
    lines = tail_source.splitlines()
    marker_line = next(i+1 for i, line in enumerate(lines) if marker in line)
    require("scalar(path+'/secondary/flag', 1)" in '\n'.join(lines[marker_line-5:marker_line]))
    require("scalar(path+'/optional64/present', 1)" in '\n'.join(lines[marker_line:marker_line+5]))
    require(calls[2]['result']['returned_issue_count'] == calls[3]['result']['returned_issue_count'] == 0)
    fixes = {}
    for identifier in (4, 5, 6, 8):
        result = calls[identifier]['result']
        fixes[identifier] = {row['filename']: row['patch'] for row in result['files']}
    first_readme = fixes[4]['README.md']
    corrected_readme = fixes[8]['README.md']
    require('+            m_Unk2: array [:0 + 198] of bit' in first_readme)
    require('             m_Unk2: array [:0 + 198] of bit' in corrected_readme)
    require('             m_Unk3: Optional:1 of (array [:0 + 64] of bit)' in corrected_readme)
    require('+              m_UnkFlags: array [:0 + 4] of bit' in corrected_readme)
    require('+              m_build: Integer(:32 + 0)' in corrected_readme)
    require(corrected_readme.index('m_Unk2: array [:0 + 198]') < corrected_readme.index('m_Unk3: Optional:1') < corrected_readme.index('+              m_build:'))
    require(fixes[4]['battlelobby.py'] is None and fixes[8]['battlelobby.py'] is None)
    mac_patch = fixes[5]['Heroes.StormReplayParser/MpqFiles/ReplayGameEvents.cs']
    require('player.IsPlatformMac = structure[8]!.Boolean!.Value' in mac_patch)
    require(not any('ReplayServerBattlelobby' in name for name in fixes[5]))
    name_patch = fixes[6]['Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs']
    require('poundIndex >= 0' in name_patch and 'namePart' in name_patch)
    require(not any(token in name_patch for token in ('ReadBitArray', 'ReadBits', 'ReadBoolean', '198', '174')))
    require(len(calls[7]['result']['commits']) == 5)
    prior_search_keys = [{'query': row.get('query'), 'path': row.get('path'),
                          'scope': row.get('repository', row.get('repositories', row.get('owner', None)))}
                         for row in previous_searches]
    new_rows = []
    for identifier in range(1, 9):
        row = calls[identifier]
        result = row['result']
        item = {'id': identifier, 'tool': row['tool'], 'arguments': row['args']}
        if row['tool'] == 'github_search_commits':
            item['returned_commits'] = [{'sha': c['sha'], 'url': c['url'], 'message': c['message']}
                                        for c in result['commits']]
        elif row['tool'] == 'github_search_issues':
            item['returned_issue_count'] = result['returned_issue_count']
        else:
            item.update(commit_sha=result['sha'], url=result['url'], message=result['message'],
                        reviewed_source_files=[{'path': p['filename'],
                                                'tool_patch_available': p['patch'] is not None,
                                                'tool_patch_utf8_sha256': sha(p['patch'].encode('utf-8')) if p['patch'] is not None else None}
                                               for p in result['files']])
        new_rows.append(item)
    return {
        'format': 'hots-player-opaque-primary-history-followup-v1',
        'status': 'no-new-authenticated-internal-layout-or-conversion-found-in-eight-call-scope',
        'producer_sha256': sha(_read(Path(__file__), 128*1024)),
        'cached_public_call_evidence': {'file': 'new-primary-call-evidence.json', 'bytes': len(evidence_raw), 'sha256': sha(evidence_raw)},
        'prior_evidence_read_before_new_requests': prior_rows,
        'prior_eleven_full_source_reviews_and_indexed_search_keys_not_repeated': prior_search_keys,
        'prior_289_group_correlations_not_repeated': True,
        'current_local_envelope': {'file': 'battlelobby_tail.py', 'sha256': sha(tail_raw),
            'opaque_read_line': marker_line, 'old_bits': 174, 'current_bits': 198,
            'preceded_by': 'numeric/string toon and optional secondary string toon',
            'followed_by': 'optional64, four flags, community-named build32 and collection choice',
            'same_profile_source_preserving_reader_not_changed': True},
        'prior_width_transition_bounds': {'last_listed_old_schema2_build': 43259, 'first_listed_schema3_build': 43481,
            'precise_transition_version_or_added_bit_positions_established': False},
        'maximum_new_primary_source_or_search_calls': 8,
        'actual_new_primary_source_or_search_calls': 8,
        'calls': new_rows,
        'new_findings': [
            {'source_call': 4, 'finding': 'The first visualization commit still labels the entire198-bit player block m_Unk2 without internal scalars.'},
            {'source_call': 8, 'finding': 'The old-version bugfix names four flags, build32 and collection-choice fields after the unchanged198-bit block and optional64. These fixes do not describe the internal24-bit width increase.'},
            {'source_call': 5, 'finding': 'IsPlatformMac is obtained from game-event user options, not from the battlelobby opaque block.'},
            {'source_call': 6, 'finding': 'The empty-player-name/tag fix changes only validation of the decoded string, with no wire reads or opaque-width change.'},
            {'source_call': 7, 'finding': 'The bounded repository commit search returned five metadata entries. No complete historical graph or all generated-Python diffs are claimed.'},
            {'source_calls': [2, 3], 'finding': 'The two explicitly scoped issue searches returned no matches; this is indexed-search evidence only.'}],
        'internal_named_fields_found': False, 'old174_embedding_in_current198_established': False,
        'added24_positions_values_or_defaults_established': False, 'conversion_or_player_field_values_inferred': False,
        'generated_Python_patches_available_for_two_visualization_commits': False,
        'new_replay_or_binary_downloads': 0, 'binary_or_client_executed': False,
        'replay_or_player_bytes_read': False, 'raw_private_player_or_account_values_emitted': False,
        'repo_or_cloud_modified': False,
        'limits': [
            'The source request budget is exhausted at eight read-only calls; no hidden follow-up fetch or broader negative search is represented.',
            'Commit patches are the tool-returned text projection. Generated battlelobby.py patches were unavailable, so their complete modifications are not independently reviewed here.',
            'Existing cached schemas already show width-only174-to198 declarations; repeated unknown labels are not evidence of a field map or zero-padding rule.',
            'Search zeroes and returned commit metadata do not establish global source absence or complete history coverage.',
            'No same-player authenticated cross-version serialization sample, engine-native declaration or internal scalar layout was obtained.']}


if __name__ == '__main__':
    report = analyze()
    output = BASE/'player-block-primary-history-followup.json'
    write_new_report(report, output)
    print(json.dumps({'primary_calls': report['actual_new_primary_source_or_search_calls'],
                      'internal_layout_found': report['internal_named_fields_found'],
                      'report_sha256': sha(_read(output, 128*1024))}))
