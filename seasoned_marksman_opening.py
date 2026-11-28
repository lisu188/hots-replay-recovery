"""Project TEN Tyrande's opening Seasoned Marksman choice and award on the derived candidate map.

Original game input 1547 (loop 364, user 7, index 2) selects the historical third
tier-one talent; original tracker record 251 awards GenericTalentSeasonedMarksman
to player 8 at loop 365. The candidate package relinks only Tyrande's tier-one
column-three row to that shared 98348 talent. This tool adds the translated choice
to the combined sparse input stream and the award to the continuous tracker prefix.
Seven genuine 98348 recordings of Tyrande's stock first purchase, including the same
selector, witness the native selection-to-award frame grammar. Talent behavior and
all later simulation remain unverified.
"""

import argparse
import bisect
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_extended_spikes_map import one, pinned, require
from build_seasoned_marksman_map import HERO, SLOT, STOCK, TALENT, TYRANDE
from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import compare, first_inputs, history, load_case, stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from signed_game_input_map import digest
from verify_signed_tracker import frames

CANDIDATE = "fa349ed928b649ea203133237999e8d4202a6e13b328224619eb1399cff23d6c"
PREFIX = "94308bf7b85f9b660a4db92e9cb13b2be66beacb4de419cefae999572f16c702"
STREAM = "e2402f0360450c75909b865ff8114f0ac342c770b54175c7632b2b35d0acc9f2"
LEDGER = "092ca220b8ee28eaab792942ca22e5a83f2c1c4e54c9e101ac7382aae0763829"
CHOICE_LABEL = "seasoned_marksman_restored_selector_requires_candidate_tree"
PURE = {"camera", "literal_trigger_chat", "recorded_final_departure"}
SOURCE_PICK = (1547, 364, 7, "HeroTyrande", SLOT)
PLAYER = 8


def candidate_tree(package, tyrande):
    """Resolve Tyrande's tier-one selectors in the stock and candidate catalogs."""
    pinned(package, CANDIDATE)
    with closing(MPQArchive(package)) as archive:
        hero_data = read_member(archive, HERO)
    record, = ET.fromstring(hero_data).findall("CHero[@id='Tyrande']")
    require([row.attrib for row in record] == [{"index": str(SLOT), "Talent": TALENT}],
            "Candidate does not relink exactly the restored selector")
    rows = one(ET.fromstring(pinned(tyrande, TYRANDE)), "CHero[@id='Tyrande']").findall("TalentTreeArray")
    stock = {}
    for index in range(3):
        require(rows[index].get("Tier") == "1" and rows[index].get("Column") == str(index + 1) and not len(rows[index]),
                "Unexpected stock tier-one row")
        stock[index] = rows[index].get("Talent")
    require(stock[SLOT] == STOCK, "Unexpected stock selector")
    return stock, {**stock, SLOT: TALENT}


def witnesses(controls, stock, target):
    corroboration = []
    for file, sha in json.loads(controls.read_bytes()):
        protocol, raw, data, events = load_case(Path(file), sha, 98348)
        first = first_inputs(protocol, raw, *history(events), {"HeroTyrande": stock})
        require(first, "Control has no Tyrande first purchase")
        for player, (_, tick, _, _, selector) in sorted(first.items()):
            require(selector in stock, "Control selector outside the stock tier")
            ordinal, = compare([stat(tick + 1, player, stock[selector])], events, data, target)
            corroboration.append(dict(sha256=sha, selector=selector, award_loop=tick + 1, award_ordinal=ordinal))
    require(any(row["selector"] == SLOT for row in corroboration), "No native witness of the restored selector")
    return sorted(corroboration, key=lambda row: row["sha256"])


def join_choice(game_dir, choice, target):
    """Insert the translated choice; every later row must be independent of Tyrande's talent state."""
    keys = json.loads(pinned(game_dir / "ordinals.private.json", LEDGER))
    stream = pinned(game_dir / "game-inputs.private.bin", STREAM)
    rows = [{k: v for k, v in row.items() if k != "_bits"} for row in target.decode_replay_game_events(stream)]
    require(len(rows) == len(keys) and all((r["_gameloop"], r["_eventid"]) == (k[1], k[2]) for k, r in zip(keys, rows)),
            "Parent input ledger differs")
    require(encode_game_events(rows, target) == stream, "Parent stream does not re-encode exactly")
    ordinals = [k[0] for k in keys]
    require(ordinals == sorted(ordinals) and SOURCE_PICK[0] not in ordinals, "Restored choice overlaps the parent")
    position = bisect.bisect_left(ordinals, SOURCE_PICK[0])
    later = Counter()
    for key, row in zip(keys[position:], rows[position:]):
        labels = set(key[3])
        if labels <= PURE or ("ping_map_or_no_target" in labels and row.get("m_unit") == 0):
            later.update(labels)
        elif labels == {"talent_index_requires_target_award_state"} and row["_userid"]["m_userId"] != SOURCE_PICK[2]:
            later.update(labels)
        else:
            raise ValueError(f"Later input {key[0]} may depend on the restored talent state")
    template = rows[ordinals.index(1536)]
    require(template["_eventid"] == 110, "Unexpected talent-choice template")
    event = {**template, "_gameloop": choice["_gameloop"], "_userid": dict(choice["_userid"]), "m_index": choice["m_index"]}
    new_keys = keys[:position] + [[SOURCE_PICK[0], SOURCE_PICK[1], 110, [CHOICE_LABEL]]] + keys[position:]
    new_rows = rows[:position] + [event] + rows[position:]
    require(all(a[1] <= b[1] for a, b in zip(new_keys, new_keys[1:])), "Input clock is not monotonic")
    encoded = encode_game_events(new_rows, target)
    require([{k: v for k, v in r.items() if k != "_bits"} for r in target.decode_replay_game_events(encoded)] == new_rows,
            "Joined stream does not decode to the intended rows")
    return new_keys, encoded, dict(later)


