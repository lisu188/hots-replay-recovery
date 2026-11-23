"""Prove which GateOrder inputs can witness a sparse projection for SignedAnnouncer."""

from contextlib import closing
from hashlib import sha256
import json

from build_gate_order_map import definition
from dragon_startup_births import predict
from hero_revive_wire import GATE_MAP
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from soundtrack_done import DRAGON, intro


SIGNED = "150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791"
SCRIPT = "MapScript.galaxy"
INTERNAL = {"(listfile)", "(attributes)"}
MODEL_ROUTINES = (
    ("bool", "gt_HookupGlobalVariables_Func"),
    ("bool", "gt_HookupJungleCreepData_Func"),
    ("bool", "gt_InitializeMapMechanic_Func"),
    ("bool", "gt_HistoricalRespawnTimes_Func"),
)
CONSUMERS = {
    "opening": "Previously verified prefix, including opening selection and recorded support inputs",
    "selection": "Opening placements and hero starts, source selection, lifetime and ownership",
    "camera": "MapInfo bounds, terrain grid and ten authored player starts",
    "point_session": "Source point-session evidence",
    "implicit_point_issue_conditional_flags": "MapInfo bounds, synchronous heightmap and source command flags",
    "same_loop_point_update_conditional_on_issue": "Source point update and preceding issue",
    "command_interval_conditional_on_issue": "Source command interval and preceding issue",
    "ping_map_or_no_target": "Authored placements or zero target and original lifetime",
    "ping_opening_hero_lifetime": "Opening hero and original lifetime",
    "talent_index_requires_target_award_state": "Target talent catalog and original award evidence",
    "talent_index_requires_earlier_unresolved_award": "Target talent catalog and preceding award",
    "unit_click_within_verified_lifetime": "Opening placement or hero, original lifetime or first Dragon activation",
    "symbiote_cancel_requires_selection": "Abathur catalog, original session and recreated selection",
    "building_target_requires_catalog_and_lifetime": "Opening building, heightmap, target catalog and original lifetime",
    "moving_hero_target_requires_reproduced_trajectory": "Opening hero, source lifetime and recreated trajectory",
    "tracker_corroborated_cast_conditional_flags": "Hero catalog, source point cast and tracker birth",
    "intro_soundtrack_requires_stock_catalog_and_recorded_schedule": "Map intro assignment, stock catalog and original completion schedule",
    "recorded_final_departure": "Source departure",
    "literal_trigger_chat": "Source physical chat frame",
}


def digest(data):
    return sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("ascii")


def members(path, expected):
    if digest(path.read_bytes()) != expected:
        raise ValueError("Wrong map for the SignedAnnouncer binding")
    with closing(MPQArchive(path)) as archive:
        listing = read_member(archive, "(listfile)").decode("ascii").splitlines()
        if len(listing) != 70 or len(set(listing)) != 70 or set(listing) & INTERNAL:
            raise ValueError("Unexpected map member inventory")
        indexes = [archive.get_hash_table_entry(name).block_table_index for name in [*listing, *INTERNAL]]
        live = {i for i, block in enumerate(archive.block_table) if block.flags & 0x80000000}
        if len(set(indexes)) != len(indexes) or live != set(indexes):
            raise ValueError("Map list differs from the live block table")
        return {name: read_member(archive, name) for name in listing}


def map_proof(witness_path, target_path, mechanics):
    witness, target = members(witness_path, GATE_MAP), members(target_path, SIGNED)
    if witness.keys() != target.keys() or {k for k in witness if witness[k] != target[k]} != {SCRIPT}:
        raise ValueError("Unexpected difference in map content")
    wx, tx = (m[SCRIPT].decode("utf-8-sig").replace("\r\n", "\n") for m in (witness, target))
    for kind, name in MODEL_ROUTINES:
        if definition(wx, kind, name) != definition(tx, kind, name):
            raise ValueError("A script routine used by the model changed: " + name)
    lib = mechanics.read_bytes()
    def startup(m):
        return predict(m["Objects"], m["Regions"], m[SCRIPT], lib)
    placements, summary = startup(target)
    if (placements, summary) != startup(witness):
        raise ValueError("Opening birth predictions differ on the two physical packages")
    intro_role = intro(target_path, SIGNED)
    if intro_role != DRAGON or intro(witness_path, GATE_MAP) != intro_role:
        raise ValueError("Opening soundtrack roles disagree")
    birth_table = [{**p, "m_unitTypeName": p["m_unitTypeName"].decode("ascii")} for p in placements]
    return dict(target_map_sha256=SIGNED, geometry_and_opening_witness_map_sha256=GATE_MAP,
                target_script_sha256=digest(target[SCRIPT]), witness_script_sha256=digest(witness[SCRIPT]),
                identical_members=len(target)-1, changed_content_members=[SCRIPT],
                equal_member_hashes_sha256=digest(canonical({k:digest(v) for k,v in target.items() if k != SCRIPT})),
                equal_script_routines=[name for _, name in MODEL_ROUTINES],
                map_mechanics_sha256=digest(lib), opening_birth_count=len(placements),
                authored_opening_units=summary["authored"], scripted_opening_units=summary["scripted"],
                opening_birth_table_sha256=digest(canonical(birth_table)), intro_soundtrack_role=intro_role)


def bind(proof, stream, ledger, receipt):
    counts = receipt["provenance_counts"]
    if not counts.keys() <= CONSUMERS.keys():
        raise ValueError("Input producer has no SignedAnnouncer dependency assessment")
    return dict(**proof, source_replay_sha256=SOURCE, input_stream_sha256=digest(stream),
                ordinal_ledger_sha256=digest(canonical(ledger)), input_count=len(ledger),
                producer_dependencies={k:CONSUMERS[k] for k in sorted(counts)},
                changed_gameplay=["first camp opening", "Dragon capture beacon reset", "opening announcer default"],
                conditions=[
                    "Input payloads and original ordinals are projected. Target trigger execution, selection, lifetimes, award state, trajectory and command acceptance remain unverified.",
                    "Opening unit tags use the ordered allocation model. Later tagged inputs require the original generation and relevant owner/lifetime to persist on the target.",
                    "Intro soundtrack completions require the recorded schedule and stock catalog. The restored announcer can change sound instances and their timing.",
                ], full_game_member=False, target_simulation_verified=False)
