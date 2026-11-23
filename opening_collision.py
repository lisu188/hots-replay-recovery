"""Check the catalog-backed collision branch of build 98348 opening descriptors."""

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
from opening_unit_radii import CORE, HEROES, OPENING, check, index_nodes, map_catalogs, projected_catalogs
from opening_unit_radii import pinned as catalog_pin
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


MODIFIER_MEMBERS = 'e97b55d0e99fd70e0b4f701be2698dac672bfa33484820e7bbff8f5cef9d73a4'
BASELINE = '7ed61d56f795b59a0bf154bc56ff443a36779b3b7aaddbc56bda0716f1fe36fd'
FIELDS = ('CollideEnableFlags','CollideDisableFlags')
WINDOWS = (
    (0x593714,0x593758,'5f57d67fe8380bf6397e'), (0x61829f,0x6182e7,'b1bed8b10022ffce419c'),
    (0x587e63,0x587e79,'33e1670de225a3d90e4e'), (0x990350,0x99035d,'206458e463248ae7ef07'),
    (0x440c00,0x440c1f,'ddddba964af471f5be37'), (0x60727a,0x60728b,'39af42494b41fee04279'),
    (0x6085a2,0x6085b3,'09612a63566326d5ee92'), (0x45674d,0x456807,'eb4f371b95409f54e0e6'),
    (0xa984fe,0xa9851f,'cc4207d708e46b41a930'), (0xa991c1,0xa991e0,'0a933dd9a7a1b6732696'),
    (0xa58fd0,0xa5900d,'55542a6c9277c1383b75'), (0xa9a35d,0xa9a373,'58a560ec7818b0c842ee'),
    (0xa97de6,0xa97e41,'9a20e44d8a6f51bd9cc6'), (0x9a8834,0x9a8885,'82300f654d28d57c01d3'),
    (0xb1d4f0,0xb1d917,'009c826afb91c183cde2'), (0xa9b64f,0xa9b663,'e486c47f588873e6ad0e'),
    (0xc33ae0,0xc33b21,'865913abb767a4b94781'), (0xb203c0,0xb203dd,'ad1fe17563f0beaf9b69'),
    (0xc1ecf0,0xc1ed0a,'af72f50cb360a5e9ec96'), (0xc3a190,0xc3a1b5,'1ddf5938d3cf3ddac2e0'),
    (0xbfe870,0xbfe948,'a061ba6183979f8ea520'), (0xc17ca0,0xc17dab,'f77de85b398c5e1c28e8'),
    (0xc18b25,0xc18bd3,'56b19f0182311e21296e'), (0xc1999b,0xc19a37,'7cb0e7ff4f0d284f84b8'),
    (0xa99590,0xa99604,'1f418a9e66b228332a35'),
)


def provider_registry(code, image, base):
    def c(rva,n):
        return code[rva-TEXT_RVA:rva-TEXT_RVA+n]
    def dest(site,op):
        check(c(site,len(op))==op,'Native dispatch instruction differs')
        return site+len(op)+4+unpack_from('<i',c(site+len(op),4))[0]
    start, end = 0xb1d4fe, 0xb1d868
    lea = bytes.fromhex('488d05')
    entries = [start+m.start() for m in re.finditer(re.escape(lea),c(start,end-start))]
    classes = {}
    for i,site in enumerate(entries):
        end_entry = entries[i+1] if i+1<len(entries) else end
        call = end_entry-5
        check(dest(call,b'\xe8') == 0xb1d3c0 and dest(call-7,bytes.fromhex('488d0d'))==0x36d2690 and
              c(call-12,1)==b'\xba','Provider registration form differs')
        id_, = unpack_from('<I',c(call-11,4))
        wrapper=dest(site,lea)
        calls=[wrapper+k for k in range(24) if c(wrapper+k,1)==b'\xe8' and
               dest(wrapper+k,b'\xe8') in (0xa954c0,0xc13260,0xc1e800,0xc36e20,0xc392a0)]
        check(len(calls)==1,'Unexpected provider constructor')
        ctor=dest(calls[0],b'\xe8')
        after_base=calls[0]+5
        if ctor!=0xa954c0:
            nested=[ctor+k for k in range(32) if c(ctor+k,1)==b'\xe8' and dest(ctor+k,b'\xe8')==0xa954c0]
            check(len(nested)==1,'Invalid delegated constructor')
            after_base=nested[0]+5
        if after_base==0xc392b2:
            check(c(after_base,2)==bytes.fromhex('33ff'),'Changed constructor prologue')
            after_base+=2
        vtable=dest(after_base,lea)
        classes[id_]=unpack_from('<Q',image(vtable+0x160,8))[0]-base
    check(sorted(classes)==list(range(1,18)) and len(entries)==17,'Provider cohort differs')
    check(set(classes.values()) == {0xa9b640,0xc33ae0,0xb203c0,0xc1ecf0,0xc3a190,0xbfe870,0xc17ca0},
          'Unknown modifier provider')
    # The second switch additionally has a byte-to-index table. Event 5 skips its special cases.
    branch = c(0xc19af8+5-1,1)[0]
    check(unpack_from('<I',c(0xc19abc+4*branch,4))[0]==0xc18b25 and
          unpack_from('<I',c(0xa9a394+4*(5-2),4))[0]==0xa9a35d and
          dest(0xbfe92e,b'\xe8')==dest(0xc19a03,b'\xe8')==0xa99590,'Different collision event routing')
    return {'registered_classes':len(classes),'distinct_handlers':len(set(classes.values())),
            'catalog_modifier_class_ids':sorted(k for k,v in classes.items() if v in (0xbfe870,0xc17ca0))}


