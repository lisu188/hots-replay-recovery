"""Read hash-bound actual replays; emit only aggregate availability counts/equality."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import decode_tail, digest
from collection_license_audit import _read, write_new_report
from mpq_reader import MPQArchive


WORK=Path(__file__).resolve().parents[1]
ORIGINAL_SHA='e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
R8_SHA='4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
CANONICAL_SHA='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'


def aggregate(rows):
    if not rows or any(not isinstance(row,bytes) or len(row)!=32 for row in rows):
        raise ValueError('Expected nonempty fixed32-byte availability rows')
    cells=[row[offset:offset+2] for row in rows for offset in range(0,32,2)]
    return {'rows':len(rows),'bytes':len(rows)*32,'zero_rows':sum(not any(row) for row in rows),
        'nonzero_rows':sum(bool(any(row)) for row in rows),'distinct_32byte_rows':len(set(rows)),
        'all_rows_identical':len(set(rows))==1,'all_bytes_zero':not any(any(row) for row in rows),
        'zero_bytes':sum(row.count(0) for row in rows),
        'nonzero_bytes':sum(sum(byte!=0 for byte in row) for row in rows),
        'distinct_two_byte_cell_values':len(set(cells)),
        'rows_with_all16_two_byte_cells_equal':sum(len({row[i:i+2] for i in range(0,32,2)})==1 for row in rows)}


def analyze():
    cohort_path=WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json'
    cohort_raw=_read(cohort_path,4*1024*1024)
    manifest=json.loads(cohort_raw)
    references=manifest['references']
    if len(references)!=12:
        raise ValueError('Expected precisely twelve established US controls')
    cases=[('original41810',WORK/'TEN_GREYMANE_source_41810.StormReplay',ORIGINAL_SHA,False),
           ('published-r8',WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay',R8_SHA,False)]
    for index,reference in enumerate(references):
        if reference['build']!=98348 or reference['schema_file_sha256']!=CANONICAL_SHA or reference['observed_payload_roundtrip'] is not True:
            raise ValueError('Current control lacks established build/schema/roundtrip provenance')
        path=(WORK/reference['replay_file']).resolve()
        if not path.is_relative_to(WORK.resolve()):
            raise ValueError('Cohort path escapes task work')
        cases.append((f'current-us-{index+1:02}',path,reference['replay_sha256'],True))
    eu_binding_path=WORK/'eu-replay-search-20261018/one-eu-current-reference-binding.json'
    eu_raw=_read(eu_binding_path,1024*1024);eu=json.loads(eu_raw)
    if eu['data_build']!=98348 or eu['file_sha256']!='a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4':
        raise ValueError('EU control lacks established98348 provenance')
    cases.append(('current-eu-01',WORK/'eu-replay-search-20261018/heroeslounge-27515-g1-20261005.StormReplay',eu['file_sha256'],True))
    result,availability_groups,registries={},[],{False:[],True:[]}
    for label,path,expected,modern in cases:
        raw=_read(path,5*1024*1024)
        if digest(raw)!=expected:
            raise ValueError('Replay differs from existing acquisition provenance')
        archive=MPQArchive(path)
        try:
            member=archive.read_file('replay.server.battlelobby')
        finally:
            archive.close()
        mods=audit_member(member,'observed-11' if modern else 'legacy-10','current-observed' if modern else 'historical-fixed')
        tail=decode_tail(member,mods['terminal_handles_end_bit'],'current-tail' if modern else 'historical-tail')
        rows=[token.value for token in tail.tokens if token.path.startswith('/availability/') and token.width is None]
        registry=[token.value for token in tail.tokens if token.path.startswith('/collections/') and token.path.endswith('/value')]
        assert len(rows)==len(registry)==(5418 if modern else 263)
        registries[modern].append(registry)
        blob=b''.join(rows)
        group=next((index for index,value in enumerate(availability_groups) if value==blob),None)
        if group is None:
            group=len(availability_groups);availability_groups.append(blob)
        result[label]={'replay_sha256':expected,'member_sha256':digest(member),'profile':tail.profile,
            'aggregate':aggregate(rows),'availability_equality_group':group+1,
            'complete_member_EOF_and_same_profile_roundtrip_verified':True,
            'raw_availability_or_slot_values_emitted':False,'ownership_semantics_inferred':False}
        if digest(_read(path,5*1024*1024))!=expected:
            raise ValueError('Replay changed during read-only audit')
    return {'format':'hots-collection-availability-aggregate-observation-v1',
        'source_producer_sha256':digest(Path(__file__).read_bytes()),
        'cohort_manifest_sha256':digest(cohort_raw),'EU_binding_sha256':digest(eu_raw),
        'cases':result,'case_count':len(result),'distinct_full_availability_blobs':len(availability_groups),
        'legacy_two_ordered_registries_identical':all(value==registries[False][0] for value in registries[False]),
        'current_thirteen_ordered_raw8byte_registries_identical':all(value==registries[True][0] for value in registries[True]),
        'availability_equality_group_counts':dict(Counter(row['availability_equality_group'] for row in result.values())),
        'raw_availability_bytes_hashes_slot_or_player_values_emitted':False,
        'availability_value_meanings_or_ownership_semantics_proven':False,
        'client_launched':False,'replay_modified':False,
        'limitations':['Equality groups compare complete availability bytes only; no raw bytes, hashes, slot identities or values are exported.',
            'Counts do not establish flags, sentinel values, entitlement ownership or safe defaults.',
            'The global registry list is compared separately from its associated availability rows.']}


if __name__=='__main__':
    report=analyze();output=WORK/'collection-registry-ready/availability-aggregate-15-cases.json'
    write_new_report(report,output)
    print(json.dumps({'cases':report['case_count'],'distinct_blobs':report['distinct_full_availability_blobs'],
        'legacy_registry_equal':report['legacy_two_ordered_registries_identical'],
        'current_registry_equal':report['current_thirteen_ordered_raw8byte_registries_identical'],
        'aggregate_cases':{key:row['aggregate'] for key,row in report['cases'].items()},
        'report_sha256':digest(output.read_bytes())},sort_keys=True))
