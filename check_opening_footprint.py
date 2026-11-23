"""Compare the two private 172-row ledgers and exercise rejection cases for bit 29."""

from argparse import ArgumentParser
import json
from pathlib import Path

from opening_unit_radii import check, pinned


BEFORE = '085de11a4512e65e649757b13670ea15e3fbe8ffc97e5577ca0a0f292280ed0a'
AFTER = 'fc02a41fdbf87bbc62cb29ec78ae11fc7476c2936a6574cfc7bbd171ab0d5d24'
SLOTS = frozenset((5,57,*range(61,66),*range(108,112),*range(165,172)))
BIT = 1 << 29


def compare(old_rows, new_rows):
    check(len(old_rows)==len(new_rows)==172, 'Opening rows missing')
    for slot,(before,after) in enumerate(zip(old_rows,new_rows,strict=True)):
        check(before['slot']==after['slot']==slot and before['known_bits']==94, 'Opening slot differs')
        old_mask, new_mask = [int.from_bytes(bytes.fromhex(r['mask']), 'little') for r in (before,after)]
        admitted = slot in SLOTS
        check(old_mask.bit_count()==94 and old_mask & BIT==0, 'Unexpected baseline mask')
        check(new_mask == (old_mask | (BIT if admitted else 0)), 'Incorrect changed mask')
        check(new_mask.bit_count()==after['known_bits']==94+admitted,'Incorrect number of known bits')
        check(dict(before,mask=after['mask'],known_bits=after['known_bits'])==after,'Unexpected row mutation')
        check(not admitted or int.from_bytes(bytes.fromhex(after['value']),'little') & BIT==0,
              'Absent footprint must project bit 29 to zero')


def verify(before, after):
    old = json.loads(pinned(before,BEFORE))
    new = json.loads(pinned(after,AFTER))
    compare(old,new)
    # A canonical input digest alone would reject any changed fixture. Test the comparator separately.
    for slot, change in ((0,{'mask':new[5]['mask'],'known_bits':95}),
                         (5,{'mask':old[5]['mask'],'known_bits':94}),
                         (5,{'value':new[0]['value']})):
        modified = list(new)
        modified[slot] = dict(new[slot],**change)
        try:
            compare(old,modified)
        except ValueError:
            continue
        raise AssertionError('Mutated fixture was accepted')
    return dict(rows=172,known_95=len(SLOTS),known_94=172-len(SLOTS),unchanged_values=172,
                falsely_added_missing_and_changed_value_rejected=3,
                prior_known_bits=sum(r['known_bits'] for r in old),known_bits=sum(r['known_bits'] for r in new),
                ledger_sha256=AFTER)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    for name in ('before','after'):
        parser.add_argument(name,type=Path)
    print(json.dumps(verify(**vars(parser.parse_args())),indent=2))
