"""Join Monstrosity casts, transformed host deaths, summon births and explicit pings."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from smartcam_tags import DST_SCHEMA, SRC_SCHEMA, components, identity, number

UNIT = b"AbathurEvolvedMonstrosity"
TALENT = b"AbathurHeroicAbilityEvolveMonstrosity"
XML = "b2ecee56c24e3a6e62c904f066f858dd5fb9fa144c2e17af423320efaf9c69e1"


def catalog(path):
    data = path.read_bytes()
    if len(data) != 311994 or sha256(data).hexdigest() != XML:
        raise ValueError("Expected 98348 AbathurData.xml")
    root = ET.fromstring(data)

    def node(tag, key):
        (value,) = root.findall(f"{tag}[@id='{key}']")
        return value

    ability = node("CAbilEffectTarget", "AbathurEvolveMonstrosity")
    effect = node("CEffectSet", ability.find("Effect").attrib["value"])
    (create,) = [
        n
        for link in effect.findall("EffectArray")
        for n in root.findall(f"CEffectCreateUnit[@id='{link.attrib['value']}']")
    ]
    unit = create.find("SpawnUnit").attrib["value"]
    if (
        unit != ability.find("ProducedUnitArray").attrib["value"]
        or unit != UNIT.decode()
    ):
        raise ValueError("Spawn unit differs from ability dependency")
    allowed = node("CValidatorCombine", "TargetIsAbathurLocustorMinion")
    if allowed.attrib["id"] not in [
        v.get("value") for v in effect.findall("ValidatorArray")
    ] or {x.get("value") for x in allowed.findall("CombineArray")} != {
        "TargetIsAbathurLocust",
        "TargetMinion",
    }:
        raise ValueError("Unexpected host validator")
    return dict(
        catalog_sha256=XML,
        ability=ability.get("id"),
        effect=effect.get("id"),
        create_effect=create.get("id"),
        spawn_unit=node("CUnit", unit).get("id"),
    )


def trace(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest or build not in (
        41810,
        97605,
        98348,
    ):
        raise ValueError("Unexpected recording")
    p = load_protocol(41810 if build == 41810 else 96477)
    if p.recovery_schema_sha256 != (SRC_SCHEMA if build == 41810 else DST_SCHEMA):
        raise ValueError("Unexpected protocol")
    shift = 18 if build == 41810 else 22
    with closing(MPQArchive(path)) as a:
        h = p.decode_replay_header(a.header["user_data_header"]["content"])
        if (
            h["m_version"]["m_build"],
            h["m_version"]["m_baseBuild"],
            h["m_dataBuildNum"],
        ) != (build,) * 3:
            raise ValueError("Replay version")
        gt, tt = a.read_file("replay.game.events"), a.read_file("replay.tracker.events")
        game, tracker = list(p.decode_replay_game_events(gt)), list(
            p.decode_replay_tracker_events(tt)
        )
    if sum(e["_bits"] for e in game) != 8 * len(gt) or sum(
        e["_bits"] for e in tracker
    ) != 8 * len(tt):
        raise ValueError("Stream extent")
    births = {identity(e): e for e in tracker if e["_eventid"] in (1, 6)}
    deaths = {identity(e): e for e in tracker if e["_eventid"] == 2}
    setup = {e["m_playerId"]: e["m_userId"] for e in tracker if e["_eventid"] == 9}
    purchases = {
        (number(e, "m_intData", "PlayerID"), e["_gameloop"])
        for e in tracker
        if e.get("m_eventName") == b"TalentChosen"
        and number(e, "m_stringData", "PurchaseName") == TALENT
    }
    casts = [
        e
        for e in game
        if e["_eventid"] == 27 and e.get("m_abil") and "TargetUnit" in e["m_data"]
    ]
    products = [
        e for e in tracker if e["_eventid"] == 1 and e["m_unitTypeName"] == UNIT
    ]
    matched, host_types, scoped_families = [], Counter(), set()
    exact_snapshots = 0
    linked = {}
    for b in products:
        tick, owner = b["_gameloop"], b["m_controlPlayerId"]
        if owner != b["m_upkeepPlayerId"] or not any(
            slot == owner and t < tick for slot, t in purchases
        ):
            raise ValueError("Summon has no matching earlier named talent purchase")
        candidates = []
        for e in casts:
            if e["_gameloop"] != tick or e["_userid"]["m_userId"] != setup[owner]:
                continue
            host = e["m_data"]["TargetUnit"]
            death = deaths.get(components(host["m_tag"], shift))
            if death and (death["_gameloop"], death["m_x"], death["m_y"]) == (
                tick + 1,
                b["m_x"],
                b["m_y"],
            ):
                candidates.append((e, host))
        if len(candidates) != 1:
            raise ValueError(
                "No unique simultaneous cast on a host dying at the summon coordinates"
            )
        e, host = candidates[0]
        hk = components(host["m_tag"], shift)
        host_born = births[hk]
        snapshot = host["m_snapshotPoint"]
        exact_snapshots += (snapshot["x"] // 4096, snapshot["y"] // 4096) == (
            b["m_x"],
            b["m_y"],
        )
        if (
            hk == identity(b)
            or host_born["_gameloop"] >= tick
            or host_born["m_unitTypeName"]
            not in (
                b"FootmanMinion",
                b"WizardMinion",
                b"RangedMinion",
                b"CatapultMinion",
                b"AbathurLocustNormal",
                b"AbathurLocustAssaultStrain",
                b"AbathurLocustBombardStrain",
            )
        ):
            raise ValueError("Host generation or next-loop death differs")
        if any(
            host_born[k] != host[v]
            for k, v in (
                ("m_controlPlayerId", "m_snapshotControlPlayerId"),
                ("m_upkeepPlayerId", "m_snapshotUpkeepPlayerId"),
            )
        ):
            raise ValueError("Host snapshot owners differ")
        family = (
            setup[owner],
            e["m_abil"]["m_abilLink"],
            e["m_abil"]["m_abilCmdIndex"],
        )
        scoped_families.add(family)
        matched.append((tick, *family))
        kind = host_born["m_unitTypeName"].decode()
        host_types[kind] += 1
        linked[identity(b)] = (tick, kind)
    all_matched = Counter(
        (
            e["_gameloop"],
            e["_userid"]["m_userId"],
            e["m_abil"]["m_abilLink"],
            e["m_abil"]["m_abilCmdIndex"],
        )
        for e in game
        if e["_eventid"] == 27
        and e.get("m_abil")
        and (
            e["_userid"]["m_userId"],
            e["m_abil"]["m_abilLink"],
            e["m_abil"]["m_abilCmdIndex"],
        )
        in scoped_families
    )
    if Counter(matched) != all_matched or len(linked) != len(products):
        raise ValueError("Births and cast family executions differ")
    ping_results = []
    for e in game:
        if e["_eventid"] == 36 and e["m_unit"]:
            k = components(e["m_unit"], shift)
            if k in linked:
                born, kind = linked[k]
                end = deaths[k]["_gameloop"] if k in deaths else None
                if (
                    not born
                    < e["_gameloop"]
                    < (end if end is not None else h["m_elapsedGameLoops"] + 1)
                ):
                    raise ValueError("Ping outside traced summon lifetime")
                ping_results.append(
                    dict(
                        cast_and_birth_loop=born,
                        host_type=kind,
                        ping_loop=e["_gameloop"],
                        summon_death_loop=end,
                    )
                )
    return dict(
        build=build,
        replay_sha256=digest,
        named_talent_purchases=len(purchases),
        tracked_summons=len(products),
        unique_casts_matched=len(matched),
        snapshot_xy_equals_summon_xy=exact_snapshots,
        host_death_xy_equals_summon_xy=sum(host_types.values()),
        host_deaths_exactly_one_loop_later=sum(host_types.values()),
        host_types=dict(host_types),
        observed_ability_link_and_index=sorted({f[1:] for f in scoped_families}),
        pings=ping_results,
    )


if __name__ == "__main__":
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("--catalog", type=Path, required=True)
    cmd.add_argument(
        "--case",
        nargs=3,
        action="append",
        required=True,
        metavar=("REPLAY", "SHA256", "BUILD"),
    )
    args = cmd.parse_args()
    print(
        json.dumps(
            dict(
                catalog=catalog(args.catalog),
                cases=[trace(Path(p), h, int(b)) for p, h, b in args.case],
            ),
            indent=2,
        )
    )
