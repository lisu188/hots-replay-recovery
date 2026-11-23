"""Check an actual SignedAnnouncer binding, the original ordinal join and the all-stage GateOrder reference."""

import argparse
import json
from pathlib import Path

from first_sync_game import game
from predict_camp_captures import SOURCE
from signed_game_input_map import bind, digest, map_proof
from verify_assembled_inputs import verify


REFERENCE = {
    "game-inputs.private.bin": "d5722b8a4e8e794d6321abe49a7d4cdf825b793fc259e3b9c94fbf2d9c814cfd",
    "ordinals.private.json": "8493263af8a2292db62fdec6e8f956534c60727c3f0e0caceea3a302c8355671",
}


def verify_totals(receipt, joined, ledger, source_bytes, final_source_loop):
    included = joined["independently_joined_inputs"]
    omitted = joined["unrepresented"]
    values = dict(build=98348, source_game_bytes=source_bytes, source_events=included+omitted,
                  included=included, omitted=omitted, last_source_event_loop=final_source_loop,
                  overlap_ordinals=sum(len(row[3])>1 for row in ledger))
    if any(type(receipt.get(key)) is not int or receipt[key]!=expected for key,expected in values.items()):
        raise ValueError("Top-level receipt summary disagrees with the physical source and ordinal join")


def check(source, gate_map, target_map, mechanics, directory, receipt, reference=None):
    proof = map_proof(gate_map, target_map, mechanics)
    data = (directory / "game-inputs.private.bin").read_bytes()
    raw_ledger = (directory / "ordinals.private.json").read_bytes()
    ledger = json.loads(raw_ledger)
    binding = bind(proof, data, ledger, receipt)
    if (receipt.get("signed_announcer_binding") != binding
            or digest(raw_ledger) != binding["ordinal_ledger_sha256"]
            or receipt["included"] != len(ledger) or receipt["sha256"] != digest(data)
            or receipt["target_simulation_verified"] is not False or receipt["full_game_member"] is not False):
        raise ValueError("Public binding disagrees with the physical maps, private stream or original ordinals")
    report = verify(source, directory, receipt)
    old, original_bytes = game(source, SOURCE, 41810)
    last_loop = max(r["_gameloop"] for r in old.decode_replay_game_events(original_bytes))
    verify_totals(receipt, report, ledger, len(original_bytes), last_loop)
    if reference is not None:
        for name, expected in REFERENCE.items():
            prior = (reference / name).read_bytes()
            if digest(prior) != expected or prior != (directory / name).read_bytes():
                raise ValueError("All-stage output differs from the pinned GateOrder reference: " + name)
        report["byte_identical_gateorder_stream_and_ledger"] = True
    return {**report, "target_map_sha256": binding["target_map_sha256"],
            "input_stream_sha256": digest(data), "ordinal_ledger_sha256": digest(raw_ledger)}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "gate_map", "target_map", "mechanics", "directory", "receipt"):
        cli.add_argument(arg, type=Path)
    cli.add_argument("--all-stage-gateorder-reference", type=Path,
                     help="Compare both private files against the pinned prior run with all optional producers enabled")
    a = cli.parse_args()
    report = check(a.source, a.gate_map, a.target_map, a.mechanics, a.directory,
                   json.loads(a.receipt.read_bytes()), a.all_stage_gateorder_reference)
    print(json.dumps(report, indent=2))
