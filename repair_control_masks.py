from __future__ import annotations

import argparse
import copy
import ctypes
import ctypes.util
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from bind_client_metadata import publish_binary
from migrate_replay import BitVector, SemanticDecoder, SemanticEncoder, dump, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import inspect_reference
from repair_startup import native_replace, v4_profile

SOURCE_DIGEST = '20a11a37fb365a17511ad27a8f7d7ebafd11c69f630794108f9d92b9675406b5'
DONOR_DIGEST = '05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75'
OUTPUT_NAME = 'TEN_GREYMANE_client98285_CONTROLS_R4_EXPERIMENTAL.StormReplay'
EXPECTED_INPUT = [(15, 32767)] * 10 + [(15, 896)] * 6
EXPECTED_REFERENCE = [(10, 1023)] * 10 + [(10, 28)] * 6
ERROR_MASK = 0x02AB


def masks(initial: dict) -> list[BitVector]:
    slots = initial['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions']
    if not isinstance(slots, list) or len(slots) != 16:
        raise ValueError('Expected exactly sixteen slot descriptions')
    values = [slot['m_allowedControls'] for slot in slots]
    for value in values:
        if not isinstance(value, BitVector) or type(value.length) is not int or type(value.value) is not int:
            raise ValueError('Invalid logical control mask')
        if not 0 < value.length <= 255 or not 0 <= value.value < 1 << value.length:
            raise ValueError('Control mask is out of range')
    return values


def validate_observation(observation: dict) -> list[BitVector]:
    if not isinstance(observation, dict) or observation.get('format') != 'hots-control-mask-observation-v1':
        raise ValueError('Unsupported control-mask observation')
    if observation.get('reference_sha256') != DONOR_DIGEST:
        raise ValueError('Unrecognized reference replay')
    if type(observation.get('declared_build')) is not int or observation['declared_build'] != 98285:
        raise ValueError('Unexpected observed build')
    if observation.get('full_reference_roundtrip') is not True:
        raise ValueError('Reference observation lacks full roundtrip provenance')
    raw = observation.get('masks')
    if not isinstance(raw, list) or len(raw) != 16:
        raise ValueError('Invalid reference mask count')
    values = []
    for item in raw:
        if not isinstance(item, list) or len(item) != 2 or any(type(x) is not int for x in item):
            raise ValueError('Invalid reference mask representation')
        values.append(tuple(item))
    if values != EXPECTED_REFERENCE:
        raise ValueError('Reference masks differ from the measured, fixed observation')
    return [BitVector(*value) for value in values]


def observe_reference(path: Path) -> dict:
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != DONOR_DIGEST:
        raise ValueError('Unexpected reference replay bytes')
    profile = inspect_reference(path, 96477, 98285)
    p = load_protocol(96477)
    archive = MPQArchive(path)
    try:
        initial = SemanticDecoder(archive.read_file('replay.initData'), p.typeinfos).instance(p.replay_initdata_typeid)
    finally:
        archive.close()
    observation = {
        'format': 'hots-control-mask-observation-v1',
        'reference_sha256': DONOR_DIGEST,
        'declared_build': 98285,
        'schema_build': 96477,
        'full_reference_roundtrip': True,
        'reference_profile_sha256': hashlib.sha256(dump(profile).encode('ascii')).hexdigest(),
        'masks': [[v.length, v.value] for v in masks(initial)],
        'client_acceptance_of_other_widths_proven': False,
    }
    validate_observation(observation)
    return observation


def transform(initial: dict, observation: dict) -> tuple[dict, list[dict]]:
    target = validate_observation(observation)
    current = masks(initial)
    if [(v.length, v.value) for v in current] != EXPECTED_INPUT:
        raise ValueError('Input masks differ from the scoped R3 experiment')
    result = copy.deepcopy(initial)
    slots = result['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions']
    changes = []
    for index, (old, new) in enumerate(zip(current, target, strict=True)):
        if old.value >> (old.length - new.length) != new.value:
            raise ValueError('Narrowing would change the preserved leading bits')
        slots[index]['m_allowedControls'] = new
        changes.append({'path': f'/m_syncLobbyState/m_gameDescription/m_slotDescriptions/{index}/m_allowedControls',
                        'before': [old.length, old.value], 'after': [new.length, new.value],
                        'operation': 'use-observed-width-preserving-leading-bits',
                        'removed_bits': old.length - new.length,
                        'removed_suffix_value': old.value & ((1 << (old.length - new.length)) - 1)})
    return result, changes


