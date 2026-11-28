import hashlib
import io
import struct
import tempfile
import unittest
import urllib.error
import zlib
from pathlib import Path

import tact_restore as tr


def md5(data):
    return hashlib.md5(data).digest()


def blte(chunks, single=False):
    """chunks: list of (mode, payload). Returns (blob, ekey hex)."""
    if single:
        mode, payload = chunks[0]
        blob = b'BLTE\0\0\0\0' + mode.encode() + (zlib.compress(payload) if mode == 'Z' else payload)
        return blob, hashlib.md5(blob).hexdigest()
    encoded = [mode.encode() + (zlib.compress(payload) if mode == 'Z' else payload) for mode, payload in chunks]
    header = b'BLTE' + struct.pack('>I', 12 + 24 * len(chunks)) + b'\x0f' + len(chunks).to_bytes(3, 'big')
    for data, (_, payload) in zip(encoded, chunks):
        header += struct.pack('>II', len(data), len(payload)) + md5(data)
    return header + b''.join(encoded), hashlib.md5(header).hexdigest()


def encoding(entries, page_kb=1):
    """entries: list of (ckey bytes, size, [ekey bytes])."""
    size = page_kb * 1024
    pages, current, first = [], b'', None
    for ckey, length, ekeys in sorted(entries):
        row = bytes([len(ekeys)]) + length.to_bytes(5, 'big') + ckey + b''.join(ekeys)
        if len(current) + len(row) > size:
            pages.append((first, current.ljust(size, b'\0')))
            current, first = b'', None
        if first is None:
            first = ckey
        current += row
    pages.append((first, current.ljust(size, b'\0')))
    espec = b'z\0'
    header = b'EN' + bytes([1, 16, 16]) + struct.pack('>HHIIBI', page_kb, page_kb, len(pages), 0, 0, len(espec))
    table = b''.join(first + md5(page) for first, page in pages)
    return header + espec + table + b''.join(page for _, page in pages)


def install(tags, entries):
    """tags: list of (name, kind, set of entry indexes); entries: list of (name, ckey bytes, size)."""
    data = b'IN' + bytes([1, 16]) + struct.pack('>HI', len(tags), len(entries))
    for name, kind, members in tags:
        mask = bytearray((len(entries) + 7) // 8)
        for index in members:
            mask[index >> 3] |= 0x80 >> (index & 7)
        data += name.encode() + b'\0' + struct.pack('>H', kind) + bytes(mask)
    for name, ckey, size in entries:
        data += name.encode() + b'\0' + ckey + struct.pack('>I', size)
    return data


def index(entries, offset_bytes, block_kb=4):
    """entries: list of (ekey bytes, size, tail bytes)."""
    block = block_kb * 1024
    width = 20 + offset_bytes
    blocks, last_keys, current, last = [], [], b'', b''
    for key, size, tail in sorted(entries):
        if len(current) + width > block:
            blocks.append(current.ljust(block, b'\0'))
            last_keys.append(last)
            current = b''
        current += key + struct.pack('>I', size) + tail
        last = key
    blocks.append(current.ljust(block, b'\0'))
    last_keys.append(last)
    toc = b''.join(last_keys) + b''.join(md5(b)[:8] for b in blocks)
    footer = md5(toc)[:8] + bytes([1, 0, 0, block_kb, offset_bytes, 4, 16, 8]) + struct.pack('<I', len(entries)) + b'\0' * 8
    return b''.join(blocks) + toc + footer


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FakeOpener:
    def __init__(self, objects):
        self.objects = objects
        self.urls = []

    def open(self, request, timeout=None):
        url = request.full_url
        self.urls.append(url)
        path = '/' + url.split('/', 3)[3]
        if path not in self.objects:
            raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)
        body = self.objects[path]
        wanted = request.get_header('Range')
        if wanted:
            start, end = map(int, wanted.split('=')[1].split('-'))
            return Response(body[start:end + 1], 206, {'Content-Range': f'bytes {start}-{end}/{len(body)}'})
        return Response(body)


def key(seed):
    return hashlib.md5(seed.encode()).hexdigest()


