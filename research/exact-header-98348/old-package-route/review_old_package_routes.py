"""Metadata-only review of previously acquired original archive and unit evidence.

No replay, game header, archive, XML, PE, cache, network or client is opened.
Inputs are explicit small saved JSON receipts plus the prior producer's source.
The source is inspected as text and is never imported or executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat

MAX_TOTAL = 2 * 1024 * 1024
MAX_FILE = 256 * 1024
ORIGINAL = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
ROOT = "83d43a8647bb5ca5caa6f2f09064da55"
NAMES = ("Core", "Teams10", "Heroes", "HeroesData", "Dragon Shire")
PINS = {
    "cache": ("work/native-20261018/original-cache-verification.json", "5174a652f4ab1481718881a06fecc294fe52457adff94e9a331bb0ba8b030cee"),
    "handles": ("work/mod-package-handles-and-realms.json", "b4a19eebeb171eb1a1f044ffe740ba39a524bd2c2b2c713f02266d50873e2265"),
    "binding": ("work/legacy-header-mapinfo-evidence/original41810-cached-header-MapInfo-evidence.json", "1a4b18326303388b12f7d7a72415a5cd8973717954b30154370fb5927727bda3"),
    "binding_source": ("work/legacy-header-mapinfo-evidence/assess_original_header_mapinfo.py", "ace17756bdd8355abf2b4cbe79b264648f135a3fbf26bca0aa6dd2211f57fba4"),
    "header_acquisition": ("work/original-eu-s2mh-acquisition-network.json", "59252dc103d3d8516fb876fd5bf81b6212d5c03de7d5d31c5ee9d864f668f11b"),
    "search10": ("work/legacy-catalog-archives-2016/research-ledger.json", "0ee7996db1da297677668c576dfc7c15996d21a5cfe990bb4252ae01f5775732"),
    "search6": ("work/legacy-build-root-research/catalog-route/legacy-catalog-route-six-operation-ledger.json", "c38917400459782f94810b89e9e24a08628420543fee41379095e5e60257e71f"),
    "units": ("observations/collection-alias-nodes-current-98348.json", "bfbc51bb4c5270cfc13ba5199821795ae4e9dfea9d2ef114a2ba954c5e274bfc"),
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def analyze(task: Path, repo: Path) -> dict:
    total = 0
    inputs = []
    guards = []

    def read(label: str, relative: str, expected: str | None = None, repository: bool = False) -> bytes:
        nonlocal total
        path = (repo if repository else task) / relative
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and not path.is_symlink(), "regular input required")
        require(0 < before.st_size <= MAX_FILE, "metadata file bound")
        require(total + before.st_size + 1 <= MAX_TOTAL, "aggregate metadata bound")
        with path.open("rb") as stream:
            raw = stream.read(MAX_FILE + 1)
        after = path.lstat()
        require(len(raw) == before.st_size and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "input changed during read")
        total += len(raw)
        digest = sha(raw)
        require(expected is None or digest == expected, "input pin mismatch: " + label)
        inputs.append({"label": label, "relative_path": relative, "root": "repo" if repository else "task", "bytes": len(raw), "sha256": digest})
        guards.append((path, after.st_size, after.st_mtime_ns))
        return raw

    objects = {}
    for label, (relative, expected) in PINS.items():
        raw = read(label, relative, expected, label == "units")
        objects[label] = raw.decode("utf-8") if label == "binding_source" else json.loads(raw)
    nova = json.loads(read("nova_selected_receipt", "work/collection-alias-research/nova-current98348-unit-identity-observation.json"))
    cache, handles, binding = objects["cache"], objects["handles"], objects["binding"]
    original = next(item for item in handles["results"] if item["id"] == "original41810")
    require(cache["original_replay_sha256"] == binding["replay_sha256"] == ORIGINAL, "original binding")
    require(binding["original_root_and_base_build41810_authenticated"] is True, "old build authentication")
    require(binding["producer_sha256"] == PINS["binding_source"][1], "prior source pin")
    require("archive_value==prefix[index]" in objects["binding_source"] and "('m_bnet','m_archiveCacheHandle')" in objects["binding_source"], "named archive gate not found")
    require(binding["aggregate"]["exact_headers_available"] == 5 and binding["aggregate"]["exact_shared_field_matches"] == 75 and binding["aggregate"]["exact_shared_field_mismatches"] == 0, "prior shared field controls")
    require(len(cache["assets"]) == len(original["entries"]) == len(original["dependency_prefix_handles"]) == len(original["terminal_s2mh_handles"]) == len(binding["headers"]) == 5, "five original packages required")
    archives = []
    for index, (asset, prefix, terminal, entry, header) in enumerate(zip(cache["assets"], original["dependency_prefix_handles"], original["terminal_s2mh_handles"], original["entries"], binding["headers"])):
        require(asset["digest_verified"] is True and asset["sha256"] == asset["expected_sha256"] == prefix["digest"], "archive receipt binding")
        require(prefix["region"] == terminal["region"] == "EU" and prefix["extension"] == "s2ma", "archive region/type")
        require(header["index"] == index and header["header_sha256"] == terminal["digest"] and header["prefix_archive_and_candidate_handle_exact"] is True, "header archive binding")
        if index < 4:
            require(asset["role"] == "current_standard_data_redirect" and asset["size_bytes"] in (28, 30, 31, 34) and asset["standard_data_target"] == NAMES[index] + ".StormMod", "known redirect receipt")
        else:
            require(asset["role"] == "old_map_archive" and asset["size_bytes"] == 2129774, "known old map receipt")
        archives.append({"index": index, "module": NAMES[index], "package_id": entry["community_named_mod_id"], "package_version": entry["community_named_mod_offset"], "region": "EU", "archive_sha256": prefix["digest"], "header_sha256": terminal["digest"], "prior_verified_archive_bytes": asset["size_bytes"], "prior_role": asset["role"], "standard_data_target": asset["standard_data_target"], "source_derived_archive_URL_not_freshly_probed": "https://eu-s2-depot.classic.blizzard.com/" + prefix["digest"] + ".s2ma", "native_named_archive_equals_original_prefix": True, "new_historical_rules_payload_lead": False})
    acquisition = objects["header_acquisition"]
    require(acquisition["source_replay_sha256"] == ORIGINAL and len(acquisition["results"]) == 5, "header acquisition source")
    require(all(x["http_status"] == 200 and x["sha256"] == x["expected_sha256"] for x in acquisition["results"]), "prior header acquisition")
    units = objects["units"]
    require(units["target_version"] == "2.57.0.98348" and units["all_projected_XML_files_exact_digest_verified"] is True and units["scanned_xml_files"] == units["expected_xml_files"] == 5575, "current complete XML scope")
    query = units["unit_identity_queries"]
    expected = {"NovaHoloCloneCloaked": 0, "NovaHoloClone": 1, "AbathurEvolvedMonstrosity": 1, "TownCannonTowerL2Standalone": 8}
    require({x["id"]: x["declaration_count"] for x in query["results"]} == expected, "saved declaration counts")
    declarations = query["direct_Catalog_CUnit_declarations"]
    require({name: sum(x["id"] == name for x in declarations) for name in expected} == expected, "declaration record consistency")
    require(nova["exact_current98348_XML_digest_match"] is True and nova["sha256"] == next(x["sha256"] for x in declarations if x["id"] == "NovaHoloClone"), "selected Nova source identity")
    require(nova["alias_or_replacement_proven"] is False and nova["parent_or_catalog_order_resolved"] is False, "preserve unresolved Nova semantics")
    nova_declaration = nova["declarations"][0]
    require(nova_declaration["id"] == "NovaHoloClone" and nova_declaration["parent"] == "StormBasicHeroicUnit", "literal Nova declaration")
    source_lines = objects["binding_source"].splitlines()
    for path, size, mtime in guards:
        end = path.lstat()
        require(stat.S_ISREG(end.st_mode) and not path.is_symlink() and (end.st_size, end.st_mtime_ns) == (size, mtime), "input changed after analysis")
    return {
        "format": "original-package-catalog-route-and-current-unit-review-v1",
        "producer_sha256": sha(Path(__file__).read_bytes()),
        "inputs": inputs,
        "metadata_read_bytes_this_producer": total,
        "metadata_read_limit": MAX_TOTAL,
        "input_guards": "SHA pins where specified; bounded regular-file reads; size/mtime unchanged after analysis. No fresh raw-asset hash check.",
        "original": {"replay_sha256": ORIGINAL, "build": 41810, "ngdp_root": ROOT, "raw_replay_or_header_reread": False},
        "archive_routes": archives,
        "archive_binding_source_anchors": [{"line": i, "text": line.strip()} for i, line in enumerate(source_lines, 1) if "archive_value==prefix[index]" in line or "('m_bnet','m_archiveCacheHandle')" in line],
        "prior_header_acquisition": {"exact_objects": 5, "bytes": sum(x["bytes"] for x in acquisition["results"]), "all_HTTP200_and_SHA_verified_in_prior_receipt": True, "depot_route_primary_source": acquisition["depot_route_source"]},
        "prior_bounded_searches": {"ten_operation_ledger_exact41810_snapshot_identified": objects["search10"]["findings"]["exact_41810_snapshot_identified"], "six_operation_ledger_exact41810_snapshot_identified": objects["search6"]["exact41810_pinned_catalog_snapshot_identified"], "lowest_build_in_133_version_inventory": objects["search6"]["version_directory_coverage"]["lowest_build_in_list"], "authenticated_41810_BuildConfig_or_CDN_config_route_identified_by_these_receipts": False, "all_repositories_branches_or_archives_exhausted": False},
        "network_decision": {"requests": 0, "bytes": 0, "new_untried_exact_historical_rules_archive_identified": False, "reason": "The five authenticated archive handles already identify four verified Standard Data redirects and one cached old map. Re-requesting those exact objects offers no distinct 41810 global catalog/rules payload. The known NGDP root alone is not an authenticated BuildConfig/CDN route."},
        "current_unit_evidence": {
            "version": units["target_version"], "source_inventory_XML_files": 5575,
            "scope": "Previously saved complete digest-bound projected gamedata XML inventory; no rescan or raw XML read in this producer.",
            "results": query["results"],
            "declarations": [{k: x[k] for k in ("id", "kind", "parent", "file", "sha256", "bytes", "catalog_child_ordinal")} for x in declarations],
            "numeric_replay_catalog_links_inferred": False,
            "cloaked_spelling_globally_removed_proven": False,
        },
        "Nova_current_literal_properties": {
            "file": nova["relative_game_path"], "sha256": nova["sha256"], "id": nova_declaration["id"], "parent": nova_declaration["parent"],
            "direct_behavior_ability_weapon_references": nova_declaration["direct_behavior_ability_weapon_references"],
            "create_effect_and_actor_or_validator_references": [x for x in nova["exact_attribute_references"] if x["owner_kind"] in ("CEffectCreateUnit", "CActorUnit", "CValidatorUnitType")],
            "parent_inheritance_or_behavior_effects_resolved": False,
            "old_Cloaked_unit_definition_available_in_reviewed_receipts": False,
            "old_to_current_alias_or_equivalent_rules_proven": False,
        },
        "conversion_constraints": [
            "Monstrosity and the standalone tower retain literal current CUnit declarations, but static name presence supplies neither numeric replay links nor equality of 2016 rules.",
            "NovaHoloCloneCloaked is absent in the complete saved current XML scope. Current NovaHoloClone explicitly references permanent-cloak-named behaviors and is a create/actor/validator target; no old-to-current alias follows from those literal references.",
            "No authenticated old Cloaked catalog definition is available here, so actual property changes and equivalence cannot be quantified. Absence does not prove removal from arbitrary binary, server-side or constructed catalogs.",
            "A simple link remap cannot by itself demonstrate that current simulation reproduces the 2016 match. These findings also do not prove that conversion is impossible.",
        ],
        "raw_assets_replays_XML_headers_PE_or_player_data_read_or_emitted": False,
        "client_network_repo_or_cloud_mutations": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "output already exists")
    report = analyze(args.task, args.repo)
    body = (json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n").encode()
    require(len(body) <= 64 * 1024, "report output bound")
    with args.output.open("xb") as stream:
        stream.write(body)
    print(json.dumps({"report_sha256": sha(body), "report_bytes": len(body), "metadata_bytes": report["metadata_read_bytes_this_producer"], "network_requests": 0}))


if __name__ == "__main__":
    main()
