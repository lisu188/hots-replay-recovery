"""One separately authorized RAM hypothesis, after a required known negative.

Keep the authenticated EU DataMod mapNamespace leaf unchanged. All other
candidate fields are the prior observed-US recipe. Only the actual complete
US terminal SHA can accept and exclusively save a private body. No retries.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0] = [str(REPO), str(HERE), str(WORK/'heroprotocol'), str(WORK/'python-deps')]

from collection_license_audit import _read, write_new_report
from regional_header_controls import extract_context, candidate_from_eu
from recover_current_eu_heroesdata_header import save_exact_header
from depot_s2mh_wire import decode_verified_header
from lossless_wire import parse, clone, encode, to_generic

sha = lambda raw: hashlib.sha256(raw).hexdigest()
HEADER_LIMIT = 512*1024
SOURCE_SHA = '33a1c5c9cd0e3d808c2a942c392fa2b5cc7077457bdbe62adad158b86ef8a4fd'
TARGET = '42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a'
PREVIOUS_NEGATIVE = 'bcbacce6174dac21f9c289f4dd6a7e6b40873c15cc96c3624a37204c4793aa67'
REPLAY_SHA = '882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'
MEMBER_SHA = 'ab03d9533081e9d69d205a6adec9df6a0aaf5ff47a05ecc8bf670b6760b0ab55'
REPLAY = WORK/'reference-donors/ngs-20261016-protectors-dragon.StormReplay'
PRIVATE = HERE/'recovered-headers-private'
CACHE = Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
PINS = {
    'regional_header_controls.py':'7cf886a8fdf8cbaad8c69dda116798a3e6caef1f3b90342b7d0a5eb7e422a6cd',
    'recover_current_eu_heroesdata_header.py':'080615308fd50f4015b8ee0e562a79240b64dc6b0d9cc1d51923d4fc953676f9',
    'lossless_wire.py':'9d725f9be88c4185419a306ef995e82a774d174a93912ffd381cced2d6ebb7a7',
    'authorized-three-US-header-trials.json':'3902c1fd08d11deacba24742128412aa9135575c4a9898c9e8b9a6cd1ac9c73c',
    'three-US-header-trials-independent-review.json':'5ee97b1e4d098a660ac14b1e86d282a42532588adc660095fc97dfda9961a0b8',
}
KNOWN_US = (
    '3392997d3afe27a33371b58cfaff37af5b67bda09ee9131e52bae0a0c80b2b76',
    '82cf19ac9ceb903631db0994023efba040a1ccfbb0e920033a742d62cb65a77b',
    '4b6fdc8eccc9eca107f7c6e5eae6c7c604e718ded019f4f4110a92300b54313f',
)

def require(test, message):
    if not test:
        raise ValueError(message)

def verify_pins():
    for name, expected in PINS.items():
        require(sha(_read(HERE/name,1024*1024)) == expected,'A frozen prerequisite differs')

def execute():
    verify_pins()
    report_path = HERE/'single-DataMod-preserved-namespace-trial.json'
    output = PRIVATE/(TARGET+'.s2mh')
    require(not output.exists() and not output.is_symlink() and
            not report_path.exists() and not report_path.is_symlink(),'Refuse existing result')
    source_path = CACHE/SOURCE_SHA[:2]/SOURCE_SHA[2:4]/(SOURCE_SHA+'.s2mh')
    source_raw = _read(source_path,HEADER_LIMIT)
    source_generic = decode_verified_header(source_raw,SOURCE_SHA)
    require(source_generic[0][0] == {0:196228,1:16} and len(source_raw) == 1660,
            'Authenticated EU DataMod identity or size differs')
    source_node = parse(source_raw)
    require(encode(source_node) == source_raw,'Source lossless roundtrip differs')
    context = extract_context(REPLAY,REPLAY_SHA,'US')
    require(context.member_sha256 == MEMBER_SHA,'Actual replay member differs')
    indices = [i for i,h in enumerate(context.prefix) if h[8:] == source_generic[0][2][8:]]
    require(len(indices) == 1,'Source archive is not one actual US package')
    index = indices[0]
    require(context.entries[index]['identity'] == (280539,16),'Actual US DataMod identity differs')
    require(context.terminal[index] == b's2mh\0\0US'+bytes.fromhex(TARGET),
            'Exact target is not advertised by the actual source replay')
    offsets = set()
    for digest in KNOWN_US:
        raw = _read(WORK/'independent-parser/s2mh-headers'/(digest+'.s2mh'),HEADER_LIMIT)
        h = decode_verified_header(raw,digest)[0]
        require(h[2][:8] == b's2ma\0\0US','Known witness region differs')
        offsets.add(h[3]-h[0][0])
    require(len(offsets) == 1,'Known prior recipe witnesses disagree')
    # Repeat only the exhausted negative recipe, requiring its complete digest.
    prior_raw = candidate_from_eu(source_raw,context,index,next(iter(offsets)))
    require(sha(prior_raw) == PREVIOUS_NEGATIVE and len(prior_raw) == 1660,
            'Required prior negative does not reproduce exactly')
    prior_node = parse(prior_raw)
    candidate = clone(prior_node)
    source_leaf = source_node.field(0).field(3)
    require(source_leaf.tag == prior_node.field(0).field(3).tag == 9,
            'Authenticated mapNamespace integer tag differs')
    candidate.field(0).set_field(3,clone(source_leaf))
    require(candidate.field(0).field(3).value == source_leaf.value,
            'Authenticated source leaf was not retained')
    # No other field, outer record, struct order, or retained wire spelling changes.
    require([k for k,_ in candidate.value] == [k for k,_ in prior_node.value],
            'Outer field order changed')
    for key,_ in prior_node.value:
        if key != 0:
            require(encode(candidate.field(key)) == encode(prior_node.field(key)),
                    'Unrelated outer field changed')
    before_header,after_header = prior_node.field(0),candidate.field(0)
    require([k for k,_ in before_header.value] == [k for k,_ in after_header.value],
            'Header field order changed')
    for key,_ in before_header.value:
        if key != 3:
            require(encode(before_header.field(key)) == encode(after_header.field(key)),
                    'A field other than root/0/3 changed')
    body = encode(candidate)
    require(0 < len(body) <= HEADER_LIMIT,'Candidate exceeds bound')
    digest = sha(body)
    matched = digest == TARGET
    saved = False
    if matched:
        decoded = decode_verified_header(body,TARGET)
        observed = context.entries[index]
        h = decoded[0]
        require(decoded == to_generic(parse(body)) and h[0] == {0:280539,1:16} and
                h[2] == context.prefix[index] and h[4][7] == observed['visuals'] and
                h[14] == observed['dependencies'],'Independent complete target binding failed')
        for table in (h[8],h[4][8]):
            require({row[0]:row[1][0] for row in table} == observed['locales'],
                    'Actual US locale handles differ')
        require(save_exact_header(body,output,TARGET),'Exact-only exclusive save refused')
        require(_read(output,HEADER_LIMIT) == body,'Saved exact body differs')
        saved = True
    else:
        require(not output.exists() and not (PRIVATE/(digest+'.s2mh')).exists(),
                'A mismatching body exists at a forbidden result path')
    require(sha(_read(source_path,HEADER_LIMIT)) == SOURCE_SHA and
            sha(_read(REPLAY,3*1024*1024)) == REPLAY_SHA,'Source input changed')
    verify_pins()
    report = {'format':'hots-one-DataMod-preserved-source-namespace-trial-v1',
              'producer_sha256':sha(_read(Path(__file__),1024*1024)),
              'frozen_prerequisite_sha256':PINS,
              'source_EU_header_sha256':SOURCE_SHA,'actual_US_replay_sha256':REPLAY_SHA,
              'actual_US_member_sha256':MEMBER_SHA,'actual_US_package_id_version':[280539,16],
              'actual_US_terminal_target_sha256':TARGET,
              'required_previous_negative_sha256':PREVIOUS_NEGATIVE,
              'previous_negative_reproduced_in_RAM':True,
              'new_recipe_trials':1,'maximum_new_recipe_trials':1,
              'only_changed_path_from_prior_negative':'root/0/3',
              'authenticated_EU_source_leaf_preserved_exactly':True,
              'all_other_Node_subtrees_wire_bytes_unchanged':True,
              'candidate_sha256':digest,'bytes':len(body),
              'matches_complete_actual_target_SHA256':matched,
              'status':'exact-target-recovered' if matched else 'whole-target-hash-mismatch-stop',
              'independent_EOF_Node_agreement_and_actual_metadata_bound':matched,
              'candidate_body_saved':saved,'candidate_body_emitted':False,
              'all_source_inputs_unchanged':True,'namespace_creator_account_player_literals_emitted':False,
              'new_network_requests':0,'client_launched':False,'replay_modified':False,
              'limits':['One literal-preservation hypothesis; no general namespace or regional semantics inferred.',
                        'Only the entire actual advertised SHA256 authenticates this specific object.',
                        'Static-object recovery does not establish replay conversion or client playback.']}
    del body,prior_raw
    write_new_report(report,report_path)
    return {'status':report['status'],'candidate_sha256':digest,'bytes':report['bytes'],
            'saved':saved,'report_sha256':sha(_read(report_path,1024*1024))}

if __name__ == '__main__':
    print(json.dumps(execute()))
