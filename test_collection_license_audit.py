"""Synthetic fixture tests only: none of these fixtures is authentic game evidence."""
from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import collection_license_audit as collector


EXPECTED = "2.57.0.98348"


class SyntheticLicenseCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="SYNTHETIC-license-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "extracted_SYNTHETIC"
        self.root.mkdir()
        self.observation = self.base / "catalog-only-SYNTHETIC.json"
        self.version_log = self.base / "live-version-SYNTHETIC.log"
        self.version_log.write_text("Heroes of the Storm: " + EXPECTED + "\n", encoding="utf-8")
        self.output = self.base / "report-SYNTHETIC.json"
        self.value = {
            "format": "hots-collection-identity-projection-v1",
            "contains_player_ownership_or_identity_data": False,
            "cases": [
                {"id": "legacy_fixture", "member_sha256": "a" * 64, "encoding": "utf8-name",
                 "items": ["Kaelthas", "UnregisteredOldName"], "count": 2, "distinct_items": 2},
                {"id": "current_fixture", "member_sha256": "b" * 64, "encoding": "big-endian-u64",
                 "items": [11336, 25016, 99999], "count": 3, "distinct_items": 3},
            ],
        }
        self.save_observation()
        self.xml("rewards.xml", '''<Catalog>
          <CRewardHero id="Kaelthas"><License value="11336"/></CRewardHero>
          <CRewardPortrait id="Portrait"><License value="25016"/></CRewardPortrait>
          <CRewardGroup id="PortraitLicense"><License value="25016"/></CRewardGroup>
          <CSkin id="DifferentSkin"><ProductId value="25016"/>
            <HyperlinkId value="DisplayName"/><RequiredRewardArray value="Portrait"/></CSkin>
          <CHero id="Kaelthas"><ProductId value="11509"/><RequiredRewardArray value="Kaelthas"/></CHero>
          <CMount id="UnrelatedMount"><RequiredRewardArray value="UnknownReward"/></CMount>
        </Catalog>''')

    def save_observation(self):
        self.observation.write_text(json.dumps(self.value), encoding="utf-8")

    def xml(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def metadata(self, value=None):
        path = self.root / "hdp.info"
        path.write_text(json.dumps(value if value is not None else {
            "Version": EXPECTED, "IsPtr": False, "HdpVersion": "5.1.0",
            "ExtractedDate": "2026-10-18T18:00:00Z", "storagePath": "/PRIVATE/DO-NOT-EXPORT"}), encoding="utf-8")
        return path

    def unbound(self, **kwargs):
        return collector.collect_unbound(self.root, self.observation, **kwargs)

    def bound(self, **kwargs):
        return collector.collect_version_bound(self.root, self.observation, EXPECTED, self.version_log, **kwargs)

    def args(self):
        return ["--root", str(self.root), "--collection-observation", str(self.observation),
                "--expected-version", EXPECTED, "--version-log", str(self.version_log), "--output", str(self.output)]

    def test_incomplete_coverage_is_retained_not_promoted(self):
        result = self.unbound()
        comparison = result["direct_comparison"]
        self.assertEqual(comparison["current_ids_with_direct_license_declarations"], 2)
        self.assertEqual(comparison["unmatched_current_ids"], [99999])
        self.assertFalse(comparison["coverage_is_effective_catalog_or_mapping_proof"])
        self.assertEqual(result["version_binding"]["status"], "unbound")
        self.assertFalse(result["legacy_to_current_mapping_proven"])

    def test_duplicates_and_namespace_collision_retain_both_sources(self):
        result = self.unbound()
        duplicate = result["direct_comparison"]["duplicate_direct_license_declarations"]["25016"]
        self.assertEqual(len(duplicate), 2)
        self.assertEqual({result["declarations"][i]["type"] for i in duplicate}, {"CRewardPortrait", "CRewardGroup"})
        collision = result["direct_comparison"]["license_product_namespace_collisions"]
        self.assertEqual([row["numeric_id"] for row in collision], [25016])
        product = result["declarations"][collision[0]["product_declaration_indexes"][0]]
        self.assertEqual(product["type"], "CSkin")
        self.assertEqual(product["fields"]["HyperlinkId"][0]["attributes"]["value"], "DisplayName")

    def test_exact_legacy_name_candidates_do_not_invent_aliases(self):
        candidates = self.unbound()["direct_comparison"]["exact_legacy_record_name_candidates"]
        self.assertEqual([item["source_collection_name"] for item in candidates], ["Kaelthas"])
        self.assertEqual(candidates[0]["direct_numeric_license_candidates"], [11336])
        self.assertFalse(candidates[0]["legacy_to_current_mapping_proven"])

    def test_index_removal_template_and_nested_fields_remain_unresolved(self):
        self.xml("unresolved.xml", '''<Catalog>
          <CRewardSkin id="Operations" parent="Parent">
            <License index="0" value="99999"/><License removed="1" value="99999"/>
            <License value="##id##"/><License value="99999"><Nested/></License>
          </CRewardSkin>
          <CHero default="1"><RequiredRewardArray value="##id##"/></CHero>
          <CMount id="Mount"><RequiredRewardArray index="0" removed="1"/></CMount>
        </Catalog>''')
        result = self.unbound()
        record = next(row for row in result["declarations"] if row["id"] == "Operations")
        self.assertIn("parent_inheritance_not_resolved", record["unresolved"])
        self.assertTrue(all(not item["direct_literal_candidate"] for item in record["fields"]["License"]))
        self.assertEqual(result["direct_comparison"]["unmatched_current_ids"], [99999])
        mount = next(row for row in result["declarations"] if row["id"] == "Mount")
        ref = mount["fields"]["RequiredRewardArray"][0]
        self.assertEqual(ref["attributes"], {"index": "0", "removed": "1"})
        self.assertIn("removal_operation_not_resolved", ref["unresolved"])

    def test_default_license_does_not_claim_concrete_coverage(self):
        self.xml("default.xml", '<Catalog><CRewardHero default="1" id="Default"><License value="99999"/></CRewardHero></Catalog>')
        self.assertEqual(self.unbound()["direct_comparison"]["unmatched_current_ids"], [99999])

    def test_duplicate_record_identity_has_no_last_write_winner(self):
        self.xml("other.xml", '<Catalog><CRewardHero id="Kaelthas"><License value="99999"/></CRewardHero></Catalog>')
        result = self.unbound()
        duplicate = next(row for row in result["direct_comparison"]["duplicate_record_identities"] if row["id"] == "Kaelthas" and row["type"] == "CRewardHero")
        self.assertEqual(len(duplicate["declaration_indexes"]), 2)
        for index in duplicate["declaration_indexes"]:
            self.assertIn("duplicate_record_identity_catalog_order_not_resolved", result["declarations"][index]["unresolved"])
        self.assertEqual(result["direct_comparison"]["exact_legacy_record_name_candidates"][0]["direct_numeric_license_candidates"], [11336, 99999])

    def test_unknown_field_attribute_value_is_not_exported_or_counted(self):
        self.xml("extra.xml", '<Catalog><CRewardHero id="Extra"><License value="99999" unexpected="PRIVATE-HIDDEN"/></CRewardHero></Catalog>')
        result = self.unbound()
        encoded = json.dumps(result)
        self.assertNotIn("PRIVATE-HIDDEN", encoded)
        self.assertIn("unexpected", encoded)
        self.assertEqual(result["direct_comparison"]["unmatched_current_ids"], [99999])

    def test_version_binding_and_metadata_allowlist(self):
        metadata = self.metadata()
        result = self.bound()
        binding = result["version_binding"]
        self.assertEqual(binding["status"], "version-log-and-extracted-metadata-match")
        self.assertEqual(binding["matching_hdp_info_files"], 1)
        self.assertEqual(binding["metadata"][0]["sha256"], collector._sha(metadata.read_bytes()))
        serialized = json.dumps(result)
        self.assertNotIn("PRIVATE", serialized)
        self.assertNotIn("storagePath", serialized)
        self.assertNotIn(str(self.base), serialized)
        self.assertEqual(binding["metadata"][0]["observed_version_strings"], [EXPECTED])

    def test_missing_hdp_info_rejects_claimed_current_build(self):
        with self.assertRaisesRegex(collector.CollectionError, "No extracted hdp.info"):
            self.bound()

    def test_old_or_ambiguous_live_version_log_is_rejected(self):
        self.metadata()
        for text in ("2.57.0.98285", EXPECTED + "\n2.57.0.98285", "not a version", EXPECTED + "_ptr"):
            with self.subTest(text=text):
                self.version_log.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(collector.CollectionError, "Live version"):
                    self.bound()

    def test_old_or_ambiguous_metadata_is_rejected(self):
        for value in ({"Version": "2.57.0.98285", "IsPtr": False}, {"v": [EXPECTED, "2.57.0.98285"]}, {"path": "/tmp/" + EXPECTED}):
            with self.subTest(value=value):
                self.metadata(value)
                with self.assertRaisesRegex(collector.CollectionError, "hdp.info"):
                    self.bound()

    def test_unsupported_metadata_shape_is_rejected(self):
        (self.root / "hdp.info").write_text(EXPECTED, encoding="utf-8")
        with self.assertRaises(collector.CollectionError):
            self.bound()
        self.metadata(EXPECTED)
        with self.assertRaisesRegex(collector.CollectionError, "Unsupported hdp.info"):
            self.bound()

    def test_only_actual_top_level_version_field_binds_metadata(self):
        values = [{"other": EXPECTED}, {"heroesVersion": EXPECTED}, {"version": EXPECTED, "isPtr": False},
                  {"Version": EXPECTED}, [{"Version": EXPECTED, "IsPtr": False}],
                  {"Version": {"major": 2, "minor": 57, "patch": 0, "build": 98285}, "IsPtr": False, "unrelated": EXPECTED},
                  {"Version": "2.57.0.98285", "IsPtr": False, "unrelated": EXPECTED},
                  {"Version": EXPECTED, "version": EXPECTED, "IsPtr": False}]
        for value in values:
            with self.subTest(value=value):
                self.metadata(value)
                with self.assertRaises(collector.CollectionError):
                    self.bound()

    def test_actual_metadata_requires_explicit_non_ptr_boolean(self):
        for flag in (True, 0, 1, "false", None):
            with self.subTest(flag=flag):
                self.metadata({"Version": EXPECTED, "IsPtr": flag, "HdpVersion": "5.1.0"})
                with self.assertRaises(collector.CollectionError):
                    self.bound()
        self.metadata({"Version": EXPECTED + "_ptr", "IsPtr": False})
        with self.assertRaises(collector.CollectionError):
            self.bound()

    def test_metadata_duplicate_keys_and_nonfinite_json_are_rejected(self):
        for text in ('{"version":"' + EXPECTED + '","version":"2.57.0.98285"}', '{"version":NaN}'):
            with self.subTest(text=text):
                (self.root / "hdp.info").write_text(text, encoding="utf-8")
                with self.assertRaises(collector.CollectionError):
                    self.bound()

    def test_projection_refuses_ownership_data_and_unallowlisted_fields(self):
        for mutate in (
            lambda value: value.update(contains_player_ownership_or_identity_data=True),
            lambda value: value.update(ownership_matrix=[]),
            lambda value: value["cases"][0].update(player_name="PRIVATE"),
        ):
            value = json.loads(json.dumps(self.value))
            mutate(value)
            self.observation.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(collector.CollectionError):
                self.unbound()

    def test_projection_validates_counts_digest_and_u64_bounds(self):
        changes = [("count", 4), ("count", True), ("distinct_items", 2), ("member_sha256", "oops"),
                   ("items", [11336, True, 99999]), ("items", [11336, -1, 99999]),
                   ("items", [11336, 1 << 64, 99999]), ("encoding", "opaque")]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                edited = json.loads(json.dumps(self.value))
                edited["cases"][1][key] = value
                self.observation.write_text(json.dumps(edited), encoding="utf-8")
                with self.assertRaises(collector.CollectionError):
                    self.unbound()

    def test_projection_requires_both_key_domains_and_identifier_names(self):
        self.value["cases"] = self.value["cases"][1:]
        self.save_observation()
        with self.assertRaisesRegex(collector.CollectionError, "Both numeric"):
            self.unbound()

    def test_duplicate_projection_labels_are_rejected(self):
        self.value["cases"][1]["id"] = self.value["cases"][0]["id"]
        self.save_observation()
        with self.assertRaisesRegex(collector.CollectionError, "duplicate collection case"):
            self.unbound()

    def test_dtd_and_entities_are_rejected_across_encodings(self):
        text = '<!DOCTYPE Catalog [<!ENTITY x "99999">]><Catalog><CRewardHero id="X"><License value="&x;"/></CRewardHero></Catalog>'
        for encoding in ("utf-8", "utf-16", "utf-32"):
            with self.subTest(encoding=encoding):
                (self.root / "DTD.xml").write_bytes(text.encode(encoding))
                with self.assertRaisesRegex(collector.CollectionError, "DTD"):
                    self.unbound()

    def test_malformed_xml_is_not_silently_skipped(self):
        self.xml("broken.xml", "<Catalog><CRewardHero></Catalog>")
        with self.assertRaisesRegex(collector.CollectionError, "Malformed XML"):
            self.unbound()

    def test_oversized_numeric_xml_license_is_rejected(self):
        self.xml("overflow.xml", f'<Catalog><CRewardHero id="Overflow"><License value="{1 << 64}"/></CRewardHero></Catalog>')
        with self.assertRaisesRegex(collector.CollectionError, "64-bit"):
            self.unbound()

    def test_depth_element_record_and_field_bounds(self):
        for overrides in (dict(xml_depth=2), dict(xml_elements_per_file=2), dict(declarations=1), dict(selected_fields=1)):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(collector.CollectionError, "bound exceeded"):
                    self.unbound(limits=replace(collector.DEFAULT_LIMITS, **overrides))

    def test_source_input_and_aggregate_byte_bounds(self):
        for overrides in (dict(observation_bytes=2), dict(xml_file_bytes=2), dict(total_source_bytes=2), dict(tree_entries=0), dict(xml_files=0)):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(collector.CollectionError, "bound exceeded"):
                    self.unbound(limits=replace(collector.DEFAULT_LIMITS, **overrides))

    def test_tree_depth_and_empty_reward_set_are_rejected(self):
        self.xml("nested/child.xml", "<Catalog/>")
        with self.assertRaisesRegex(collector.CollectionError, "tree depth"):
            self.unbound(limits=replace(collector.DEFAULT_LIMITS, tree_depth=0))
        (self.root / "rewards.xml").unlink()
        with self.assertRaisesRegex(collector.CollectionError, "No reward"):
            self.unbound()

    def test_symlink_tree_is_not_followed(self):
        outside = self.base / "outside.xml"
        outside.write_text("PRIVATE", encoding="utf-8")
        try:
            os.symlink(outside, self.root / "link.xml")
        except (OSError, NotImplementedError):
            self.skipTest("Host does not permit synthetic symlink creation")
        with self.assertRaisesRegex(collector.CollectionError, "link or reparse"):
            self.unbound()

    def test_deterministic_relative_file_identities_and_no_raw_xml(self):
        self.xml("nested/aaa.xml", '<Catalog><CRewardMount id="Mount"><License value="555"/></CRewardMount></Catalog>')
        first, second = self.unbound(), self.unbound()
        self.assertEqual(first, second)
        paths = [row["path"] for row in first["source_files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertTrue(all(not Path(path).is_absolute() for path in paths))
        self.assertNotIn("<Catalog>", json.dumps(first))
        self.assertFalse(first["catalog_load_order_resolved"])

    def test_cli_creates_only_new_lf_report_and_preserves_inputs(self):
        self.metadata()
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(collector.main(self.args()), 0)
        raw = self.output.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"\r", raw)
        self.assertEqual(json.loads(raw)["version_binding"]["expected_version"], EXPECTED)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    def test_existing_output_is_rejected_before_collection(self):
        self.output.write_bytes(b"keep me")
        with patch.object(collector, "collect_version_bound") as collect, redirect_stderr(io.StringIO()):
            self.assertEqual(collector.main(self.args()), 1)
            collect.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b"keep me")

    def test_missing_parent_is_rejected_before_collection(self):
        self.output = self.base / "missing" / "report.json"
        with patch.object(collector, "collect_version_bound") as collect, redirect_stderr(io.StringIO()):
            self.assertEqual(collector.main(self.args()), 1)
            collect.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_parent_file_and_output_within_tree_are_rejected(self):
        parent_file = self.base / "parent-file"
        parent_file.write_bytes(b"keep")
        for output in (parent_file / "report.json", self.root / "report.json"):
            with self.subTest(output=output), self.assertRaises((collector.CollectionError, OSError)):
                collector._output_preflight(output, self.root)

    def test_failed_parse_or_binding_never_creates_report(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(collector.main(self.args()), 1)
        self.assertFalse(self.output.exists())
        self.metadata()
        self.xml("broken.xml", "<Catalog>")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(collector.main(self.args()), 1)
        self.assertFalse(self.output.exists())

    def test_report_size_bound_and_exclusive_write(self):
        report = self.unbound()
        with self.assertRaisesRegex(collector.CollectionError, "Report byte bound"):
            collector.write_new_report(report, self.output, limits=replace(collector.DEFAULT_LIMITS, report_bytes=1))
        self.assertFalse(self.output.exists())
        collector.write_new_report(report, self.output)
        original = self.output.read_bytes()
        with self.assertRaisesRegex(collector.CollectionError, "refusing overwrite"):
            collector.write_new_report(report, self.output)
        self.assertEqual(self.output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