def enumerators(executable, section):
    raw, code = pinned(executable,PE), pinned(section,TEXT)
    for a,b,h in WINDOWS:
        check(sha256(code[a-TEXT_RVA:b-TEXT_RVA]).hexdigest().startswith(h),f'Native routine differs at {a:x}')
    nt, = unpack_from('<I',raw,60)
    table = nt+24+unpack_from('<H',raw,nt+20)[0]
    sections = [unpack_from('<III',raw,table+40*i+12) for i in range(unpack_from('<H',raw,nt+6)[0])]
    base, = unpack_from('<Q',raw,nt+48)
    def image(rva,n):
        off, = (o+rva-a for a,l,o in sections if a<=rva and rva+n<=a+l)
        return raw[off:off+n]
    seq = []
    for i in range(32):
        v,p,n = unpack_from('<QQQ',image(0x2bf4858+24*i,24))
        check(i==v and 0<n<40,'Unrecognized collision mask enumeration')
        seq.append(image(p-base,n).decode('ascii'))
    check(seq[23:26] == ['Land24','Flying','FlyingImmobile'] and len(set(seq))==32,'Collision bit positions')
    for site,word in ((0x59372f,b'Collide'),(0x456770,b'CollideEnableFlags'),(0x4567b2,b'CollideDisableFlags')):
        # Both common RIP-relative LEA forms encode the displacement after three bytes.
        dest = site+7+unpack_from('<i',code,site-TEXT_RVA+3)[0]
        check(image(dest,len(word)+1)==word+b'\0','Catalog registration differs')
    ptr,n = unpack_from('<QQ',image(0x2bb9660,16))
    check(image(ptr-base,n)==b'SModification' and unpack_from('<Q',image(0x2bb9680,8))[0]==base+0x440c00,
          'Unexpected modification constructor')
    return seq,provider_registry(code,image,base)


def collision_mask(index, unit, labels):
    current, seen, resolved = unit, set(), {}
    while current not in seen:
        seen.add(current)
        nodes = index[current]
        check(bool(nodes),f'Unknown CUnit {current}')
        declarations, parents = {}, set()
        for _, n in nodes:
            check(not (set(n.attrib)-{'id','parent','default'}),'Unhandled catalog attribute')
            if n.get('parent'):
                parents.add(n.attrib['parent'])
            for e in n:
                if e.tag != 'Collide':
                    check('collide' not in str(e.attrib).lower() or e.tag=='FlagArray',
                          'Indirect collision change')
                    continue
                name, value = e.get('index'), e.get('value')
                check(set(e.attrib)=={'index','value'} and name in labels and value in ('0','1')
                      and not len(e),'Unhandled collision field')
                check(name not in declarations or declarations[name]==value, 'Conflicting collision fields')
                declarations[name]=value
        for name,value in declarations.items():
            resolved.setdefault(name,int(value))
        check(len(parents)<=1,'Conflicting parents')
        if current is None:
            return sum(v<<labels.index(k) for k,v in resolved.items())
        current=next(iter(parents),None)
    raise ValueError('Cyclic CUnit inheritance')


