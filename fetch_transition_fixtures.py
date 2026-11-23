"""Retrieve only the pinned public test artifacts and verify their Git object identities."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1
from pathlib import Path
import urllib.request
from urllib.parse import quote

NEXUS = "MJLang/Nexus", "4784e0a2555a675fd870790a2a27fa6158e99902", "test/support/"
HTC = ("HeroesToolChest/Heroes.StormReplayParser", "d381dd9c273205c0fd7ac402c75eef98c6fa6c78",
       "Tests/Heroes.StormReplayParser.Tests/Replays/")
CASES = [
    (NEXUS, "dragon_shire.StormReplay", "a857a59ebfe031a2d7d2d32dca222cc9fc4126b9", 581465),
    (HTC, "AIDragonShire1_75589.StormR", "cc5bcbe07c3d112949d32828972e26f87bef89f5", 146976),
    (HTC, "CustomHGC2018BattlefieldofEternity1_68509.StormR", "8f02e0aeee7f0a7b2121b7e977282e8de668c7be", 1447659),
    (("nexus-devtools/heroprotocoldocs", "c9a2bbe20b6a1debee70dcea157385db2f13ba74", "public/"),
      "Garden of Terror (122).StormReplay", "e9d9c5dfaddd077104782b903e90238efe753a61", 3393674),
    (HTC, "CustomBattlefieldofEternity1_65006.StormR", "b1907f8c8f51f25afb3ff3add1b58458660d46dd", 2762215),
    (("nydus/heroprotocol", "08d8f6b68cfa1258dea5da2a8d9e258d98ccba3d", "test/replays/"),
      "towers-of-doom.StormReplay", "6a554be1dd6a51a422ceb630c9ed692c46297284", 2183482),
]

def fetch(case, directory):
    (repo, ref, prefix), name, digest, size = case
    dst = directory / (digest + ".private.StormReplay")
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/" + quote(prefix + name)
    if dst.exists():
        body = dst.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=20) as response:
            body = response.read(size + 1)
    if len(body) != size or sha1(f"blob {size}\0".encode() + body).hexdigest() != digest:
        raise ValueError("Unexpected public Git object")
    if not dst.exists():
        with dst.open("xb") as f:
            f.write(body)
    return name, size


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_directory", type=Path)
    args = parser.parse_args()
    args.private_directory.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(3) as pool:
        print(list(pool.map(lambda case: fetch(case, args.private_directory), CASES)))
