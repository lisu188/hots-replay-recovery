"""Bounded metadata-only reader for five already identified B41810 crash sets.

Full-file hash passes treat bytes as opaque. Structural parsing follows only
header/directory/module/name/CodeView RVAs. No memory/thread/exception/context
stream contents are interpreted, copied or returned. Error text parsing is
restricted to its first 45 header lines and explicitly allowlisted fields.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import struct
import uuid

from collection_license_audit import write_new_report

DISTINCT_LIMIT = 2*1024*1024
FILE_LIMIT = 256*1024
MAX_MODULES = 1024
CASE_TIMES = ('2022-07-27 22.10.05', '2022-07-27 22.11.31',
              '2022-08-09 20.10.37', '2022-08-09 20.12.10', '2022-08-09 20.13.42')
MODULE = 'HeroesOfTheStorm_x64.exe'
SUMMARY_CATEGORY = 'e_errorIdStreaming (NGDP:E_DATA_ERROR)'
SUMMARY_MESSAGE = "An error occurred downloading game data from Blizzard's servers. Please check your internet connection and try again later."


def require(condition):
    if not condition:
        raise ValueError('Bounded preserved crash metadata validation failed')


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def regular(path):
    require(not path.is_symlink() and path.is_file())
    size = path.stat().st_size
    require(1 <= size <= FILE_LIMIT)
    return size


class Input:
    def __init__(self, path, size, counter):
        self.path, self.size, self.counter = path, size, counter

    def hash(self):
        regular(self.path)
        hasher, read = hashlib.sha256(), 0
        with self.path.open('rb') as stream:
            while read < self.size:
                raw = stream.read(min(16384, self.size-read))
                require(bool(raw))
                hasher.update(raw)
                read += len(raw)
                self.counter['opaque_hash_bytes'] += len(raw)
        require(read == self.size and regular(self.path) == self.size)
        return hasher.hexdigest()

    def at(self, stream, offset, count):
        require(type(offset) is int and type(count) is int and 0 <= offset <= self.size and 0 <= count <= self.size-offset)
        stream.seek(offset)
        raw = stream.read(count)
        require(len(raw) == count)
        self.counter['selected_metadata_bytes'] += len(raw)
        return raw


def local_path_probe(value):
    """Only fixed/removable drive metadata; never resolve UNC/network paths."""
    drive = PureWindowsPath(value).drive
    if not re.fullmatch(r'[A-Za-z]:', drive):
        return {'local_drive_metadata_check_performed': False, 'original_module_path_exists_now': None}
    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive+'\\')
    if drive_type not in (2, 3):
        return {'local_drive_metadata_check_performed': False, 'original_local_drive_currently_available': False,
                'original_module_path_exists_now': None}
    candidate = Path(value)
    exists = candidate.is_file()
    result = {'local_drive_metadata_check_performed': True, 'original_local_drive_currently_available': True,
              'original_module_path_exists_now': exists}
    if exists:
        result['existing_file_size_metadata_only'] = candidate.stat().st_size
    return result


def module_metadata(source):
    with source.path.open('rb') as stream:
        def read(offset, count):
            return source.at(stream, offset, count)
        signature, version, count, directory, checksum, dump_time, flags = struct.unpack('<IIIIIIQ', read(0, 32))
        require(signature == 0x504d444d and 1 <= count <= 128)
        entries = [struct.unpack('<III', read(directory+12*index, 12)) for index in range(count)]
        require(all(0 <= rva <= source.size and size <= source.size-rva for _, size, rva in entries))
        modules = [row for row in entries if row[0] == 4]
        require(len(modules) == 1)
        _, size, rva = modules[0]
        number = struct.unpack('<I', read(rva, 4))[0]
        require(1 <= number <= MAX_MODULES and 4+108*number <= size)
        targets = []
        for index in range(number):
            raw = read(rva+4+108*index, 108)
            base, image_size, image_checksum, image_time, name_rva = struct.unpack_from('<QIIII', raw)
            length = struct.unpack('<I', read(name_rva, 4))[0]
            require(length <= 8192 and length % 2 == 0)
            name = read(name_rva+4, length).decode('utf-16-le')
            if PureWindowsPath(name).name.casefold() != MODULE.casefold():
                continue
            fixed = struct.unpack_from('<13I', raw, 24)
            require(fixed[0] == 0xfeef04bd)
            cv_size, cv_rva = struct.unpack_from('<II', raw, 76)
            require(24 < cv_size <= 8192)
            cv = read(cv_rva, cv_size)
            require(cv[:4] == b'RSDS' and b'\0' in cv[24:])
            age = struct.unpack_from('<I', cv, 20)[0]
            guid = uuid.UUID(bytes_le=cv[4:20])
            pdb_name = PureWindowsPath(cv[24:].split(b'\0', 1)[0].decode('utf-8')).name
            file_version = (fixed[2]>>16, fixed[2]&65535, fixed[3]>>16, fixed[3]&65535)
            product_version = (fixed[4]>>16, fixed[4]&65535, fixed[5]>>16, fixed[5]&65535)
            require(file_version == product_version == (0, 17, 0, 41810))
            targets.append({'module_basename': MODULE, 'module_list_ordinal': index,
                'file_version': list(file_version), 'product_version': list(product_version),
                'base_of_image': hex(base), 'size_of_image': image_size, 'PE_checksum': image_checksum,
                'PE_timestamp': image_time, 'PE_timestamp_UTC': utc(image_time),
                'CodeView': {'signature': 'RSDS', 'PDB_basename': pdb_name, 'GUID': str(guid).upper(),
                             'age_decimal': age, 'age_hex': format(age, 'X'),
                             'GUID_age_symbol_index': guid.hex.upper()+format(age, 'X')},
                'module_path_contains_Base41810': 'base41810' in name.casefold(),
                'private_original_path_probe': local_path_probe(name)})
        require(len(targets) == 1)
        return {'signature': 'MDMP', 'header_version': version, 'header_checksum': checksum,
                'dump_timestamp': dump_time, 'dump_timestamp_UTC': utc(dump_time), 'flags': hex(flags),
                'directory_stream_count': count, 'directory_stream_types_and_sizes': [
                    {'stream_type': tag, 'declared_bytes': length} for tag, length, _ in entries],
                'module_count': number, 'target': targets[0],
                'memory_thread_exception_or_context_stream_contents_decoded': False}


def error_header_metadata(source):
    # Inspect only the header. Later Error sections contain memory and process
    # diagnostics and are intentionally not parsed or copied.
    lines = []
    with source.path.open('rb') as stream:
        for _ in range(45):
            raw = stream.readline(4097)
            require(len(raw) <= 4096)
            source.counter['selected_metadata_bytes'] += len(raw)
            if not raw:
                break
            lines.append(raw.decode('utf-8-sig', errors='strict').rstrip('\r\n'))
    fields = {}
    for tag in ('Exe.Architecture', 'Inspector.BuildNumber', 'Inspector.Summary', 'ErrorType', 'GetLastError'):
        matches = [match.group(1).strip() for line in lines
                   if (match := re.match(r'^<'+re.escape(tag)+r'>\s*(.*)$', line))]
        require(len(matches) == 1)
        fields[tag] = matches[0]
    require(fields['Exe.Architecture'] == 'x86_64')
    require(fields['Inspector.BuildNumber'] == 'B41810 (Heroes.17)')
    require(fields['ErrorType'] == 'e_errorIdStreaming' and fields['GetLastError'] == '0')
    require(SUMMARY_CATEGORY in fields['Inspector.Summary'] and SUMMARY_MESSAGE in fields['Inspector.Summary'])
    return {'header_lines_inspected': len(lines), 'architecture': 'x86_64', 'build_number': 41810,
            'build_branch': 'Heroes.17', 'error_type': 'e_errorIdStreaming', 'GetLastError': 0,
            'static_error_category': SUMMARY_CATEGORY, 'static_error_message': SUMMARY_MESSAGE,
            'later_memory_process_parameters_or_session_sections_parsed': False}


def analyze(root):
    root = root.resolve(strict=True)
    require(root.is_dir())
    folders = sorted(path for path in root.glob('*B41810 Error') if path.is_dir() and not path.is_symlink())
    require(len(folders) == 5)
    require(tuple(path.name.split(' ', 2)[0]+' '+path.name.split(' ', 2)[1] for path in folders) == CASE_TIMES)
    counter = {'opaque_hash_bytes': 0, 'selected_metadata_bytes': 0}
    inputs = []
    for folder in folders:
        for suffix in ('.dmp', '.txt'):
            path = folder/(folder.name+suffix)
            inputs.append(Input(path, regular(path), counter))
    distinct = sum(source.size for source in inputs)
    require(distinct <= DISTINCT_LIMIT)
    before = {source.path: source.hash() for source in inputs}
    rows = []
    for index, folder in enumerate(folders):
        dump, error = inputs[2*index:2*index+2]
        rows.append({'case_id': 'crash-'+str(index+1), 'folder_time_label_only': CASE_TIMES[index],
                     'dump': {'bytes': dump.size, 'sha256_before': before[dump.path], **module_metadata(dump)},
                     'Error_text': {'bytes': error.size, 'sha256_before': before[error.path], **error_header_metadata(error)}})
    for index, row in enumerate(rows):
        for key, source in zip(('dump', 'Error_text'), inputs[2*index:2*index+2]):
            after = source.hash()
            require(after == before[source.path])
            row[key]['sha256_after'] = after
    identities = {json.dumps({key: row['dump']['target'][key] for key in
        ('module_basename', 'file_version', 'product_version', 'size_of_image', 'PE_checksum', 'PE_timestamp', 'CodeView')}, sort_keys=True)
        for row in rows}
    require(len(identities) == 1)
    return {'format': 'hots-five-preserved41810-crash-module-metadata-v1',
            'producer_SHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'distinct_input_limit_bytes': DISTINCT_LIMIT, 'distinct_input_files': 10,
            'distinct_input_bytes': distinct, 'reader_run_byte_counts': counter,
            'counting_scope': 'Distinct crash inputs are capped at2MiB. Opaque before/after hash passes and selected metadata reads are counted separately; this run does not cap repeated read traffic at2MiB.',
            'case_count': 5, 'same_target_module_version_PE_metadata_and_CodeView_identity_all_cases': True,
            'target_identity_is_reported_by_artifacts_not_a_complete_executable_SHA': True,
            'cases': rows, 'all_ten_input_file_digests_unchanged': True,
            'raw_dump_Error_file_or_memory_contents_copied': False,
            'raw_module_PDB_or_other_local_paths_emitted': False,
            'Variables_NGDP_buildinfo_chats_or_session_files_read': False,
            'network_requests': 0, 'client_or_debugger_launched': False,
            'limits': [
                'The reported executable version is0.17.0.41810; crash folder dates and preserved .build.info must be interpreted separately.',
                'Module-list PE metadata and CodeView identify a reported loaded module; no complete executable or PDB was acquired or hashed.',
                'Image bases are observed load addresses and differ across crash dates; SizeOfImage is an in-memory image extent, not a file length.',
                'The generic NGDP:E_DATA_ERROR streaming message does not identify a missing content key, actual historical root or the underlying network/content failure.',
                'Only header/directory/module metadata and first45Error header lines are parsed. Raw memory, threads, exceptions, contexts, later process fields and session information are not decoded or copied.',
                'The source files were processed in place; no raw dump or Error log is saved in the work folder.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink() and args.output.parent.is_dir())
    report = analyze(args.input_root)
    write_new_report(report, args.output)
    print(json.dumps({'cases': report['case_count'], 'distinct_input_bytes': report['distinct_input_bytes'],
                      'same_target_identity': True, 'report_SHA256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))
