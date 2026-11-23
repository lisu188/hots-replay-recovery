"""Test whether gate death order could produce wave slot order with prior completed drains."""

import argparse
from itertools import combinations
import json
from pathlib import Path

from unit_generation_evidence import audit
from unit_slot_pool import UnitSlotPool


def forbidden(ranks):
    """Return the first completed 132 or 213 pattern, including its stream ordinals."""
    seen = []
    for k, c in enumerate(ranks):
        if c is None:
            continue
        if c < 0 or any(a == c for _, a in seen):
            raise ValueError("Invalid or repeated first-reuse rank")
        for (i, a), (j, b) in combinations(seen, 2):
            if a < c < b or b < a < c:
                return dict(wave_ordinals=[i,j,k], release_ranks=[a,b,c])
        seen.append((k,c))
    return None


def verify_model():
    """Exhaust actual five-slot drain partitions and every rank subsequence."""
    n = 5
    counts = 0
    for boundaries in range(1 << (n-1)):
        pool = UnitSlotPool()
        initial = [pool.allocate() for _ in range(n)]
        for j, tag in enumerate(initial):
            pool.retire(tag)
            if j == n - 1 or boundaries & (1 << j):
                pool.drain()
        recovered = [pool.allocate() for _ in range(n)]
        if any(g != 2 for _,g in recovered):
            raise ValueError("Unexpected generation in drain test")
        for m in range(n+1):
            for chosen in combinations([i for i,_ in recovered],m):
                if forbidden(chosen) is not None:
                    raise ValueError("Rejected a physical-model subsequence")
                counts += 1
    return dict(slots=n, partitions=1 << (n-1), subsequences=counts)


def check(case):
    ranks = case["first_wave_released_slot_ranks"]
    return dict(build=case["build"], sha256=case["sha256"],
                eligible_generation_two_wave_units=sum(x is not None for x in ranks),
                first_forbidden_subsequence=forbidden(ranks))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--case", action="append", required=True, nargs=3, metavar=("REPLAY","SHA256","BUILD"))
    args = cli.parse_args()
    rows = [check(audit(Path(p),h,int(b))) for p,h,b in args.case]
    print(json.dumps(dict(model=verify_model(),cases=rows),indent=2))
