"""Project the known bits of each loop-zero spatial descriptor on the unmodified live-radius branch."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from hero_revive_wire import GATE_MAP
from predict_camp_captures import SOURCE
from unit_spatial_descriptor import LAYOUT, U32, append_handle, small_handle
from opening_spatial_fields import measure

RADII_SHA = "f48a3b52add7c0e2ce34104727b248a60b222ebbb482537eaa0cbe958f67228d"


def project(rows, radius_file):
    data = radius_file.read_bytes().replace(b"\r\n",b"\n")
    if sha256(data).hexdigest() != RADII_SHA:
        raise ValueError("Unexpected resolved opening catalog")
    catalog = json.loads(data)
    if (catalog["map_sha256"] != GATE_MAP or catalog["opening_slots"] != len(rows) or
            [r["index"] for r in rows] != list(range(len(rows)))):
        raise ValueError("Opening map or slot order differs")
    conditioned, cell_occupancy = [], Counter()
    large_count = 0
    for row in rows:
        entry = catalog["by_unit"][row["unit"]]
        if row["index"] not in entry["slots"]:
            raise ValueError("Slot disagrees with the catalog report")
        radius = entry["radius_fixed4096"]
        if not isinstance(radius,int) or not 0 <= radius < (1 << 31)-1023:
            raise ValueError("Unsupported live map radius")
        mask = LAYOUT.pack(row["low24_mask"] | 0x0f000000, 65535, 65535, U32)
        key = row["low24"] | ((((radius+1023)//1024) & 15) << 24)
        cell = row["cell_x"], row["cell_y"]
        descriptor_value = LAYOUT.pack(key,*cell,radius)
        if radius > 0x3c00:
            hypothetical = append_handle(large_count, deferred=False)
            large_count += 1
        else:
            depth, occupied = divmod(cell_occupancy[cell],15)
            hypothetical = small_handle(*cell,depth,occupied)
            cell_occupancy[cell] += 1
        conditioned.append(dict(slot=row["index"],unit=row["unit"],value=descriptor_value.hex(),mask=mask.hex(),
                                known_bits=sum(b.bit_count() for b in mask),
                                hypothetical_handle_in_empty_grid=hypothetical))
    return conditioned, dict(opening_slots=len(rows), live_radius_bits_histogram=dict(Counter(r["known_bits"] for r in conditioned)),
                             radius_above_small_threshold=large_count, radius_at_or_below_small_threshold=len(rows)-large_count,
                             distinct_occupied_small_cells_in_model=len(cell_occupancy),
                             largest_small_cell_population_in_model=max(cell_occupancy.values()),
                             hypothesized_empty_grid_insertion_order_verified=False, native_fast_crc_verified=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("source","gate_map","mechanics","radii"):
        parser.add_argument(field,type=Path)
    parser.add_argument("--private-output",type=Path)
    args = parser.parse_args()
    _, rows = measure(args.source,SOURCE,41810,args.gate_map,args.mechanics)
    conditioned, report = project(rows,args.radii)
    encoded = json.dumps(conditioned,separators=(",",":")).encode()
    if args.private_output:
        with args.private_output.open("xb") as output:
            output.write(encoded)
    print(json.dumps(dict(**report,ledger_sha256=sha256(encoded).hexdigest()),indent=2))
