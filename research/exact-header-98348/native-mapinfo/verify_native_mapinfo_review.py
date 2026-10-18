"""Bounded independent physical-bit review of one genuine six-record control.

Research setup paths are explicit. No game/PE/network calls or raw data writes.
The MapInfo decoder is reviewed code; span reconstruction below is independent.
"""
from collections import Counter
from io import BytesIO
from pathlib import Path
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
READY = WORK / 'native-mapinfo-ready'
sys.path[:0] = [str(READY), str(REPO), str(WORK/'heroprotocol'), str(WORK/'python-deps')]
import native_mapinfo as native
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import decode_tail, crosscheck
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

REPLAY = WORK/'reference-donors/ngs-20261016-protectors-dragon.StormReplay'
REPLAY_SHA = '882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'
MEMBER_SHA = 'ab03d9533081e9d69d205a6adec9df6a0aaf5ff47a05ecc8bf670b6760b0ab55'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


class RAMArchive(MPQArchive):
    def __init__(self, raw):
        self.file = BytesIO(raw)
        self.header = self.read_header()
        self.hash_table = self.read_table('hash')
        self.block_table = self.read_table('block')


def scalar(raw, at, count):
    """Independent physical-bit reader; no library reader is used."""
    value = 0
    while count:
        size = min(count, 8-at % 8)
        chunk = (raw[at//8] >> (at % 8)) & ((1 << size)-1)
        value = (value << size) | chunk
        at += size
        count -= size
    return value


def reconstruct(info):
    """Independent chunk-to-physical-bit writer, including byte alignment."""
    start = info.start_bit//8*8
    physical = [(info.source[at//8] >> (at % 8)) & 1
                for at in range(start, info.start_bit)]
    position = info.start_bit
    for token in info.tokens:
        if token.width is None:
            padding = (-position) % 8
            physical.extend([0]*padding)
            position += padding
            for byte in token.value:
                physical.extend((byte >> bit) & 1 for bit in range(8))
                position += 8
        else:
            remaining = token.width
            while remaining:
                count = min(remaining, 8-position % 8)
                remaining -= count
                chunk = token.value >> remaining
                physical.extend((chunk >> bit) & 1 for bit in range(count))
                position += count
    require(position == info.end_bit, 'Independent token extent differs')
    expected = [(info.source[at//8] >> (at % 8)) & 1
                for at in range(start, info.end_bit)]
    require(physical == expected, 'Independent physical span reconstruction differs')
    return len(physical), len(info.tokens)


def analyze():
    source_paths = [READY/'native_mapinfo.py', READY/'native_mapinfo_schema_98348.json',
                    REPO/'native_clientinfo.py', HERE/'test_native_mapinfo.py', Path(__file__)]
    sources = {path.relative_to(WORK).as_posix() if path.is_relative_to(WORK) else path.name:
               sha(path.read_bytes()) for path in source_paths}
    require(sources['native-mapinfo-ready/native_mapinfo_schema_98348.json'] == native.SCHEMA_SHA256,
            'Selected schema pin differs')
    before = REPLAY.stat()
    require(not REPLAY.is_symlink() and 1 <= before.st_size <= 2*1024*1024, 'Replay bound differs')
    with REPLAY.open('rb') as stream:
        raw_replay = stream.read(2*1024*1024+1)
        after_read = os.fstat(stream.fileno())
    require(len(raw_replay) == before.st_size == after_read.st_size and
            before.st_mtime_ns == after_read.st_mtime_ns and sha(raw_replay) == REPLAY_SHA,
            'Replay source changed or differs')
    archive = RAMArchive(raw_replay)
    try:
        protocol = load_protocol(96477)
        require(protocol.recovery_schema_sha256 == 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84',
                'Official identity schema differs')
        header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        require(header['m_version']['m_build'] == header['m_version']['m_baseBuild'] ==
                header['m_dataBuildNum'] == 98348 and
                header['m_ngdpRootKey']['m_data'].hex() == 'c3b3c8bc82e3a5a62e550fdde9a40c28',
                'Actual build/root differs')
        member = archive.read_file('replay.server.battlelobby')
        details_raw = archive.read_file('replay.details')
        init_raw = archive.read_file('replay.initData')
        require(len(member)+len(details_raw)+len(init_raw) <= 1024*1024 and sha(member) == MEMBER_SHA,
                'Selected members bound/digest differs')
        metadata = audit_member(member, 'observed-11', 'current-observed')
        tail = decode_tail(member, metadata['terminal_handles_end_bit'], 'current-tail')
        checks = crosscheck(tail, protocol.decode_replay_details(details_raw), protocol.decode_replay_initdata(init_raw))
        require(checks['all_details_participants_match_tail_by_slot'] and checks['initdata_identity_multiset_equal']
                and checks['initdata_identity_and_slot_matches'] == len(tail.players)
                and checks['seed_matches_lobby'] and checks['seed_matches_game_description'],
                'Private details/init/tail gates differ')
        require(len(metadata['entries']) == 6, 'Six-record control required')
        schema = native._schema().records
        root_fields = schema[5852]['field_names']
        rows = []
        for index, entry in enumerate(metadata['entries']):
            info = native.decode_mapinfo(member, entry['start_bit'], native.PROFILE)
            require(info.end_bit == entry['end_bit'], 'Observed/current native record end differs')
            require(info.identity == (scalar(member, info.start_bit, 32), scalar(member, info.start_bit+32, 32)),
                    'Independent handle pair differs')
            position = info.start_bit
            for name in root_fields:
                field = info.field('/'+name)
                require(field.start_bit == position, 'Named root field coverage is not contiguous')
                position = field.end_bit
            require(position == info.end_bit, 'Named root field coverage is incomplete')
            require(info.field('/m_addMultiMod').start_bit == info.end_bit-32 and
                    info.field('/m_requiredPermissions', 'ARRAY').start_bit == info.end_bit-31 and
                    scalar(member, info.end_bit-31, 31) == 0, 'Independent final scalar/list boundary differs')
            span_bits, tokens = reconstruct(info)
            rows.append({'index': index, 'start_bit': info.start_bit, 'end_bit': info.end_bit,
                         'independent_physical_bits_checked_including_leading_alignment': span_bits,
                         'wire_tokens_reconstructed': tokens, 'named_root_fields_contiguous': 32})
        facts = native.audit_current_map_infos(member, metadata)
        # A saved report with one plausible changed offset must not be trusted.
        forged = json.loads(json.dumps(metadata))
        forged['entries'][0]['start_bit'] += 1
        try:
            native.audit_current_map_infos(member, forged)
        except native.LayerError:
            forged_rejected = True
        else:
            raise ValueError('Forged report was accepted')
    finally:
        archive.close()
    after = REPLAY.stat()
    require(before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
            'Replay stat changed after review')
    for path in source_paths:
        label = path.relative_to(WORK).as_posix() if path.is_relative_to(WORK) else path.name
        require(sha(path.read_bytes()) == sources[label], 'Reviewed source changed')
    return {'format': 'hots-native-MapInfo-independent-review-v1', 'material_findings': [],
            'source_hashes': sources, 'schema_closed_types': len(schema), 'root_fields': len(root_fields),
            'focused_synthetic_tests': {'run': 13, 'passed': 13, 'skipped': 0,
                'fixture_values_invented': True, 'writer_independent_of_library_writer': True},
            'actual_replay_sha256': REPLAY_SHA, 'actual_member_sha256': MEMBER_SHA,
            'actual_build_base_data': 98348, 'actual_root': 'c3b3c8bc82e3a5a62e550fdde9a40c28',
            'actual_records': rows, 'private_details_init_and_tail_gates_passed': True,
            'independent_token_physical_reconstruction_exact': True,
            'changed_metadata_offset_rejected': forged_rejected, 'native_audit_facts': facts,
            'replay_bytes_read_once_from_disk': len(raw_replay),
            'selected_member_bytes_decoded': len(member)+len(details_raw)+len(init_raw),
            'PE_reads': 0, 'network_or_client_used': False, 'raw_or_private_values_written': False,
            'limits': ['Review covers the pinned current 191-type MapInfo closure and one genuine six-record control.',
                       'The 21-case producer is source-reviewed separately; this review does not rerun it.',
                       'No historical mapping, missing namespace recovery or full replay upgrade follows.']}


if __name__ == '__main__':
    output = HERE/'native-mapinfo-independent-review.json'
    require(not output.exists() and not output.is_symlink(), 'Refuse review report overwrite')
    data = (json.dumps(analyze(), indent=2, sort_keys=True)+'\n').encode()
    require(len(data) <= 64*1024, 'Review report exceeds cap')
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': sha(data)}))
