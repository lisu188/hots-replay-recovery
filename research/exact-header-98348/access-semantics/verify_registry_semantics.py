"""Read-only review of saved static CASC text evidence, without opening CASC.

Only a new sanitized review receipt is written. Game texts and header bodies
stay private, and no network or extraction helper is executed.
"""
from pathlib import Path
import hashlib
import json
import re

from collection_license_audit import _read, write_new_report
from depot_s2mh_wire import decode_verified_header

WORK = Path(__file__).resolve().parents[1]
BASE = WORK/'licensed-registry-semantics'
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
ALLOW_SHA = 'c869cbec5a1cc399794e8314740597b7d420a86cbd8f704606bfa072b92fc554'
REPORT_SHA = '827aef5bc8ff4de516a720ec61a04c27c07517145177cfca23124b1faa056185'
ROOT = 'c3b3c8bc82e3a5a62e550fdde9a40c28'
DLL = '8be4b72776a3a4eca6708cc204860c51592c8f886224dd6ccbdec03b6fa82a11'
OBS = '0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9'
OLD = 'b34d0f30dc3b9cf47694982106a04006a49ce43422e02f71ed18b33b7bfcc6c4'
CURRENT = '0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a'
TEXTS = {'natives.galaxy', 'NativeLib_h.galaxy', 'NativeLib.galaxy',
         'HeroesLib.galaxy', 'HeroesLib_h.galaxy', 'ConfigData.xml'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def gitblob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('Saved registry semantics evidence verification failed')


def verify():
    allow_raw = _read(BASE/'registry-semantics-final-allowlist.json', 128*1024)
    report_raw = _read(BASE/'registry-access-semantics-findings-v2.json', 128*1024)
    require(sha(allow_raw) == ALLOW_SHA and sha(report_raw) == REPORT_SHA)
    allow, report = json.loads(allow_raw), json.loads(report_raw)
    entries = allow['allowlisted_files']
    require(len(entries) == 12 and len({row['name'] for row in entries}) == 12)
    require(not TEXTS & {row['name'] for row in entries})
    require('registry-access-semantics-findings.json' not in {row['name'] for row in entries})
    for row in entries:
        require(Path(row['name']).name == row['name'])
        raw = _read(BASE/row['name'], 1024*1024)
        require(len(raw) == row['bytes'] and sha(raw) == row['sha256'])
    ops = {}
    for row in report['operation_reports']:
        raw = _read(BASE/row['name'], 128*1024)
        require(sha(raw) == row['sha256'] and len(raw) == row['bytes'])
        op = json.loads(raw)
        require(op['root'] == op['actual_root_content_md5'] == ROOT)
        require(op['version'] == '2.57.0.98348' and op['dll_sha256'] == DLL)
        require(op['blocked_http_attempts_during_casc'] == 0 and op['denying_http_handler_canary_passed'])
        require(op['installed_config_hashes_unchanged'] and op['config_parsed_from_scratch_copies'])
        require(op['installed_indices_and_data_access'] == 'explicit-read-only')
        require(not op['cache_enabled'] and not op['online_fallback_flag'] and op['load_flags'] == 'None')
        require(not op['game_client_launched'] and not op['game_storage_modified'])
        require(not op['library_clear_succeeded'] and op['library_clear_exception_type'] == 'System.NullReferenceException')
        ops[row['name']] = op
    require(len(ops) == 4)
    bodies = {}
    text_rows = []
    for name in ('installed-native-three-members.json', 'installed-heroes-three-members.json'):
        for row in ops[name]['members']:
            filename = row['saved_name']
            require(filename in TEXTS and filename not in bodies)
            require(row['read'] and row['full_casc_content_md5_verified'])
            raw = _read(BASE/filename, 1024*1024)
            require(len(raw) == row['bytes'] and sha(raw) == row['sha256'])
            require(hashlib.md5(raw).hexdigest() == row['casc_content_md5'])
            bodies[filename] = raw
            text_rows.append({'file': filename, 'bytes': len(raw), 'sha256': sha(raw),
                              'content_MD5_matches_saved_CASC_key': True})
    require(set(bodies) == TEXTS and sum(map(len, bodies.values())) == 779428)
    require(ops['installed-native-three-members.json']['total_text_bytes_read'] == 290010)
    require(ops['installed-heroes-three-members.json']['new_text_bytes_read'] == 489418)
    require(ops['installed-heroes-three-members.json']['cumulative_text_bytes_read'] == 779428)
    bindings = {row['file']: row for row in report['actual_CASC_and_public_source_binding']}
    require(gitblob(bodies['HeroesLib.galaxy']) == bindings['HeroesLib.galaxy']['git_blob_sha1'] == '0cf700ed3ae8e5b6dff5c812d2de9bddd7899b0b')
    require(gitblob(bodies['ConfigData.xml']) == bindings['ConfigData.xml']['git_blob_sha1'] == 'f63298d1a04a7148ca6b32cc161a2eed82da5152')
    for binding in bindings.values():
        require(binding['public_commit'] == 'e3e57cb640f18002a4feebe3872cefe04072d814')
        require('/blob/'+binding['public_commit']+'/' in binding['url'])
    heroes = bodies['HeroesLib.galaxy'].decode('utf-8').splitlines()
    for row in report['current_authenticated_functions']:
        first, last = row['line_start'], row['line_end']
        require(heroes[first-1].startswith('bool '+row['function']+' (') and heroes[last-1] == '}')
        body = '\n'.join(heroes[first-1:last])
        require(body.count('PlayerHasReward(') == 1 and row['source_sha256'] == sha(bodies['HeroesLib.galaxy']))
        if 'IsHeroInRotationForPlayer' in row['function']:
            require('FreeToPlayRewardArray' in body and 'lv_heroRotationSlotsAvailable += 1' in body)
        else:
            require('RequiredRewardArray' in body and 'return false;' in body and 'return true;' in body)
            require('GameModes_TryMe' in body and 'dEBUGGameIsOnline == false' in body)
            if row['function'].endswith('AccessToHero'):
                require(all(token in body for token in ('AllowAIRandomSelection', 'AllowHumanRandomSelection', 'GameIsPractice()', 'GameIsCooperative()', 'IsHeroInRotationForPlayer', 'IsHeroInFreebieSet')))
            elif row['function'].endswith('AccessToSkin'):
                require('lp_skinIndex == 1' in body)
            elif row['function'].endswith('AccessToMount'):
                require('lp_mountIndex == 1' in body and 'Flags[FreePlay]' in body)
    require(len(report['current_authenticated_functions']) == 4)
    for filename in ('natives.galaxy', 'NativeLib_h.galaxy', 'NativeLib.galaxy'):
        text = bodies[filename].decode('utf-8')
        require(all(not re.search(term, text, re.I) for term in ('license', 'reward', 'entitle', 'collection', 'HyperlinkId')))
    require(sum(raw.decode('utf-8').count('PlayerHasReward') for raw in bodies.values()) == 4)
    cfg = bodies['ConfigData.xml'].decode('utf-8').splitlines()
    for index, name in enumerate(report['current_Config_FreeToPlayRewardArray']['catalog_names']):
        require('<FreeToPlayRewardArray value="'+name+'" />' in cfg[1064+index])
    # Recheck the corrected named-unit premise against authenticated static headers.
    old = decode_verified_header(_read(WORK/'depot-headers/original-eu'/(OLD+'.s2mh'), 512*1024), OLD)[0]
    current = decode_verified_header(_read(WORK/'header-reconstruction/recovered-headers-private'/(CURRENT+'.s2mh'), 512*1024), CURRENT)[0]
    old_names = list(dict.fromkeys(value.decode('ascii') for value in old[23]))
    require(len(old[23]) == 264 and len(old_names) == 263)
    require(23 not in current and len(current[24]) == 5497 and len(set(current[24])) == 5418)
    observed_raw = _read(REPO/'observations/collection-identities-2026-10-18.json', 1024*1024)
    require(sha(observed_raw) == OBS)
    observed = {row['id']: row for row in json.loads(observed_raw)['cases']}
    require(old_names == observed['original']['items'] == observed['r8']['items'])
    require(list(dict.fromkeys(current[24])) == observed['protectors']['items'] == observed['stormblessed']['items'])
    negatives = report['fresh_static_registry_crosscheck']['checked_named_unit_membership']
    require(set(negatives) == {'NovaHoloCloneCloaked', 'AbathurEvolvedMonstrosity', 'TownCannonTower'})
    require(all(value is False and name not in old_names for name, value in negatives.items()))
    common_canary = None
    for name in ('inventory_installed_native_filenames.ps1', 'inventory_installed_heroes_library_filenames.ps1',
                 'read_three_installed_native_members.ps1', 'read_three_installed_heroes_members.ps1'):
        source = _read(BASE/name, 128*1024).decode('utf-8')
        require(all(token in source for token in (
            '[OfflineCascHttp]::Rejected=0', 'UseOnlineFallbackForMissingFiles=$false',
            'LoadFlags=[CASCLib.LoadFlags]::None', '[CASCLib.CDNCache]::Enabled=$false',
            'LoadLocalStorageConfig($configCopy', "GetProperty('BasePath').SetValue($config,$installed)",
            "-ne '2.57.0.98348'", ROOT, DLL, '[IO.FileMode]::CreateNew')))
        block = source.split('public sealed class OfflineCascHttp', 1)[1].split('public sealed class ScopedCascLog', 1)[0]
        # Frozen raw SHA pins above remain exact. These derivatives differ only
        # in LF versus CRLF spelling inside this otherwise identical source block.
        block = '\n'.join(block.splitlines())
        require(common_canary is None or common_canary == block)
        common_canary = block
        require(not re.search(r'(?i)Start-Process|HeroesSwitcher|HeroesOfTheStorm_x64', source))
    for row in entries:
        require(sha(_read(BASE/row['name'], 1024*1024)) == row['sha256'])
    require(sha(_read(BASE/'registry-semantics-final-allowlist.json', 128*1024)) == ALLOW_SHA)
    return {
        'format': 'hots-registry-access-semantics-independent-review-v1',
        'review_source_sha256': sha(_read(Path(__file__), 128*1024)),
        'reviewed_final_allowlist_sha256': ALLOW_SHA, 'reviewed_findings_v2_sha256': REPORT_SHA,
        'twelve_allowlisted_files_hash_verified': True, 'six_private_bodies': text_rows,
        'six_private_body_total_bytes': 779428, 'body_MD5_and_SHA256_match_saved_root_bound_reports': True,
        'four_saved_operations_canary_passed_and_zero_HTTP': True,
        'derivative_guard_source_review_passed': True,
        'actual_four_access_function_branches_and_config_entries_reviewed': True,
        'local_public_blob_identifiers_recomputed_exactly': True,
        'remote_commit_blob_link_provenance_independently_refetched': False,
        'old263_registry_and_three_corrected_named_unit_negatives_verified': True,
        'current5497_raw_5418_unique_registry_verified': True,
        'availability32byte_binding_or_ownership_meaning_established': False,
        'material_findings_in_scoped_review': [],
        'new_CASC_open_or_extraction': False, 'network_requests': 0,
        'new_unit_tests_or_CI_claimed': False, 'raw_text_or_header_body_written': False,
        'raw_game_texts_in_public_allowlist': False,
        'limits': [
            'Saved operation reports and source guards are reviewed; no fresh CASC open or denying-handler canary is executed.',
            'Local git blob IDs match the IDs recorded for the public commit; remote fetch provenance remains reported evidence rather than an independently repeated request.',
            'Current access helpers show reward checks plus free/practice/rotation/mode branches, not PlayerHasReward implementation or old/current availability-bit semantics.',
            'The three named NPC-style symbols are absent from the authenticated old263 registry; this is a corrected scoped membership fact, not global catalog absence.',
            'SC2 declaration and bounded historical-search evidence remain separate from authenticated HotS historical native API proof.']}


if __name__ == '__main__':
    result = verify()
    output = Path(__file__).with_name('registry-semantics-independent-review.json')
    write_new_report(result, output)
    print(json.dumps({'review_receipt_sha256': sha(_read(output, 128*1024)),
                      'private_body_files_verified': 6, 'new_CASC_operations': 0, 'network_requests': 0}))