class ConfigAndBlteTests(unittest.TestCase):
    def test_parse_config(self):
        parsed = tr.parse_config(b'# Build Configuration\n\nroot = aa\ninstall = bb cc\nempty =\n')
        self.assertEqual(parsed, {'root': ['aa'], 'install': ['bb', 'cc'], 'empty': []})
        with self.assertRaises(tr.TactError):
            tr.parse_config(b'root = aa\nroot = bb\n')

    def test_single_and_multi_chunk_decode(self):
        blob, ekey = blte([('N', b'hello')], single=True)
        self.assertEqual(tr.decode_blte(blob, ekey, 100)[0], b'hello')
        payload = [('N', b'abc' * 100), ('Z', b'xyz' * 1000), ('N', b'')]
        blob, ekey = blte(payload)
        data, info = tr.decode_blte(blob, ekey, 10000)
        self.assertEqual(data, b'abc' * 100 + b'xyz' * 1000)
        self.assertEqual((info['chunks'], info['modes']), (3, 'NZ'))

    def test_decode_rejections(self):
        blob, ekey = blte([('N', b'abc'), ('Z', b'def' * 50)])
        tampered = bytearray(blob)
        tampered[-1] ^= 1
        cases = {
            'chunk checksum': (bytes(tampered), ekey, 1000),
            'EKey': (blob, key('other'), 1000),
            'bound': (blob, ekey, 10),
            'trailing': (blob + b'x', ekey, 1000),
        }
        for label, (data, digest, bound) in cases.items():
            with self.subTest(label), self.assertRaises(tr.TactError):
                tr.decode_blte(data, digest, bound)
        encrypted, digest = blte([('E', b'secret')])
        with self.assertRaisesRegex(tr.TactError, 'refused'):
            tr.decode_blte(encrypted, digest, 1000)
        bad_size = bytearray(blob)
        bad_size[7] += 1
        with self.assertRaisesRegex(tr.TactError, 'header size'):
            tr.decode_blte(bytes(bad_size), None, 1000)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.rows = [(md5(b'c%d' % i), 1000 + i, [md5(b'e%d' % i), md5(b'f%d' % i)][:1 + i % 2]) for i in range(120)]
        self.table = encoding(self.rows, page_kb=1)

    def test_encoding_lookup_across_pages(self):
        for ckey, size, ekeys in (self.rows[0], self.rows[57], self.rows[119]):
            hit = tr.encoding_lookup(self.table, ckey.hex())
            self.assertEqual((hit['file_size'], hit['ekeys']), (size, [e.hex() for e in ekeys]))
        self.assertGreater(hit['page_count'], 1)
        with self.assertRaises(tr.TactError):
            tr.encoding_lookup(self.table, key('absent'))

    def test_encoding_page_checksum_is_required(self):
        target = self.rows[3][0]
        page_count = struct.unpack_from('>I', self.table, 9)[0]
        pages_start = 22 + 2 + 32 * page_count
        tampered = bytearray(self.table)
        tampered[tampered.index(target, pages_start) + 1] ^= 0xFF
        with self.assertRaisesRegex(tr.TactError, 'checksum'):
            tr.encoding_lookup(bytes(tampered), target.hex())

    def test_install_entries_and_tags(self):
        data = install([('Windows', 1, {0, 2}), ('x86_64', 2, {0}), ('OSX', 1, {1})],
                       [('Versions\\Base1\\Game_x64.exe', md5(b'a'), 5), ('Game.app', md5(b'b'), 6), ('Data.txt', md5(b'c'), 7)])
        entries, trailing = tr.parse_install(data + b'\0\0')
        self.assertEqual(trailing, 2)
        self.assertEqual(entries[0], {'name': 'Versions\\Base1\\Game_x64.exe', 'ckey': md5(b'a').hex(), 'size': 5,
                                      'tags': ['Windows', 'x86_64']})
        self.assertEqual([e['tags'] for e in entries[1:]], [['OSX'], ['Windows']])
        self.assertEqual(tr.normalize_name(entries[0]['name']), 'versions/base1/game_x64.exe')


class IndexTests(unittest.TestCase):
    def test_group_and_plain_index_lookup_across_blocks(self):
        rows = [(md5(b'k%d' % i), 10 + i, struct.pack('>HI', i % 7, 1000 * i)) for i in range(400)]
        group = index(rows, 6)
        for ekey, size, tail in (rows[0], rows[201], rows[399]):
            archive, offset = struct.unpack('>HI', tail)
            self.assertEqual(tr.index_lookup(group, ekey.hex()),
                             {'size': size, 'archive_index': archive, 'offset': offset,
                              'ordinal': sorted(r[0] for r in rows).index(ekey)})
        self.assertIsNone(tr.index_lookup(group, key('absent')))
        plain = index([(md5(b'p'), 99, struct.pack('>I', 77))], 4)
        self.assertEqual(tr.index_lookup(plain, md5(b'p').hex()), {'size': 99, 'offset': 77, 'ordinal': 0})

    def test_unsupported_index_footer(self):
        data = bytearray(index([(md5(b'p'), 1, b'')], 0))
        data[-28 + 12] = 5
        with self.assertRaises(tr.TactError):
            tr.index_lookup(bytes(data), md5(b'p').hex())


