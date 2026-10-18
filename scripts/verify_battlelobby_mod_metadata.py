"""Verify immutable original/R8 mod metadata and optional current controls.

This only reads replay archives. Its sole output is a new sanitized JSON report.
Modern build/core-stream provenance is supplied by the separate reference audit;
this script checks only the selected battlelobby serialization profiles.
"""
import argparse
import json
from pathlib import Path

from audit_battlelobby_mod_metadata import LayerError, audit_member, sha256, source_provenance
from battlelobby_attribute_layer import ORIGINAL_SHA256, _read, transcode_member

R8_SHA256 = '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
ATTR_MEMBER_SHA256 = 'bee7a6367574224321539ab21f0613e7c8e369a588327a2758ec53d64efe5edd'


def member(path):
    from mpq_reader import MPQArchive
    # Reject oversized or nonregular archives before the existing MPQ reader.
    # Its container/decompression validation remains a separate dependency.
    _read(path)
    archive = MPQArchive(path)
    try:
        return archive.read_file('replay.server.battlelobby')
    finally:
        archive.close()


def verify(original, candidate, references):
    original, candidate = Path(original), Path(candidate)
    if sha256(_read(original)) != ORIGINAL_SHA256 or sha256(_read(candidate)) != R8_SHA256:
        raise LayerError('Pinned immutable original and published R8 inputs are required')
    if len(references) > 8:
        raise LayerError('At most eight modern controls are supported')
    results = []
    for label, path in (('original', original), ('published-r8', candidate)):
        raw = member(path)
        result = audit_member(raw, 'legacy-10', 'historical-fixed')
        if result['used_mod_count'] != 5 or result['mod_metadata_count'] != 5:
            raise LayerError('Pinned source mod-count observations changed')
        result.update(id=label, replay_sha256=sha256(_read(path)))
        results.append(result)
        if label == 'published-r8':
            converted, _ = transcode_member(raw, 'legacy-10', 'observed-11')
            if sha256(converted) != ATTR_MEMBER_SHA256:
                raise LayerError('Pinned prospective attribute member changed')
            result = audit_member(converted, 'observed-11', 'historical-fixed')
            result.update(id='r8-prospective-attribute-layer-memory-only',
                          source_replay_sha256=R8_SHA256, replay_created=False)
            results.append(result)
    for index, path in enumerate(map(Path, references)):
        result = audit_member(member(path), 'observed-11', 'current-observed')
        result.update(id=f'provided-modern-control-{index+1}', replay_sha256=sha256(_read(path)),
                      declared_build_and_core_streams_require_separate_reference_report=True)
        results.append(result)
    source_results = results[:3]
    if len({x['section_sha256'] for x in source_results}) != 1 or len({x['after_section_sha256'] for x in source_results}) != 1:
        raise LayerError('Old source mod section or suffix preservation differs')
    if sha256(_read(original)) != ORIGINAL_SHA256 or sha256(_read(candidate)) != R8_SHA256:
        raise LayerError('A pinned input changed during verification')
    return dict(format='hots-battlelobby-mod-metadata-fixture-verification-v2',
                sources=source_provenance(), results=results,
                source_section_and_suffix_exact_in_original_r8_and_attr_candidate=True,
                synthetic_or_real_native_client_used=False, replay_or_member_written=False,
                conclusion='Source static arcade sections are counted arrays, privately preserved exactly; complete current package coherence and replay compatibility remain separate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--modern-reference', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.suffix.lower() != '.json':
        parser.error('Output must be a new .json report')
    output = verify(args.original, args.candidate, args.modern_reference)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(fixtures_checked=len(output['results']),
                          all_same_profile_roundtrips_exact=True,
                          replay_or_member_written=False)))
