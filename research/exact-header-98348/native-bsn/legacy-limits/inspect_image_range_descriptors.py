"""Inspect minidump range descriptors only; never read their pointed-to bytes.

Opaque full-file hashing is separate from the aggregate64KiB metadata budget.
Output contains image-relative offsets only, never raw process addresses.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct

from collection_license_audit import _read, write_new_report

METADATA_LIMIT = 64*1024
DUMP_LIMIT = 256*1024
PRIOR_SHA = 'a40cde35e02707ff2c484dcc98b2bafa4a86bd30eae1ddf2d6b6fc98f7fb85ea'
WORK = Path(__file__).resolve().parents[1]


def require(condition):
    if not condition:
        raise ValueError('Bounded image-range descriptor verification failed')


def merged(intervals):
    result = []
    for start, stop in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], stop))
        else:
            result.append((start, stop))
    return result


def whole_hash(path, size, counts):
    hasher, read = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while read < size:
            raw = stream.read(min(16384, size-read))
            require(bool(raw))
            hasher.update(raw)
            read += len(raw)
            counts['opaque_hash_bytes'] += len(raw)
    require(path.stat().st_size == size and read == size)
    return hasher.hexdigest()


def analyze(root):
    prior_raw = _read(WORK/'legacy41810-crash-metadata/five-preserved41810-module-metadata.json', 128*1024)
    require(hashlib.sha256(prior_raw).hexdigest() == PRIOR_SHA)
    prior = json.loads(prior_raw)
    require(prior['case_count'] == 5 and prior['all_ten_input_file_digests_unchanged'])
    root = root.resolve(strict=True)
    folders = sorted(p for p in root.glob('*B41810 Error') if p.is_dir() and not p.is_symlink())
    require(len(folders) == 5)
    counts = {'selected_descriptor_and_module_metadata_bytes': 0, 'opaque_hash_bytes': 0}
    rows = []
    for folder, reference in zip(folders, prior['cases']):
        require(folder.name.startswith(reference['folder_time_label_only']+' '))
        path = folder/(folder.name+'.dmp')
        require(not path.is_symlink() and path.is_file())
        size = path.stat().st_size
        require(size == reference['dump']['bytes'] and size <= DUMP_LIMIT)
        expected = reference['dump']['sha256_before']
        require(expected == reference['dump']['sha256_after'])
        before = whole_hash(path, size, counts)
        require(before == expected)
        with path.open('rb') as stream:
            def read(offset, amount):
                require(type(offset) is int and type(amount) is int and 0 <= offset <= size and 0 <= amount <= size-offset)
                require(counts['selected_descriptor_and_module_metadata_bytes']+amount <= METADATA_LIMIT)
                stream.seek(offset)
                raw = stream.read(amount)
                require(len(raw) == amount)
                counts['selected_descriptor_and_module_metadata_bytes'] += len(raw)
                return raw
            header = struct.unpack('<IIIIIIQ', read(0, 32))
            require(header[0] == 0x504d444d and 1 <= header[2] <= 128)
            directory = [struct.unpack('<III', read(header[3]+12*i, 12)) for i in range(header[2])]
            require(all(0 <= rva <= size and length <= size-rva for _, length, rva in directory))
            module_streams = [entry for entry in directory if entry[0] == 4]
            memory_streams = [entry for entry in directory if entry[0] == 5]
            require(len(module_streams) == len(memory_streams) == 1)
            _, module_size, module_rva = module_streams[0]
            module_count = struct.unpack('<I', read(module_rva, 4))[0]
            require(module_count == reference['dump']['module_count'] and 4+108*module_count <= module_size)
            ordinal = reference['dump']['target']['module_list_ordinal']
            require(ordinal == 0)
            module = read(module_rva+4+108*ordinal, 108)
            image_base, image_size, checksum, timestamp = struct.unpack_from('<QIII', module)
            fixed = struct.unpack_from('<13I', module, 24)
            require(fixed[0] == 0xfeef04bd and (fixed[2]>>16, fixed[2]&65535, fixed[3]>>16, fixed[3]&65535) == (0, 17, 0, 41810))
            target = reference['dump']['target']
            require(image_base == int(target['base_of_image'], 16) and image_size == target['size_of_image'])
            require(checksum == target['PE_checksum'] and timestamp == target['PE_timestamp'])
            image_end = image_base+image_size
            require(image_end <= 1<<64)
            _, descriptor_size, descriptor_rva = memory_streams[0]
            range_count = struct.unpack('<I', read(descriptor_rva, 4))[0]
            require(range_count <= 2048 and descriptor_size == 4+16*range_count)
            descriptors = read(descriptor_rva+4, 16*range_count)
            intersections, full_inside, outside, captured_total = [], 0, 0, 0
            for index in range(range_count):
                start, length, data_rva = struct.unpack_from('<QII', descriptors, 16*index)
                require(length > 0 and start+length <= 1<<64 and 0 <= data_rva <= size and length <= size-data_rva)
                captured_total += length
                low, high = max(start, image_base), min(start+length, image_end)
                if low < high:
                    entirely = image_base <= start and start+length <= image_end
                    full_inside += entirely
                    intersections.append({'image_relative_start': low-image_base, 'byte_count': high-low,
                                          'original_range_entirely_within_image': entirely})
                else:
                    outside += 1
            image_ranges = merged([(row['image_relative_start'], row['image_relative_start']+row['byte_count']) for row in intersections])
            header_ranges = merged([(max(0, start), min(4096, stop)) for start, stop in image_ranges if start < 4096])
            covered_header = sum(stop-start for start, stop in header_ranges)
        after = whole_hash(path, size, counts)
        require(after == before == expected)
        rows.append({'case_id': reference['case_id'], 'dump_bytes': size, 'dump_SHA256_before': before, 'dump_SHA256_after': after,
            'module_identity': {'basename': 'HeroesOfTheStorm_x64.exe', 'file_version': [0, 17, 0, 41810],
                                'SizeOfImage': image_size, 'PDB_GUID': target['CodeView']['GUID'], 'PDB_age': target['CodeView']['age_decimal']},
            'memory_list_descriptor_stream_bytes': descriptor_size, 'memory_range_count': range_count,
            'all_captured_ranges_declared_bytes': captured_total, 'ranges_without_image_overlap': outside,
            'ranges_entirely_within_image': full_inside, 'ranges_with_any_image_overlap': len(intersections),
            'image_intersections': intersections, 'unique_captured_image_bytes': sum(stop-start for start, stop in image_ranges),
            'first4096_image_bytes_covered': covered_header, 'first4096_image_bytes_fully_covered': covered_header == 4096,
            'memory_contents_PE_header_bytes_or_section_table_read': False})
    return {'format': 'hots-five41810-minidump-image-range-descriptor-feasibility-v1',
        'producer_SHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'prior_authenticated_module_receipt_SHA256': PRIOR_SHA, 'case_count': 5,
        'selected_metadata_limit_bytes': METADATA_LIMIT, 'reader_run_byte_counts': counts,
        'descriptor_format': 'MINIDUMP_MEMORY_LIST: ULONG32count plus16-byte MINIDUMP_MEMORY_DESCRIPTOR entries, from Microsoft Windows SDK minidumpapiset.h',
        'cases': rows, 'any_old_image_bytes_declared_captured': any(row['unique_captured_image_bytes'] for row in rows),
        'all_source_dump_hashes_unchanged_and_equal_existing_pins': True,
        'raw_VAs_nonimage_addresses_file_paths_or_memory_contents_emitted': False,
        'pointed_to_memory_ranges_thread_context_heap_or_PE_contents_decoded': False,
        'network_requests': 0, 'client_process_or_debugger_launched': False,
        'raw_dump_or_memory_bytes_copied': False,
        'limits': ['Only descriptor metadata is parsed; before/after SHA passes are opaque and counted separately.',
                   'Image-relative intersections describe declared capture coverage only. No MZ/PE signature, section table or BSN schema bytes are read or authenticated.',
                   'Absence of captured old image bytes in these five dumps would rule out direct old-image/schema extraction from their memory ranges, not from other artifacts.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink() and args.output.parent.is_dir())
    report = analyze(args.input_root)
    write_new_report(report, args.output)
    print(json.dumps({'cases': 5, 'metadata_bytes': report['reader_run_byte_counts']['selected_descriptor_and_module_metadata_bytes'],
                      'any_old_image_bytes_declared_captured': report['any_old_image_bytes_declared_captured'],
                      'per_case_image_bytes': [row['unique_captured_image_bytes'] for row in report['cases']],
                      'report_SHA256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))
