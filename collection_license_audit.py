"""Collect direct static catalog declarations without resolving catalog semantics.

The CLI requires independent version-log and extracted hdp.info evidence.  The
collect_unbound() helper is for explicitly unversioned research fixtures only.
Neither interface exports ownership matrices, raw XML, or arbitrary metadata.
Filesystem races and partial writes after an I/O failure are not transactional.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import xml.etree.ElementTree as ET


class CollectionError(ValueError):
    """Malformed, unsupported, oversized, or insufficiently bound evidence."""


@dataclass(frozen=True)
class Limits:
    tree_entries: int = 40000
    tree_depth: int = 48
    xml_files: int = 20000
    xml_file_bytes: int = 64 * 1024 * 1024
    total_source_bytes: int = 768 * 1024 * 1024
    observation_bytes: int = 8 * 1024 * 1024
    version_log_bytes: int = 128 * 1024
    metadata_bytes: int = 256 * 1024
    xml_depth: int = 128
    xml_elements_per_file: int = 1000000
    declarations: int = 150000
    selected_fields: int = 500000
    text_characters: int = 1024
    json_nodes: int = 20000
    report_bytes: int = 128 * 1024 * 1024


DEFAULT_LIMITS = Limits()
VERSION = re.compile(r"2\.[0-9]+\.[0-9]+\.[0-9]+(?:_ptr)?\Z")
VERSION_TOKEN = re.compile(r"(?<![\w.])2\.[0-9]+\.[0-9]+\.[0-9]+(?:_ptr)?(?![\w.])")
U64_MAX = (1 << 64) - 1
TRACKED_LOADOUTS = {"CHero", "CSkin", "CMount"}
SELECTED_FIELDS = {"License", "RequiredRewardArray", "ProductId", "HyperlinkId"}
ALLOWED_FIELD_ATTRIBUTES = {"value", "index", "removed"}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _plain(path: Path, *, directory: bool = False) -> os.stat_result:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or _reparse(info):
        raise CollectionError("Symlinks and reparse points are unsupported")
    wanted = stat.S_ISDIR if directory else stat.S_ISREG
    if not wanted(info.st_mode):
        raise CollectionError("Expected a regular directory" if directory else "Expected a regular file")
    return info


def _read(path: Path, bound: int) -> bytes:
    before = _plain(path)
    if before.st_size > bound:
        raise CollectionError("Input file size bound exceeded")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise CollectionError("Input identity changed before reading")
        raw = stream.read(bound + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > bound or len(raw) != before.st_size or after.st_size != before.st_size:
        raise CollectionError("Input size changed or exceeded bound")
    return raw


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CollectionError("Duplicate JSON object key")
        result[key] = value
    return result


def _json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(CollectionError("Non-finite JSON value")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CollectionError("Invalid UTF-8 JSON evidence") from error


def _string(value, limits: Limits, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value) or len(value) > limits.text_characters:
        raise CollectionError("Invalid or oversized catalog string")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise CollectionError("Control characters are unsupported")
    return value


def _u64(value) -> int:
    if type(value) is not int or not 0 <= value <= U64_MAX:
        raise CollectionError("Expected an unsigned 64-bit integer")
    return value


def _load_observation(path: Path, limits: Limits) -> dict:
    raw = _read(path, limits.observation_bytes)
    value = _json(raw)
    allowed = {"format", "contains_player_ownership_or_identity_data", "cases"}
    if not isinstance(value, dict) or set(value) != allowed:
        raise CollectionError("Collection projection must use the catalog-only allowlisted schema")
    if value["format"] != "hots-collection-identity-projection-v1" or value["contains_player_ownership_or_identity_data"] is not False:
        raise CollectionError("Collection projection is not catalog-only")
    cases = value["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 16:
        raise CollectionError("Invalid collection case count")
    names, numbers, summaries, seen = set(), set(), [], set()
    for case in cases:
        keys = {"id", "member_sha256", "encoding", "items", "count", "distinct_items"}
        if not isinstance(case, dict) or set(case) != keys:
            raise CollectionError("Unexpected collection case fields")
        case_id = case["id"]
        if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", case_id) or case_id in seen:
            raise CollectionError("Invalid or duplicate collection case label")
        seen.add(case_id)
        digest = case["member_sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CollectionError("Invalid bound member digest")
        items = case["items"]
        if not isinstance(items, list) or len(items) > 65535 or type(case["count"]) is not int or case["count"] != len(items):
            raise CollectionError("Collection count mismatch or bound exceeded")
        encoding = case["encoding"]
        if encoding == "big-endian-u64":
            for item in items:
                _u64(item)
            numbers.update(items)
        elif encoding == "utf8-name":
            for item in items:
                _string(item, limits)
                if len(item.encode("utf-8")) > 256 or not all(c.isalnum() or c in "_.-" for c in item):
                    raise CollectionError("Expected a catalog asset identifier")
            names.update(items)
        else:
            raise CollectionError("Unsupported collection key encoding")
        distinct = len(set(items))
        if type(case["distinct_items"]) is not int or case["distinct_items"] != distinct:
            raise CollectionError("Distinct collection count mismatch")
        summaries.append({"id": case_id, "member_sha256": digest, "encoding": encoding,
                          "count": len(items), "distinct_items": distinct})
    if not numbers or not names:
        raise CollectionError("Both numeric current keys and named legacy keys are required")
    return {"bytes": len(raw), "sha256": _sha(raw), "format": value["format"],
            "cases": summaries, "names": names, "numbers": numbers}


def _inventory(root: Path, limits: Limits):
    _plain(root, directory=True)
    root = root.absolute()
    stack, entries, xml_count = [(root, 0)], 0, 0
    files = []
    while stack:
        folder, depth = stack.pop()
        if depth > limits.tree_depth:
            raise CollectionError("Extracted tree depth bound exceeded")
        with os.scandir(folder) as stream:
            for entry in stream:
                entries += 1
                if entries > limits.tree_entries:
                    raise CollectionError("Extracted tree entry bound exceeded")
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode) or _reparse(info):
                    raise CollectionError("Extracted tree contains a link or reparse point")
                path = Path(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    stack.append((path, depth + 1))
                elif stat.S_ISREG(info.st_mode):
                    if path.suffix.lower() == ".xml" or path.name.lower() == "hdp.info":
                        relative = path.relative_to(root).as_posix()
                        _string(relative, limits)
                        files.append((relative, path))
                        xml_count += path.suffix.lower() == ".xml"
                        if xml_count > limits.xml_files:
                            raise CollectionError("XML file count bound exceeded")
                else:
                    raise CollectionError("Extracted tree contains a special file")
    return sorted(files), entries


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _selected_field(element, limits: Limits) -> dict:
    attributes = {key: _string(value, limits, empty=True) for key, value in element.attrib.items()}
    unknown = sorted(set(attributes) - ALLOWED_FIELD_ATTRIBUTES)
    # Export only known scalar attributes. Unknown attribute names are diagnostic;
    # their values, text bodies and nested XML are deliberately not copied.
    result = {"attributes": {key: attributes[key] for key in sorted(set(attributes) & ALLOWED_FIELD_ATTRIBUTES)}}
    reasons = []
    if unknown:
        for key in unknown:
            _string(key, limits)
        result["unsupported_attribute_names"] = unknown
        reasons.append("unsupported_attributes")
    if list(element) or (element.text or "").strip():
        reasons.append("nested_or_text_field_content_not_interpreted")
    if "index" in attributes:
        reasons.append("indexed_array_operation_not_resolved")
    if "removed" in attributes:
        reasons.append("removal_operation_not_resolved")
    value = attributes.get("value")
    if value is None:
        reasons.append("missing_value")
    elif "##" in value:
        reasons.append("template_not_resolved")
    if _local(element.tag) in {"License", "ProductId"} and value is not None and "##" not in value:
        if re.fullmatch(r"[0-9]+", value):
            number = int(value)
            _u64(number)
            result["numeric_value"] = number
        else:
            reasons.append("non_numeric_value_not_interpreted")
    result["unresolved"] = reasons
    result["direct_literal_candidate"] = not reasons
    return result


def _parse_xml(raw: bytes, relative: str, limits: Limits, declarations: list, field_counter: list) -> dict:
    # Null stripping also detects ASCII DTD markup in UTF-16/UTF-32 input.
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", raw.replace(b"\x00", b""), re.IGNORECASE):
        raise CollectionError("DTD and entity declarations are forbidden")
    depth, elements, ordinal, root_tag, current = 0, 0, -1, None, None
    first_index = len(declarations)
    try:
        parser = ET.iterparse(io.BytesIO(raw), events=("start", "end"))
        root_element = None
        for event, element in parser:
            if event == "start":
                depth += 1
                elements += 1
                if depth > limits.xml_depth or elements > limits.xml_elements_per_file:
                    raise CollectionError("XML depth or element count bound exceeded")
                tag = _local(element.tag)
                if depth == 1:
                    root_tag, root_element = _string(tag, limits), element
                elif depth == 2:
                    ordinal += 1
                    if root_tag == "Catalog" and (tag.startswith("CReward") or tag in TRACKED_LOADOUTS):
                        _string(tag, limits)
                        if len(declarations) >= limits.declarations:
                            raise CollectionError("Declaration count bound exceeded")
                        attrs = {key: _string(value, limits, empty=True) for key, value in element.attrib.items()}
                        current = {"source": relative, "xml_child_ordinal": ordinal, "type": tag,
                                   "id": attrs.get("id"), "parent": attrs.get("parent"), "default": attrs.get("default"),
                                   "fields": {}, "unresolved": []}
                        extra = sorted(set(attrs) - {"id", "parent", "default"})
                        if extra:
                            current["other_attribute_names"] = [_string(key, limits) for key in extra]
                            current["unresolved"].append("other_record_attributes_not_interpreted")
                        if not current["id"]:
                            current["unresolved"].append("no_concrete_record_id")
                        elif "##" in current["id"]:
                            current["unresolved"].append("record_id_template_not_resolved")
                        if current["parent"] is not None:
                            current["unresolved"].append("parent_inheritance_not_resolved")
                        if current["default"] is not None:
                            current["unresolved"].append("default_declaration_not_resolved")
            else:
                if depth == 3 and current is not None and _local(element.tag) in SELECTED_FIELDS:
                    field_counter[0] += 1
                    if field_counter[0] > limits.selected_fields:
                        raise CollectionError("Selected field count bound exceeded")
                    key = _local(element.tag)
                    current["fields"].setdefault(key, []).append(_selected_field(element, limits))
                if depth >= 3:
                    element.clear()
                elif depth == 2:
                    if current is not None:
                        current["declaration_index"] = len(declarations)
                        declarations.append(current)
                        current = None
                    if root_element is not None:
                        root_element.clear()
                depth -= 1
    except (ET.ParseError, UnicodeError, RecursionError) as error:
        raise CollectionError("Malformed XML input") from error
    return {"xml_root": root_tag, "xml_elements": elements,
            "tracked_declarations": len(declarations) - first_index}


def _metadata_versions(raw: bytes, limits: Limits) -> list[str]:
    value = _json(raw)
    # HeroesDataParser v5.1.0 CASCExtractService.CreateInfoFile serializes
    # ModsInfoFile.Version with the original PascalCase property names. Other
    # strings are not game-version
    # evidence, even when they happen to equal the requested version.
    if (not isinstance(value, dict) or not isinstance(value.get("Version"), str)
            or not VERSION.fullmatch(value["Version"]) or value["Version"].endswith("_ptr")
            or value.get("IsPtr") is not False
            or any(key.casefold() in {"version", "isptr"} and key not in {"Version", "IsPtr"} for key in value)):
        raise CollectionError("Unsupported hdp.info shape: expected live Version string and IsPtr false, without mixed aliases")
    stack, nodes = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > limits.json_nodes or depth > 32:
            raise CollectionError("hdp.info structure bound exceeded")
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    return [value["Version"]]


def _comparison(declarations: list, observation: dict) -> dict:
    license_ids, product_ids, identities = defaultdict(list), defaultdict(list), defaultdict(list)
    for record in declarations:
        identity = (record["type"], record["id"])
        if record["id"]:
            identities[identity].append(record["declaration_index"])
        concrete = bool(record["id"]) and "##" not in record["id"] and record["default"] is None
        for field, mapping in (("License", license_ids), ("ProductId", product_ids)):
            if field == "License" and not record["type"].startswith("CReward"):
                continue
            if concrete:
                for item in record["fields"].get(field, []):
                    if item["direct_literal_candidate"] and "numeric_value" in item:
                        mapping[item["numeric_value"]].append(record["declaration_index"])
    duplicates = []
    for (kind, key), indexes in sorted(identities.items()):
        if len(indexes) > 1:
            duplicates.append({"type": kind, "id": key, "declaration_indexes": indexes})
            for index in indexes:
                declarations[index]["unresolved"].append("duplicate_record_identity_catalog_order_not_resolved")
    candidates = []
    for name in sorted(observation["names"]):
        records = [row for row in declarations if row["type"].startswith("CReward") and row["id"] == name]
        if records:
            numeric = sorted({item["numeric_value"] for row in records
                              if row["default"] is None for item in row["fields"].get("License", [])
                              if item["direct_literal_candidate"] and "numeric_value" in item})
            candidates.append({"source_collection_name": name,
                               "reward_declaration_indexes": [row["declaration_index"] for row in records],
                               "direct_numeric_license_candidates": numeric,
                               "candidates_present_in_current_collection": sorted(set(numeric) & observation["numbers"]),
                               "legacy_to_current_mapping_proven": False})
    current = observation["numbers"]
    matched = current & set(license_ids)
    return {"current_observed_unique_ids": len(current), "legacy_observed_unique_names": len(observation["names"]),
            "direct_license_unique_ids": len(license_ids), "current_ids_with_direct_license_declarations": len(matched),
            "current_ids_without_direct_license_declarations": len(current - matched),
            "matched_current_ids": sorted(matched), "unmatched_current_ids": sorted(current - matched),
            "direct_license_ids_not_observed_in_current_collection": sorted(set(license_ids) - current),
            "direct_license_declarations_by_id": {str(key): value for key, value in sorted(license_ids.items())},
            "duplicate_direct_license_declarations": {str(key): value for key, value in sorted(license_ids.items()) if len(value) > 1},
            "duplicate_record_identities": duplicates,
            "license_product_namespace_collisions": [
                {"numeric_id": key, "license_declaration_indexes": license_ids[key], "product_declaration_indexes": product_ids[key]}
                for key in sorted(set(license_ids) & set(product_ids))],
            "exact_legacy_record_name_candidates": candidates,
            "coverage_is_effective_catalog_or_mapping_proof": False}


def _collect(root: Path, observation_path: Path, expected_version: str | None,
             version_log: Path | None, limits: Limits) -> dict:
    if expected_version is not None and (not VERSION.fullmatch(expected_version) or expected_version.endswith("_ptr")):
        raise CollectionError("Expected version must be an exact live Heroes version")
    observation = _load_observation(observation_path, limits)
    binding = {"status": "unbound", "expected_version": None, "version_log": None,
               "matching_hdp_info_files": 0, "metadata": []}
    if expected_version is not None:
        if version_log is None:
            raise CollectionError("Version log is required")
        log = _read(version_log, limits.version_log_bytes)
        try:
            versions = sorted(set(VERSION_TOKEN.findall(log.decode("utf-8-sig"))))
        except UnicodeError as error:
            raise CollectionError("Version log must be UTF-8") from error
        if versions != [expected_version]:
            raise CollectionError("Live version log does not exclusively identify the expected version")
        binding.update(expected_version=expected_version,
                       version_log={"bytes": len(log), "sha256": _sha(log), "observed_versions": versions})
    files, tree_entries = _inventory(root, limits)
    declarations, sources, total, counter = [], [], 0, [0]
    for relative, path in files:
        metadata = path.name.lower() == "hdp.info"
        raw = _read(path, limits.metadata_bytes if metadata else limits.xml_file_bytes)
        total += len(raw)
        if total > limits.total_source_bytes:
            raise CollectionError("Aggregate source byte bound exceeded")
        source = {"path": relative, "bytes": len(raw), "sha256": _sha(raw),
                  "kind": "hdp.info" if metadata else "XML"}
        if metadata:
            versions = _metadata_versions(raw, limits)
            item = {"path": relative, "bytes": len(raw), "sha256": _sha(raw),
                    "version_field": "Version", "is_ptr": False, "observed_version_strings": versions}
            binding["metadata"].append(item)
            if expected_version is not None:
                if versions != [expected_version]:
                    raise CollectionError("hdp.info does not exclusively identify the expected version")
                binding["matching_hdp_info_files"] += 1
        else:
            source.update(_parse_xml(raw, relative, limits, declarations, counter))
        sources.append(source)
    if not declarations or not any(row["type"].startswith("CReward") for row in declarations):
        raise CollectionError("No reward declarations were found")
    if expected_version is not None:
        if binding["matching_hdp_info_files"] < 1:
            raise CollectionError("No extracted hdp.info metadata binds the expected version")
        binding["status"] = "version-log-and-extracted-metadata-match"
    comparison = _comparison(declarations, observation)
    return {"format": "hots-direct-collection-license-declarations-v1", "version_binding": binding,
            "collection_observation": {key: observation[key] for key in ("bytes", "sha256", "format", "cases")},
            "counts": {"tree_entries": tree_entries, "source_files": len(sources),
                       "xml_files": sum(row["kind"] == "XML" for row in sources),
                       "source_bytes": total, "tracked_declarations": len(declarations), "selected_fields": counter[0]},
            "source_files": sources, "declarations": declarations, "direct_comparison": comparison,
            "limitations": ["Only direct local scalar declarations are candidates; catalog load order, inheritance, defaults, templates and array overrides are not resolved.",
                            "XML child ordinals identify source locations; they are not runtime catalog indices.",
                            "ProductId, HyperlinkId and License are separate namespaces; numeric collisions do not establish identity.",
                            "Exact legacy names are candidates only; no legacy rename aliases or ownership mapping are inferred.",
                            "Version agreement binds the supplied log and extracted metadata, not cryptographic authenticity of those inputs.",
                            "No raw XML, arbitrary hdp.info values, ownership matrices or player identities are exported."],
            "catalog_load_order_resolved": False, "catalog_inheritance_resolved": False,
            "legacy_to_current_mapping_proven": False, "client_playback_validated": False,
            "replay_modified": False, "raw_xml_exported": False}


def collect_unbound(root: Path, collection_observation: Path, *, limits: Limits = DEFAULT_LIMITS) -> dict:
    """Research helper: its report always explicitly lacks current-build binding."""
    return _collect(Path(root), Path(collection_observation), None, None, limits)


def collect_version_bound(root: Path, collection_observation: Path, expected_version: str,
                          version_log: Path, *, limits: Limits = DEFAULT_LIMITS) -> dict:
    return _collect(Path(root), Path(collection_observation), expected_version, Path(version_log), limits)


def _output_preflight(output: Path, root: Path) -> None:
    if output.exists() or output.is_symlink():
        raise CollectionError("Output already exists; refusing overwrite")
    _plain(output.parent, directory=True)
    try:
        output.resolve().relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise CollectionError("Output must be outside the extracted input tree")


def write_new_report(report: dict, output: Path, *, limits: Limits = DEFAULT_LIMITS) -> None:
    if output.exists() or output.is_symlink():
        raise CollectionError("Output already exists; refusing overwrite")
    _plain(output.parent, directory=True)
    raw = (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    if len(raw) > limits.report_bytes:
        raise CollectionError("Report byte bound exceeded")
    with output.open("xb") as stream:
        stream.write(raw)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--collection-observation", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--version-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _output_preflight(args.output, args.root)
        report = collect_version_bound(args.root, args.collection_observation, args.expected_version, args.version_log)
        write_new_report(report, args.output)
    except (CollectionError, OSError) as error:
        # Paths, arbitrary metadata and malformed XML text are not echoed.
        print("Collection failed: " + (str(error) if isinstance(error, CollectionError) else type(error).__name__), file=sys.stderr)
        return 1
    counts = report["direct_comparison"]
    print("Version-bound direct declaration observation saved; "
          f"{counts['current_ids_with_direct_license_declarations']}/{counts['current_observed_unique_ids']} current keys have direct License candidates; "
          "no effective catalog or legacy mapping claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
