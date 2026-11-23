"""Combine the verified TEN game-input projections at their original physical ordinals."""

import argparse
from collections import Counter
import first_sync_game
from hashlib import sha256
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from command_interval_sequences import generate as project_intervals
from encoders import encode_game_events as named_encode
from extend_point_prefix import extend, identity
from extend_game_fragments import extra_rows
from first_sync_game import game
from full_camera_inputs import audit as project_cameras
from immediate_point_updates import generate as project_updates
from implicit_building_issues import generate as project_building_issues
from implicit_hero_issues import generate as project_hero_issues
from implicit_point_issues import generate as project_issues
from initial_point_sessions import analyze as point_sessions
from literal_chat_input import verify_chat
from match_selections import CONTROL_RECEIPT, pinned, plan as project_selections
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from point_ability_births import generate as project_point_abilities
from predict_camp_captures import SOURCE
from soundtrack_done import verified_rows as project_soundtrack
from symbiote_inputs import generate as project_symbiote
from terminal_user_leaves import leaves
from unit_click_inputs import generate as project_clicks


def payload(row):
    return {k:v for k,v in row.items() if not k.startswith("_")}


def assemble(source, gate_map, mechanics, curve, selection_controls, prefix64, abathur_control, abathur_xml,
             original_map, historical_controls, nova_xml=None, soundtrack_evidence=None, signed_announcer_map=None,
             merc_capture_map=None, merc_game_library=None):
    if signed_announcer_map is None and (merc_capture_map is not None or merc_game_library is not None):
        raise ValueError("The MercCapture route also requires the physical SignedAnnouncer parent")
    if signed_announcer_map is not None:
        from signed_game_input_map import bind, map_proof
        proof = map_proof(gate_map, signed_announcer_map, mechanics, merc_capture_map, merc_game_library)
    target = target_protocol()
    selections = {}
    sources = {}

    def add(ordinal, row, provenance):
        if ordinal in selections:
            prior = selections[ordinal]
            if identity(prior) != identity(row) or payload(prior) != payload(row):
                raise ValueError(f"Conflicting target predictions at source ordinal {ordinal}")
        else:
            selections[ordinal] = row
        sources.setdefault(ordinal, []).append(provenance)

    prefix, _ = extend(source, prefix64.read_bytes())
    for i,row in enumerate(target.decode_replay_game_events(prefix)):
        add(i, row, "opening")
    sessions, _, _ = point_sessions(source, SOURCE, 41810)
    for ordinal, row in sessions:
        add(ordinal, row, "point_session")
    pinned(selection_controls, CONTROL_RECEIPT)
    summary, data, _ = project_selections(source, gate_map, mechanics, curve,
                                         json.loads(selection_controls.read_bytes()), 98348)
    admissions = (r for r in summary["rows"] if r["admitted"])
    for record, row in zip(admissions, target.decode_replay_game_events(data), strict=True):
        add(record["game_event_ordinal"], row, "selection")
    data, _, ordinals, _ = project_cameras(source, SOURCE, 41810, gate_map)
    for (ordinal, _, _), row in zip(ordinals, target.decode_replay_game_events(data), strict=True):
        add(ordinal, row, "camera")
    data, _, notes = project_symbiote(source, abathur_control, abathur_xml)
    for record, row in zip(notes, target.decode_replay_game_events(data), strict=True):
        add(record["ordinal"], row, "symbiote_cancel_requires_selection")
    extra, _ = extra_rows(source, gate_map, original_map, historical_controls)
    for ordinal,row,label in extra:
        add(ordinal,row,label)
    departures, _ = leaves(source,SOURCE,41810)
    for ordinal,row in departures:
        add(ordinal,row,"recorded_final_departure")
    clicks, _, _ = project_clicks(source,gate_map,mechanics,curve)
    for ordinal,row in clicks.items():
        add(ordinal,row,"unit_click_within_verified_lifetime")
    point_issues, _, _ = project_issues(source, gate_map)
    for ordinal, row in point_issues.items():
        add(ordinal, row, "implicit_point_issue_conditional_flags")
    point_updates, _, _ = project_updates(source)
    for ordinal, row in point_updates.items():
        add(ordinal, row, "same_loop_point_update_conditional_on_issue")
    interval_rows, _, _ = project_intervals(source)
    for ordinal, row in interval_rows.items():
        add(ordinal, row, "command_interval_conditional_on_issue")
    catalog = Path(first_sync_game.__file__).parent / "observations/dragonshire-building-catalog-links.json"
    buildings, _, _ = project_building_issues(source, gate_map, mechanics, catalog)
    for ordinal, row in buildings.items():
        add(ordinal, row, "building_target_requires_catalog_and_lifetime")

    anchors = catalog.with_name("runtime-catalog-reference-anchors-98348.json")
    heroes, _, _ = project_hero_issues(source, gate_map, mechanics, curve, selection_controls, anchors)
    for ordinal, row in heroes.items():
        add(ordinal, row, "moving_hero_target_requires_reproduced_trajectory")
    if nova_xml is not None:
        casts, _, _ = project_point_abilities(source, abathur_xml, nova_xml)
        for ordinal, row in casts.items():
            add(ordinal, row, "tracker_corroborated_cast_conditional_flags")

    if soundtrack_evidence is not None:
        for ordinal, row in project_soundtrack(source, original_map, gate_map, soundtrack_evidence):
            if ordinal in selections:
                raise ValueError(f"Duplicate soundtrack source ordinal {ordinal}")
            add(ordinal, row, "intro_soundtrack_requires_stock_catalog_and_recorded_schedule")

    old, raw = game(source, SOURCE, 41810)
    total, missing, represented = Counter(), Counter(), Counter()
    manifest, native_rows, ordered = [], [], []
    source_end = previous = offset = 0
    first_gap = None
    for ordinal, original in enumerate(old.decode_replay_game_events(raw)):
        tick, user, kind = identity(original)
        size, rem = divmod(original["_bits"], 8)
        if rem or size < 1 or offset+size > len(raw):
            raise ValueError("Invalid source game member")
        if kind == 32:
            verify_chat(original,source_end,raw[offset:offset+size],old,target)
            add(ordinal,original,"literal_trigger_chat")
        offset += size
        total[kind] += 1
        source_end = tick
        row = selections.get(ordinal)
        if row is None:
            missing[kind] += 1
            if first_gap is None:
                first_gap = dict(ordinal=ordinal, loop=tick, kind=kind)
            continue
        if identity(row) != (tick, user, kind):
            raise ValueError("Projected input belongs to another source frame")
        tid,name = target.game_event_types[kind]
        if name != original["_event"] or name != row["_event"]:
            raise ValueError("Event identity changed")
        fields = _anonymous(payload(row), target.typeinfos, tid)
        native_rows.append(GameEvent(tick-previous, user, kind, fields))
        previous = tick
        ordered.append(row)
        manifest.append([ordinal, tick, kind, sources[ordinal]])
        represented[kind] += 1
    if offset != len(raw) or len(ordered) != len(selections):
        raise ValueError("Incomplete source scan or unconsumed projections")
    result = encode_game_events(native_rows)
    if named_encode(ordered,target) != result or not result.startswith(prefix):
        raise ValueError("Writers disagree or validated opening prefix has changed")
    if any(r.event != expected for r,expected in zip(iter_game_events(result), native_rows, strict=True)):
        raise ValueError("Combined native readback differs")
    receipt = dict(build=98348, source_events=total.total(), source_game_bytes=len(raw),
                last_source_event_loop=source_end, included=represented.total(), omitted=missing.total(),
                included_by_event_id=dict(sorted(represented.items())), omitted_by_event_id=dict(sorted(missing.items())),
                provenance_counts=dict(Counter(label for row in manifest for label in row[-1])),
                overlap_ordinals=sum(len(row[-1])>1 for row in manifest), first_omitted=first_gap,
                last_included_loop=previous, bytes=len(result), sha256=sha256(result).hexdigest(),
                full_game_member=False, target_simulation_verified=False)
    if signed_announcer_map is not None:
        label = "signed_announcer_binding" if merc_capture_map is None else "merc_capture_binding"
        receipt[label] = bind(proof, result, manifest, receipt)
    return result, manifest, receipt


