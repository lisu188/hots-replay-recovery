from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

MAP_SHA256 = 'f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f'
BUILD = 98285
TOKEN = 'HRC98285_20260929_P1'
MAX_ENTRIES = 16384
CHUNK = 256
OUTPUT = 'TEN_GREYMANE_CATALOG_PROBE_98285.StormMap'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xml_root(raw: bytes, expected: str) -> ET.Element:
    if not isinstance(raw, bytes) or len(raw) > 4 * 1024 * 1024:
        raise ValueError('XML exceeds the diagnostic input limit')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('XML declarations with entities are not accepted')
    root = ET.fromstring(raw)
    if root.tag != expected or sum(1 for _ in root.iter()) > 50000:
        raise ValueError('Unexpected XML root or excessive element count')
    return root


def galaxy_source() -> str:
    return '''
trigger HRC_CatalogTimer;
string HRC_CatalogSession;

bank HRC_Open (string name) {
    bank result;
    BankLoad(name, 1);
    result = BankLastCreated();
    BankWait(result);
    BankSectionRemove(result, "meta");
    BankSectionRemove(result, "entries");
    BankSectionRemove(result, "valid");
    BankValueSetFromString(result, "meta", "format", "hots-runtime-catalog-v1");
    BankValueSetFromString(result, "meta", "token", "@TOKEN@");
    BankValueSetFromString(result, "meta", "session", HRC_CatalogSession);
    BankValueSetFromInt(result, "meta", "expected_build", @BUILD@);
    BankValueSetFromString(result, "meta", "base_map_sha256", "@MAP@");
    return result;
}

bool HRC_Export (int catalog, string label) {
    bank output;
    int count;
    int first;
    int last;
    int index;
    int part;
    string entry;
    count = CatalogEntryCount(catalog);
    if (count < 1 || count > @MAX@) {
        return false;
    }
    first = 1;
    part = 0;
    while (first <= count) {
        last = first + @CHUNK@ - 1;
        if (last > count) {
            last = count;
        }
        output = HRC_Open("@TOKEN@_" + label + "_" + IntToString(part));
        BankValueSetFromString(output, "meta", "catalog", label);
        BankValueSetFromInt(output, "meta", "catalog_id", catalog);
        BankValueSetFromInt(output, "meta", "count", count);
        BankValueSetFromInt(output, "meta", "part", part);
        BankValueSetFromInt(output, "meta", "first", first);
        BankValueSetFromInt(output, "meta", "last", last);
        index = first;
        while (index <= last) {
            entry = CatalogEntryGet(catalog, index);
            BankValueSetFromString(output, "entries", IntToString(index), entry);
            if (CatalogEntryIsValid(catalog, entry)) {
                BankValueSetFromInt(output, "valid", IntToString(index), 1);
            }
            else {
                BankValueSetFromInt(output, "valid", IntToString(index), 0);
            }
            index = index + 1;
        }
        BankValueSetFromInt(output, "meta", "complete", 1);
        BankSave(output);
        first = last + 1;
        part = part + 1;
    }
    return true;
}

bool HRC_CatalogCallback (bool testConds, bool runActions) {
    bank manifest;
    bool units;
    bool abilities;
    if (!runActions) {
        return true;
    }
    HRC_CatalogSession = IntToString(RandomInt(1, 1073741823)) + "_" + IntToString(RandomInt(1, 1073741823));
    manifest = HRC_Open("@TOKEN@_Manifest");
    BankValueSetFromString(manifest, "meta", "catalog", "Manifest");
    BankValueSetFromInt(manifest, "meta", "complete", 0);
    BankSave(manifest);
    units = HRC_Export(c_gameCatalogUnit, "Unit");
    abilities = HRC_Export(c_gameCatalogAbil, "Abil");
    if (units && abilities) {
        BankValueSetFromInt(manifest, "meta", "Unit", CatalogEntryCount(c_gameCatalogUnit));
        BankValueSetFromInt(manifest, "meta", "Abil", CatalogEntryCount(c_gameCatalogAbil));
        BankValueSetFromInt(manifest, "meta", "complete", 1);
        BankSave(manifest);
        UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("HOTS CATALOG PROBE: export requested. Exit this map and collect the HRC98285 bank files. This is NOT the recovered match."));
    }
    else {
        UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("HOTS CATALOG PROBE: catalog count outside supported limits. Do not treat this export as complete."));
    }
    return true;
}

void InitMap () {
    HRC_OriginalInitMap();
    HRC_CatalogTimer = TriggerCreate("HRC_CatalogCallback");
    TriggerAddEventTimeElapsed(HRC_CatalogTimer, 1.0, c_timeGame);
}
'''.replace('@TOKEN@', TOKEN).replace('@MAP@', MAP_SHA256).replace('@BUILD@', str(BUILD)).replace('@MAX@', str(MAX_ENTRIES)).replace('@CHUNK@', str(CHUNK))


