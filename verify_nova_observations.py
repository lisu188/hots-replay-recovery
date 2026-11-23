"""Check the frozen aggregate receipts and the key positive and counterexample observations."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


def pinned_json(path, expected):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    canonical = json.dumps(value, sort_keys=True, separators=(",",":")).encode()
    if sha256(canonical).hexdigest() != expected:
        raise ValueError("Aggregate receipt changed: " + path.name)
    return value


def verify(source, controls):
    s = pinned_json(source, "ac5dc7a236359e4eaf49a36bd9f10445ecd802fdfd1c30900ddf1f5571d8016b")
    rows = pinned_json(controls, "46753a93c640f897ce897a13cd27384bb6d37e7ab1da0253935aacc4aeff57ed")
    if len(rows) != 24 or len({r["digest"] for r in rows}) != 24 or s["recorded_utc_date"] != "2016-04-12":
        raise ValueError("Source identity or number of independent controls")
    prior = [r for r in rows if r["digest"] != s["source_sha256"]]
    if len(prior) != 23 or any(r["non_nova_378"] for r in prior):
        raise ValueError("Unexpected independent control")
    picks = defaultdict(Counter)
    for r in prior:
        for talent, counts in r["post_378_hero_motion_by_first_talent"].items():
            picks["covert" if talent == "NovaMasteryCovertOpsPinningShot" else "other"].update(counts)
    if [(c["one_loop_chords"],c["near_2_64_chords"],c["near_1_76_chords"])
            for c in (picks["other"],picks["covert"])] != [(1001,325,0),(89,42,9)]:
        raise ValueError("Independent motion controls")
    focus, = [r for r in s["link378_observed_snapshot_chords"] if r["issue_loop"] == 8412]
    if focus["tracker_birth_type"] != "HeroTyrande" or focus["after"]["nonzero_chord_rate_range"] != [1.753,1.757]:
        raise ValueError("TEN movement observation")
    return {"match_date": s["recorded_utc_date"], "original_link378_issues": 24, "independent_link378_issues": 226,
            "movement_by_first_talent": dict(picks), "exact_original_timer_recovered": False}


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source",type=Path)
    cli.add_argument("controls",type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())),indent=2))