def modifiers(archive, files, gate_map, labels):
    members, counts = [], Counter()
    directory = archive.is_dir()
    with (nullcontext() if directory else ZipFile(archive)) as z:
        for name in (files if directory else z.namelist()):
            raw=(archive/name).read_bytes() if directory else z.read(name)
            h=sha256(raw).hexdigest()
            check(files[name]['sha256']==h and files[name]['bytes']==len(raw),'Unrecognized XML')
            document=ET.fromstring(raw)
            fields=[e for e in document.iter() if e.tag in FIELDS]
            references = sum(f.lower() in (str(e.attrib)+' '+str(e.text)).lower()
                             for e in document.iter() for f in FIELDS)
            check(not references,'Unexpected indirect collision modification')
            lower=raw.lower()
            check(len(fields)==sum(lower.count(f.lower().encode()) for f in FIELDS),
                  'Referenced collision modifier outside an ordinary field')
            if not fields:
                check(directory, 'Unexpected modifier archive member')
                continue
            members.append((name,h))
            for e in fields:
                check(set(e.attrib)=={'index','value'} and e.get('index') in labels
                      and e.get('value') in ('0','1') and not len(e),'Unexpected field expression')
                counts[(e.tag, e.attrib['index'], e.attrib['value'])] += 1
    check(sha256(json.dumps(sorted(members),separators=(',',':')).encode()).hexdigest()==MODIFIER_MEMBERS,
          'Incomplete selection of modifier XML files')
    with closing(MPQArchive(gate_map)) as ar:
        names = read_member(ar,'(listfile)').decode().splitlines()
        for name in [n for n in names if n.lower().endswith(('.xml','.galaxy'))]:
            raw = read_member(ar,name).lower()
            check(all(f.lower().encode() not in raw for f in FIELDS),'Map alters a collision modifier')
    return counts


def generate(executable, section, projection, units, modifier_xml, gate_map, opening, baseline):
    labels,providers=enumerators(executable,section)
    files,global_nodes=projected_catalogs(projection,units)
    authored, map_nodes=map_catalogs(gate_map)
    counts=modifiers(modifier_xml,files,gate_map,labels)
    check(sum(n for k,n in counts.items() if k[0]==FIELDS[0])==0 and sum(counts.values())==48,
          'Override cohort differs')
    qualified=index_nodes([(p,n) for p,n in global_nodes if p.startswith((CORE,HEROES))]+map_nodes)
    superset=index_nodes(global_nodes+map_nodes)
    witness=[x for x in json.loads(catalog_pin(opening,OPENING)) if x['loop']==0]
    rows=json.loads(catalog_pin(baseline,BASELINE))
    check([x['slot'] for x in rows]==list(range(172)) and
          [(x['slot'],x['unit']) for x in rows]==[(x['slot'],x['unit']) for x in witness],
          'Opening slot assignment differs')
    types=Counter(x['unit'] for x in rows)
    check(types==authored+Counter(TownMercCampCaptureBeacon=5,DragonballCaptureBeacon=2),'Map units changed')
    masks={}
    for name in sorted(types):
        m=collision_mask(qualified,name,labels)
        check(m==collision_mask(superset,name,labels),'Package changes collision mask for '+name)
        masks[name]=m
    controls = {u:collision_mask(superset,u,labels) for u in ('MedicMedivacDropship','ZagaraMutalisk')}
    check(controls == {'MedicMedivacDropship':0x1000000, 'ZagaraMutalisk':0x1000102},
          'Air-only or mixed native catalog control differs')
    admitted=Counter()
    for row in rows:
        # With arbitrary disable bits, any low-only base and no high enables still yields a low-only mask.
        if masks[row['unit']] & 0xff000000:
            continue
        val=bytearray.fromhex(row['value'])
        mask=bytearray.fromhex(row['mask'])
        check(len(val)==len(mask)==12 and mask[3]==0x4f and (val[3] & 0x10)==0
              and row['known_bits']==93,'Unexpected baseline descriptor')
        mask[3] |= 0x10
        row.update(mask=mask.hex(), known_bits=sum(b.bit_count() for b in mask))
        admitted[row['unit']]+=1
    output=json.dumps(rows,separators=(',',':')).encode()
    return output, dict(build=98348,native_windows=len(WINDOWS),category5_registry=providers,projection_xml=len(files),
                        modifier_xml_members=12,explicit_enable_fields=0,explicit_disable_fields=sum(counts.values()),
                        opening_slots=len(rows),opening_types=len(types),recorded_type_base_masks=masks,
                        slot_count_by_base_mask=dict(sorted(Counter(masks[x['unit']] for x in rows).items())),
                        positive_catalog_controls=controls,
                        slots_by_known_bits=dict(sorted(Counter(x['known_bits'] for x in rows).items())),
                        bit_28_zero_slots=sum(admitted.values()),ledger_sha256=sha256(output).hexdigest(),
                        condition='Unmodified recorded catalog type and live radius. Effective high enables may come only from the scanned authored modifier path. Low enables and arbitrary disables are allowed.',
                        all_live_override_writers_proven=False,first_fast_crc_verified=False)


if __name__=='__main__':
    cli=ArgumentParser(description=__doc__)
    for k in ('executable','section','projection','units','modifier_xml','gate_map','opening','baseline'):
        cli.add_argument(k,type=Path)
    cli.add_argument('--private-output',type=Path)
    args=vars(cli.parse_args())
    path=args.pop('private_output')
    data,result=generate(**args)
    if path:
        with path.open('xb') as out:
            out.write(data)
    print(json.dumps(result,indent=2))
