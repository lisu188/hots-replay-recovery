"""Validate complete Dragon Shire loop-zero birth payloads against one or more replay archives."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from dragon_startup_births import predict, rebuild, require

MEMBERS = ("Objects", "Regions", "MapScript.galaxy")


def inputs(path):
    with closing(MPQArchive(path)) as archive:
        return [archive.read_file(key) for key in MEMBERS]


def verify(map_path, mechanics, build, replays, variants):
    map_sha = sha256(map_path.read_bytes()).hexdigest()
    assets = inputs(map_path)
    rows, info = predict(*assets, mechanics)
    extra = [
        dict(r, m_unitTypeName=r["m_unitTypeName"].decode())
        for r in rows[info["authored"] :]
    ]
    result = dict(
        build=build,
        map_sha256=map_sha,
        members=dict(zip(MEMBERS, [sha256(raw).hexdigest() for raw in assets])),
        **info,
        scripted_births=extra,
        variants=[],
        cases=[]
    )
    for variant in variants:
        actual = predict(*inputs(variant), mechanics)
        require(actual == (rows, info), "Variant differs from stock")
        result["variants"].append(
            dict(
                name=variant.name,
                sha256=sha256(variant.read_bytes()).hexdigest(),
                predictions_equal_to_stock=True,
            )
        )
    protocol = load_protocol({41810: 41810, 98348: 96477}[build])
    for replay in replays:
        with closing(MPQArchive(replay)) as archive:
            h = protocol.decode_replay_header(
                archive.header["user_data_header"]["content"]
            )
            d = protocol.decode_replay_details(archive.read_file("replay.details"))
            init = protocol.decode_replay_initdata(archive.read_file("replay.initData"))
            dep = d["m_cacheHandles"]
            require(
                (
                    h["m_version"]["m_build"],
                    h["m_version"]["m_baseBuild"],
                    h["m_dataBuildNum"],
                )
                == (build,) * 3,
                "Physical build differs",
            )
            require(
                dep == init["m_syncLobbyState"]["m_gameDescription"]["m_cacheHandles"]
                and dep[-1][:4] == b"s2ma"
                and dep[-1][8:].hex() == map_sha,
                "Map dependency differs",
            )
            wire = archive.read_file("replay.tracker.events")
        result["cases"].append(
            dict(
                replay_sha256=sha256(replay.read_bytes()).hexdigest(),
                **rebuild(wire, protocol, rows)
            )
        )
    if not replays:
        raise ValueError("At least one original replay is required")
    if build == 98348:
        root = ElementTree.fromstring(assets[0])
        sconce_id = info["camps"][0]["sconce_object_id"]
        unit = next(
            n for n in root.findall("ObjectUnit") if int(n.attrib["Id"]) == sconce_id
        )
        require(
            unit.attrib["UnitType"] == "LootBannerSconce", "Missing original sconce"
        )
        unit.set("UnitType", "CampOwnershipFlag")
        altered, changed_info = predict(
            ElementTree.tostring(root), *assets[1:], mechanics
        )
        require(len(altered) == len(rows) - 1, "Expected one fewer team-colored icon")
        try:
            rebuild(wire, protocol, altered)
        except ValueError as e:
            if str(e) != "Unexpected number of startup births":
                raise
        else:
            raise ValueError("Invalid current map was accepted")
        result["negative_sconce"] = dict(
            camp_object_id=sconce_id,
            original_scripted=info["scripted"],
            altered_scripted=changed_info["scripted"],
            rejected=True,
        )
    # Keep the creation count and tags but exchange the XY of the two shrine beacons.
    wrong = [dict(r) for r in rows]
    for field in ("m_x", "m_y"):
        wrong[-1][field], wrong[-2][field] = wrong[-2][field], wrong[-1][field]
    try:
        rebuild(wire, protocol, wrong)
    except ValueError as e:
        if str(e) != "Masked startup reconstruction differs":
            raise
    else:
        raise ValueError("Incorrect shrine order was accepted")
    result["negative_shrine_order_rejected"] = True
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("mechanics", type=Path)
    parser.add_argument("replay", type=Path, nargs="+")
    parser.add_argument("--build", type=int, choices=(41810, 98348), required=True)
    parser.add_argument("--variant", type=Path, action="append", default=[])
    args = parser.parse_args()
    print(
        json.dumps(
            verify(
                args.map,
                args.mechanics.read_bytes(),
                args.build,
                args.replay,
                args.variant,
            ),
            indent=2,
        )
    )
