"""Verify descriptor bit 30 for the catalog types assigned to the Dragon Shire opening."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from opening_unit_radii import CORE, HEROES, OPENING, GATE_ORDER, check, index_nodes, map_catalogs, projected_catalogs
from opening_unit_radii import pinned as catalog_pin
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


WINDOWS = (
    (0x2389a0, 0x2389b3, '900616fd2ac6496d2dab97bf'),
    (0x2006ed3, 0x2006ee6, '512b25dfc92bcfd5474467b2'),
    (0x205aed4, 0x205af41, '72ebb273c20ab43b30066c56'),
    (0xb0ae41, 0xb0ae6e, '2ca1a5a71d77cb6cd0575747'),
    (0x5935c0, 0x593604, 'da06ae0263acbeec2772c61e'),
    (0x587e42, 0x587e68, '847fde62d63279b62c9922a3'),
    (0x617f1a, 0x617f51, 'a61e3d49701da7ac6e228b73'),
    (0x587f17, 0x587f38, 'aa3c40611610e93ca080038e'),
    (0x58bda4, 0x58bdb5, '5e90c76d2c8efc80951bfd73'),
    (0x9bb030, 0x9bb052, '10361b4bdca135de213d5423'),
    (0x6fd780, 0x6fd7f3, '4c2f6ec3301c6fb3bdd2e365'),
    (0x9a8891, 0x9a88b9, 'dcd05c7bb196ae47f992f83e'),
    (0x9bbb86, 0x9bbb8e, 'e4ca012afc05e6727889d11c'),
)


def native(executable, decoded):
    pe = pinned(executable, PE)
    code = pinned(decoded, TEXT)
    nt, = unpack_from('<I', pe, 60)
    first = nt + 24 + unpack_from('<H', pe, nt+20)[0]
    sections = [unpack_from('<III', pe, first+40*i+12)
                for i in range(unpack_from('<H', pe, nt+6)[0])]
    image, = unpack_from('<Q', pe, nt+48)

    def original(rva, size):
        off, = (start+rva-va for va,length,start in sections if va <= rva and rva+size <= va+length)
        return pe[off:off+size]

    def reference(rva, prefix):
        off = rva-TEXT_RVA
        op = bytes.fromhex(prefix)
        check(code[off:off+len(op)] == op, f'Unexpected instruction at {rva:x}')
        return rva+len(op)+4+unpack_from('<i', code, off+len(op))[0]

    for start, end, digest in WINDOWS:
        check(sha256(code[start-TEXT_RVA:end-TEXT_RVA]).hexdigest().startswith(digest),
              f'Unexpected code at {start:x}')
    for place, instruction, name in (
        (0x2389a0, '488d15', b'UnitTypeTestFlag'), (0xb0ae46, '488d0d', b'c_unitFlagMissile'),
        (0xb0ae56, '4c8d05', b'Missile'), (0xb0ae62, '488d0d', b'c_unitFlagMissileName'),
        (0x5935c7, '488d0d', b'FlagArray'),
    ):
        check(original(reference(place, instruction), len(name)+1) == name+b'\0', 'Unexpected native field name')
    def call(site, dest):
        check(reference(site, 'e8') == dest, f'Unexpected call at {site:x}')
    call(0x2006ed9, 0x205aeb0)
    call(0x587e51, 0x617f10)
    call(0x587f33, 0x58bd30)
    call(0x9bb041, 0x6fd780)
    call(0x9bb04d, 0x6fd780)
    call(0x9bbb89, 0x9a90e0)
    entry = reference(0x2389a7, '488d0d')
    check(entry == 0x4120b50+24*1671, 'UnitTypeTestFlag registration index')
    check(unpack_from('<I', code, 0x200accc-TEXT_RVA+4*1671)[0] == 0x2006ed3, 'Galaxy dispatch arm')
    table = 0x2bf4ef8
    labels = []
    for i in range(71):
        value, ptr, n = unpack_from('<QQQ', original(table+24*i,24))
        check(value == i and 0 < n < 80, 'Flag enumerator mismatch')
        labels.append(original(ptr-image,n).decode('ascii'))
    check(labels[18:21] == ['Uncloakable','Missile','Undetectable'], 'FlagArray enumeration')
    label, length = unpack_from('<QQ', original(0x2bcdae0,16))
    check(original(label-image,length) == b'CUnit' and
          unpack_from('<Q',original(0x2bcdb00,8))[0] == image+0x587e30 and
          unpack_from('<Q',original(0x2bcdb10,8))[0] == image+0x587ef0, 'CUnit hooks')
    return labels


def missile(index, unit, flags):
    current = unit
    seen = set()
    while current not in seen:
        seen.add(current)
        rows = index[current]
        check(bool(rows), f'Unknown CUnit {current}')
        values, parents = set(), set()
        for _, node in rows:
            check(not (set(node.attrib) - {'id','parent','default'}), 'Unrecognized CUnit attribute')
            if node.get('parent'):
                parents.add(node.attrib['parent'])
            for child in node:
                if child.tag != 'FlagArray':
                    check('flagarray' not in str(child.attrib).lower(), 'Unhandled FlagArray reference')
                    continue
                check(set(child.attrib)=={'index','value'} and child.get('index') in flags
                      and child.get('value') in ('0','1') and not len(child), 'Unhandled FlagArray operation')
                if child.get('index') == 'Missile':
                    values.add(int(child.attrib['value']))
        check(len(values)<=1 and len(parents)<=1, 'Conflicting CUnit declarations')
        if values:
            return values.pop()
        if current is None:
            return 0
        current = next(iter(parents), None)
    raise ValueError('CUnit inheritance cycle')


def generate(executable, decoded, projection, catalog, gate_map, witnesses):
    labels = native(executable, decoded)
    _, installed = projected_catalogs(projection, catalog)
    authored, placed = map_catalogs(gate_map)
    rows = [r for r in json.loads(catalog_pin(witnesses, OPENING)) if r['loop']==0]
    check([r['slot'] for r in rows] == list(range(172)), 'Changed opening slots')
    types = Counter(r['unit'] for r in rows)
    check(types == authored + Counter(TownMercCampCaptureBeacon=5, DragonballCaptureBeacon=2),
          'Opening types differ from the map')
    active = index_nodes([(p,n) for p,n in installed if p.startswith((CORE,HEROES))] + placed)
    all_packages = index_nodes(installed + placed)
    fixtures = {u:missile(all_packages,u,labels) for u in
                ('MISSILE','MISSILE_INVULNERABLE','XalatathVoidEruptionDummyMissile','HealingPadSearchUnit')}
    check(list(fixtures.values()) == [1,1,0,0], 'Set, inherit, clear or default flag failure')
    by_unit = {}
    for unit in sorted(types):
        flag = missile(active, unit, labels)
        check(flag == missile(all_packages, unit, labels), f'Other map or package changes {unit}')
        by_unit[unit] = {'missile':flag, 'slots':[r['slot'] for r in rows if r['unit']==unit]}
    return dict(build=98348, map_sha256=GATE_ORDER, executable_sha256=PE[1], text_sha256=TEXT[1],
                native_windows=len(WINDOWS), array_index=labels.index('Missile'), bit=30,
                opening_slots=len(rows), opening_types=len(types), positive_and_negative_controls=fixtures,
                recorded_type_set_slots=sum(types[u]*d['missile'] for u,d in by_unit.items()),
                qualified_for='Selected shared type equals the recorded opening type, or has the same Missile flag.',
                runtime_selected_type_observed=False, first_fast_crc_verified=False, by_unit=by_unit)


def recorded_type_ledger(spatial, report):
    raw = catalog_pin(spatial, 'd786bd7da91e7067c6b4ecf167684a584e61de6b34f092d156dfb606ab2816cb')
    check((report['build'],report['map_sha256'],report['executable_sha256'],report['text_sha256'],
           report['bit'],report['array_index'],report['opening_slots']) ==
          (98348,GATE_ORDER,PE[1],TEXT[1],30,19,172), 'Recorded-type evidence differs')
    assignment = sorted((slot,u,r['missile']) for u,r in report['by_unit'].items() for slot in r['slots'])
    check(sha256(json.dumps(assignment,separators=(',',':')).encode()).hexdigest() ==
          'ee7b160ef1e3c17250e8302f476c478b96587d8c9be9ba4ce4035da1addd915a',
          'Recorded unit types or flag assignments differ')
    rows = json.loads(raw)
    check([r['slot'] for r in rows] == list(range(report['opening_slots'])), 'Different slot sequence')
    for row in rows:
        unit = report['by_unit'][row['unit']]
        check(row['slot'] in unit['slots'], 'Inconsistent type for this slot')
        value, mask = (bytearray.fromhex(row[k]) for k in ('value','mask'))
        check(len(mask)==len(value)==12 and row['known_bits']==92 and mask[3]==15,
              'Different incoming descriptor mask')
        value[3] = (value[3] & 0xbf) | unit['missile'] << 6
        mask[3] |= 0x40
        row.update(value=value.hex(), mask=mask.hex(), known_bits=sum(b.bit_count() for b in mask))
    return json.dumps(rows,separators=(',',':')).encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('executable','decoded','projection','catalog','gate_map','witnesses'):
        parser.add_argument(arg,type=Path)
    parser.add_argument('--spatial-ledger',type=Path)
    parser.add_argument('--private-output',type=Path)
    args = parser.parse_args()
    if args.private_output and not args.spatial_ledger:
        parser.error('--private-output requires --spatial-ledger')
    report = generate(args.executable,args.decoded,args.projection,args.catalog,args.gate_map,args.witnesses)
    if args.spatial_ledger:
        ledger = recorded_type_ledger(args.spatial_ledger,report)
        report['recorded_type_live_radius_ledger'] = {
            'sha256':sha256(ledger).hexdigest(), 'known_bits_per_slot':93, 'slots':report['opening_slots']}
        if args.private_output:
            with args.private_output.open('xb') as output:
                output.write(ledger)
    print(json.dumps(report, indent=2))
