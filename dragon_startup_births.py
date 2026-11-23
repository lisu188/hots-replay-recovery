"""Reconstruct Dragon Shire loop-zero birth payloads from map members and 98348 script rules."""

from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import math
import re
from xml.etree import ElementTree as ET

from encoders import encode_tracker_events

MECHANICS_SHA = "d49dbde21198963f953efa16c8d8bb6b035d2d8bd8f0d41b5989fecbb4e35b1f"
BIRTH = "NNet.Replay.Tracker.SUnitBornEvent"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unsigned(text, limit, label):
    require(
        isinstance(text, str) and re.fullmatch(r"[0-9]{1,10}", text), f"Invalid {label}"
    )
    value = int(text)
    require(value <= limit, f"Out-of-range {label}")
    return value


def indexed(root, child, key):
    rows = {}
    for node in root.findall(child):
        value = unsigned(node.get(key), 2**32 - 1, f"{child} ID")
        require(value not in rows, f"Duplicate numeric {child} ID {value}")
        rows[value] = node
    return rows


def fixed_values(text, count):
    parts = text.split(",") if isinstance(text, str) else []
    require(len(parts) == count, "Unexpected fixed-point tuple length")
    require(
        all(
            re.fullmatch(r"[+-]?(?:[0-9]{1,7}(?:\.[0-9]{1,12})?|\.[0-9]{1,12})", p)
            for p in parts
        ),
        "Invalid fixed-point decimal",
    )
    values = tuple(Decimal(p) for p in parts)
    require(
        all(-(2**19) <= v <= Decimal(2**19) - Decimal(1) / 4096 for v in values),
        "Value outside signed 20.12 coordinate range",
    )
    return values


def xy(node):
    x, y, _ = fixed_values(node.get("Position"), 3)
    require(
        0 <= x < 256 and 0 <= y < 256,
        "Position exceeds unsigned 8-bit tracker projection",
    )
    return x, y


def region_shapes(region):
    """Parse the positive circle and subtractive shapes used by the five stock camp regions."""
    result = []
    for shape in region.findall("shape"):
        kind = shape.get("type")
        subtract = len(result) > 0
        sizes = {
            "circle": {"center": 2, "radius": 1},
            "rect": {"quad": 4},
            "diamond": {"center": 2, "width": 1, "height": 1},
        }
        require(
            kind in sizes and (subtract or kind == "circle"),
            "Unsupported camp region shape",
        )
        expected = set(sizes[kind]) | ({"negative"} if subtract else set())
        require(
            len(shape) == len(expected) and {n.tag for n in shape} == expected,
            "Malformed camp region shape members",
        )
        fields = {
            key: tuple(
                Fraction(v) for v in fixed_values(shape.find(key).get("value"), arity)
            )
            for key, arity in sizes[kind].items()
        }
        if kind == "rect":
            l, b, r, t = fields["quad"]
            require(l < r and b < t, "Invalid rectangle bounds")
        elif kind == "circle":
            require(fields["radius"][0] > 0, "Invalid circle radius")
        else:
            require(
                fields["width"][0] > 0 and fields["height"][0] > 0,
                "Invalid diamond dimensions",
            )
        result.append((kind, subtract, fields))
    require(result, "Empty camp region")
    return result


def in_shapes(shapes, pos):
    x, y = map(Fraction, pos)
    inside = False
    for kind, subtract, fields in shapes:
        if kind == "rect":
            left, bottom, right, top = fields["quad"]
            hit = left <= x <= right and bottom <= y <= top
        else:
            a, b = fields["center"]
            dx, dy = x - a, y - b
            if kind == "circle":
                hit = dx * dx + dy * dy <= fields["radius"][0] ** 2
            elif kind == "diamond" and subtract:
                w, h = fields["width"][0], fields["height"][0]
                # The stock sconce points agree under axis-aligned diamonds and either
                # 45-degree rotation of a rectangle. Refuse positions where this matters.
                options = {
                    abs(dx) / (w / 2) + abs(dy) / (h / 2) <= 1,
                    2 * (dx + dy) ** 2 <= w * w and 2 * (dx - dy) ** 2 <= h * h,
                    2 * (dx - dy) ** 2 <= w * w and 2 * (dx + dy) ** 2 <= h * h,
                }
                require(len(options) == 1, "Ambiguous diamond geometry")
                hit = options.pop()
            else:
                raise ValueError(f"Unsupported region shape {kind}")
        if subtract and hit:
            return False
        if not subtract and not hit:
            return False
        inside |= hit and not subtract
    return inside


def region_contains(region, pos):
    return in_shapes(region_shapes(region), pos)


