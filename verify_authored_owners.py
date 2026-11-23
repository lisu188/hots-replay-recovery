"""Compare authored Player with both tracker owner fields after removing those fields."""

from collections import Counter
from hashlib import sha256
from xml.etree import ElementTree

from encoders import encode_tracker_events
from map_startup_identity import BIRTH, parse_objects, predict_startup, verify_startup


def check_owners(xml, wire, protocol):
    rows = parse_objects(xml)
    attributes = {
        int(node.attrib["Id"]): node.get("Player")
        for node in ElementTree.fromstring(xml).findall("ObjectUnit")
    }
    events = list(protocol.decode_replay_tracker_events(wire))
    masked = list(events)
    keys = ("m_controlPlayerId", "m_upkeepPlayerId")
    birth_offsets = {
        n for n, e in enumerate(events) if e["_event"] == BIRTH and e["_gameloop"] == 0
    }
    for n in birth_offsets:
        masked[n] = {k: v for k, v in events[n].items() if k not in keys}
    predictions, report = predict_startup(rows, masked)
    checked, _ = verify_startup(predictions, events, report)
    owners = Counter()
    verified = {}
    for a in checked:
        authored = attributes[a.object_id]
        owner = 0 if authored is None else int(authored)
        offset = a.event_offset
        for key in keys:
            masked[offset][key] = owner
        if any(masked[offset][key] != events[offset][key] for key in keys):
            raise ValueError(f"Owner disagreement for ObjectUnit {a.object_id}")
        owners["absent" if authored is None else authored] += 1
        verified[offset] = (a.index, a.recycle)
    for offset in birth_offsets - verified.keys():
        for key in keys:
            masked[offset][key] = events[offset][key]
    reconstructed = encode_tracker_events(masked, protocol)
    if reconstructed != wire:
        raise ValueError("Tracker bytes differ after owner reconstruction")
    authored_tags = set(verified.values())
    later_changes = [
        e
        for e in events
        if e["_gameloop"] > 0
        and e["_event"].endswith(".SUnitOwnerChangeEvent")
        and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) in authored_tags
    ]
    return dict(
        tracker_sha256=sha256(wire).hexdigest(),
        all_startup_owner_pairs_masked=len(birth_offsets),
        pairs_from_xml=len(checked),
        unassigned_pairs_from_original=len(birth_offsets) - len(checked),
        authored_player_counts=dict(sorted(owners.items())),
        tracker_byte_equal=True,
        recorded_owner_change_events_for_authored_tags=len(later_changes),
        distinct_authored_tags_with_recorded_owner_change=len(
            {(e["m_unitTagIndex"], e["m_unitTagRecycle"]) for e in later_changes}
        ),
    )
