import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from build_dragonshire_talent_map import INCLUDE, append_include, build_map, conventional_catalog


class DragonShireMapTests(unittest.TestCase):
    def test_existing_include_retains_its_position(self):
        original = b'<Includes>\r\n    <Catalog path="GameData/DoodadAutoData.xml" />\r\n</Includes>\r\n'
        result = append_include(original)
        self.assertEqual(
            [e.attrib["path"] for e in ET.fromstring(result)], ["GameData/DoodadAutoData.xml", INCLUDE]
        )
        self.assertIn(original.split(b"</Includes>")[0], result)
        with self.assertRaises(ValueError):
            append_include(result)

    def test_conventional_catalog_keeps_nested_fields_and_order(self):
        inputs = [
            b'<CBehaviorTokenCounter id="Q"><ConditionalEvents index="0" CompareValue="25" /></CBehaviorTokenCounter>',
            b'<CBehaviorBuff id="S"><Modification><UnifiedMoveSpeedFactor value="-0.30" /></Modification></CBehaviorBuff>',
        ]
        children = list(ET.fromstring(conventional_catalog([ET.fromstring(data) for data in inputs])))
        self.assertEqual([ET.tostring(item).strip() for item in children], inputs)

    def test_invalid_input_and_existing_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            out = Path(temp) / "destination"
            source.write_bytes(b"unrecognized map")
            with self.assertRaises(ValueError):
                build_map(source, source, source, out)
            self.assertFalse(out.exists())
            out.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                build_map(source, source, source, out)
            with self.assertRaises(FileExistsError):
                build_map(source, source, source, source)
            self.assertEqual(out.read_bytes(), b"existing")
            self.assertEqual(source.read_bytes(), b"unrecognized map")
