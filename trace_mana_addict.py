"""Project Kael'thas's Mana Addict thresholds from TEN_GREYMANE's credited globe events."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import file_digest, sha256
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from migrate_replay import SOURCE_SHA256, decode_events, protocol
from mpq_reader import MPQArchive
from restore_mana_addict_threshold import STOCK_SHA256 as HERO_XML_SHA, TALENT
from source_talent_path_41810 import CATALOG_SHA256
from talent_choice_audit import STAT, _fields

TRACKER_SHA = "1a9a556f9f1fde466d17c4a3a3fbb31cbec8d8086bef97efeb796f1f5175245f"


def read_rules(catalog, hero_xml):
    old, current = catalog.read_bytes(), hero_xml.read_bytes()
    if sha256(old).hexdigest() != CATALOG_SHA256 or sha256(current).hexdigest() != HERO_XML_SHA:
        raise ValueError("Unexpected source catalog or target hero declaration")
    (hero,) = (hero for hero in json.loads(old) if hero["id"] == "Kaelthas")
    (talent,) = (t for t in hero["talents"]["1"] if t["id"] == TALENT)
    pattern = (
        r"Increases your maximum Mana by (\d+) when you pick up a Regeneration Globe\.\s+"
        r"Once you've gathered (\d+) Regeneration Globes, you can also activate Arcane Barrier to gain "
        r"a Shield equal to (\d+)% of your maximum Mana for (\d+) seconds\. (\d+) second cooldown\."
    )
    match = re.fullmatch(pattern, talent["description"])
    if not match:
        raise ValueError("Source description is outside the supported grammar")
    fields = (
        "max_mana_per_globe",
        "globe_threshold",
        "shield_max_mana_percent",
        "duration_seconds",
        "cooldown_seconds",
    )
    source_rules = dict(zip(fields, map(int, match.groups())))
    root = ET.fromstring(current)
    quest = root.find("CTalent[@id='KaelthasManaAddict']/QuestData")
    token = quest.attrib["StackBehavior"]
    gate = root.find(f"CBehaviorTokenCounter[@id='{token}']/ConditionalEvents")
    if gate.attrib["Compare"] != "GE" or gate.attrib["CompareValue"] != quest.attrib["TargetCount"]:
        raise ValueError("Inconsistent target quest configuration")
    scale = root.find("CAccumulatorToken[@id='KaelthasManaAddictAccumulator']")
    mana = root.find(
        "CBehaviorBuff[@id='KaelthasManaAddictManaRegen']/Modification/VitalMaxArray[@index='Energy']/AccumulatorArray"
    )
    award = root.find(
        "CEffectSet[@id='RegenGlobeImpactSet']/EffectArray[@value='KaelthasManaAddictQuestIncrement']"
    )
    increment = root.find("CEffectModifyTokenCount[@id='KaelthasManaAddictQuestIncrement']")
    unlock = root.find(
        "CEffectApplyBehavior[@id='KaelthasArcaneBarrierApplyUnlockingCarry']/Behavior"
    )
    use = root.find("CEffectApplyBehavior[@id='KaelthasArcaneBarrierApplyBehavior']")
    validator = root.find(
        "CValidatorUnitCompareBehaviorCount[@id='KaelthasManaAddictHasArcaneBarrierUnlocked']"
    )
    caster = root.find("CAbilEffectInstant[@id='KaelthasArcaneBarrier']")
    buff = root.find("CBehaviorBuff[@id='KaelthasArcaneBarrier']")
    if (
        mana.get("value") != scale.get("id")
        or scale.find("TokenId").get("value") != token
        or award is None
        or increment.find("TokenId").get("value") != token
        or increment.find("WhichUnit").get("Value") != "Target"
        or gate.find("Event[@EventId='QuestComplete']").get("Effect")
        != "KaelthasArcaneBarrierApplyUnlockingCarry"
        or unlock.get("value") != validator.find("Behavior").get("value")
        or validator.find("Compare").get("value") != "GT"
        or use.find("ValidatorArray").get("value") != validator.get("id")
        or use.find("Behavior").get("value") != buff.get("id")
        or caster.find("Effect").get("value") != use.get("id")
    ):
        raise ValueError("Unexpected target mana or barrier effect path")
    fraction = buff.find("DamageResponse/ModifyLimitVitalMaxFractionArray[@index='Energy']")
    target_values = (
        int(scale.find("Scale").get("value")),
        int(gate.attrib["CompareValue"]),
        int(fraction.get("value")) * 100,
        int(buff.find("Duration").get("value")),
        int(caster.find("Cost/Cooldown").get("TimeUse")),
    )
    return source_rules, dict(zip(fields, target_values))


def project_tracker(events, end_loop, old, current):
    """An owner receives one modelled count per post-purchase credited tracker record."""
    heroes, purchases, credits = {}, {}, defaultdict(list)
    score_names, upgrades = set(), set()
    last_tick = -1
    for ordinal, event in enumerate(events, 1):
        tick, kind = event["_gameloop"], event["_event"]
        if not last_tick <= tick <= end_loop:
            raise ValueError("Tracker order or bounds")
        last_tick = tick
        if kind.endswith(".SScoreResultEvent"):
            score_names.update(r["m_name"] for r in event["m_instanceList"])
        elif kind.endswith(".SUpgradeEvent"):
            upgrades.add(event["m_upgradeTypeName"])
        elif kind == STAT:
            name = event["m_eventName"]
            if name not in (b"PlayerSpawned", b"TalentChosen", b"RegenGlobePickedUp"):
                continue
            ints, strings = _fields(event, "m_intData"), _fields(event, "m_stringData")
            player = ints[b"PlayerID"]
            if name == b"PlayerSpawned":
                previous = heroes.setdefault(player, strings[b"Hero"])
                if previous != strings[b"Hero"]:
                    raise ValueError("Multiple primary heroes for a single player")
            elif name == b"TalentChosen" and strings[b"PurchaseName"] == TALENT.encode():
                if player in purchases or heroes.get(player) != b"HeroKaelthas":
                    raise ValueError("Unresolved quest purchaser")
                purchases[player] = (tick, ordinal)
            elif name == b"RegenGlobePickedUp":
                if set(ints) != {b"PlayerID"} or strings or event["m_fixedData"]:
                    raise ValueError("Globe event carries other fields")
                credits[player].append((tick, ordinal))
    if len(purchases) != 2:
        raise ValueError("Expected the two recorded quest purchases")
    result = []
    for player, purchase in sorted(purchases.items(), key=lambda entry: entry[1]):
        after = [record for record in credits[player] if record > purchase]
        ticks = [tick for tick, _ in after]

        def crossing(rules):
            threshold = rules["globe_threshold"]
            return ticks[threshold - 1] if len(ticks) >= threshold else None

        source_loop, target_loop = crossing(old), crossing(current)
        if target_loop is None or (source_loop is not None and target_loop >= source_loop):
            window = None
        else:
            window = {
                "from_loop_inclusive": target_loop,
                "until_source_threshold_loop_exclusive": source_loop,
                "still_open_at_end_of_recorded_credits": source_loop is None,
            }
        result.append(
            {
                "purchase_loop": purchase[0],
                "credited_before_purchase": len(credits[player]) - len(after),
                "credited_after_purchase": len(after),
                "ordered_credit_loops": ticks,
                "same_loop_multiplicities": {str(k): n for k, n in Counter(ticks).items() if n > 1},
                "source_threshold_loop": source_loop,
                "target_threshold_loop_on_source_credits": target_loop,
                "earlier_target_eligibility_window_on_source_credits": window,
                "projected_end_bonus_max_mana": len(after) * old["max_mana_per_globe"],
            }
        )
    needles = (b"quest", b"barrier", b"mana", b"globe", b"stack")

    def names(collection):
        return sorted(n.decode("ascii") for n in collection if any(k in n.lower() for k in needles))

    return {
        "tracker_events": ordinal,
        "last_tracker_loop": last_tick,
        "header_elapsed_loops": end_loop,
        "all_named_globe_events": sum(map(len, credits.values())),
        "score_field_count": len(score_names),
        "upgrade_type_count": len(upgrades),
        "candidate_score_field_names": names(score_names),
        "candidate_upgrade_names": names(upgrades),
        "owners_by_purchase_order": result,
    }


def trace(source, catalog, hero_xml):
    old, current = read_rules(catalog, hero_xml)
    p = protocol(41810, local=True)
    with closing(MPQArchive(source)) as archive:
        archive.file.seek(0)
        if (
            source.stat().st_size != 635140
            or file_digest(archive.file, "sha256").hexdigest() != SOURCE_SHA256
        ):
            raise ValueError("Expected original TEN_GREYMANE archive")
        header = p.decode_replay_header(archive.header["user_data_header"]["content"])
        tracker = archive.read_file("replay.tracker.events")
    if header["m_version"]["m_baseBuild"] != 41810 or sha256(tracker).hexdigest() != TRACKER_SHA:
        raise ValueError("Unexpected build or tracker")
    return {
        "format": "source-credit-mana-addict-thresholds-v1",
        "source_sha256": SOURCE_SHA256,
        "tracker_sha256": TRACKER_SHA,
        "source_catalog_sha256": CATALOG_SHA256,
        "target_xml_sha256": HERO_XML_SHA,
        "source_rules": old,
        "target_rules": current,
        "trace": project_tracker(
            decode_events(tracker, p, "tracker"), header["m_elapsedGameLoops"], old, current
        ),
        "scope": "Tracker credits are named and owner-specific. Eligibility windows and bonus mana assume one granted stack per credit. The original token counter, barrier cast, shield amount and synchronization equivalence are unverified.",
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for option in ("source", "catalog", "hero-xml"):
        cli.add_argument("--" + option, required=True, type=Path)
    args = cli.parse_args()
    sys.stdout.buffer.write(
        (json.dumps(trace(args.source, args.catalog, args.hero_xml), indent=2) + "\n").encode(
            "utf-8"
        )
    )
