"""Check the emitted camp callback, registration and recorded opening flag transfers offline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import subprocess
from tempfile import TemporaryDirectory

from camp_owner_wire import (
    FIELDS,
    OWNER,
    encode_sparse,
    frame_bytes,
    read_tracker,
    target_protocol,
)
from dragon_startup_births import predict
from first_camp_event_order import layout
from predict_camp_captures import CONTROLS, SOURCE
from verify_gate_order_map import function, member

PARENT = "bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008"
CANDIDATE = "5c241e8f9f316909ea237e5dd9f1c4d4ec2e7ea3224d383c596588c7eaf1b9ae"
MANIFEST = "87b44ff3f91d9058f5001f926129a04d225f8a11fa05b99e1571362539ec3b7b"
TIMER = "libMapM_gt_JungleCreepCampRespawnTimerExpires"
TABLE = "libMapM_gv_jungleCreepCamps"
OPEN = "gf_OpenHistoricalCamp"
STOCK = "libMapM_gf_JungleInitializeCreepCamp"
SCHEDULE = "gf_ScheduleHistoricalCampOpening"
CALLBACK = "gt_HistoricalCampBirthTimer_Func"
FLAGS = [477, 479, 478, 480, 476]


def hash_bytes(blob):
    return sha256(blob).hexdigest()


def libraries(manifest):
    assert hash_bytes(manifest.read_bytes()) == MANIFEST
    sources = {}
    for row in json.loads(manifest.read_bytes())["members"]:
        data = (manifest.parent / row["saved_name"]).read_bytes()
        assert len(data) == row["bytes"] and hash_bytes(data) == row["sha256"]
        sources[row["saved_name"]] = data.decode("utf-8-sig").replace("\r\n", "\n")
    return sources


def verify_source(parent, candidate, manifest):
    assert hash_bytes(parent.read_bytes()) == PARENT
    assert hash_bytes(candidate.read_bytes()) == CANDIDATE
    sources = libraries(manifest)
    archive_script = (
        lambda path: member(path, "MapScript.galaxy")
        .decode("ascii")
        .replace("\r\n", "\n")
    )
    old, new = archive_script(parent), archive_script(candidate)
    stock = sources["mapmechanicslib.galaxy"]
    names = [
        "gf_RegisterHistoricalCampBirthTimer",
        "gf_HistoricalCampInitTriggers",
        "gf_HistoricalCampInitLib",
    ]
    bindings = [
        (names[0], TIMER + "_Init"),
        (names[1], "libMapM_InitTriggers"),
        (names[2], "libMapM_InitLib"),
    ]
    for custom, original in bindings:
        restored = function(new, custom)
        for left, right in [*bindings, (CALLBACK, TIMER + "_Func")]:
            restored = restored.replace(left, right)
        assert restored == function(stock, original)
        assert sum(s.count(original + "();") for s in [old, *sources.values()]) == 1
    gate = "gt_HistoricalGatesOpen_Func"
    # Removing the complete inserted helper block and the two call-site substitutions
    # must recover every character of the pinned parent.
    begin = new.index("bool gv_HistoricalCampOpeningPending = false;")
    end = new.index("bool " + gate + " (", begin)
    reduced = new[:begin] + new[end:]
    assert (
        reduced.replace("    " + SCHEDULE + "();\n", "").replace(
            names[2] + "();", "libMapM_InitLib();"
        )
        == old
    )
    assert new.count(SCHEDULE + "();") == new.count(names[2] + "();") == 1
    assert (
        "TriggerExecute(libMapM_gt_StartJungleCampTimers, true, false);\n    "
        + SCHEDULE
        + "();"
        in function(new, gate)
    )
    initialize = function(stock, "libMapM_gt_InitializeJungleCamps_Func")
    assert initialize.index("TriggerAddEventTimer(" + TIMER) < initialize.index(
        STOCK + "(lv_camp);"
    )
    assert "if (!((libGame_gv_gameStarted == false)))" in function(new, gate)
    assert "libGame_gv_gameStarted = true;" in function(new, gate)
    original, emitted = function(stock, STOCK), function(new, OPEN)
    (lookup,) = [
        line for line in original.splitlines() if 'UnitGroup("LootBannerSconce"' in line
    ]
    (banner,) = [
        line
        for line in original.splitlines()
        if "libMapM_gf_JungleDropLootBannerinMercCamp(" in line
    ]
    owner = f"    UnitSetOwner({TABLE}[lp_camp].lv_campOwnershipFlagUnit, libCore_gv_cOMPUTER_Hostile, true);"
    expected = (
        original.replace(STOCK + " (", OPEN + " (")
        .replace(
            lookup,
            f"    {TABLE}[lp_camp].lv_campOwnershipFlagUnit = gf_HistoricalCampFlag(lp_camp);",
        )
        .replace(banner, f"    {TABLE}[lp_camp].lv_stateIsEnabled = true;")
        .replace(
            "    lv_iconUnit = UnitLastCreated();",
            "    lv_iconUnit = UnitLastCreated();\n" + owner,
        )
    )
    assert emitted == expected and emitted.count(owner) == 1
    assert (
        emitted.index('1, "JungleCampIconUnitTeamColor"')
        < emitted.index(owner)
        < emitted.index(".lv_campIconUnit = lv_iconUnit;")
    )
    respawn = function(stock, "auto_libMapM_gf_JungleRespawnCreepsForCamp_TriggerFunc")
    assert (
        respawn.index("Wait(0.125, c_timeGame);")
        < respawn.index("lv_i = 1;")
        < respawn.index("lv_defenderUnitTypes[lv_i]")
    )
    assert (
        "lv_mapDataDefenderSpawnPoints[lv_i]" in respawn
        and "libCore_gv_cOMPUTER_Hostile" in respawn
    )
    assert (
        "const fixed libMapM_gv_bALJungleBirthDelay = 3.0;"
        in sources["mapmechanicslib_h.galaxy"]
    )
    return [function(new, n) for n in ("gf_HistoricalCampFlag", SCHEDULE, CALLBACK)]


def startup_and_flags(candidate, library, replay_paths):
    predicted, _ = predict(
        *(member(candidate, key) for key in ("Objects", "Regions", "MapScript.galaxy")),
        library.read_bytes(),
    )
    flag_positions = {
        xy: (row["m_unitTagIndex"], row["m_unitTagRecycle"])
        for row in predicted
        if row["m_unitTypeName"] == b"CampOwnershipFlag"
        for xy in [(row["m_x"], row["m_y"])]
    }
    camps = layout(candidate)
    assert len(predicted) == 172 and len(flag_positions) == 5
    assert [flag[0] for _, flag, _ in camps] == FLAGS
    assert all(
        row["m_unitTypeName"] != b"JungleCampIconUnitTeamColor" for row in predicted
    )
    # The checked map schedules these five transfers at gate +120s. The four source
    # fixtures all open their gates at loop 610. No physical transfer supplies a tag.
    rows = [
        dict(
            _gameloop=610 + 120 * 16,
            _eventid=3,
            _event=OWNER,
            m_unitTagIndex=idx,
            m_unitTagRecycle=gen,
            m_controlPlayerId=15,
            m_upkeepPlayerId=15,
        )
        for _, flag, _ in camps
        for idx, gen in [flag_positions[flag[1]]]
    ]
    sparse, _ = encode_sparse(rows)
    tags = {(e["m_unitTagIndex"], e["m_unitTagRecycle"]) for e in rows}
    fixtures = {hash_bytes(path.read_bytes()): path for path in replay_paths}
    assert set(fixtures) == {SOURCE, *CONTROLS} and len(replay_paths) == len(fixtures)
    matches = []
    for digest, path in sorted(fixtures.items()):
        p, wire, _ = read_tracker(path, 41810)
        events = list(p.decode_replay_tracker_events(wire))
        births = [e for e in events if e["_eventid"] == 1 and e["_gameloop"] == 0]
        assert [{k: e[k] for k in predicted[0]} for e in births] == predicted
        assert [
            e["_gameloop"] for e in events if e.get("m_eventName") == b"GatesOpen"
        ] == [610]
        offset = previous = i = 0
        for event in events:
            assert event["_bits"] % 8 == 0
            size = event["_bits"] // 8
            tag = (event.get("m_unitTagIndex"), event.get("m_unitTagRecycle"))
            if tag in tags and 0 < event["_gameloop"] <= 2530:
                assert event["_eventid"] not in (1, 2, 4)
                if event["_eventid"] == 3:
                    assert i < 5 and event["_gameloop"] == rows[i]["_gameloop"]
                    assert all(event[k] == rows[i][k] for k in FIELDS)
                    assert (
                        frame_bytes(rows[i], previous, target_protocol())
                        == wire[offset : offset + size]
                    )
                    i += 1
            offset += size
            previous = event["_gameloop"]
        assert offset == len(wire) and i == 5
        matches.append(
            dict(
                replay_sha256=digest,
                verified_startup_births=len(births),
                physical_flag_frames=i,
            )
        )
    header = member(candidate, "DocumentHeader")
    assert header[:12] == b"oreH\x08\0\0\0oreH"
    return sparse, dict(
        flag_frame_sha256=hash_bytes(sparse),
        flag_frame_bytes=len(sparse),
        flag_tags_in_camp_order=[r["m_unitTagIndex"] for r in rows],
        declared_document_map_word=f"{unpack_from('<I',header,28)[0]:08x}",
        controls=matches,
    )


def verify(parent, candidate, manifest, fixtures, harness, cc, private_output=None):
    if not __debug__:
        raise RuntimeError("Verifier requires assertions")
    emitted = verify_source(parent, candidate, manifest)
    template = harness.read_text()
    assert template.count("/* EMITTED FUNCTIONS */") == 1
    with TemporaryDirectory() as out:
        source, exe = Path(out) / "camp.c", Path(out) / "camp-test"
        source.write_text(
            template.replace("/* EMITTED FUNCTIONS */", "\n\n".join(emitted))
        )
        subprocess.run(
            [
                cc,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(exe),
            ],
            check=True,
        )
        result = subprocess.run([str(exe)], text=True, capture_output=True, check=True)
    sparse, wire_receipt = startup_and_flags(
        candidate, manifest.with_name("mapmechanicslib.galaxy"), fixtures
    )
    if private_output:
        with private_output.open("xb") as f:
            f.write(sparse)
    return dict(
        map_sha256=hash_bytes(candidate.read_bytes()),
        harness=json.loads(result.stdout),
        **wire_receipt,
        later_camp_lifetimes_verified=False,
        target_sync_records_verified=0,
        native_playback_verified=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("parent", "candidate", "manifest"):
        parser.add_argument(arg, type=Path)
    parser.add_argument("fixtures", nargs=4, type=Path)
    parser.add_argument(
        "--harness",
        type=Path,
        default=Path(__file__).with_name("historical_camp_harness.c"),
    )
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--private-output", type=Path)
    print(json.dumps(verify(**vars(parser.parse_args())), indent=2))