def instrument_script(raw: bytes) -> bytes:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError('Map script size is unsupported')
    source = raw.decode('utf-8-sig')
    if 'HRC_' in source:
        raise ValueError('Diagnostic instrumentation already exists')
    match = re.search(r'\bvoid\s+InitMap\s*\(\s*\)\s*\{\s*InitLibs\(\);\s*InitGlobals\(\);\s*InitTriggers\(\);\s*\}\s*\Z', source)
    if match is None or len(re.findall(r'\bInitMap\s*\(', source)) != 1:
        raise ValueError('Original map initialization does not match the inspected hook')
    name = source.index('InitMap', match.start())
    return (source[:name] + 'HRC_OriginalInitMap' + source[name + len('InitMap'):] + galaxy_source()).encode('utf-8')


def instrument_banks(raw: bytes) -> bytes:
    root = xml_root(raw, 'BankList')
    for item in root:
        if item.tag != 'Bank' or set(item.attrib) != {'Name', 'Player'} or item.attrib['Name'].startswith(TOKEN):
            raise ValueError('Bank preload list has unexpected or existing probe entries')
    for label in ('Unit', 'Abil'):
        for part in range((MAX_ENTRIES + CHUNK - 1) // CHUNK):
            ET.SubElement(root, 'Bank', {'Name': f'{TOKEN}_{label}_{part}', 'Player': '1'})
    ET.SubElement(root, 'Bank', {'Name': TOKEN + '_Manifest', 'Player': '1'})
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


class Storm:
    def __init__(self, library: str | None = None):
        found = library or ctypes.util.find_library('storm')
        if not found:
            raise RuntimeError('Native StormLib is required')
        self.lib = ctypes.CDLL(found)
        h, d, p = ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER
        signatures = {
            'SFileOpenArchive': ([ctypes.c_char_p, d, d, p(h)], ctypes.c_bool),
            'SFileOpenFileEx': ([h, ctypes.c_char_p, d, p(h)], ctypes.c_bool),
            'SFileGetFileSize': ([h, p(d)], d),
            'SFileReadFile': ([h, h, d, p(d), h], ctypes.c_bool),
            'SFileCloseFile': ([h], ctypes.c_bool),
            'SFileCloseArchive': ([h], ctypes.c_bool),
            'SFileCreateFile': ([h, ctypes.c_char_p, ctypes.c_uint64, d, d, d, p(h)], ctypes.c_bool),
            'SFileWriteFile': ([h, h, d, d], ctypes.c_bool),
            'SFileFinishFile': ([h], ctypes.c_bool),
            'SFileFlushArchive': ([h], ctypes.c_bool),
        }
        for name, (args, result) in signatures.items():
            getattr(self.lib, name).argtypes = args
            getattr(self.lib, name).restype = result

    def open(self, path: Path, writable: bool = False):
        h = ctypes.c_void_p()
        if not self.lib.SFileOpenArchive(str(path.resolve()).encode(), 0, 0 if writable else 0x100, ctypes.byref(h)):
            raise RuntimeError('Native archive open failed')
        return h

    def read(self, archive, name: str) -> bytes:
        h = ctypes.c_void_p()
        if not self.lib.SFileOpenFileEx(archive, name.encode('ascii'), 0, ctypes.byref(h)):
            raise ValueError('Missing archive member: ' + name)
        try:
            high = ctypes.c_uint32()
            count = self.lib.SFileGetFileSize(h, ctypes.byref(high))
            if high.value or count > 32 * 1024 * 1024:
                raise ValueError('Archive member exceeds the diagnostic limit')
            buf, got = ctypes.create_string_buffer(count), ctypes.c_uint32()
            if count and (not self.lib.SFileReadFile(h, buf, count, ctypes.byref(got), None) or got.value != count):
                raise ValueError('Incomplete archive member read')
            return bytes(buf.raw[:count])
        finally:
            self.lib.SFileCloseFile(h)

    def members(self, path: Path) -> dict[str, bytes]:
        h = self.open(path)
        try:
            names = self.read(h, '(listfile)').decode('utf-8-sig').splitlines()
            if not 1 <= len(names) <= 1024 or len(set(names)) != len(names):
                raise ValueError('Invalid archive member list')
            for name in names:
                if '..' in name.replace('\\', '/').split('/') or name.startswith(('/', '\\')):
                    raise ValueError('Unsafe archive member name')
            return {name: self.read(h, name) for name in names}
        finally:
            self.lib.SFileCloseArchive(h)

    def replace(self, path: Path, replacements: dict[str, bytes]) -> None:
        h = self.open(path, True)
        try:
            for name, raw in sorted(replacements.items()):
                f = ctypes.c_void_p()
                if not self.lib.SFileCreateFile(h, name.encode('ascii'), 0, len(raw), 0, 0x81000200, ctypes.byref(f)):
                    raise RuntimeError('Native member replacement failed')
                try:
                    written = self.lib.SFileWriteFile(f, ctypes.create_string_buffer(raw), len(raw), 2)
                finally:
                    finished = self.lib.SFileFinishFile(f)
                if not written or not finished:
                    raise RuntimeError('Native member write failed')
            if not self.lib.SFileFlushArchive(h):
                raise RuntimeError('Native archive flush failed')
        finally:
            if not self.lib.SFileCloseArchive(h):
                raise RuntimeError('Native archive close failed')


def build_probe(source: Path, output: Path, library: str | None = None) -> dict:
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise FileExistsError('Probe output must be a new directory')
    raw = source.read_bytes()
    if len(raw) > 32 * 1024 * 1024 or digest(raw) != MAP_SHA256:
        raise ValueError('Map is not the hash-bound current Dragon Shire dependency')
    storm = Storm(library)
    before = storm.members(source)
    replacements = {'MapScript.galaxy': instrument_script(before['MapScript.galaxy']),
                    'BankList.xml': instrument_banks(before['BankList.xml'])}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.catalog-probe-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'probe'
        stage.mkdir()
        candidate = stage / OUTPUT
        candidate.write_bytes(raw)
        storm.replace(candidate, replacements)
        after = storm.members(candidate)
        if set(before) != set(after):
            raise AssertionError('Probe archive member set changed')
        for name, value in before.items():
            expected = replacements.get(name, value)
            if name not in ('(attributes)', '(listfile)') and after[name] != expected:
                raise AssertionError('Unexpected map member change: ' + name)
        changes = [{'member': name, 'before_sha256': digest(before[name]), 'after_sha256': digest(value)}
                   for name, value in sorted(replacements.items())]
        report = {'format': 'hots-runtime-probe-build-v1', 'expected_build': BUILD, 'token': TOKEN,
                  'base_map_sha256': MAP_SHA256, 'probe_sha256': digest(candidate.read_bytes()),
                  'size': candidate.stat().st_size, 'map_members_checked': len(before), 'changes': changes,
                  'original_initialization_preserved': True, 'dependencies_preserved': True,
                  'game_installation_modified': False, 'replay_modified': False,
                  'game_executable_started': False, 'galaxy_compilation_verified': False,
                  'runtime_indices_observed': False, 'client_playback_validated': False,
                  'limits': {'max_entries_per_catalog': MAX_ENTRIES, 'entries_per_bank': CHUNK},
                  'limitations': ['This is a diagnostic map, not the original recovered match.',
                                  'Standalone loading can have different initialization and omit talents.',
                                  'Bank completion is checked on import; BankSave itself does not prove durable output.',
                                  'The expected build is a target label, not a version read from the game.',
                                  'Runtime names must match independently observed anchors before use.']}
        (stage / 'probe-report.json').write_text(json.dumps(report, indent=2) + '\n')
        (stage / 'catalog-probe.galaxy').write_text(galaxy_source(), encoding='utf-8')
        (stage / 'map-changes.jsonl').write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in changes))
        if digest(source.read_bytes()) != MAP_SHA256 or output.exists():
            raise ValueError('Source or destination changed during generation')
        stage.rename(output)
    return report