class FakeCdnTests(unittest.TestCase):
    PATH = 'tpr/Test-a'
    NAME = 'Versions\\Base1\\Game_x64.exe'

    def build(self, archived):
        content = b'MZ' + bytes(range(256)) * 300
        ckey = md5(content)
        blob, ekey = blte([('Z', content[:30000]), ('N', content[30000:])])
        other = md5(b'other-file')
        manifest = install([('Windows', 1, {0, 1})], [(self.NAME, ckey, len(content)), ('Other.dll', other, 3)])
        install_blob, install_ekey = blte([('Z', manifest)])
        table = encoding([(ckey, len(content), [bytes.fromhex(ekey)]), (other, 3, [md5(b'x')])])
        encoding_blob, encoding_ekey = blte([('Z', table)])
        objects = {}

        def put(kind, name, body, suffix=''):
            objects[f'/{self.PATH}/{kind}/{name[:2]}/{name[2:4]}/{name}{suffix}'] = body

        archive_key = key('archive')
        cdn_config = f'# CDN Configuration\narchives = {key("a0")} {archive_key}\narchive-group = {key("group")}\n'.encode()
        build_config = (f'# Build Configuration\nroot = {key("root")}\ninstall = {hashlib.md5(manifest).hexdigest()} {install_ekey}\n'
                        f'encoding = {hashlib.md5(table).hexdigest()} {encoding_ekey}\nbuild-name = B1\n').encode()
        put('config', hashlib.md5(build_config).hexdigest(), build_config)
        put('config', hashlib.md5(cdn_config).hexdigest(), cdn_config)
        put('data', install_ekey, install_blob)
        put('data', encoding_ekey, encoding_blob)
        if archived:
            prefix = b'\x00' * 123
            put('data', archive_key, prefix + blob + b'\x01' * 50)
            put('data', key('group'), index([(bytes.fromhex(ekey), len(blob), struct.pack('>HI', 1, len(prefix)))], 6), '.index')
        else:
            put('data', ekey, blob)
        return objects, content, hashlib.md5(build_config).hexdigest(), hashlib.md5(cdn_config).hexdigest()

    def run_restore(self, archived=False, pin=None, list_only=False, existing=False):
        objects, content, build_key, cdn_key = self.build(archived)
        opener = FakeOpener(objects)
        cdn = tr.Cdn(['http://cdn.test'], self.PATH, 1 << 24, opener=opener)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'restored'
            if existing:
                out.mkdir()
            sha = pin or hashlib.sha256(content).hexdigest()
            try:
                receipt = tr.restore(cdn, build_key, cdn_key, self.NAME.replace('\\', '/'), len(content), sha, out, list_only)
                written = (out / 'Game_x64.exe').read_bytes() if (out / 'Game_x64.exe').exists() else None
                return receipt, written, content, None
            except tr.TactError as error:
                return None, out.exists() and not existing, content, error

    def test_loose_restore(self):
        receipt, written, content, error = self.run_restore()
        self.assertIsNone(error)
        self.assertEqual(written, content)
        self.assertEqual(receipt['location']['kind'], 'loose')
        self.assertTrue(receipt['restored']['matches_pin'])
        self.assertFalse(receipt['executed_restored_file'])

    def test_archive_restore_uses_exact_range(self):
        receipt, written, content, error = self.run_restore(archived=True)
        self.assertIsNone(error)
        self.assertEqual(written, content)
        self.assertEqual((receipt['location']['kind'], receipt['location']['archive_index']), ('archive', 1))
        self.assertEqual(receipt['requests'][-1]['range'], [123, 123 + receipt['location']['encoded_bytes'] - 1])

    def test_pin_mismatch_leaves_no_output(self):
        receipt, created, _, error = self.run_restore(pin='0' * 64)
        self.assertIsNone(receipt)
        self.assertRegex(str(error), 'pin')
        self.assertFalse(created)

    def test_existing_output_and_list_only(self):
        _, _, _, error = self.run_restore(existing=True)
        self.assertRegex(str(error), 'new output directory')
        receipt, written, _, error = self.run_restore(list_only=True)
        self.assertIsNone(error)
        self.assertIsNone(written)
        self.assertEqual([e['name'] for e in receipt['same_basename_entries']], [self.NAME])

    def test_cdn_policy(self):
        for server in ('ftp://cdn.test', 'http://cdn.test/path', 'http://cdn.test/?q=1'):
            with self.subTest(server), self.assertRaises(tr.TactError):
                tr.Cdn([server], self.PATH, 1)
        with self.assertRaises(tr.TactError):
            tr.Cdn(['http://cdn.test'], '../escape', 1)
        with self.assertRaisesRegex(tr.TactError, 'redirect'):
            tr.NoRedirect().redirect_request(None, None, 302, 'Found', {}, 'http://elsewhere.test/x')
        objects, *_ = self.build(False)
        cdn = tr.Cdn(['http://cdn.test'], self.PATH, 10, opener=FakeOpener(objects))
        config_key = next(p for p in objects if '/config/' in p).rsplit('/', 1)[1]
        with self.assertRaisesRegex(tr.TactError, 'budget|bound'):
            cdn.fetch('config', config_key)
        cdn = tr.Cdn(['http://cdn.test'], self.PATH, 1 << 20, opener=FakeOpener({}))
        self.assertIsNone(cdn.fetch('data', key('missing'), allow_missing=True))
        with self.assertRaisesRegex(tr.TactError, 'unavailable'):
            cdn.fetch('data', key('missing'))


if __name__ == '__main__':
    unittest.main()
