from decimal import Decimal
from hashlib import sha256
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

import dragon_startup_births as births
from encoders import encode_tracker_events
import protocol41810


def fixture():
    objects = ET.Element("PlacedObjects")
    regions = ET.Element("Regions")
    script = [
        "libCore_gv_sYSJungleCreepCamps = true;",
        "libMapM_gf_MMGardensDragonInitTowers();",
    ]
    for n, name in enumerate(
        ("DragonShireShrineSun", "DragonShireShrineMoon", "LootBannerSconce"), 1
    ):
        ET.SubElement(
            objects, "ObjectUnit", Id=str(n), UnitType=name, Position=f"{n},1,0"
        )
    for n in range(5):
        x = 3 + n * 10
        ET.SubElement(objects, "ObjectPoint", Id=str(n), Position=f"{x},1,0")
        reg = ET.SubElement(regions, "region", id=str(n))
        shape = ET.SubElement(reg, "shape", type="circle")
        ET.SubElement(shape, "center", value=f"{x},1")
        ET.SubElement(shape, "radius", value="2")
        script.extend(
            (
                "lv_junglecamp += 1;",
                "lv_mapDataCampType = libMapM_ge_JungleCampTypes_MercCamp;",
                f"lv_mapDataCampCaptainSpawnPoint = PointFromId({n});",
                f"lv_mapDataDefenderLeashRegion = RegionFromId({n});",
            )
        )
    return objects, regions, "\n".join(script).encode()


def predictions(objects, regions, script):
    with patch.object(births, "MECHANICS_SHA", sha256(b"test-rules").hexdigest()):
        return births.predict(
            ET.tostring(objects), ET.tostring(regions), script, b"test-rules"
        )


class DragonBirthTests(unittest.TestCase):
    def test_duplicate_normalized_ids_in_each_namespace(self):
        for child, attr in (
            ("ObjectUnit", "Id"),
            ("ObjectPoint", "Id"),
            ("region", "id"),
        ):
            with self.subTest(child=child):
                obj, reg, s = fixture()
                root = reg if child == "region" else obj
                ET.SubElement(root, child, {attr: "01"})
                with self.assertRaisesRegex(ValueError, "Duplicate numeric"):
                    predictions(obj, reg, s)

    def test_owner_bounds(self):
        for value in ("-1", "16", "1.0", " 1", "1_0", ""):
            with self.subTest(value=value):
                obj, reg, s = fixture()
                obj.find("ObjectUnit").set("Player", value)
                with self.assertRaisesRegex(ValueError, "owner"):
                    predictions(obj, reg, s)
        obj, reg, s = fixture()
        obj.find("ObjectUnit").set("Player", "15")
        rows, _ = predictions(obj, reg, s)
        self.assertEqual(rows[0]["m_controlPlayerId"], 15)

    def test_coordinate_validation(self):
        for text in (
            "NaN,1,0",
            "Inf,1,0",
            "1,2",
            "1e1,1,0",
            "1,1,524288",
            "-1,2,0",
            "256,2,0",
            "0,1,-524289",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                births.xy(ET.Element("ObjectUnit", Position=text))
        self.assertEqual(
            births.xy(ET.Element("ObjectUnit", Position="255.999755859375,0,-524288")),
            (Decimal("255.999755859375"), 0),
        )

    def test_malformed_regions_fail_even_without_sconces(self):
        for bad in ("empty", "duplicate", "wrong", "zero", "negative"):
            obj, reg, s = fixture()
            obj.remove(obj.find("ObjectUnit[@UnitType='LootBannerSconce']"))
            shape = reg.find("region/shape")
            if bad == "empty":
                reg.find("region").remove(shape)
            elif bad == "duplicate":
                ET.SubElement(shape, "center", value="3,1")
            elif bad == "wrong":
                shape.set("type", "ellipse")
            elif bad == "zero":
                shape.find("radius").set("value", "0")
            else:
                ET.SubElement(shape, "negative")
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                predictions(obj, reg, s)

    def test_duplicate_camp_references_or_overlapping_sconce(self):
        obj, reg, s = fixture()
        for old, new in (
            (b"PointFromId(1)", b"PointFromId(0)"),
            (b"RegionFromId(1)", b"RegionFromId(0)"),
            (b"RegionFromId(1)", b"RegionFromId(900)"),
        ):
            with self.subTest(old=old, new=new), self.assertRaises(ValueError):
                predictions(obj, reg, s.replace(old, new))
        reg.findall("region")[1].find("shape/center").set("value", "3,1")
        with self.assertRaisesRegex(ValueError, "two camp regions"):
            predictions(obj, reg, s)

    def test_branch_and_full_payload_mask(self):
        obj, reg, s = fixture()
        rows, scope = predictions(obj, reg, s)
        self.assertEqual(scope["scripted"], 8)
        self.assertEqual(
            [c["enabled_after_current_initializer"] for c in scope["camps"]],
            [True, False, False, False, False],
        )
        wire = encode_tracker_events(
            [dict(row, _event=births.BIRTH, _eventid=1, _gameloop=0) for row in rows],
            protocol41810,
        )
        self.assertEqual(
            births.rebuild(wire, protocol41810, rows)["fields_rebuilt"], 7 * len(rows)
        )
        changed = list(rows)
        changed[-1] = dict(rows[-1], m_unitTagIndex=0)
        with self.assertRaisesRegex(ValueError, "differs"):
            births.rebuild(wire, protocol41810, changed)


if __name__ == "__main__":
    unittest.main()
