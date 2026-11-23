"""Independently compare the collision-branch ledger to its 93-bit input."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from opening_unit_radii import check, pinned


def verify(before, after):
    a = json.loads(pinned(before, '7ed61d56f795b59a0bf154bc56ff443a36779b3b7aaddbc56bda0716f1fe36fd'))
    raw = pinned(after, '085de11a4512e65e649757b13670ea15e3fbe8ffc97e5577ca0a0f292280ed0a')
    b = json.loads(raw)
    check(len(a)==len(b)==172 and [x['slot'] for x in a]==list(range(172)), 'Unexpected slot order')
    for old,new in zip(a,b,strict=True):
        orig, result = [int.from_bytes(bytes.fromhex(r['mask']),'little') for r in (old,new)]
        check(orig ^ result == 1<<28 and result.bit_count()==94 and orig.bit_count()==93,'Unexpected mask')
        check(old['value']==new['value'] and int.from_bytes(bytes.fromhex(new['value']),'little') & (1<<28)==0,
              'Unexpected value change')
        check(dict(old,mask=new['mask'],known_bits=94)==new,'Other input fields differ')
    def flag(base,enable,disable):
        effective = (base|enable) & ~disable
        return bool(effective & 0xff000000) and not bool(effective & 0xffffff)
    # Disable masks may erase every low bit, including in a mixed ground/flying archetype.
    for base in (0,2,16,32,35):
        for enable in (0,1,0x800000,0xffffff):
            for disable in (0,base,0xffffff,0xffffffff):
                check(not flag(base,enable,disable),'Low-only case changed')
    check(flag(0x1000000,0,0) and not flag(0x1000102,0,0) and flag(0x1000102,0,0x102)
          and flag(2,0x1000000,2),'Failed air enable or disable counterexample')
    return dict(slots=len(b),added_bit=28,known_bits=94,unchanged_values=len(b),
                low_only_cases=80,air_cases=4,ledger_sha256=sha256(raw).hexdigest())


if __name__=='__main__':
    cli=ArgumentParser(description=__doc__)
    for name in ('before','after'):
        cli.add_argument(name,type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())),indent=2))
