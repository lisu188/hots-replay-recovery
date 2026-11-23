"""Verify the 98348 authored hidden flag, its temporary counter, and the bit-29 refresh."""
import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from xml.etree import ElementTree as ET

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


MAPS = (
    ('archived_41810', 'e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250', 165, 107),
    ('retail_98348', 'f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f', 158, 111),
    ('gate_order', 'bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008', 165, 107),
)
WINDOWS = (
    (0xa2a1d4, 0xa2a1ed, '5514f3912db1fc2596bfb5b1'),
    (0xa2a29f, 0xa2a2cd, '24cd40378415886b1e9bbd98'),
    (0xa316ae, 0xa316c7, '6a70fc6be4189264094aab7e'),
    (0xa2b006, 0xa2b010, 'fb3e50e8483ec4b881a15973'),
    (0xa2a020, 0xa2a086, 'f78a4bb25cc230ed9b284b2c'),
    (0xa2ee9d, 0xa2eef7, '3fe31392849c8a2af9335e49'),
    (0xa2ef71, 0xa2ef9c, '393d3cbbf6fa464f83f7a33e'),
    (0xa2b4c7, 0xa2b4d1, 'fb3e50e8483ec4b881a15973'),
    (0xa2e3db, 0xa2e42e, '2b06e9de3fbe83e816ba4235'),
    (0xa2e454, 0xa2e4ad, '47f93d470b9eb9b5d796888c'),
    (0x990c6b, 0x990ca4, '363e10ce501d16062f9b4a29'),
    (0x99003e, 0x990081, '9992c64406ad2f1e22e4fe23'),
    (0x990350, 0x99035d, '206458e463248ae7ef07913c'),
    (0x9bb3c3, 0x9bb3d8, '4a9b94657ea9086f790ab3ad'),
    (0x99e2bd, 0x99e311, '6e934087ee6fd51bdad4ced6'),
    (0x9bb9de, 0x9bb9e6, '798f6eba76a8caa94361b1bd'),
    (0x99ac00, 0x99ace3, 'ab2049e2164b116d55955287'),
    (0x990e9a, 0x990eae, 'a554887991c9376121a060d7'),
    (0x9977ef, 0x997803, '7e0eece41978efcf076d9639'),
    (0x9bbb86, 0x9bbba3, '481333fa0c8abdcb5fce93b4'),
    (0x99ecf9, 0x99ed30, 'd019a6a19862d66c224862f1'),
    (0x9a8859, 0x9a88d1, '1a001c999c31dde66ac77954'),
)


def check(condition, why):
    if not condition:
        raise ValueError(why)


def native(exe, section):
    original, text = pinned(exe, PE), pinned(section, TEXT)
    nt, = unpack_from('<I', original, 60)
    first = nt + 24 + unpack_from('<H', original, nt + 20)[0]
    sections = [unpack_from('<III', original, first + i*40 + 12)
                for i in range(unpack_from('<H', original, nt + 6)[0])]

    def image(rva, size):
        off, = (raw+rva-base for base,length,raw in sections if base <= rva and rva+size <= base+length)
        return original[off:off+size]

    def ref(site, opcode):
        off = site - TEXT_RVA
        prefix = bytes.fromhex(opcode)
        check(text[off:off+len(prefix)] == prefix, f'opcode at {site:x}')
        return site+len(prefix)+4+unpack_from('<i', text, off+len(prefix))[0]

    def literal(table, index):
        pointer, size = unpack_from('<QQ', image(table + index*16,16))
        return image(pointer - 0x140000000, size).decode('ascii')

    for begin, end, expected in WINDOWS:
        check(sha256(text[begin-TEXT_RVA:end-TEXT_RVA]).hexdigest().startswith(expected), f'window {begin:x}')
    for site, destination in (
        (0xa2a1e8,0xa2a290),(0xa316b6,0xa2a290),(0xa316c2,0xa2afc0),
        (0xa2eeb3,0xa29fe0),(0xa2eedc,0xa29fe0),(0xa2e484,0x996d90),
        (0x996fb8,0x990af0),(0x990c88,0x1a2b6c0),(0x990c90,0x990020),(0x99705a,0x9baef0),
        (0x9bb3d3,0x99e2b0),(0x9bb9e1,0x99ac00),(0x9bbb89,0x9a90e0),(0x9bbb9e,0x99ecf0),
        (0xa2e4a8,0x99e2b0),(0x99acd3,0x9977e0),
    ):
        check(ref(site,'e8') == destination, f'call {site:x}')
    check(ref(0x99acce,'e9') == 0x990e90, 'bit 29 setter')
    names = ref(0xa2a020,'488d1d')
    labels = [literal(names,i) for i in range(14)]
    check(labels[4:6] == ['UnitHidden','ForcePlacement'], 'placement flag indices')
    for slot, value in [(0x2f70410,'index'),(0x2f70420,'Index'),(0x2f70430,'value'),(0x2f70440,'Value')]:
        check(literal(slot,0) == value, 'attribute name')
    return labels


def authored(path, pin, labels):
    name, expected, count, forced = pin
    check(sha256(path.read_bytes()).hexdigest() == expected, f'map {name}')
    with closing(MPQArchive(path)) as archive:
        data = read_member(archive, 'Objects')
    if isinstance(data, tuple):
        raise ValueError('unexpected map member')
    units = ET.fromstring(data).findall('ObjectUnit')
    check(len(units)==count, f'placement count {name}')
    masks = Counter()
    for unit in units:
        mask = 0
        for child in unit:
            check(child.tag == 'Flag', 'unexpected placed unit child')
            flag = 1 << labels.index(child.attrib['Index'])
            value = child.attrib['Value']
            check(value in ('0','1'), 'unexpected boolean')
            mask = mask | flag if value == '1' else mask & ~flag
        masks[mask] += 1
    check(dict(masks)=={0:count-forced, 1<<5:forced}, f'placement masks {name}')
    return dict(map=name, sha256=expected, objects_sha256=sha256(data).hexdigest(), units=count,
                force_placement=forced, hidden_spawn_bit_set=sum(n for m,n in masks.items() if m & 16))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe','section','archive','retail','gate_order'):
        parser.add_argument(name,type=Path)
    args = parser.parse_args()
    labels = native(args.exe,args.section)
    rows = [authored(path,pin,labels) for path,pin in zip((args.archive,args.retail,args.gate_order),MAPS)]
    print(json.dumps(dict(build=98348, original_sha256=PE[1], static_text_sha256=TEXT[1],
                         checked_windows=len(WINDOWS), placement_hidden_index=4, spawn_hidden_bit=8,
                         fresh_unit_runtime_masks=[0,0], maps=rows,
                         bit29_when_bit31_at_recompute=0, complete_opening_descriptors=None), indent=2))
