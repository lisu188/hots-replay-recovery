"""Exercise fail-closed cohort validation before iterating private replay inputs."""

from argparse import ArgumentParser
from pathlib import Path
import json
from first_sound_timing import verify_manifest


def verify(cases):
    verify_manifest(cases)
    verify_manifest(list(reversed(cases)))
    path, digest, build = cases[0]
    changes = {
        "empty": [], "omitted": cases[1:], "extra": cases+[cases[0]],
        "substituted_digest": [(path,"0"*64,build),*cases[1:]],
        "substituted_build": [(path,digest,41810 if build==98348 else 98348),*cases[1:]],
        "duplicate_replaced_case": [cases[1],*cases[1:]]
    }
    for name, altered in changes.items():
        try:
            verify_manifest(altered)
        except ValueError:
            continue
        raise ValueError("Cohort accepted "+name)
    return list(changes)


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("manifest",type=Path)
    print(json.dumps(verify(json.loads(parser.parse_args().manifest.read_bytes()))))
