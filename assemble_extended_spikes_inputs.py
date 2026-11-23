"""Join TEN's restored first Anub'arak choice to defensible MercCapture input projections."""

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from build_extended_spikes_map import HERO, TALENTS, PARENT, require
from encoders import encode_game_events
from first_sync_game import game
from initial_talent_tracker import LEDGER, STREAM, pinned
from mpq_reader import MPQArchive
from mpq_mixed_sectors import read_member
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from signed_game_input_map import CONSUMERS, INTERNAL, canonical, digest, members
from verify_assembled_inputs import verify
from verify_extended_spikes_choice import CANDIDATE, input_row

PARENT_RECEIPT = "e061838d2125bb42c2c0b95ca88bb962b565999133e58e259a8c1ed92598fdc5"
CHOICE_RECEIPT = "dc1ff2146fd11259f7ef070ebca627982166d2cbf58ccfb4cef011a82f64e9d4"
CHOICE_LABEL = "extended_spikes_restored_selector_requires_projected_tier"
PURE = {"camera", "literal_trigger_chat", "recorded_final_departure"}
REVIEWED_LATER = {
    "opening", "selection", "point_session", "implicit_point_issue_conditional_flags",
    "same_loop_point_update_conditional_on_issue", "command_interval_conditional_on_issue",
    "ping_map_or_no_target", "ping_opening_hero_lifetime", "talent_index_requires_target_award_state",
    "talent_index_requires_earlier_unresolved_award", "unit_click_within_verified_lifetime",
    "symbiote_cancel_requires_selection", "building_target_requires_catalog_and_lifetime",
    "moving_hero_target_requires_reproduced_trajectory", "tracker_corroborated_cast_conditional_flags",
    "intro_soundtrack_requires_stock_catalog_and_recorded_schedule",
}


def bound_json(path, fingerprint):
    obj = json.loads(path.read_bytes())
    require(digest(canonical(obj)) == fingerprint, "Unexpected receipt " + path.name)
    return obj


