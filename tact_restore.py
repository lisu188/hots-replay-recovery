"""Restore one install-manifest file of a TACT build from Blizzard's CDN.

Acquisition only: nothing is executed, installed or written outside a new
output directory. Every hop is content addressed and checked:

* configuration MD5 == its key;
* BLTE header (or whole single-chunk blob) MD5 == EKey and every chunk MD5;
* decoded MD5 == CKey for the encoding table, install manifest and file;
* the encoding page MD5 of the page that resolves the file's CKey;
* the install entry and encoding sizes, then an explicit whole-file
  length/SHA-256 pin before anything is written.

Requests go only to the explicitly listed CDN servers, redirects are refused
and the total download is budgeted. Only N (raw) and Z (zlib) BLTE chunks are
accepted; encrypted or other chunk modes are refused.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from urllib.parse import urlsplit

FORMAT = 'tact-install-file-restore-v1'
CONFIG_LIMIT = 1 << 20
MANIFEST_LIMIT = 256 << 20
INDEX_LIMIT = 128 << 20


class TactError(Exception):
    """A verification, format or policy failure."""


def require(condition, message):
    if not condition:
        raise TactError(message)


def md5_hex(data):
    return hashlib.md5(data).hexdigest()


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def is_key(value):
    return isinstance(value, str) and len(value) == 32 and all(c in '0123456789abcdef' for c in value)


def parse_config(data: bytes) -> dict[str, list[str]]:
    """Parse a TACT text configuration (``key = value ...`` lines)."""
    values: dict[str, list[str]] = {}
    for line in data.decode('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        key = key.strip()
        require(separator and key and key not in values, f'malformed or duplicate configuration key {key!r}')
        values[key] = value.split()
    return values


def key_pair(config, name):
    pair = config.get(name, [])
    require(len(pair) >= 2 and is_key(pair[0]) and is_key(pair[1]), f'configuration lacks a {name} CKey/EKey pair')
    return pair[0], pair[1]


def decode_blte(data: bytes, ekey: str | None, max_output: int) -> tuple[bytes, dict]:
    """Decode a BLTE blob, verifying its EKey digest and every chunk checksum."""
    require(len(data) >= 9 and data[:4] == b'BLTE', 'missing BLTE signature')
    header_size = struct.unpack_from('>I', data, 4)[0]
    if header_size == 0:
        header_digest = md5_hex(data)
        chunks = [(len(data) - 8, None, None)]
        position = 8
    else:
        require(len(data) >= 12 and data[8] == 0x0F, 'unsupported BLTE chunk table')
        count = int.from_bytes(data[9:12], 'big')
        require(count > 0 and header_size == 12 + 24 * count and len(data) >= header_size, 'BLTE header size mismatch')
        header_digest = md5_hex(data[:header_size])
        chunks = []
        for index in range(count):
            compressed, decompressed = struct.unpack_from('>II', data, 12 + 24 * index)
            chunks.append((compressed, decompressed, data[20 + 24 * index:36 + 24 * index]))
        position = header_size
    if ekey is not None:
        require(header_digest == ekey, 'BLTE header digest differs from the EKey')
    output = bytearray()
    modes = set()
    for compressed, decompressed, checksum in chunks:
        require(compressed >= 1 and position + compressed <= len(data), 'truncated BLTE chunk')
        chunk = data[position:position + compressed]
        position += compressed
        if checksum is not None:
            require(hashlib.md5(chunk).digest() == checksum, 'BLTE chunk checksum mismatch')
        mode = chr(chunk[0])
        modes.add(mode)
        remaining = max_output - len(output)
        if mode == 'N':
            payload = chunk[1:]
        elif mode == 'Z':
            inflater = zlib.decompressobj()
            try:
                payload = inflater.decompress(chunk[1:], remaining + 1)
            except zlib.error as error:
                raise TactError(f'invalid zlib chunk: {error}') from None
            require(len(payload) <= remaining, 'decoded output exceeds its bound')
            require(inflater.eof and not inflater.unconsumed_tail and not inflater.unused_data,
                    'incomplete or trailing zlib chunk data')
        else:
            raise TactError(f'refused BLTE chunk mode {mode!r}')
        require(len(payload) <= remaining, 'decoded output exceeds its bound')
        if decompressed is not None:
            require(len(payload) == decompressed, 'BLTE chunk size mismatch')
        output += payload
    require(position == len(data), 'trailing bytes after BLTE chunks')
    return bytes(output), {'chunks': len(chunks), 'modes': ''.join(sorted(modes)), 'header_md5_equals_ekey': ekey is not None}


def encoding_lookup(data: bytes, ckey: str) -> dict:
    """Resolve a CKey to its file size and EKeys, verifying the page checksum."""
    require(len(data) >= 22 and data[:2] == b'EN' and data[2] == 1, 'unsupported encoding header')
    require(data[3] == 16 and data[4] == 16, 'unexpected encoding hash sizes')
    page_kb, _ekey_page_kb, page_count, _ekey_page_count, flags, espec_size = struct.unpack_from('>HHIIBI', data, 5)
    require(flags == 0 and page_kb > 0 and page_count > 0, 'unsupported encoding layout')
    table = 22 + espec_size
    page_size = page_kb * 1024
    pages = table + 32 * page_count
    require(len(data) >= pages + page_count * page_size, 'truncated encoding CKey pages')
    firsts = [data[table + 32 * i:table + 32 * i + 16] for i in range(page_count)]
    require(all(a <= b for a, b in zip(firsts, firsts[1:])), 'encoding page table is not sorted')
    target = bytes.fromhex(ckey)
    index = bisect.bisect_right(firsts, target) - 1
    require(index >= 0, 'CKey precedes the encoding page table')
    page = data[pages + index * page_size:pages + (index + 1) * page_size]
    require(hashlib.md5(page).digest() == data[table + 32 * index + 16:table + 32 * index + 32],
            'encoding page checksum mismatch')
    position = 0
    while position + 22 <= len(page) and page[position]:
        count = page[position]
        require(position + 22 + 16 * count <= len(page), 'truncated encoding page entry')
        size = int.from_bytes(page[position + 1:position + 6], 'big')
        if page[position + 6:position + 22] == target:
            ekeys = [page[position + 22 + 16 * i:position + 38 + 16 * i].hex() for i in range(count)]
            return {'page': index, 'page_count': page_count, 'file_size': size, 'ekeys': ekeys}
        position += 22 + 16 * count
    raise TactError('CKey is not present in its encoding page')


def parse_install(data: bytes) -> tuple[list[dict], int]:
    """Parse an install manifest into entries with their tag names."""
    require(len(data) >= 10 and data[:2] == b'IN' and data[2] == 1 and data[3] == 16, 'unsupported install header')
    tag_count, entry_count = struct.unpack_from('>HI', data, 4)
    mask_bytes = (entry_count + 7) // 8
    position = 10

    def cstring():
        nonlocal position
        end = data.find(b'\0', position)
        require(end >= 0, 'unterminated install string')
        value = data[position:end].decode('utf-8')
        position = end + 1
        return value

    tags = []
    for _ in range(tag_count):
        name = cstring()
        require(position + 2 + mask_bytes <= len(data), 'truncated install tag')
        kind = struct.unpack_from('>H', data, position)[0]
        mask = data[position + 2:position + 2 + mask_bytes]
        position += 2 + mask_bytes
        tags.append((name, kind, mask))
    entries = []
    for index in range(entry_count):
        name = cstring()
        require(position + 20 <= len(data), 'truncated install entry')
        entries.append({'name': name, 'ckey': data[position:position + 16].hex(),
                        'size': struct.unpack_from('>I', data, position + 16)[0],
                        'tags': [tag for tag, _, mask in tags if mask[index >> 3] & (0x80 >> (index & 7))]})
        position += 20
    return entries, len(data) - position


def normalize_name(name):
    return name.replace('\\', '/').casefold()


def parse_index_footer(data: bytes) -> dict:
    require(len(data) >= 28, 'archive index is too short')
    footer = data[-28:]
    version, _, _, block_kb, offset_bytes, size_bytes, key_bytes, checksum_size = footer[8:16]
    require(version == 1 and checksum_size == 8 and key_bytes == 16 and size_bytes == 4 and block_kb > 0,
            'unsupported archive index footer')
    require(offset_bytes in (0, 4, 6), f'unsupported archive index offset width {offset_bytes}')
    return {'block_bytes': block_kb * 1024, 'offset_bytes': offset_bytes, 'size_bytes': size_bytes,
            'key_bytes': key_bytes, 'elements': struct.unpack_from('<I', footer, 16)[0]}


def index_lookup(data: bytes, ekey: str) -> dict | None:
    """Scan an archive index's packed blocks for one EKey."""
    footer = parse_index_footer(data)
    block = footer['block_bytes']
    width = footer['key_bytes'] + footer['size_bytes'] + footer['offset_bytes']
    target = bytes.fromhex(ekey)
    limit = len(data) - 28
    position = seen = 0
    while seen < footer['elements']:
        block_end = (position // block + 1) * block
        if position + width > block_end:
            position = block_end
            continue
        require(position + width <= limit, 'archive index entries overrun the footer')
        key = data[position:position + 16]
        if not any(key):
            position = block_end
            continue
        seen += 1
        if key == target:
            size = struct.unpack_from('>I', data, position + 16)[0]
            tail = data[position + 20:position + width]
            entry = {'size': size, 'ordinal': seen - 1}
            if footer['offset_bytes'] == 6:
                entry['archive_index'], entry['offset'] = struct.unpack('>HI', tail)
            elif footer['offset_bytes'] == 4:
                entry['offset'] = struct.unpack('>I', tail)[0]
            return entry
        position += width
    return None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TactError(f'refused HTTP redirect {code} to {newurl}')


class Cdn:
    """Budgeted, allowlisted CDN reader that logs every request."""

    def __init__(self, servers, cdn_path, budget, opener=None, timeout=60):
        require(servers, 'at least one CDN server is required')
        for server in servers:
            parts = urlsplit(server)
            require(parts.scheme in ('http', 'https') and parts.hostname and parts.path in ('', '/')
                    and not parts.query and not parts.fragment, f'invalid CDN server {server!r}')
        require(cdn_path and not cdn_path.startswith('/') and '..' not in cdn_path.split('/'), 'invalid CDN path')
        self.servers = [server.rstrip('/') for server in servers]
        self.cdn_path = cdn_path.strip('/')
        self.budget = budget
        self.used = 0
        self.log = []
        self.opener = opener or urllib.request.build_opener(NoRedirect)
        self.timeout = timeout

    def fetch(self, kind, key, suffix='', limit=CONFIG_LIMIT, byte_range=None, allow_missing=False):
        require(kind in ('config', 'data') and is_key(key) and suffix in ('', '.index'), 'invalid CDN object request')
        errors = []
        missing = 0
        for server in self.servers:
            url = f'{server}/{self.cdn_path}/{kind}/{key[:2]}/{key[2:4]}/{key}{suffix}'
            headers = {'User-Agent': 'hots-replay-recovery-tact-restore'}
            if byte_range:
                headers['Range'] = f'bytes={byte_range[0]}-{byte_range[1]}'
            row = {'url': url, 'range': list(byte_range) if byte_range else None}
            try:
                with self.opener.open(urllib.request.Request(url, headers=headers), timeout=self.timeout) as response:
                    row['status'] = response.status
                    if byte_range:
                        expected = f'bytes {byte_range[0]}-{byte_range[1]}/'
                        require(response.status == 206 and response.headers.get('Content-Range', '').startswith(expected),
                                'CDN did not honor the exact byte range')
                    body = response.read(min(limit, self.budget - self.used) + 1)
            except urllib.error.HTTPError as error:
                row['status'] = error.code
                self.log.append(row)
                if error.code == 404:
                    missing += 1
                    continue
                errors.append(f'{url}: HTTP {error.code}')
                continue
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
                row['error'] = type(error).__name__
                self.log.append(row)
                errors.append(f'{url}: {type(error).__name__}')
                continue
            row['bytes'] = len(body)
            row['sha256'] = sha256_hex(body)
            self.log.append(row)
            require(len(body) <= limit, f'{url} exceeds its {limit}-byte bound')
            self.used += len(body)
            require(self.used <= self.budget, 'download budget exceeded')
            if byte_range:
                require(len(body) == byte_range[1] - byte_range[0] + 1, 'short byte-range response')
            return body
        if missing == len(self.servers) and allow_missing:
            return None
        raise TactError(f'object {kind}/{key}{suffix} unavailable: ' + '; '.join(errors or ['HTTP 404 from every server']))


def restore(cdn: Cdn, build_key, cdn_key, name, expect_size, expect_sha256, output_dir: Path, list_only=False):
    """Restore one install file; returns the receipt. Writes only into a new output_dir."""
    started = time.time()
    require(is_key(build_key) and is_key(cdn_key), 'configuration keys must be 32 lowercase hex digits')
    require(len(expect_sha256) == 64 and expect_size > 0, 'an explicit size and SHA-256 pin are required')
    if not list_only:
        require(not output_dir.exists() and output_dir.parent.is_dir(), 'a new output directory is required')
    receipt = {'format': FORMAT, 'executed_restored_file': False, 'installed_restored_file': False,
               'build_config': build_key, 'cdn_config': cdn_key, 'cdn_path': cdn.cdn_path, 'requested_name': name}
    build_raw = cdn.fetch('config', build_key)
    require(md5_hex(build_raw) == build_key, 'build configuration MD5 differs from its key')
    build = parse_config(build_raw)
    receipt['build_name'] = build.get('build-name', [None])[0]
    install_ckey, install_ekey = key_pair(build, 'install')
    install_blob = cdn.fetch('data', install_ekey, limit=MANIFEST_LIMIT)
    install, install_info = decode_blte(install_blob, install_ekey, MANIFEST_LIMIT)
    require(md5_hex(install) == install_ckey, 'install manifest MD5 differs from its CKey')
    entries, trailing = parse_install(install)
    receipt['install_manifest'] = {'ckey': install_ckey, 'ekey': install_ekey, 'entries': len(entries),
                                   'trailing_bytes': trailing, 'blte': install_info}
    wanted = normalize_name(name)
    basename = wanted.rsplit('/', 1)[-1]
    candidates = [entry for entry in entries if normalize_name(entry['name']).rsplit('/', 1)[-1] == basename]
    receipt['same_basename_entries'] = candidates[:32]
    matches = [entry for entry in entries if normalize_name(entry['name']) == wanted]
    if list_only:
        receipt['requests'] = cdn.log
        receipt['downloaded_bytes'] = cdn.used
        return receipt
    require(len(matches) == 1, f'expected one install entry named {name!r}, found {len(matches)}')
    entry = matches[0]
    receipt['install_entry'] = entry
    require(entry['size'] == expect_size, 'install entry size differs from the pin')
    cdn_raw = cdn.fetch('config', cdn_key)
    require(md5_hex(cdn_raw) == cdn_key, 'CDN configuration MD5 differs from its key')
    cdn_config = parse_config(cdn_raw)
    encoding_ckey, encoding_ekey = key_pair(build, 'encoding')
    encoding_blob = cdn.fetch('data', encoding_ekey, limit=MANIFEST_LIMIT)
    encoding, encoding_info = decode_blte(encoding_blob, encoding_ekey, MANIFEST_LIMIT)
    require(md5_hex(encoding) == encoding_ckey, 'encoding table MD5 differs from its CKey')
    hit = encoding_lookup(encoding, entry['ckey'])
    receipt['encoding'] = {'ckey': encoding_ckey, 'ekey': encoding_ekey, 'blte': encoding_info, **hit}
    require(hit['file_size'] == expect_size, 'encoding file size differs from the pin')
    content = None
    for ekey in hit['ekeys']:
        location = {'ekey': ekey}
        blob = cdn.fetch('data', ekey, limit=2 * expect_size + (1 << 20), allow_missing=True)
        if blob is not None:
            location['kind'] = 'loose'
        else:
            group = cdn_config.get('archive-group', [None])[0]
            require(is_key(group), 'CDN configuration has no archive-group index')
            index = cdn.fetch('data', group, '.index', limit=INDEX_LIMIT)
            location['archive_group'] = {'key': group, 'bytes': len(index), 'sha256': sha256_hex(index)}
            found = index_lookup(index, ekey)
            if found is None or 'archive_index' not in found:
                receipt.setdefault('unlocated_ekeys', []).append(ekey)
                continue
            archives = cdn_config.get('archives', [])
            require(found['archive_index'] < len(archives), 'archive index outside the CDN configuration')
            archive = archives[found['archive_index']]
            require(is_key(archive) and found['size'] > 0, 'invalid archive location')
            location.update(kind='archive', archive=archive, **found)
            blob = cdn.fetch('data', archive, limit=found['size'],
                             byte_range=(found['offset'], found['offset'] + found['size'] - 1))
        content, info = decode_blte(blob, ekey, expect_size)
        location['blte'] = info
        location['encoded_bytes'] = len(blob)
        receipt['location'] = location
        require(md5_hex(content) == entry['ckey'], 'decoded file MD5 differs from its CKey')
        break
    require(content is not None, 'no EKey of the file could be located on the CDN')
    digest = sha256_hex(content)
    require(len(content) == expect_size and digest == expect_sha256, 'restored file differs from the size/SHA-256 pin')
    output_dir.mkdir()
    target = output_dir / entry['name'].replace('\\', '/').rsplit('/', 1)[-1]
    with target.open('xb') as stream:
        stream.write(content)
    require(sha256_hex(target.read_bytes()) == expect_sha256, 'written file failed read-back verification')
    receipt['restored'] = {'file_name': target.name, 'bytes': len(content), 'md5': md5_hex(content), 'sha256': digest,
                           'matches_pin': True}
    receipt['requests'] = cdn.log
    receipt['downloaded_bytes'] = cdn.used
    receipt['elapsed_seconds'] = round(time.time() - started, 1)
    with (output_dir / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--server', action='append', required=True, help='CDN server base URL; repeat for fallbacks')
    parser.add_argument('--cdn-path', required=True)
    parser.add_argument('--build-config', required=True)
    parser.add_argument('--cdn-config', required=True)
    parser.add_argument('--name', required=True, help='install-manifest file name')
    parser.add_argument('--expect-size', type=int, required=True)
    parser.add_argument('--expect-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-download-bytes', type=int, default=256 << 20)
    parser.add_argument('--list-only', action='store_true', help='print same-basename install entries; write nothing')
    args = parser.parse_args(argv)
    cdn = Cdn(args.server, args.cdn_path, args.max_download_bytes)
    try:
        receipt = restore(cdn, args.build_config, args.cdn_config, args.name, args.expect_size,
                          args.expect_sha256.lower(), args.output_dir, args.list_only)
    except TactError as error:
        print(json.dumps({'error': str(error), 'requests': cdn.log, 'downloaded_bytes': cdn.used}, indent=2))
        return 2
    summary = {key: receipt.get(key) for key in ('build_name', 'install_entry', 'restored', 'downloaded_bytes')}
    if args.list_only:
        summary['same_basename_entries'] = receipt['same_basename_entries']
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