if __name__=="__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source","gate_map","mechanics","curve","selection_controls","prefix64","abathur_control","abathur_xml"):
        cli.add_argument(arg,type=Path)
    cli.add_argument("--original-map",required=True,type=Path)
    cli.add_argument("--nova-xml",type=Path,help="Include birth-corroborated point casts using the pinned Nova catalog")
    cli.add_argument("--soundtrack-evidence",type=Path,help="Include conditional intro completions using the verified cross-map receipt")
    cli.add_argument("--signed-announcer-map",type=Path,help="Bind projected inputs to this actual target package using the positional GateOrder map as a checked witness")
    cli.add_argument("--merc-capture-map",type=Path,help="Bind to the concrete MercCapture derivative of the supplied SignedAnnouncer")
    cli.add_argument("--merc-game-library",type=Path,help="Pinned 98348 GameLib used to reproduce the MercCapture script")
    cli.add_argument("--historical-control",action="append",required=True,type=Path)
    cli.add_argument("--private-dir",type=Path)
    a=cli.parse_args()
    controls=[(path,sha256(path.read_bytes()).hexdigest()) for path in a.historical_control]
    data, ledger, receipt=assemble(a.source,a.gate_map,a.mechanics,a.curve,a.selection_controls,
                                   a.prefix64,a.abathur_control,a.abathur_xml,a.original_map,controls,a.nova_xml,
                                   a.soundtrack_evidence,a.signed_announcer_map,a.merc_capture_map,a.merc_game_library)
    if a.private_dir:
        a.private_dir.mkdir(exist_ok=False)
        (a.private_dir/"game-inputs.private.bin").write_bytes(data)
        (a.private_dir/"ordinals.private.json").write_text(json.dumps(ledger,separators=(",",":")),encoding="utf-8")
    print(json.dumps(receipt,indent=2))