def predict(objects, regions, map_script, mechanics):
    """Consume map/script inputs only. Return seven fields per birth in creation order."""
    require(
        sha256(mechanics).hexdigest() == MECHANICS_SHA,
        "Unsupported MapMechanics library",
    )
    script = map_script.decode("utf-8-sig")
    require(
        "libCore_gv_sYSJungleCreepCamps = true;" in script,
        "Jungle not explicitly enabled",
    )
    require(
        "libMapM_gf_MMGardensDragonInitTowers(" in script,
        "Missing Dragon Shrine initialization",
    )
    root = ET.fromstring(objects)
    region_root = ET.fromstring(regions)
    require(
        root.tag == "PlacedObjects" and region_root.tag == "Regions",
        "Unexpected map member root",
    )
    by_id = indexed(root, "ObjectUnit", "Id")
    units = [by_id[k] for k in sorted(by_id)]
    points = indexed(root, "ObjectPoint", "Id")
    reg = indexed(region_root, "region", "id")
    placements = []

    def make(kind, position, owner):
        x, y = position
        require(
            isinstance(kind, str) and 0 < len(kind.encode()) < 256,
            "Invalid tracker unit type",
        )
        return dict(
            m_unitTagIndex=len(placements),
            m_unitTagRecycle=1,
            m_unitTypeName=kind.encode(),
            m_controlPlayerId=owner,
            m_upkeepPlayerId=owner,
            m_x=math.floor(x),
            m_y=math.floor(y),
        )

    for u in units:
        placements.append(
            make(u.get("UnitType"), xy(u), unsigned(u.get("Player", "0"), 15, "owner"))
        )
    sconces = [u for u in units if u.attrib["UnitType"] == "LootBannerSconce"]
    camps = []
    used_points = set()
    used_regions = set()
    used_sconces = set()
    blocks = script.split("lv_junglecamp += 1;")[1:]
    require(len(blocks) == 5, "Expected five Dragon Shire camps")
    for block in blocks:
        require(
            block.count("lv_mapDataCampType = libMapM_ge_JungleCampTypes_MercCamp;")
            == 1,
            "Unexpected camp type",
        )
        (point,) = re.findall(
            r"lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\)", block
        )
        (leash,) = re.findall(
            r"lv_mapDataDefenderLeashRegion = RegionFromId\((\d+)\)", block
        )
        point = unsigned(point, 2**32 - 1, "camp point ID")
        leash = unsigned(leash, 2**32 - 1, "leash region ID")
        require(
            point in points and leash in reg,
            "Camp references a missing point or region",
        )
        require(
            point not in used_points and leash not in used_regions,
            "Repeated camp point or leash region",
        )
        used_points.add(point)
        used_regions.add(leash)
        position = xy(points[point])
        shapes = region_shapes(reg[leash])
        matches = [u for u in sconces if in_shapes(shapes, xy(u))]
        require(len(matches) <= 1, "Ambiguous sconce")
        if matches:
            sconce_id = int(matches[0].attrib["Id"])
            require(sconce_id not in used_sconces, "Sconce belongs to two camp regions")
            used_sconces.add(sconce_id)
        placements.append(make("TownMercCampCaptureBeacon", position, 0))
        if matches:
            placements.append(make("JungleCampIconUnitTeamColor", position, 0))
        camps.append(
            dict(
                captain_point_id=int(point),
                leash_region_id=int(leash),
                sconce_object_id=int(matches[0].attrib["Id"]) if matches else None,
                enabled_after_current_initializer=bool(matches),
            )
        )
    for kind in ("DragonShireShrineSun", "DragonShireShrineMoon"):
        (shrine,) = [u for u in units if u.attrib["UnitType"] == kind]
        placements.append(
            make(
                "DragonballCaptureBeacon",
                xy(shrine),
                unsigned(shrine.get("Player", "0"), 15, "owner"),
            )
        )
    return placements, dict(
        authored=len(units), scripted=len(placements) - len(units), camps=camps
    )


def rebuild(wire, protocol, predictions):
    events = list(protocol.decode_replay_tracker_events(wire))
    offsets = [
        i for i, e in enumerate(events) if e["_event"] == BIRTH and e["_gameloop"] == 0
    ]
    require(len(offsets) == len(predictions), "Unexpected number of startup births")
    for i in offsets:
        events[i] = {k: v for k, v in events[i].items() if k.startswith("_")}
    for i, p in zip(offsets, predictions):
        events[i].update(p)
    require(
        encode_tracker_events(events, protocol) == wire,
        "Masked startup reconstruction differs",
    )
    return dict(
        masked_births=len(offsets),
        fields_rebuilt=sum(map(len, predictions)),
        original_birth_payloads_retained=0,
        tracker_sha256=sha256(wire).hexdigest(),
        tracker_bytes=len(wire),
        reconstructed_tracker_byte_equal=True,
    )