def branch(source, parent, candidate, base, parent_report, choice_report, directory):
    require(not directory.exists(), "A fresh private output directory is required")
    parent_data = members(parent,PARENT)
    pinned(candidate,CANDIDATE)
    with closing(MPQArchive(candidate)) as archive:
        names = read_member(archive,"(listfile)").decode("ascii").splitlines()
        require(len(names) == len(set(names)) == 71 and not set(names) & INTERNAL, "Unexpected candidate listing")
        blocks = {archive.get_hash_table_entry(n).block_table_index for n in set(names) | INTERNAL}
        require(len(blocks) == 73 and blocks == {i for i,b in enumerate(archive.block_table) if b.flags & 0x80000000},
                "Unaccounted candidate block")
        new_data = {n:read_member(archive,n) for n in names}
    require(new_data.keys()-parent_data.keys() == {HERO} and not parent_data.keys()-new_data.keys() and
            {k for k in parent_data if parent_data[k] != new_data[k]} == {TALENTS}, "Unexpected map changes")
    parent_receipt = bound_json(parent_report,PARENT_RECEIPT)
    binding = parent_receipt["merc_capture_binding"]
    choice_receipt = bound_json(choice_report,CHOICE_RECEIPT)
    ten = choice_receipt["ten"]
    require(binding["target_map_sha256"] == PARENT and choice_receipt["candidate_sha256"] == CANDIDATE and
            set(binding["producer_dependencies"]) == set(CONSUMERS) == PURE | REVIEWED_LATER, "Map or producers differ")
    original = pinned(base/"game-inputs.private.bin",STREAM)
    keys = json.loads(pinned(base/"ordinals.private.json",LEDGER))
    require(len(keys) == 21585 and all(k[0] != ten["input_ordinal"] for k in keys),"Restored selector overlaps parent")
    p = target_protocol()
    keep, held, held_labels, kept_labels = {}, {}, Counter(), Counter()
    anub_held, anub_retained = Counter(), Counter()
    for record,row in zip(keys,p.decode_replay_game_events(original),strict=True):
        index,tick,kind,labels = record
        require((row["_gameloop"],row["_eventid"]) == (tick,kind) and set(labels) <= set(CONSUMERS),
                "Baseline row differs from its physical ledger")
        # No preceding talent award can affect a frame selected before this input.
        allowed = index < ten["input_ordinal"] or bool(PURE.intersection(labels))
        if "ping_map_or_no_target" in labels and row["m_unit"] == 0:
            allowed = True
        if "talent_index_requires_target_award_state" in labels:
            # The validated three Merc first purchases involve two other unchanged hero trees.
            require(index in (427,1536,6214) and row["_userid"]["m_userId"] != ten["user"] and row["m_index"] == 2,
                    "Unassessed first purchase")
            allowed = True
        if allowed:
            keep[index] = (row,labels)
            kept_labels.update(labels)
        else:
            held[index] = record
            held_labels.update(labels)
        if index > ten["input_ordinal"] and row["_userid"]["m_userId"] == ten["user"]:
            (anub_retained if allowed else anub_held).update(labels)
    selection = input_row(ten["tick"],ten["user"])
    require(digest(encode_game_events([selection],p)) == choice_receipt["private_game_sha256"],
            "Choice translator payload differs")
    keep[ten["input_ordinal"]] = (selection,[CHOICE_LABEL])
    old,raw = game(source,SOURCE,41810)
    selected, ledger = [], []
    found, absent, provenance = Counter(), Counter(), Counter()
    first_gap = None
    for ordinal,event in enumerate(old.decode_replay_game_events(raw)):
        kind,tick,uid = event["_eventid"],event["_gameloop"],event["_userid"]["m_userId"]
        if ordinal not in keep:
            absent[kind] += 1
            if first_gap is None:
                first_gap = dict(ordinal=ordinal,loop=tick,kind=kind)
            continue
        row,labels = keep[ordinal]
        require((tick,uid,kind) == (row["_gameloop"],row["_userid"]["m_userId"],row["_eventid"]),
                "Different original input ordinal")
        if ordinal == ten["input_ordinal"]:
            require(event["m_index"] == ten["selector"] == 0, "Original Anub'arak selector differs")
        selected.append(row)
        ledger.append([ordinal,tick,kind,labels])
        found[kind] += 1
        provenance.update(labels)
    wire = encode_game_events(selected,p)
    for generated,row in zip(p.decode_replay_game_events(wire),selected,strict=True):
        require({k:v for k,v in generated.items() if k!="_bits"} == {k:v for k,v in row.items() if k!="_bits"},
                "Post-join event payload changed")
    require(found.total() == len(keep) and len(keep)+len(held) == len(keys)+1, "Incomplete branch partition")
    result = dict(build=98348,source_events=found.total()+absent.total(),source_game_bytes=len(raw),
                  last_source_event_loop=tick,included=found.total(),omitted=absent.total(),
                  included_by_event_id=dict(sorted(found.items())),omitted_by_event_id=dict(sorted(absent.items())),
                  provenance_counts=dict(provenance),overlap_ordinals=sum(len(r[3])>1 for r in ledger),
                  first_omitted=first_gap,last_included_loop=ledger[-1][1],bytes=len(wire),sha256=digest(wire),
                  full_game_member=False,target_simulation_verified=False)
    result["extended_spikes_binding"] = dict(parent_sha256=PARENT,candidate_sha256=CANDIDATE,
        parent_stream_sha256=STREAM,parent_ledger_sha256=LEDGER,parent_receipt_canonical_sha256=PARENT_RECEIPT,
        translator_receipt_canonical_sha256=CHOICE_RECEIPT,parent_rows_retained=len(keep)-1,
        retained_parent_labels=dict(sorted(kept_labels.items())),parent_rows_withheld=len(held),
        withheld_parent_labels=dict(sorted(held_labels.items())),added_original_ordinal=ten["input_ordinal"],
        later_anubarak_user_retained_labels=dict(sorted(anub_retained.items())),
        later_anubarak_user_withheld_labels=dict(sorted(anub_held.items())),
        ledger_sha256=digest(canonical(ledger)),held_ledger_sha256=digest(canonical(list(held.values()))),
        condition="Historic selector and ordinary tier-one acceptance on the separate catalog candidate. Later cameras, zero-target pings, source chat/departures and three separately evidenced first choices retain their original conditions.")
    # Verify the final wire and original join again with the independent native decoder before publication.
    with TemporaryDirectory(dir=directory.parent) as temp:
        pending = Path(temp)/"inputs"
        pending.mkdir()
        (pending/"game-inputs.private.bin").write_bytes(wire)
        (pending/"ordinals.private.json").write_bytes(canonical(ledger))
        (pending/"withheld-ordinals.private.json").write_bytes(canonical(list(held.values())))
        result["independent_join"] = verify(source,pending,result)
        pending.rename(directory)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source","parent","candidate","base","parent_report","choice_report","directory"):
        cli.add_argument(name,type=Path)
    print(json.dumps(branch(**vars(cli.parse_args())),indent=2))