def parse_bank(raw: bytes) -> dict[str, dict[str, str | int]]:
    root = xml_root(raw, 'Bank')
    sections = {}
    for section in root:
        if section.tag == 'Signature':
            continue
        if section.tag != 'Section' or set(section.attrib) != {'name'}:
            raise ValueError('Unexpected bank element')
        name = section.attrib['name']
        if name not in ('meta', 'entries', 'valid') or name in sections:
            raise ValueError('Unknown or duplicate bank section')
        values = {}
        for key in section:
            if key.tag != 'Key' or set(key.attrib) != {'name'} or len(key) != 1:
                raise ValueError('Malformed bank key')
            value = key[0]
            field = key.attrib['name']
            if field in values or value.tag != 'Value' or len(value) or len(value.attrib) != 1:
                raise ValueError('Duplicate or malformed bank value')
            kind, text = next(iter(value.attrib.items()))
            if kind not in ('string', 'int') or len(text) > 1024:
                raise ValueError('Unsupported bank value')
            if kind == 'int':
                if re.fullmatch(r'-?(0|[1-9][0-9]{0,8})', text) is None:
                    raise ValueError('Noncanonical integer')
                values[field] = int(text)
            else:
                values[field] = text
        sections[name] = values
    meta = sections.get('meta', {})
    expected = {'format': 'hots-runtime-catalog-v1', 'token': TOKEN, 'expected_build': BUILD,
                'base_map_sha256': MAP_SHA256, 'complete': 1}
    if any(meta.get(k) != v or type(meta.get(k)) is not type(v) for k, v in expected.items()):
        raise ValueError('Wrong probe identity or incomplete bank')
    if re.fullmatch(r'[0-9]{1,10}_[0-9]{1,10}', str(meta.get('session', ''))) is None:
        raise ValueError('Invalid bank session')
    return sections


