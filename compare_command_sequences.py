"""Count command-manager references with a unique preceding issue from the same player."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path

from first_sync_game import game
from implicit_point_issues import validate_manifest
from predict_camp_captures import SOURCE


def audit(case):
    path, digest, build = case
    protocol, raw = game(Path(path), digest, build)
    issues = defaultdict(list)
    references = []
    counts = Counter()
    for ordinal, event in enumerate(protocol.decode_replay_game_events(raw)):
        kind = event["_eventid"]
        if kind not in (27, 103, 104, 105):
            continue
        sequence = event.get("m_sequence")
        key = (event["_userid"]["m_userId"], sequence)
        if kind == 27 and sequence is not None:
            issues[key].append(ordinal)
        elif kind != 27:
            references.append((ordinal, kind, key))
            if kind == 103:
                counts[f"manager_state_{event['m_state']}"] += 1

    for ordinal, kind, key in references:
        occurrences = issues.get(key, ())
        if key[1] is None:
            result = "omitted"
        elif not occurrences:
            result = "no_issue"
        elif len(occurrences) > 1:
            result = "ambiguous"
        elif occurrences[0] > ordinal:
            result = "later_issue"
        else:
            result = "unique_earlier_issue"
        counts[f"{kind}_{result}"] += 1
    return digest, counts


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "control_manifest"):
        cli.add_argument(arg, type=Path)
    args = cli.parse_args()
    controls = json.loads(args.control_manifest.read_bytes())
    validate_manifest(controls)
    cases = [(path, digest, 98348) for digest, path in controls.items()]
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(audit, cases))
    _, source = audit((args.source, SOURCE, 41810))
    total = sum(results.values(), Counter())
    print(json.dumps(dict(source=source, target=total, control_count=len(results),
                          by_control=results), indent=2))
