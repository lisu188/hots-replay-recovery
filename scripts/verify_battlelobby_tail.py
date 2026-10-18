"""Read original/R8 and optional hash-bound modern cohort; write sanitized JSON."""
import argparse
import json
from pathlib import Path

from audit_battlelobby_mod_metadata import audit_member
from battlelobby_attribute_layer import ORIGINAL_SHA256, _read
from battlelobby_tail import LayerError, crosscheck, decode_tail, digest, summary

R8_SHA256='4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
CANONICAL_SHA256='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
ORIGINAL_SCHEMA_SHA256='879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd'


def verify_one(path, label, expected, modern):
    from mpq_reader import MPQArchive
    from protocol_loader import load_protocol
    if digest(_read(path)) != expected: raise LayerError('Replay digest differs from pinned input')
    protocol=load_protocol(96477 if modern else 41810)
    if not modern and protocol.recovery_schema_sha256 != ORIGINAL_SCHEMA_SHA256:
        raise LayerError('Canonical pinned Blizzard41810 schema is required')
    if modern and protocol.recovery_schema_sha256 != CANONICAL_SHA256:
        raise LayerError('Canonical pinned Blizzard96477 schema is required')
    archive=MPQArchive(path)
    try:
        raw=archive.read_file('replay.server.battlelobby')
        mods=audit_member(raw,'observed-11' if modern else 'legacy-10','current-observed' if modern else 'historical-fixed')
        tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail' if modern else 'historical-tail')
        # R8's replay.details/initData use current serialization while retaining
        # historical tail bits. Select their actual schema independently.
        identity_protocol=load_protocol(96477) if label=='published-r8' else protocol
        if label=='published-r8' and identity_protocol.recovery_schema_sha256 != CANONICAL_SHA256:
            raise LayerError('Canonical pinned Blizzard96477 schema is required for R8 identities')
        details=identity_protocol.decode_replay_details(archive.read_file('replay.details'))
        initial=identity_protocol.decode_replay_initdata(archive.read_file('replay.initData'))
        checks=crosscheck(tail,details,initial)
        if (not checks['all_details_participants_match_tail_by_slot'] or
            not checks['initdata_identity_multiset_equal'] or
            checks['initdata_identity_and_slot_matches'] != checks['players_checked'] or
            not checks['seed_matches_lobby'] or not checks['seed_matches_game_description'] or
            checks['disabled_hero_list_equal'] is False):
            raise LayerError('Private identity, slot, seed or disabled-list crosscheck differs')
        report=summary(tail)
        report.update(id=label,replay_sha256=expected,identity_schema_sha256=identity_protocol.recovery_schema_sha256,
                      identity_crosscheck=checks,required_private_crosschecks_verified=True)
    finally: archive.close()
    if digest(_read(path)) != expected: raise LayerError('Replay changed during audit')
    return report


def verify(original,candidate,cohort_manifest=None,cohort_root=None):
    rows=[verify_one(original,'original41810',ORIGINAL_SHA256,False),
          verify_one(candidate,'published-r8',R8_SHA256,False)]
    source_manifest=None
    if cohort_manifest is not None:
        if cohort_root is None: raise LayerError('Explicit cohort root is required')
        source=_read(cohort_manifest);source_manifest=digest(source);manifest=json.loads(source)
        refs=manifest['references']
        if not 1<=len(refs)<=16: raise LayerError('Unsupported cohort size')
        if len({r['replay_sha256'] for r in refs}) != len(refs): raise LayerError('Duplicate cohort replay')
        root=Path(cohort_root).resolve()
        for index,ref in enumerate(refs):
            if ref['build']!=98348 or ref['schema_file_sha256']!=CANONICAL_SHA256 or ref['observed_payload_roundtrip'] is not True:
                raise LayerError('Cohort admission lacks pinned current-reference proof')
            path=(root/ref['replay_file']).resolve()
            if not path.is_relative_to(root): raise LayerError('Cohort path escapes declared root')
            rows.append(verify_one(path,f'current-control-{index+1:02}',ref['replay_sha256'],True))
    return dict(format='hots-battlelobby-tail-fixture-verification-v1',cohort_manifest_sha256=source_manifest,
        canonical_blizzard_schema_sha256=CANONICAL_SHA256,results=rows,
        canonical_original_blizzard_schema_sha256=ORIGINAL_SCHEMA_SHA256,
        no_member_or_replay_written=True,client_launched=False,conversion_performed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--cohort-manifest',type=Path)
    parser.add_argument('--cohort-root',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.suffix.lower()!='.json':
        parser.error('Output must be a new .json report')
    report=verify(args.original,args.candidate,args.cohort_manifest,args.cohort_root)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream: json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(fixtures=len(report['results']),all_complete_eof_roundtrips_exact=True,
                          required_private_identity_seed_crosschecks_verified=True,
                          client_launched=False),indent=2))
