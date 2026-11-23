"""Join explicit point casts and symbolic historical command sessions to independent same-loop unit births."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events as named_encode
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from smartcam_tags import R8

SUMMONS = {
    "Abathur": "AbathurToxicNest",
    "Nova": "NovaHoloClone",
    "Deckard": "DeckardHealingPotion",
    "Fenix": "FenixPlasmaCutterLaserUnit",
}
PROTOCOL = {
    41810: "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd",
    66488: "c2c264dbe4d1ba21e5c4d1702f17b48477482217951b51ebd1984174130d1b90",
    98348: "e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84",
}
TARGET = {"Abathur": 154, "Nova": 523}
LEGACY = {"Abathur": 173, "Nova": 244}
FLAG = 0x2100100
COHORT = "d5da568f0448899e5c80ef67e831dc9f38a26052eded9846db6d088de4c39b97"


def projected_issue(e, hero, unit):
    if (
        hero not in TARGET
        or unit != SUMMONS[hero]
        or e["_eventid"] != 27
        or e["m_cmdFlags"] != 0x100
        or e["m_abil"] != {"m_abilLink": LEGACY[hero], "m_abilCmdIndex": 0, "m_abilCmdData": None}
        or set(e["m_data"]) != {"TargetPoint"}
        or e["m_otherUnit"] is not None
        or e["m_unitGroup"] is not None
        or e.get("m_vector") is not None
    ):
        return None
    return {
        **e,
        "m_abil": {**e["m_abil"], "m_abilLink": TARGET[hero]},
        "m_cmdFlags": FLAG,
        "m_vector": None,
    }


def catalog(paths):
    spec = (
        (
            "AbathurToxicNest",
            "AbathurToxicNestInitialSet",
            "ToxicNestCreateUnit",
            "AbathurToxicNest",
            "b2ecee56c24e3a6e62c904f066f858dd5fb9fa144c2e17af423320efaf9c69e1",
        ),
        (
            "NovaHoloDecoy",
            "NovaHoloDecoyInitialSet",
            "NovaHoloCloneCreateUnit",
            "NovaHoloClone",
            "721086138a01ff65659616556ea617c85f968d8bd28ec888fa6397bde0ce113a",
        ),
    )
    for path, (ability, initial, create, unit, digest) in zip(paths, spec, strict=True):
        data = path.read_bytes()
        if sha256(data).hexdigest() != digest:
            raise ValueError("Unexpected installed catalog XML")
        root = ElementTree.fromstring(data)
        if (
            root.find(f"./CAbilEffectTarget[@id='{ability}']/Effect").get("value") != initial
            or root.find(f"./CEffectSet[@id='{initial}']/EffectArray[@value='{create}']") is None
            or root.find(f"./CEffectCreateUnit[@id='{create}']/WhichLocation").get("Value") != "TargetPoint"
            or root.find(f"./CEffectCreateUnit[@id='{create}']/SpawnUnit").get("value") != unit
        ):
            raise ValueError("Unexpected ability / effect / initial targeted unit path")


def scan(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    p = load_protocol(96477 if build == 98348 else build)
    if sha256(Path(p.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != PROTOCOL[build]:
        raise ValueError("Unexpected named protocol")
    with closing(MPQArchive(path)) as a:
        h = p.decode_replay_header(a.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Replay build mismatch")
        slots = p.decode_replay_initdata(a.read_file("replay.initData"))["m_syncLobbyState"][
            "m_lobbyState"
        ]["m_slots"]
        actors = {
            s["m_userId"]: (i, s["m_hero"].decode())
            for i, s in enumerate(slots, 1)
            if s.get("m_hero")
            and s["m_control"] == 2
            and not s["m_observe"]
            and s.get("m_userId") is not None
            and s["m_hero"].decode() in SUMMONS
        }
        tracker = list(p.decode_replay_tracker_events(a.read_file("replay.tracker.events")))
        raw = a.read_file("replay.game.events")
    slot_to_hero = dict(actors.values())
    births = defaultdict(list)
    for e in tracker:
        slot = e.get("m_controlPlayerId")
        if e["_eventid"] != 1 or slot not in slot_to_hero:
            continue
        unit = e["m_unitTypeName"].decode()
        hero = slot_to_hero[slot]
        if unit == SUMMONS[hero] or (hero == "Nova" and unit == "NovaHoloCloneCloaked"):
            births[slot, e["_gameloop"], e["m_x"], e["m_y"]].append(unit)
    command_rows = defaultdict(list)
    issues = defaultdict(list)
    prev = offset = 0
    for i, e in enumerate(p.decode_replay_game_events(raw)):
        t = e["_gameloop"]
        user = e["_userid"]["m_userId"]
        kind = e["_eventid"]
        end = offset + e["_bits"] // 8
        if e["_bits"] % 8 or end <= offset or end > len(raw) or t < prev:
            raise ValueError("Invalid frame boundaries")
        if user in actors and kind in (25, 27, 103, 104, 105):
            command_rows[user].append((i, e, prev, raw[offset:end]))
            if kind == 27:
                issues[user, e["m_sequence"]].append(i)
        prev, offset = t, end
    if offset != len(raw):
        raise ValueError("Incomplete game member")
    hits = defaultdict(list)
    symbolic_offsets = Counter()
    explicit_cell_casts = defaultdict(list)
    for user, rows in command_rows.items():
        slot, hero = actors[user]
        for j, (i, e, prev, physical) in enumerate(rows):
            kind = e["_eventid"]
            point = e["m_data"].get("TargetPoint") if kind == 27 else e["m_target"] if kind == 104 else None
            if point is None:
                continue
            key = slot, e["_gameloop"], point["x"] // 4096, point["y"] // 4096
            if (
                kind == 27
                and e["m_abil"]
                and hero == "Abathur"
                and e["m_abil"]["m_abilLink"] == {41810: 173, 98348: 154}.get(build)
            ):
                explicit_cell_casts[slot, key[2], key[3]].append(key[1])
            if kind == 104 and hero == "Abathur" and j + 1 < len(rows):
                manager = rows[j + 1][1]
                seq = e["m_sequence"]
                if (
                    seq is not None
                    and (user, seq) not in issues
                    and manager["_eventid"] == 103
                    and manager["_gameloop"] == key[1]
                    and manager["m_state"] == 1
                    and manager["m_sequence"] == seq
                ):
                    for delta in (-16, -1, 0, 1, 16):
                        if births.get((slot, key[1] + delta, key[2], key[3])) == ["AbathurToxicNest"]:
                            symbolic_offsets[str(delta)] += 1
            if key in births:
                hits[key].append((rows[j], rows[j + 1] if j + 1 < len(rows) else None))
    accepted = {}
    evidence = {}
    stats = Counter()
    shapes = Counter()
    hidden = []
    recent_alternatives = 0
    for key, units in births.items():
        slot, tick, x, y = key
        hero = slot_to_hero[slot]
        if len(units) != 1 or len(hits[key]) != 1:
            stats[f"{hero}/no_unique_input"] += len(units)
            continue
        (unit,) = units
        (i, e, prev, physical), following = hits[key][0]
        kind = e["_eventid"]
        user = e["_userid"]["m_userId"]
        seq = e["m_sequence"]
        if kind == 104:
            if (
                seq is not None
                and not issues.get((user, seq))
                and following
                and following[1]["_eventid"] == 103
                and following[1]["m_sequence"] == seq
                and following[1]["_gameloop"] == tick
            ):
                state = following[1]["m_state"]
                stats[f"{unit}/never_issued_state{state}"] += 1
                hidden.append((i, following[0], user, seq, tick, unit, x, y))
                if hero == "Abathur" and any(0 < tick - t <= 32 for t in explicit_cell_casts[slot, x, y]):
                    recent_alternatives += 1
                evidence[i] = (e, prev, physical)
                evidence[following[0]] = following[1:]
            else:
                stats[f"{unit}/other_update"] += 1
            continue
        if e["m_abil"] is None:
            stats[f"{unit}/implicit_issue"] += 1
            continue
        link = e["m_abil"]["m_abilLink"]
        flag = e["m_cmdFlags"]
        layout = (
            e["m_abil"]["m_abilCmdIndex"],
            e["m_abil"]["m_abilCmdData"],
            e["m_otherUnit"],
            e["m_unitGroup"],
            e.get("m_vector"),
        )
        if layout != (0, None, None, None, None):
            stats[f"{unit}/other_explicit_layout"] += 1
            continue
        stats[f"{unit}/explicit_issue"] += 1
        shapes[f"{unit}/{link}/{hex(flag)}"] += 1
        evidence[i] = (e, prev, physical)
        if digest == SOURCE:
            projected = projected_issue(e, hero, unit)
            if projected is not None:
                accepted[i] = projected
    # Check source frames including both symbolic observations and each anchored physical issue.
    elapsed = 0
    enc = []
    physical = bytearray()
    for _, (e, prev, frame) in sorted(evidence.items()):
        elapsed += e["_gameloop"] - prev
        enc.append({**e, "_gameloop": elapsed})
        physical.extend(frame)
    if named_encode(enc, p) != physical:
        raise ValueError("Anchored original frame bytes differ")
    if build == 98348:
        tp = target_protocol()
        native = []
        for _, (e, prev, _) in sorted(evidence.items()):
            tid = tp.game_event_types[e["_eventid"]][0]
            payload = {k: e[k] for k, _, _ in tp.typeinfos[tid][1][0]}
            native.append(
                GameEvent(
                    e["_gameloop"] - prev,
                    e["_userid"]["m_userId"],
                    e["_eventid"],
                    _anonymous(payload, tp.typeinfos, tid),
                )
            )
        if encode_game_events(native) != physical:
            raise ValueError("Native target caster frame bytes differ")
    return (
        dict(sorted(accepted.items())),
        sorted(hidden),
        dict(
            replay_sha256=digest,
            build=build,
            heroes=sorted(set(slot_to_hero.values())),
            births=sum(map(len, births.values())),
            counts=dict(sorted(stats.items())),
            anchored_explicit_shapes=dict(sorted(shapes.items())),
            unissued_abathur_state1_shifted_birth_tests={
                str(k): symbolic_offsets[str(k)] for k in (-16, -1, 0, 1, 16)
            },
            hidden_nests_with_earlier_same_cell_explicit_cast_within_32_loops=recent_alternatives,
            enclosing_frames=len(enc),
            enclosing_bytes=len(physical),
            enclosing_sha256=sha256(physical).hexdigest(),
        ),
    )


def generate(source, abathur_catalog, nova_catalog):
    """Return conditional explicit ID27 projections by source ordinal, sparse bytes and aggregate evidence."""
    catalog((abathur_catalog, nova_catalog))
    rows, hidden, src = scan(source, SOURCE, 41810)
    target = target_protocol()
    sparse = named_encode(list(rows.values()), target)
    decoded = list(target.decode_replay_game_events(sparse))
    keys = (
        "_eventid",
        "_gameloop",
        "_userid",
        "m_abil",
        "m_cmdFlags",
        "m_data",
        "m_sequence",
        "m_vector",
        "m_otherUnit",
        "m_unitGroup",
    )
    if (
        len(rows) != 51
        or len(hidden) != 62
        or [tuple(e[k] for k in keys) for e in decoded]
        != [tuple(e[k] for k in keys) for e in rows.values()]
        or encode_game_events([x.event for x in iter_game_events(sparse)]) != sparse
    ):
        raise ValueError("Target projection diverges")
    return (
        rows,
        sparse,
        dict(
            source=src,
            emitted=len(rows),
            sparse_bytes=len(sparse),
            sparse_sha256=sha256(sparse).hexdigest(),
            ordinal_sha256=sha256(json.dumps(list(rows), separators=(",", ":")).encode()).hexdigest(),
            symbolic_effects=len(hidden),
            added_unrecorded_issues=0,
            flag_mapping_conditional=True,
            target_simulation_verified=False,
        ),
    )


def control(case):
    return scan(*case)[2]


def compare_r8(path, rows):
    if sha256(path.read_bytes()).hexdigest() != R8:
        raise ValueError("Unexpected retained R8 archive")
    p = target_protocol()
    with closing(MPQArchive(path)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (98285,) * 3:
            raise ValueError("Unexpected R8 build")
        game = arc.read_file("replay.game.events")
    counts = Counter()
    for ordinal, e in enumerate(p.decode_replay_game_events(game)):
        if ordinal not in rows:
            continue
        projected = rows[ordinal]
        if any(
            e[k] != projected[k]
            for k in (
                "_gameloop",
                "_userid",
                "_eventid",
                "m_data",
                "m_sequence",
                "m_otherUnit",
                "m_unitGroup",
                "m_vector",
            )
        ):
            raise ValueError("R8 timing, identity or point differs")
        counts["same_context"] += 1
        counts["matching_projected_ability"] += e["m_abil"] == projected["m_abil"]
        counts["matching_projected_flags"] += e["m_cmdFlags"] == projected["m_cmdFlags"]
    if counts["same_context"] != len(rows):
        raise ValueError("R8 lacks a projected ordinal")
    return dict(build=98285, replay_sha256=R8, **counts)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("source", "abathur_catalog", "nova_catalog"):
        p.add_argument(k, type=Path)
    p.add_argument("--controls", type=Path)
    p.add_argument("--jobs", type=int, default=2, choices=range(1, 5))
    p.add_argument("--private-output", type=Path)
    p.add_argument("--private-ordinals", type=Path)
    p.add_argument("--private-symbolic", type=Path)
    p.add_argument("--retained-r8", type=Path)
    a = p.parse_args()
    rows, raw, report = generate(a.source, a.abathur_catalog, a.nova_catalog)
    if a.retained_r8:
        report["retained_r8"] = compare_r8(a.retained_r8, rows)
    if a.controls:
        refs = json.loads(a.controls.read_bytes())
        if len(refs) != 48 or sha256(" ".join(sorted(refs)).encode()).hexdigest() != COHORT:
            raise ValueError("Unexpected 23 historical, one intermediate and 24 target control set")
        with ProcessPoolExecutor(a.jobs) as pool:
            report["controls"] = list(
                pool.map(control, [(Path(v["path"]), h, v["build"]) for h, v in sorted(refs.items())])
            )
        cohorts = defaultdict(list)
        for r in report["controls"]:
            cohorts[r["build"]].append(r)
        summary = {}
        for b, count in {41810: 23, 66488: 1, 98348: 24}.items():
            if len(cohorts[b]) != count:
                raise ValueError("Incomplete build cohort")
            summary[str(b)] = {
                name: dict(sum((Counter(c[name]) for c in cohorts[b]), Counter()))
                for name in (
                    "counts",
                    "anchored_explicit_shapes",
                    "unissued_abathur_state1_shifted_birth_tests",
                )
            }
        if summary["98348"]["anchored_explicit_shapes"] != {
            "AbathurToxicNest/154/0x2100100": 62,
            "NovaHoloClone/523/0x2100100": 124,
        }:
            raise ValueError("Ambiguous target same-loop ability or flags")
        report["heldout_by_build"] = summary
    for path, data in [
        (a.private_output, raw),
        (a.private_ordinals, json.dumps(list(rows), separators=(",", ":")).encode()),
    ]:
        if path:
            with path.open("xb") as out:
                out.write(data)
    if a.private_symbolic:
        with a.private_symbolic.open("x", encoding="utf8") as out:
            json.dump(scan(a.source, SOURCE, 41810)[1], out, separators=(",", ":"))
    print(json.dumps(report, indent=2))
