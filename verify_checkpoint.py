from __future__ import annotations

import argparse
import base64
import ctypes
import ctypes.util
import hashlib
import itertools
import json
import struct
import zlib
from pathlib import Path

import mpyq

from migrate_replay import BitVector, decode_events, protocol, write_json
from mpq_reader import MPQArchive
from mpq_rebuild import verify_container


SOURCE_LISTFILE_MD5 = '8b539c554452a290100542cc97a05439'


def native(value):
    if isinstance(value, BitVector):
        return value.length, value.value
    if isinstance(value, dict):
        return {k: native(v) for k, v in value.items() if k != '_bits'}
    if isinstance(value, list):
        return [native(v) for v in value]
    return value


def restore_json(value):
    if isinstance(value, dict):
        if set(value) == {'$bytes_base64'}:
            return base64.b64decode(value['$bytes_base64'], validate=True)
        if set(value) == {'$bitvector'}:
            v = value['$bitvector']
            return v['length'], int(v['packed'], 16)
        return {k: restore_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [restore_json(v) for v in value]
    return value


def stormlib_check(path, members, required):
    name = ctypes.util.find_library('storm')
    if not name:
        if required:
            raise RuntimeError('StormLib library was not found')
        return {'tested': False}
    lib = ctypes.CDLL(name)
    handle = ctypes.c_void_p
    dword = ctypes.c_uint32
    lib.SFileOpenArchive.argtypes = [ctypes.c_char_p, dword, dword, ctypes.POINTER(handle)]
    lib.SFileOpenArchive.restype = ctypes.c_bool
    lib.SFileOpenFileEx.argtypes = [handle, ctypes.c_char_p, dword, ctypes.POINTER(handle)]
    lib.SFileOpenFileEx.restype = ctypes.c_bool
    lib.SFileGetFileSize.argtypes = [handle, ctypes.POINTER(dword)]
    lib.SFileGetFileSize.restype = dword
    lib.SFileReadFile.argtypes = [handle, ctypes.c_void_p, dword, ctypes.POINTER(dword), ctypes.c_void_p]
    lib.SFileReadFile.restype = ctypes.c_bool
    lib.SFileCloseFile.argtypes = [handle]
    lib.SFileCloseArchive.argtypes = [handle]
    archive = handle()
    if not lib.SFileOpenArchive(str(Path(path).resolve()).encode(), 0, 0, ctypes.byref(archive)):
        raise AssertionError('StormLib rejected the rebuilt archive')
    try:
        for filename, expected in members.items():
            file_handle = handle()
            if not lib.SFileOpenFileEx(archive, filename.encode(), 0, ctypes.byref(file_handle)):
                raise AssertionError(f'StormLib cannot open {filename}')
            try:
                high = dword()
                size = lib.SFileGetFileSize(file_handle, ctypes.byref(high))
                if high.value or size != len(expected or b''):
                    raise AssertionError(f'StormLib size mismatch: {filename}')
                if size:
                    buf = ctypes.create_string_buffer(size)
                    read = dword()
                    if not lib.SFileReadFile(file_handle, buf, size, ctypes.byref(read), None):
                        raise AssertionError(f'StormLib read failed: {filename}')
                    if read.value != size or buf.raw != expected:
                        raise AssertionError(f'StormLib content mismatch: {filename}')
            finally:
                lib.SFileCloseFile(file_handle)
    finally:
        lib.SFileCloseArchive(archive)
    return {'tested': True, 'all_members_equal': True, 'member_count': len(members)}


def verify(folder, require_stormlib=False):
    folder = Path(folder)
    report_path = folder / 'report.json'
    report = json.loads(report_path.read_text())
    build = report['target_protocol']
    path = folder / f'TEN_GREYMANE_protocol{build}.StormReplay'
    if hashlib.sha256(path.read_bytes()).hexdigest() != report['output_sha256']:
        raise AssertionError('Checkpoint digest mismatch')
    p = protocol(build)
    archive = MPQArchive(path)
    independent = mpyq.MPQArchive(str(path), listfile=False)
    try:
        members = {}
        names = archive.read_file('(listfile)').decode().splitlines() + ['(listfile)', '(attributes)']
        for name in names:
            raw = archive.read_file(name)
            if independent.read_file(name) != raw:
                raise AssertionError(f'mpyq content mismatch: {name}')
            members[name] = raw
        header = p.decode_replay_header(independent.header['user_data_header']['content'])
        expected_header = restore_json(json.loads((folder / 'header.json').read_text()))
        if header != expected_header:
            raise AssertionError('Official header decoder disagrees with JSON projection')
        initial = p.decode_replay_initdata(independent.read_file('replay.initData'))
        expected_initial = restore_json(json.loads((folder / 'initData.json').read_text()))
        if initial != expected_initial:
            raise AssertionError('Official lobby decoder disagrees with JSON projection')
        counts = {}
        sentinel = object()
        for kind in ('game', 'message', 'tracker'):
            raw = members[f'replay.{kind}.events']
            own = decode_events(raw, p, kind)
            official = getattr(p, f'decode_replay_{kind}_events')(raw)
            count = 0
            for a, b in itertools.zip_longest(own, official, fillvalue=sentinel):
                if a is sentinel or b is sentinel or native(a) != native(b):
                    raise AssertionError(f'Official {kind} decoder mismatch at event {count}')
                count += 1
            counts[kind] = count
        if counts != report['events']:
            raise AssertionError('Official event counts differ')
        attrs = members['(attributes)']
        version, flags = struct.unpack_from('<II', attrs)
        if version != 100 or flags != 5:
            raise AssertionError('Unexpected attributes layout')
        count = len(archive.block_table)
        omitted_source_digests = []
        for name, raw in members.items():
            if name == '(attributes)' or raw is None:
                continue
            index = archive.get_hash_table_entry(name).block_table_index
            crc = struct.unpack_from('<I', attrs, 8 + 4 * index)[0]
            start = 8 + 4 * count + 16 * index
            recorded_md5 = attrs[start:start + 16]
            actual_md5 = hashlib.md5(raw).digest()
            if crc != zlib.crc32(raw):
                raise AssertionError(f'Member CRC32 mismatch: {name}')
            if name == '(listfile)' and recorded_md5 == bytes(16):
                if actual_md5.hex() != SOURCE_LISTFILE_MD5:
                    raise AssertionError('Listfile differs from preserved original')
                omitted_source_digests.append(name)
            elif recorded_md5 != actual_md5:
                raise AssertionError(f'Member MD5 mismatch: {name}')
        report['independent_validation'] = {
            'blizzard_decoded_all_streams': True, 'blizzard_event_counts': counts,
            'mpyq_all_members_equal': True, 'member_crc32_and_available_md5': True,
            'md5_omitted_in_original': omitted_source_digests,
            'stormlib': stormlib_check(path, members, require_stormlib),
            'mpq_v4': verify_container(path),
        }
        write_json(report_path, report)
        print(json.dumps(report['independent_validation'], indent=2))
        return report
    finally:
        archive.close()
        independent.file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--require-stormlib', action='store_true')
    args = parser.parse_args()
    verify(args.folder, args.require_stormlib)