def generate(source, package, tyrande, prefix, game_dir, controls, output):
    require(not output.exists(), "A fresh private output directory is required")
    stock, projected = candidate_tree(package, tyrande)
    src, raw, data, original = load_case(source, SOURCE, 41810)
    setup, heroes, levels = history(original)
    picks = first_inputs(src, raw, setup, heroes, levels, {"HeroTyrande": {}})
    require(list(picks.items()) == [(PLAYER, SOURCE_PICK)], "Source Tyrande choice differs")
    index, tick, uid, hero, selector = SOURCE_PICK
    source_row = list(src.decode_replay_game_events(raw))[index]
    require((source_row["_eventid"], source_row["_gameloop"], source_row["_userid"]["m_userId"], source_row["m_index"]) ==
            (110, tick, uid, selector), "Source game input differs")
    award = stat(tick + 1, PLAYER, projected[selector])
    require(compare([award], original, data, src) == [251], "Source award differs")
    require([e["_eventid"] for e in original if 355 < e["_gameloop"] <= tick + 1] == [10], "Original event interval changed")
    target = target_protocol()
    before = pinned(prefix, PREFIX)
    previous = frames(before, target)
    require(len(previous) == 272 and previous[-1][0]["_gameloop"] == 355, "Unexpected parent tracker prefix")
    projected_setup, projected_heroes, projected_levels = history(e for e, *_ in previous)
    require(projected_setup[uid][1] == PLAYER and projected_heroes[PLAYER][1] == hero and
            any(t < tick and level >= 1 for t, level in projected_levels[PLAYER]), "Target opening differs")
    corroboration = witnesses(controls, stock, target)
    keys, stream, later = join_choice(game_dir, source_row, target)
    result = before + encode_tracker_events([{**award, "_gameloop": tick + 1 - previous[-1][0]["_gameloop"]}], target)
    decoded = frames(result, target)
    require(len(decoded) == 273 and decoded[-1][0] == award and
            encode_tracker_events([e for e, *_ in decoded], target) == result, "Wrong projected prefix")
    following = original[252]
    output.mkdir()
    with (output / "TEN.prefix-through-365.private.bin").open("xb") as f:
        f.write(result)
    with (output / "game-inputs.private.bin").open("xb") as f:
        f.write(stream)
    ledger = json.dumps(keys, separators=(",", ":")).encode("ascii")
    with (output / "ordinals.private.json").open("xb") as f:
        f.write(ledger)
    return dict(candidate_sha256=CANDIDATE, source_sha256=SOURCE, current_hero_sha256=TYRANDE,
                source_input_ordinal=index, selection_loop=tick, user=uid, player=PLAYER, selector=selector,
                stock_choice=stock[selector], projected_choice=projected[selector],
                source_award_ordinal=251, target_award_ordinal=len(decoded) - 1,
                parent_prefix_sha256=PREFIX, frames=len(decoded), bytes=len(result), sha256=digest(result), last_loop=tick + 1,
                next_source_tracker_ordinal=252, next_loop=following["_gameloop"], next_source_event_id=following["_eventid"],
                parent_stream_sha256=STREAM, parent_ledger_sha256=LEDGER, game_inputs=len(keys),
                omitted_game_inputs=104257 - len(keys), stream_bytes=len(stream), stream_sha256=digest(stream),
                ledger_sha256=digest(ledger), choice_label=CHOICE_LABEL, later_rows_by_label=later,
                controls=corroboration, historic_behavior_restored=False, target_unit_allocator_verified=False,
                target_simulation_verified=False, verified_target_syncs=0)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("source", "package", "tyrande", "prefix", "game_dir", "controls", "output"):
        cli.add_argument(name, type=Path)
    print(json.dumps(generate(**vars(cli.parse_args())), indent=2))
