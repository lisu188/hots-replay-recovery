"""Targeted, private-in-RAM replay-header pattern test; never writes a replay."""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
from inspect_player_opaque import load_cases, scalar_hits, _Reader, _read
from protocol_loader import load_protocol
from mpq_reader import MPQArchive

WORK = Path(__file__).resolve().parent


def positions(tail):
    pos = len(tail.prefix) * 8
    out = {}
    for token in tail.tokens:
        if token.width is None:
            pos += -pos % 8
        out[token.path] = pos
        pos += len(token.value)*8 if token.width is None else token.width
    assert pos == tail.member_bytes * 8
    return out


def main():
    cases, manifest_sha = load_cases()
    # The raw MPQ user header, independently decoded with the pinned official
    # schema, provides these expected values; no player field supplies them.
    paths = [WORK/'TEN_GREYMANE_source_41810.StormReplay',
             WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay']
    manifest = json.loads(_read(WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json'))
    paths += [WORK/ref['replay_file'] for ref in manifest['references']]
    results = []
    for case, path in zip(cases, paths, strict=True):
        archive = MPQArchive(path)
        try:
            protocol = load_protocol(96477 if case['modern'] or case['id']=='r8' else 41810)
            header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        finally:
            archive.close()
        build = header['m_version']['m_build']
        pos = positions(case['tail'])
        expected_build = 98348 if case['modern'] else (98285 if case['id']=='r8' else 41810)
        assert build == expected_build
        fields = [t.value for t in case['tail'].tokens if t.path.endswith('/community_named_build32')]
        assert len(fields) == len(case['players'])
        record_results = []
        for i, player in enumerate(case['players']):
            start = pos[f'/players/{i}/unknown32']
            end = pos[f'/players/{i+1}/unknown32'] if i+1<len(case['players']) else case['tail'].report['boundaries_bits']['players_end']
            block = player['start']
            row = {'record_ordinal': i, 'record_bits':end-start,
                   'opaque_start_relative_to_record':block-start,
                   'community_field_start_relative_to_opaque':pos[f'/players/{i}/community_named_build32']-block}
            for label, value in [('header_build_u32',build),
                                 ('header_build_u32_byte_reversed',int.from_bytes(build.to_bytes(4,'big'),'little'))]:
                offsets = scalar_hits(case['raw'],start,end-start,32,value)
                row[label] = {'opaque_hits': [x+start-block for x in offsets if block<=x+start<=block+player['size']-32],
                              'whole_record_hits_relative_to_opaque': [x+start-block for x in offsets]}
            # Wrong-build controls use all other observed header builds. All
            # players share a header build, so a wrong-slot control is invalid.
            row['wrong_build_controls'] = {str(v): scalar_hits(case['raw'],start,end-start,32,v)
                                           for v in (41810,98285,98348) if v!=build}
            record_results.append(row)
        results.append({'case':case['id'],'replay_sha256':case['sha256'],
            'member_sha256':case['member_sha256'],'header_build':build,
            'records':len(record_results),'community_field_matches_header':sum(v==build for v in fields),
            'records_with_header_build_in_opaque':sum(bool(x['header_build_u32']['opaque_hits']) for x in record_results),
            'records_with_header_build_anywhere_in_record':sum(bool(x['header_build_u32']['whole_record_hits_relative_to_opaque']) for x in record_results),
            'records_with_reversed_header_build_anywhere_in_record':sum(bool(x['header_build_u32_byte_reversed']['whole_record_hits_relative_to_opaque']) for x in record_results),
            'record_results':record_results})
        assert hashlib.sha256(_read(path)).hexdigest()==case['sha256']
    report={'format':'hots-player-header-build-pattern-test-v1','source_manifest_sha256':manifest_sha,
        'method':'Full unsigned32 decoded header build and complete reversed-octet representation at every bit offset within independently delimited player records. Private player values remain in RAM.',
        'cases':results,'wrong_slot_control_applicable':False,
        'wrong_slot_control_reason':'The header build is match-global and equal for every player; wrong-slot matches cannot validate semantics.',
        'no_named_internal_field_or_conversion_inferred':True,'replays_unchanged':True,'client_launched':False}
    out=WORK/'player-header-build-pattern-test.json'
    with out.open('x',encoding='utf-8',newline='\n') as f: json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'cases':len(results),'records':sum(x['records'] for x in results),
        'old_header_in_opaque':sum(x['records_with_header_build_in_opaque'] for x in results if not x['case'].startswith('current')),
        'current_header_in_opaque':sum(x['records_with_header_build_in_opaque'] for x in results if x['case'].startswith('current')),
        'summary':[{k:v for k,v in x.items() if k!='record_results'} for x in results],
        'report_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
