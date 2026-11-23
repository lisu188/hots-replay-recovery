"""Identify changes to command-event layouts across the original Blizzard protocol definitions."""
import argparse
import ast
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import tarfile

UPSTREAM = "9af3ea7150f1a8acb53464c92519a9bbcc7a3594"


def shape(types, index):
    kind, args = types[index]
    if kind == "_struct":
        return [kind, [[name, shape(types, child), tag] for name, child, tag in args[0]]]
    if kind == "_optional":
        return [kind, shape(types,args[0])]
    if kind == "_choice":
        return [kind, args[0], [[k,name,shape(types,child)] for k,(name,child) in sorted(args[1].items())]]
    if kind == "_array":
        return [kind,args[0],shape(types,args[1])]
    if kind not in ("_int","_bool","_null","_blob","_bitarray","_fourcc","_real32","_real64"):
        raise ValueError(f"Unknown command field codec {kind}")
    return [kind,args]


def layouts(source):
    assignments = {}
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
            if node.targets[0].id in ("typeinfos","game_event_types"):
                assignments[node.targets[0].id] = ast.literal_eval(node.value)
    result = {}
    for event in (27,103,104,105):
        tid,name = assignments["game_event_types"][event]
        fields = shape(assignments["typeinfos"],tid)
        if fields[0] != "_struct":
            raise ValueError(f"Unexpected root for {name}")
        result[event] = (name, fields[1])
    return result


def original_definitions(repository):
    tree = subprocess.run(["git","-C",str(repository),"archive","--format=tar",UPSTREAM,
                           "heroprotocol/versions"],check=True,stdout=subprocess.PIPE).stdout
    with tarfile.open(fileobj=io.BytesIO(tree),mode="r:") as archive:
        for member in archive:
            name = Path(member.name)
            if member.isfile() and name.suffix == ".py" and name.stem.startswith("protocol"):
                number = name.stem.removeprefix("protocol")
                if number.isdecimal() and 39445 <= int(number) <= 96477:
                    yield int(number),archive.extractfile(member).read()


def scan(repository):
    prior = None
    ranges = []
    count = 0
    for build, source in sorted(original_definitions(repository)):
        current = layouts(source)
        count += 1
        if current != prior:
            changed = {}
            for event,(name,fields) in current.items():
                old = {} if prior is None else {f[0]:f[1:] for f in prior[event][1]}
                new = {f[0]:f[1:] for f in fields}
                diff = [k for k in dict.fromkeys([*old,*new]) if old.get(k) != new.get(k)]
                if diff:
                    changed[event] = diff
            digest = sha256(json.dumps(current,separators=(",",":"),sort_keys=True).encode()).hexdigest()
            flags = dict((f[0],f[1]) for f in current[27][1])["m_cmdFlags"]
            ranges.append(dict(first=build,last=build,definitions=1,changed_fields=changed,
                               issue_flag_width=flags[1][0][1],family_sha256=digest))
            prior = current
        else:
            ranges[-1]["last"] = build
            ranges[-1]["definitions"] += 1
    if count != 347:
        raise ValueError("Incomplete original corpus")
    return dict(upstream=UPSTREAM, protocol_definitions=count, ranges=ranges)


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("heroprotocol_repository",type=Path)
    print(json.dumps(scan(cli.parse_args().heroprotocol_repository),indent=2))