def integrity(path: Path) -> dict:
    path = Path(path)
    v4_profile(path)
    name = ctypes.util.find_library('storm')
    if not name:
        raise RuntimeError('Native StormLib is required for raw checksum verification')
    library = ctypes.CDLL(name)
    handle, dword = ctypes.c_void_p, ctypes.c_uint32
    declarations = {
        'SFileOpenArchive': ([ctypes.c_char_p, dword, dword, ctypes.POINTER(handle)], ctypes.c_bool),
        'SFileCloseArchive': ([handle], ctypes.c_bool),
        'SFileVerifyFile': ([handle, ctypes.c_char_p, dword], dword),
        'SFileVerifyRawData': ([handle, dword, ctypes.c_char_p], ctypes.c_int),
    }
    for key, (args, result) in declarations.items():
        function = getattr(library, key)
        function.argtypes, function.restype = args, result
    archive = MPQArchive(path)
    try:
        names = archive.read_file('(listfile)').decode('ascii').splitlines() + ['(listfile)', '(attributes)']
    finally:
        archive.close()
    if len(names) != 14 or len(set(names)) != 14:
        raise ValueError('Unexpected member list')
    native = handle()
    if not library.SFileOpenArchive(str(path.resolve()).encode(), 0, 0x100, ctypes.byref(native)):
        raise RuntimeError('Could not open archive for checksum verification')
    try:
        tables = {str(kind): library.SFileVerifyRawData(native, kind, None) for kind in range(1, 7)}
        members = {key: library.SFileVerifyFile(native, key.encode('ascii'), 15) for key in names}
    finally:
        if not library.SFileCloseArchive(native):
            raise RuntimeError('Could not close checksum-verification archive')
    if any(tables.values()) or any(value & ERROR_MASK for value in members.values()):
        raise ValueError('Native raw-data or member checksum verification failed')
    return {'raw_table_results': tables, 'member_verification_flags': members,
            'member_error_mask': ERROR_MASK, 'all_available_checksums_passed': True}


def repair(source: Path, output: Path, observation: dict) -> dict:
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise FileExistsError(output)
    validate_observation(observation)
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_DIGEST:
        raise ValueError('Expected the immutable R3 candidate')
    before = inspect_reference(source, 96477, 98285)
    input_integrity = integrity(source)
    p = load_protocol(96477)
    archive = MPQArchive(source)
    try:
        header = archive.header['user_data_header']['content']
        names = archive.read_file('(listfile)').decode('ascii').splitlines()
        original = {name: archive.read_file(name) or b'' for name in names}
        initial = SemanticDecoder(original['replay.initData'], p.typeinfos).instance(p.replay_initdata_typeid)
        intended, changes = transform(initial, observation)
        encoder = SemanticEncoder(p.typeinfos)
        encoder.instance(p.replay_initdata_typeid, intended)
        lobby = encoder.getvalue()
    finally:
        archive.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='controls-r4-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'checkpoint'
        stage.mkdir()
        destination = stage / OUTPUT_NAME
        container = native_replace(source, destination, header, {'replay.initData': lobby})
        after = inspect_reference(destination, 96477, 98285)
        output_integrity = integrity(destination)
        from mpyq import MPQArchive as IndependentArchive
        check = MPQArchive(destination)
        independent = IndependentArchive(str(destination), listfile=False)
        try:
            if check.header['user_data_header']['content'] != header:
                raise ValueError('Header changed during the mask-only experiment')
            if set(check.read_file('(listfile)').decode('ascii').splitlines()) != set(names):
                raise ValueError('Archive member set changed')
            for name, old in original.items():
                expected = lobby if name == 'replay.initData' else old
                if (check.read_file(name) or b'') != expected or (independent.read_file(name) or b'') != expected:
                    raise ValueError(f'Unexpected member difference: {name}')
            decoded = SemanticDecoder(check.read_file('replay.initData'), p.typeinfos).instance(p.replay_initdata_typeid)
            if decoded != intended:
                raise ValueError('Re-decoded lobby differs from the explicit mask transform')
        finally:
            check.close()
            independent.file.close()
        if before['streams'] != after['streams']:
            raise ValueError('At least one event stream changed')
        artifact = {'name': OUTPUT_NAME, **publish_binary(destination)}
        report = {
            'format': 'hots-control-mask-experiment-v1',
            'status': 'experimental-awaiting-client-test',
            'input_sha256': SOURCE_DIGEST, 'reference_sha256': DONOR_DIGEST,
            'declared_build': 98285, 'schema_build': 96477,
            'artifact': artifact, 'container': container, 'metadata_changes': len(changes),
            'changed_replay_members': ['replay.initData'],
            'old_lobby_bytes': len(original['replay.initData']), 'new_lobby_bytes': len(lobby),
            'header_bytes_identical': True, 'all_event_stream_bytes_identical': True,
            'other_replay_member_bytes_identical': True, 'all_masks_equal_reference': True,
            'mpyq_members_equal': True, 'observed_payload_roundtrip': True,
            'input_integrity': input_integrity, 'output_integrity': output_integrity,
            'client_playback_validated': False, 'cause_of_rejection_proven': False,
            'limitations': [
                'The observed ten-bit width is not proof that fifteen-bit masks cause rejection.',
                'The removed suffix contains five set bits for ten player slots and five zero bits for six observer slots.',
                'All leading ten bits are preserved; this changes allowed-control descriptors, not gameplay commands.',
                'Legacy battlelobby, dependency and synchronization payloads remain unconverted.',
                'No HotS executable was run by this generator.',
            ],
        }
        write_json(stage / 'report.json', report)
        write_json(stage / 'reference-mask-observation.json', observation)
        write_json(stage / 'candidate-profile.json', after)
        (stage / 'changes.jsonl').write_text(''.join(dump(change) + '\n' for change in changes), encoding='ascii')
        if output.exists():
            raise FileExistsError(output)
        shutil.move(str(stage), str(output))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument('--reference', type=Path)
    reference.add_argument('--observation', type=Path)
    args = parser.parse_args()
    observation = observe_reference(args.reference) if args.reference else json.loads(args.observation.read_text('utf-8'))
    print(json.dumps(repair(args.source, args.output, observation), indent=2))


if __name__ == '__main__':
    main()
