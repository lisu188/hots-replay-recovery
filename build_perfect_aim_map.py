"""Restore the documented build-41810 Perfect Aim mana refund in an ExtendedSpikesRange copy."""

from argparse import ArgumentParser
from contextlib import closing
from datetime import date, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_dragonshire_talent_map import digest, inventory
from build_extended_spikes_map import GENN, HISTORICAL, one, pinned, require
from first_sync_game import game
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from runtime_catalog_probe import Storm

PARENT = "e7ce5d12d5a93840a333a6e27b3f15d9cab9917be2e88d0040f19d638e4f9bbf"
MEMBER = r"Base.StormData\GameData\EffectData.xml"
Q = "GreymaneGilneanCocktail"
TALENT = Q + "PerfectAim"
APPLY, PROC, REFUND, REMOVE, TOKEN = (
    TALENT + s for s in ("ApplyCanGetRefund", "ProcSet", "ModifyUnit", "RemoveCanGetRefund", "CanGetRefund")
)


def source_date_and_choice(path):
    protocol, inputs = game(path, SOURCE, 41810)
    with closing(MPQArchive(path)) as archive:
        details = protocol.decode_replay_details(archive.read_file("replay.details"))
        tracker = archive.read_file("replay.tracker.events")
    day = date(1601, 1, 1) + timedelta(days=details["m_timeUTC"] // (86400 * 10**7))
    require(day == date(2016, 4, 12), "Unexpected original UTC match date")
    event = next(e for i, e in enumerate(protocol.decode_replay_game_events(inputs)) if i == 1286)
    require((event["_eventid"], event["_gameloop"], event["_userid"]["m_userId"], event["m_index"]) ==
            (110, 241, 2, 1), "Original input differs")
    award = next(e for i, e in enumerate(protocol.decode_replay_tracker_events(tracker)) if i == 248)
    require(award.get("m_eventName") == b"TalentChosen" and award["_gameloop"] == 242 and
            award["m_intData"] == [{"m_key": b"PlayerID", "m_value": 3}] and
            award["m_stringData"] == [{"m_key": b"PurchaseName", "m_value": TALENT.encode()}],
            "Original award differs")
    return dict(source_sha256=SOURCE, build=41810, utc_date=day.isoformat(), input_ordinal=1286,
                input_loop=241, selector=1, user_id=2, award_ordinal=248, award_loop=242, player=3)


def check_catalog(historical, genn):
    old, = [hero for hero in json.loads(pinned(historical, HISTORICAL)) if hero["id"] == "Greymane"]
    choice, = (t for t in old["talents"]["1"] if t["id"] == TALENT)
    require(choice["description"] == "Increases Gilnean Cocktail's range by 30.3571% and refunds 50 Mana if it hits an enemy Hero.",
            "Unexpected historical talent description")
    xml = ET.fromstring(pinned(genn, GENN))

    def node(tag, name):
        return one(xml, f"{tag}[@id='{name}']")

    def values(entry, field):
        return [e.attrib["value"] for e in entry.findall(field)]

    def value(entry, field):
        return one(entry, field).attrib["value"]

    effect = node("CEffectCreateHealer", REFUND)
    require(effect.get("parent") == "StormManaRestore" and one(effect, "ImpactUnit").get("Value") == "Caster"
            and value(effect, "RechargeVitalRate") == "45", "Unexpected stock refund")
    mods = [tuple(value(e, k) for k in ("Type", "Catalog", "Entry", "Field", "Value"))
            for e in node("CTalent", TALENT).findall("AbilityModificationArray/Modifications")]
    require(mods == [("FlatModification", "Effect", APPLY, "Chance", "1.000000"),
                     ("FlatModification", "Effect", PROC, "Chance", "1.000000"),
                     ("FlatModification", "Actor", Q + "Guide", "Height", "2.550000"),
                     ("FlatModification", "Effect", Q + "LaunchMissile", "ImpactLocation.ProjectionDistanceScale", "2.550000")],
            "Unexpected talent modifiers")
    base = Decimal(value(node("CEffectLaunchMissileAdvanced", Q + "LaunchMissile"), "ImpactLocation/ProjectionDistanceScale"))
    guide = Decimal(value(node("CActorQuad", Q + "Guide"), "Height"))
    require(guide == base == Decimal("8.5"), "Unexpected stock guide or missile projection")
    proc = node("CEffectSet", PROC)
    apply = node("CEffectApplyBehavior", APPLY)
    require(APPLY in values(node("CEffectSet", Q + "InitialSet"), "EffectArray") and
            value(apply, "Chance") == value(proc, "Chance") == "0" and one(apply, "WhichUnit").get("Value") == "Caster" and
            value(apply, "Behavior") == TOKEN and value(node("CBehaviorBuff", TOKEN), "Duration") == "1.25",
            "Unexpected caster token or timing")
    validator = "GreymaneHasGilneanCocktailCanGetPerfectAimRefund"
    count = node("CValidatorUnitCompareBehaviorCount", validator)
    remove = node("CEffectRemoveBehavior", REMOVE)
    require(values(proc, "ValidatorArray") == [validator, "TargetIsHero"] and
            value(count, "Value") == "1" and value(count, "Behavior") == value(remove, "BehaviorLink") == TOKEN and
            one(count, "WhichUnit").get("Value") == one(remove, "WhichUnit").get("Value") == "Caster" and
            values(proc, "EffectArray") == [REMOVE, REFUND], "Unexpected refund gate or consumption order")
    require(PROC in values(node("CEffectCreatePersistent", Q + "ImpactSetPersistent"), "PeriodicEffectArray") and
            PROC in values(node("CEffectSet", Q + "SpreadImpactSet"), "EffectArray") and
            one(node("CEffectEnumArea", Q + "SpreadSearchArea"), "AreaArray").get("Effect") == Q + "SpreadImpactSet",
            "Unexpected direct or spread impact path")
    return dict(historical_hero_catalog_sha256=HISTORICAL, stock_hero_catalog_sha256=GENN,
                historic_refund=50, stock_refund=45, historic_described_range_percent="30.3571",
                stock_projection_base=str(base), stock_projection_increase="2.55", stock_projection_percent="30",
                stock_refund_paths=["direct", "spread"], stock_token_duration_seconds="1.25")


def build(parent, historical, genn, source, output, stormlib=None):
    require(not output.exists() and not output.is_symlink(), "Fresh output path required")
    original = pinned(parent, PARENT)
    match = source_date_and_choice(source)
    catalog = check_catalog(historical, genn)
    storm = Storm(stormlib)
    before, parent_check = inventory(parent, storm)
    for name, data in before.items():
        normalized = name.lower().replace("\\", "/")
        if normalized.startswith("base.stormdata/gamedata/") and normalized.endswith(".xml"):
            require(not any(n.get("id") == REFUND for n in ET.fromstring(data)), "Existing refund override")
    initial = before[MEMBER]
    require(initial.count(b"</Catalog>") == 1, "Unexpected effect catalog")
    record = ET.Element("CEffectCreateHealer", id=REFUND)
    ET.SubElement(record, "RechargeVitalRate", value="50")
    updated = initial.replace(b"</Catalog>", ET.tostring(record, encoding="us-ascii") + b"\r\n</Catalog>")
    with TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "candidate.s2ma"
        staged.write_bytes(original)
        storm.replace(staged, {MEMBER: updated})
        after, candidate_check = inventory(staged, storm)
        require(after == {**before, MEMBER: updated} and parent.read_bytes() == original, "Unexpected archive changes")
        image = staged.read_bytes()
        os.link(staged, output)
    return dict(parent_sha256=PARENT, candidate_sha256=digest(image), candidate_bytes=len(image),
                changed_member=MEMBER, old_member_sha256=digest(initial), new_member_sha256=digest(updated),
                unchanged_content_members=len(before)-1, parent_checks=parent_check, candidate_checks=candidate_check,
                source=match, catalog=catalog, historic_absolute_distance_verified=False,
                native_catalog_loading_verified=False, replay_written=False)


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    for name in ("parent", "historical", "genn", "source", "output"):
        cli.add_argument(name, type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
