"""Check public longitudinal controls with their own build's protocol and physical game member."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha1, sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from urllib.parse import quote

from encoders import encode_game_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from fetch_transition_fixtures import CASES

UPSTREAM = "9af3ea7150f1a8acb53464c92519a9bbcc7a3594"
# LF Git blobs verified directly at the original Blizzard revision above.
SCHEMAS = {
    47479: "d000ba135ca9983eea1a878d65141dea1211c4da22945bf20fd5ac3aabf3652d",
    59799: "5064b1fa17ac806c10f8e5bd9c685fad8a70b6b46466e04e0a6e76d0c6589588",
    65006: "9eba5b09122e3bb6825bac9809cc54d884a59436efe1f059eae215d36a40b9cb",
    66488: "c2c264dbe4d1ba21e5c4d1702f17b48477482217951b51ebd1984174130d1b90",
    68509: "a2cd7a34b6d8869a13da50bfef2b4921195dce15aa1c236b238d65b464891e9c",
    75589: "e210cea98c6202bbb22ee3af33dd668dc4815fb720498c5e63d6c62978f119c6",
}


def count(path, expected_git, schema_dir):
    body = path.read_bytes()
    if sha1(f"blob {len(body)}\0".encode() + body).hexdigest() != expected_git:
        raise ValueError("Unexpected Git object")
    with closing(MPQArchive(path)) as arc:
        content = arc.header["user_data_header"]["content"]
        header = load_protocol(96477).decode_replay_header(content)
        b = header["m_version"]["m_baseBuild"]
        if header["m_version"]["m_build"] != b or header["m_dataBuildNum"] != b:
            raise ValueError("Different protocol and data builds")
        schema = schema_dir / f"protocol{b}.py"
        schema_hash = sha256(schema.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if schema_hash != SCHEMAS.get(b):
            raise ValueError("Unexpected original protocol source")
        spec = spec_from_file_location(f"fixture_protocol{b}", schema)
        protocol = module_from_spec(spec)
        spec.loader.exec_module(protocol)
        own_header = protocol.decode_replay_header(content)
        if (own_header["m_version"], own_header["m_dataBuildNum"]) != (header["m_version"], b):
            raise ValueError("Build-specific header disagrees")
        raw = arc.read_file("replay.game.events")
    events = list(protocol.decode_replay_game_events(raw))
    if sum(e["_bits"] for e in events) != len(raw)*8 or encode_game_events(events, protocol) != raw:
        raise ValueError("Replay's exact build schema did not reproduce its complete game member")
    issues = defaultdict(list)
    seqs = defaultdict(set)
    states = Counter()
    for i, e in enumerate(events):
        if e["_eventid"] == 27:
            if e["_event"] != "NNet.Game.SCmdEvent" or e["m_sequence"] is None:
                raise ValueError("Unexpected issue frame")
            u, seq = e["_userid"]["m_userId"], e["m_sequence"]
            issues[u, seq].append(i)
            seqs[u].add(seq)
    observed = defaultdict(Counter)
    earlier = Counter()
    example = {}
    for i, e in enumerate(events):
        k = e["_eventid"]
        if k not in (103, 104, 105):
            continue
        kind = str(k) if k != 103 else f"103/state{e['m_state']}"
        if k == 103:
            states[e["m_state"]] += 1
        u, seq = e["_userid"]["m_userId"], e["m_sequence"]
        existing = issues.get((u, seq), ())
        if seq is None:
            label = "omitted"
        elif not existing:
            label = "no_same_user_issue_anywhere"
        elif len(existing) != 1:
            label = "multiple_same_user_issues"
        elif existing[0] >= i:
            label = "only_later_issue"
        else:
            label = "unique_earlier_issue"
        observed[kind][label] += 1
        if existing and existing[0] < i:
            earlier[kind] += 1
        if k != 103 or e["m_state"] not in (1, 2) or seq is None:
            continue
        key = kind + "/" + label
        if key in example:
            continue
        by_seq = sorted(seqs[u])
        j = bisect_left(by_seq, seq)
        example[key] = dict(manager_ordinal=i, loop=e["_gameloop"], user_index=u, sequence=seq,
                            matching_issue_ordinals=list(existing),
                            previous_issued_numeric_value=by_seq[j-1] if j else None,
                            next_issued_numeric_value=next((q for q in by_seq[j:] if q > seq), None))
    return dict(physical_build=b, replay_sha256=sha256(body).hexdigest(), replay_bytes=len(body),
                protocol_git_lf_sha256=schema_hash, protocol_commit=UPSTREAM,
                game_member_sha256=sha256(raw).hexdigest(), game_member_bytes=len(raw),
                full_game_roundtrip=True, events=len(events), issues=sum(map(len, issues.values())),
                different_user_sequence_pairs=len(issues),
                command_manager_states=dict(sorted(states.items())), reference_outcomes=dict(observed),
                references_with_any_earlier_same_user_issue={k: earlier[k] for k in observed},
                first_examples=example)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("schema_dir", type=Path)
    p.add_argument("private_directory", type=Path)
    a = p.parse_args()
    rows = []
    for (repo, ref, prefix), name, digest, size in CASES:
        f = a.private_directory / (digest+".private.StormReplay")
        r = count(f, digest, a.schema_dir)
        if r["replay_bytes"] != size:
            raise ValueError("Fixture size changed")
        r.update(source=f"https://github.com/{repo}/blob/{ref}/" + quote(prefix+name), git_blob_sha1=digest)
        rows.append(r)
    print(json.dumps(sorted(rows, key=lambda r: r["physical_build"]), indent=2))