def combine_banks(files: dict[str, bytes], anchors: dict[str, int]) -> dict:
    if not files or len(files) > 2 * ((MAX_ENTRIES + CHUNK - 1) // CHUNK) + 1:
        raise ValueError('Unexpected bank file count')
    parsed = {name: parse_bank(raw) for name, raw in files.items()}
    sessions = {value['meta']['session'] for value in parsed.values()}
    if len(sessions) != 1:
        raise ValueError('Mixed export sessions')
    manifest_name = TOKEN + '_Manifest.StormBank'
    if manifest_name not in parsed or parsed[manifest_name]['meta'].get('catalog') != 'Manifest':
        raise ValueError('A completed manifest is required')
    manifest = parsed[manifest_name]['meta']
    catalogs, expected_names = {}, {manifest_name}
    catalog_ids = {}
    for label in ('Unit', 'Abil'):
        count = manifest.get(label)
        if type(count) is not int or not 1 <= count <= MAX_ENTRIES:
            raise ValueError('Invalid reported catalog count')
        rows = []
        for part, first in enumerate(range(1, count + 1, CHUNK)):
            name = f'{TOKEN}_{label}_{part}.StormBank'
            expected_names.add(name)
            if name not in parsed:
                raise ValueError('Missing bank chunk: ' + name)
            bank = parsed[name]
            catalog_id = bank['meta'].get('catalog_id')
            if type(catalog_id) is not int or not 0 <= catalog_id < 128:
                raise ValueError('Invalid native catalog identifier')
            if label in catalog_ids and catalog_ids[label] != catalog_id:
                raise ValueError('Native catalog identifier differs across chunks')
            catalog_ids[label] = catalog_id
            last = min(count, first + CHUNK - 1)
            expected = {'catalog': label, 'part': part, 'count': count, 'first': first, 'last': last}
            if any(type(bank['meta'].get(k)) is not type(v) or bank['meta'].get(k) != v for k, v in expected.items()):
                raise ValueError('Bank chunk metadata is inconsistent')
            keys = {str(i) for i in range(first, last + 1)}
            if set(bank.get('entries', {})) != keys or set(bank.get('valid', {})) != keys:
                raise ValueError('Bank chunk has missing or extra indices')
            for index in range(first, last + 1):
                entry, valid = bank['entries'][str(index)], bank['valid'][str(index)]
                if not isinstance(entry, str) or not re.fullmatch(r'[A-Za-z0-9_@.#:+\-]*', entry) or type(valid) is not int or valid not in (0, 1):
                    raise ValueError('Invalid catalog entry or validity flag')
                rows.append({'index': index, 'id': entry, 'valid': bool(valid)})
        names = [r['id'] for r in rows if r['id']]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate nonempty catalog identifiers')
        catalogs[label] = rows
    if len(set(catalog_ids.values())) != 2:
        raise ValueError('Unit and ability catalogs must be distinct')
    if set(files) != expected_names:
        raise ValueError('Unexpected extra or stale bank files')
    if not anchors or any(not isinstance(k, str) or type(v) is not int or not 1 <= v <= MAX_ENTRIES for k, v in anchors.items()):
        raise ValueError('Independent reference anchors are required')
    by_id = {r['id']: r['index'] for r in catalogs['Unit'] if r['id'] and r['valid']}
    mismatches = [{'id': name, 'expected_index': index, 'observed_index': by_id.get(name)}
                  for name, index in sorted(anchors.items()) if by_id.get(name) != index]
    return {'format': 'hots-runtime-catalog-export-v1', 'token': TOKEN, 'expected_build': BUILD,
            'actual_build_verified': False, 'session': next(iter(sessions)), 'catalogs': catalogs,
            'native_catalog_ids': catalog_ids,
            'reference_anchor_count': len(anchors), 'anchor_mismatches': mismatches,
            'all_unit_anchors_match': not mismatches, 'ability_indices_independently_validated': False,
            'catalog_context_equivalence_proven': False, 'automatically_applied_to_replay': False,
            'client_playback_validated': False, 'input_sha256': {n: digest(b) for n, b in sorted(files.items())}}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build')
    build.add_argument('source', type=Path)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--stormlib')
    export = sub.add_parser('read')
    export.add_argument('banks', type=Path)
    export.add_argument('--anchors', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        result = build_probe(args.source, args.output, args.stormlib)
    else:
        if args.output.exists():
            raise FileExistsError(args.output)
        paths = sorted(args.banks.glob(TOKEN + '_*.StormBank'))
        if any(p.is_symlink() or not p.is_file() for p in paths):
            raise ValueError('Bank inputs must be regular local files')
        anchors = json.loads(args.anchors.read_text())['unit_anchors']
        result = combine_banks({p.name: p.read_bytes() for p in paths}, anchors)
        with args.output.open('x', encoding='utf-8') as out:
            out.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
