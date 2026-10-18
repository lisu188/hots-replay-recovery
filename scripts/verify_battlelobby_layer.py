"""Reproduce the real original/R8 and modern-control offline layer evidence.

This reads replay archives but writes only a new JSON report. It never invokes
HotS, modifies a replay, or promotes the in-memory result to a playable artifact.
Run with the repository and its pinned upstream/dependencies on PYTHONPATH.
"""
import argparse
import json
from pathlib import Path

from battlelobby_attribute_layer import (ORIGINAL_SHA256, LayerError, _read,
    _write_new, crosscheck_original, decode_layer, digest, encode_layer,
    summary, transcode_member)

R8_SHA256 = '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
R8_MEMBER_SHA256 = '2902a33a450491e8717a8006cef4627f2c12d1c0b854fc4f698dc1de0ade9640'
TRANSFORMED_MEMBER_SHA256 = 'bee7a6367574224321539ab21f0613e7c8e369a588327a2758ec53d64efe5edd'


def member(path):
    from mpq_reader import MPQArchive
    archive = MPQArchive(path)
    try:
        return archive.read_file('replay.server.battlelobby')
    finally:
        archive.close()


def verify(original, candidate, references):
    original, candidate = Path(original), Path(candidate)
    if digest(_read(original)) != ORIGINAL_SHA256 or digest(_read(candidate)) != R8_SHA256:
        raise LayerError('The pinned original and published R8 fixtures are required')
    if len(references) > 4:
        raise LayerError('At most four modern reference fixtures are accepted')
    results = {'format': 'hots-battlelobby-layer-fixture-verification-v1', 'fixtures': [],
               'new_replay_created': False, 'client_executed': False,
               'client_playback_validated': False}
    for role, path in [('original', original), ('published-r8', candidate)]:
        raw = member(path)
        model = decode_layer(raw, 'legacy-10')
        converted, report = transcode_member(raw, 'legacy-10', 'observed-11')
        check = crosscheck_original(model, original)
        if check['values_matched'] != 428:
            raise LayerError('Original attribute cross-check scope changed')
        if role == 'published-r8' and (digest(raw) != R8_MEMBER_SHA256 or digest(converted) != TRANSFORMED_MEMBER_SHA256):
            raise LayerError('Published R8 member or bounded transformation changed')
        results['fixtures'].append({'role': role, 'replay_sha256': digest(_read(path)),
                                    'source': summary(model), 'target': report['target'],
                                    'numeric_values_and_flags_preserved': report['numeric_values_and_flags_preserved'],
                                    'inverse_roundtrip_exact': report['inverse_roundtrip_exact'],
                                    'original_attributes': check})
    from reference_replay import inspect_reference
    for path in map(Path, references):
        profile = inspect_reference(path, 96477, 98348)
        if profile['schema_file_sha256'] != 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84':
            raise LayerError('Modern controls require the canonical pinned Blizzard schema')
        raw = member(path)
        model = decode_layer(raw, 'observed-11')
        if encode_layer(model, 'observed-11') != raw:
            raise LayerError('Modern fixture round-trip differs')
        results['fixtures'].append({'role': 'genuine-source-modern-control',
                                    'replay_sha256': profile['file_sha256'],
                                    'declared_build': profile['target']['m_version']['m_build'],
                                    'observed_payload_roundtrip': profile['observed_payload_roundtrip'],
                                    'stream_counts': {k: v['count'] for k, v in profile['streams'].items()},
                                    'source': summary(model), 'replay_authenticity_signature_verified': False})
    if digest(_read(original)) != ORIGINAL_SHA256 or digest(_read(candidate)) != R8_SHA256:
        raise LayerError('A pinned input changed during verification')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--modern-reference', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from battlelobby_attribute_layer import _check_new
    _check_new(args.output)
    result = verify(args.original, args.candidate, args.modern_reference)
    _write_new(args.output, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'fixtures_checked': len(result['fixtures']), 'client_executed': False,
                      'new_replay_created': False, 'report': str(args.output)}, indent=2))
