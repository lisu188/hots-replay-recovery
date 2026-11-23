"""Repair selection catalog links in a private R8 camera/ping copy with its original tracker."""

import argparse
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from first_sync_selections import encode_frame
from integrate_r8_camera_pings import GAME, inventory
from match_selections import CONTROL_RECEIPT, plan, target_protocol, pinned
from mpq_reader import MPQArchive
from runtime_catalog_probe import Storm

PARENT = "152f510b0cf30bf200d58b33877de1a7ee2fa63762dc03dff3369efa9a3da740"


def repair_game(game, patches, ledger):
    p = target_protocol()
    edited = bytearray(game)
    found = offset = previous = changed = 0
    histogram = {}
    for e in p.decode_replay_game_events(game):
        count, rem = divmod(e["_bits"], 8)
        end = offset + count
        if rem or count < 1 or end > len(game):
            raise ValueError("Invalid R8 frame extent")
        if e["_eventid"] == 28:
            r = ledger["rows"][found]
            if e["_gameloop"] != r["loop"]:
                raise ValueError("R8 selection order differs")
            dst = patches.get(r["game_event_ordinal"])
            if dst:
                check = deepcopy(e)
                src = deepcopy(e)
                before = [g["m_unitLink"] for g in src["m_delta"]["m_addSubgroups"]]
                if before != [a["source_link"] for a in r["additions"]]:
                    raise ValueError("Unrecognized parent subgroup links")
                for g, a in zip(check["m_delta"]["m_addSubgroups"], r["additions"], strict=True):
                    if a["target_link"] is not None:
                        g["m_unitLink"] = a["target_link"]
                if {k: v for k, v in check.items() if k != "_bits"} != {
                    k: v for k, v in dst.items() if k != "_bits"
                }:
                    raise ValueError("R8 payload differs beyond the authenticated catalog fields")
                original = encode_frame(e, previous, p)
                replacement = encode_frame(check, previous, p)
                if original != game[offset:end] or len(replacement) != count:
                    raise ValueError("Cannot reproduce equal-length physical frame")
                if replacement != original:
                    edited[offset:end] = replacement
                    changed += 1
                    for a in r["additions"]:
                        if a["target_link"] is not None and a["target_link"] != a["source_link"]:
                            histogram[a["unit"]] = histogram.get(a["unit"], 0) + 1
            found += 1
        previous = e["_gameloop"]
        offset = end
    if offset != len(game) or found != len(ledger["rows"]) or not changed:
        raise ValueError("Incomplete repair pass")
    repaired = bytes(edited)
    ix = 0
    for left, right in zip(
        p.decode_replay_game_events(game), p.decode_replay_game_events(repaired), strict=True
    ):
        if left["_eventid"] == 28:
            row = ledger["rows"][ix]
            if row["game_event_ordinal"] in patches:
                for g, a in zip(left["m_delta"]["m_addSubgroups"], row["additions"], strict=True):
                    if a["target_link"] is not None:
                        g["m_unitLink"] = a["target_link"]
            ix += 1
        if left != right:
            raise ValueError("Different event beyond selected catalog fields")
    return repaired, dict(
        selections=found,
        changed_selection_frames=changed,
        changed_unit_links=histogram,
        changed_game_bytes=sum(a != b for a, b in zip(game, repaired)),
        original_game_sha256=sha256(game).hexdigest(),
        game_sha256=sha256(repaired).hexdigest(),
    )


def integrate(source, parent, package, mechanics, curve, controls, output, stormlib):
    pinned(parent, PARENT)
    pinned(controls, CONTROL_RECEIPT)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    rows, _, patches = plan(source, package, mechanics, curve, json.loads(controls.read_bytes()), 98285)
    storm = Storm(stormlib)
    header, before, _ = inventory(parent, storm)
    with closing(MPQArchive(source)) as arc:
        if before["replay.tracker.events"] != arc.read_file("replay.tracker.events"):
            raise ValueError("Recorded tracker differs")
    game, counts = repair_game(before[GAME], patches, rows)
    with TemporaryDirectory(dir=output.parent) as temp:
        dest = Path(temp) / "selections.StormReplay"
        dest.write_bytes(parent.read_bytes())
        storm.replace(dest, {GAME: game})
        new_header, after, _ = inventory(dest, storm)
        changed = sorted(k for k in before if before[k] != after[k])
        if (
            new_header != header
            or before.keys() != after.keys()
            or changed != ["(attributes)", GAME]
            or after[GAME] != game
        ):
            raise ValueError("Archive verification failure")
        digest = sha256(dest.read_bytes()).hexdigest()
        pinned(parent, PARENT)
        os.link(dest, output)
    return dict(
        parent_sha256=PARENT,
        output_sha256=digest,
        bytes=output.stat().st_size,
        retained_build=98285,
        unchanged_selection_tag_fields=True,
        changed_members=changed,
        physical_control_build=98285,
        destination_simulation_verified=False,
        **counts
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "parent", "package", "mechanics", "curve", "controls", "output"):
        cli.add_argument(arg, type=Path)
    cli.add_argument("--stormlib", required=True)
    a = cli.parse_args()
    print(
        json.dumps(
            integrate(
                a.source, a.parent, a.package, a.mechanics, a.curve, a.controls, a.output, a.stormlib
            ),
            indent=2,
        )
    )
