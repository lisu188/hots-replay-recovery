"""Resolve build-98348 opening descriptor bit 29 on the ordinary authored-footprint branch."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing, nullcontext
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import unpack_from
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_unit_radii import CORE, HEROES, OPENING, check, index_nodes, map_catalogs
from opening_unit_radii import pinned, projected_catalogs
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned as native_input


BASELINE = '085de11a4512e65e649757b13670ea15e3fbe8ffc97e5577ca0a0f292280ed0a'
FOOTPRINT_MEMBERS = '7b153d311982ed826d5dd634450ecf30e358948df7bcd6cf8461d06cf120a672'
LINKS = ('Footprint', 'DeadFootprint')
WINDOWS = (
    (0x594874,0x5948ff),(0x617f1a,0x617f26),(0x618052,0x618060),(0x587e30,0x587e55),
    (0x9a3a93,0x9a3ac0),(0x9a0080,0x9a029b),(0x98c5a0,0x98c71c),(0x99fe80,0x99fea9),
    (0x991660,0x99170b),(0x9ba120,0x9ba1bc),(0x99ac00,0x99ace3),(0x990e90,0x990ed3),
    (0x9977e0,0x997808),(0x99003e,0x990081),(0x9bb2cf,0x9bb2da),(0xa316b6,0xa316c7),
    (0xa3236e,0xa323cf),(0xa2a2f5,0xa2a311),(0xa2e20f,0xa2e388),(0xa2e3db,0xa2e4a8),
    (0x236a0f,0x236a46),(0x2004cf2,0x2004d28),(0x204dca0,0x204dd04),(0x205df30,0x205e607),
    (0x996dac,0x996db8),(0x997054,0x99705f),(0x9bb9de,0x9bb9e6),(0x9bbb86,0x9bbba3),
    (0x9a8859,0x9a88d1),
)
WINDOW_SHA = '10e5d20a3c90329d0cd0d1190fad9a30df9eafd50db7c2f51ae0522bb22f0929'


def verify_native(executable, section):
    image = native_input(executable, PE)
    text = native_input(section, TEXT)
    digest = sha256(b''.join(text[a-TEXT_RVA:b-TEXT_RVA] for a,b in WINDOWS)).hexdigest()
    check(digest == WINDOW_SHA, 'Native footprint path differs')
    nt, = unpack_from('<I', image, 60)
    table = nt + 24 + unpack_from('<H', image, nt+20)[0]
    base, = unpack_from('<Q', image, nt+48)
    sections = [unpack_from('<III', image, table+40*i+12)
                for i in range(unpack_from('<H', image, nt+6)[0])]

    def read(rva, count):
        offset, = (r+rva-a for a,n,r in sections if a<=rva and rva+count<=a+n)
        return image[offset:offset+count]

    def ref(site, prefix):
        offset = site-TEXT_RVA
        check(text[offset:offset+len(prefix)] == prefix, 'Unexpected native reference')
        return site+len(prefix)+4+unpack_from('<i',text,offset+len(prefix))[0]

    for site, prefix, name in ((0x594874,'488d0d',b'Footprint'), (0x5948cc,'488d05',b'DeadFootprint'),
                               (0x236a0f,'488d15',b'UnitCreate')):
        check(read(ref(site,bytes.fromhex(prefix)),len(name)+1)==name+b'\0', 'Native symbol mismatch')
    for address, key in ((0x2f704d0,b'footprint'),(0x2f704e0,b'Footprint')):
        pointer,length = unpack_from('<QQ',read(address,16))
        check(read(pointer-base,length)==key, 'Unexpected placed footprint attribute')
    check(unpack_from('<II',read(0x2f2f7d0,8))==(1,0x21), 'Empty lookup key differs')
    entry = ref(0x236a1b,bytes.fromhex('488d0d'))
    idx, rem = divmod(entry-0x4120b50,24)
    check(not rem and idx==1453 and unpack_from('<I',text,0x200accc-TEXT_RVA+idx*4)[0]==0x2004cf2,
          'Unexpected UnitCreate entry')
    for site,target in ((0x2004d23,0x204dca0),(0x204dcf9,0x205df30),(0x205e602,0x996d90),
                        (0x99705a,0x9baef0),(0x9bb9e1,0x99ac00),(0x9ba19b,0x991660)):
        check(ref(site,b'\xe8')==target,'Unexpected call target')
    setters = [m.start()+TEXT_RVA for m in re.finditer(rb'[\xe8\xe9]',text[:-4])
               if m.end()+4+TEXT_RVA+unpack_from('<i',text,m.end())[0]==0x990e90]
    check(setters==[0x99acce,0x9ba1a7], 'Different direct footprint setter paths')
    return setters


def resolved_links(index, unit):
    values = {}
    seen = set()
    current = unit
    while current not in seen:
        seen.add(current)
        nodes = index[current]
        check(nodes,'Unknown CUnit parent')
        parents = set()
        layer = {}
        for _, n in nodes:
            check(set(n.attrib)<= {'id','parent','default'}, 'Unhandled CUnit attributes')
            if n.get('parent'):
                parents.add(n.attrib['parent'])
            for field in n:
                if field.tag in LINKS:
                    check(set(field.attrib)=={'value'} and not len(field),'Unsupported link expression')
                    value = field.attrib['value']
                    check(field.tag not in layer or layer[field.tag]==value, 'Conflicting CUnit link')
                    layer[field.tag] = value
        check(len(parents)<=1, 'Conflicting CUnit parents')
        for field,value in layer.items():
            values.setdefault(field,value)
        if current is None:
            return tuple(values.get(k,'') for k in LINKS)
        current = next(iter(parents),None)
    raise ValueError('Cyclic CUnit inheritance')


def footprint_ids(files, archive, gate):
    members = []
    declarations = []
    directory = archive.is_dir()
    with (nullcontext() if directory else ZipFile(archive)) as z:
        for name in (files if directory else z.namelist()):
            raw = (archive/name).read_bytes() if directory else z.read(name)
            info = files[name]
            check(len(raw)==info['bytes'] and sha256(raw).hexdigest()==info['sha256'],'Unknown catalog input')
            found = list(ET.fromstring(raw).iter('CFootprint'))
            if found:
                members.append((name, info['sha256']))
                declarations.extend(found)
            else:
                check(directory,'Unexpected footprint archive member')
    check(sha256(json.dumps(sorted(members),separators=(',',':')).encode()).hexdigest()==FOOTPRINT_MEMBERS,
          'Incomplete footprint declarations')
    with closing(MPQArchive(gate)) as mpq:
        names = read_member(mpq,'(listfile)').decode().splitlines()
        for name in names:
            if name.lower().endswith('.xml'):
                declarations.extend(ET.fromstring(read_member(mpq,name)).iter('CFootprint'))
        objects = list(ET.fromstring(read_member(mpq,'Objects')).iter('ObjectUnit'))
        check(len(objects)==165 and all(
            set(o.attrib)<= {'Id','Position','Scale','UnitType','Rotation','Player','Variation'}
            and all(c.tag=='Flag' and set(c.attrib)=={'Index','Value'} for c in o) for o in objects),
            'Unhandled placed footprint input')
    ids = [n.get('id') for n in declarations if n.get('id')]
    check(len(declarations)==204 and len(ids)==203 and
          [n.attrib for n in declarations if not n.get('id')]==[{'default':'1'}],
          'Unnamed or unrecognized footprint declaration')
    return set(ids)


def scripted_requests(folder):
    mech = pinned(folder/'mapmechanicslib.galaxy','d49dbde21198963f953efa16c8d8bb6b035d2d8bd8f0d41b5989fecbb4e35b1f')
    lib = pinned(folder/'nativelib.galaxy','c7df2bc2fc3b43acffcc54f37a605af646e5dfedbdcb383a54ddc3bc06ebf876')
    check(mech.count(b'UnitCreate(1, "DragonballCaptureBeacon",')==2 and
          mech.count(b'libNtve_gf_CreateUnitsWithDefaultFacing(1, "TownMercCampCaptureBeacon",')==1,
          'Unexpected script creation path')
    body = lib.split(b'void libNtve_gf_CreateUnitsWithDefaultFacing (',1)[1].split(b'\n}',1)[0]
    check(body.count(b'UnitCreate(lp_count, lp_type, lp_style, lp_player, lp_p, lv_angle, lp_creatorUnit);')==1,
          'Unexpected default-facing wrapper')


def generate(executable, section, projection, units, footprints, gate, scripts, opening, baseline):
    setters = verify_native(executable,section)
    files, nodes = projected_catalogs(projection, units)
    authored, added = map_catalogs(gate)
    named = footprint_ids(files,footprints,gate)
    scripted_requests(scripts)
    rows = json.loads(pinned(baseline,BASELINE))
    births = [r for r in json.loads(pinned(opening,OPENING)) if r['loop']==0]
    check([r['slot'] for r in rows]==list(range(172)) and
          [(r['slot'],r['unit']) for r in rows]==[(r['slot'],r['unit']) for r in births],
          'Unexpected opening slot assignments')
    types = Counter(r['unit'] for r in rows)
    check(types==authored+Counter(TownMercCampCaptureBeacon=5, DragonballCaptureBeacon=2),'Map cohort changed')
    active = index_nodes([(p,n) for p,n in nodes if p.startswith((CORE,HEROES))]+added)
    superset = index_nodes(nodes+added)
    admitted = {}
    for name,count in sorted(types.items()):
        links = resolved_links(active, name)
        if not any(links):
            check(links==resolved_links(superset, name),'Another package changes an otherwise absent link')
            admitted[name]=count
    check(resolved_links(active,'TownCannonTowerL3')[0] in named, 'Missing named footprint control')
    for row in rows:
        if row['unit'] not in admitted:
            continue
        mask = bytearray.fromhex(row['mask'])
        value = bytes.fromhex(row['value'])
        check(len(mask)==len(value)==12 and row['known_bits']==94 and mask[3]==0x5f and not(value[3]&32),
              'Unexpected starting descriptor')
        mask[3] |= 32
        row.update(mask=mask.hex(),known_bits=95)
    private = json.dumps(rows,separators=(',',':')).encode()
    return private,dict(build=98348,native_windows=len(WINDOWS),direct_setter_sites=[hex(a) for a in setters],
                        verified_xml=len(files),footprint_xml_members=22,footprint_named_declarations=203,
                        footprint_class_defaults=1,opening_slots=172,
                        ordinary_creation_routes={'placed_xml':165,'galaxy_UnitCreate':7},
                        no_link_slots_by_type=admitted,
                        slots_by_known_bits=dict(sorted(Counter(r['known_bits'] for r in rows).items())),
                        private_ledger_sha256=sha256(private).hexdigest(),
                        condition='Inherits the 94-bit ledger assumptions. The empty catalog key resolves to null, the recorded type and ordinary creation footprint persist, and only the two identified setter paths can enable the bit before the sample.',
                        runtime_registry_complete=False,first_fast_crc_verified=False)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    for name in ('executable','section','projection','units','footprints','gate','scripts','opening','baseline'):
        parser.add_argument(name,type=Path)
    parser.add_argument('--private-output',type=Path)
    args=vars(parser.parse_args())
    path=args.pop('private_output')
    data, report=generate(**args)
    if path:
        with path.open('xb') as handle:
            handle.write(data)
    print(json.dumps(report,indent=2))
