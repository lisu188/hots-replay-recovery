"""Check recovered command, ping, and tracker fields against the historical-layout receipts."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from camp_owner_wire import sparse_source
from convert_historical_pings import generate as generate_pings
from dragonshire_packages import historical_package_digest
from smartcam_startup import project
from snapshot_wire import generate as generate_points


def verify(source, original, package, mechanics):
    package_sha = historical_package_digest(package)
    with TemporaryDirectory() as temp:
        points = generate_points(original, package, source, Path(temp) / "points")
    pings, ping_info = generate_pings(source, original, package)
    owners, owner_info = sparse_source(source, package, mechanics, 41810)
    camera = project(source, original, package)
    baseline = Path(__file__).resolve().parent / "observations" / "smartcam-initial-endpoints.json"
    expected = json.loads(baseline.read_bytes())["41810"]["projections"]
    if camera["projections"] != expected:
        raise ValueError("Map-backed camera references changed")
    if len({package_sha, points["historical_map_sha256"], ping_info["target_layout_sha256"],
            owner_info["map_sha256"], camera["target_map_sha256"]}) != 1:
        raise ValueError("Different packages used during verification")
    hashes = [points["binary_sha256"], points["index_sha256"],
              sha256(pings).hexdigest(), sha256(owners).hexdigest()]
    if hashes != [
        "1caf663b5823c277735745a7fe528d6b989b0542e4689a4771c4afcf280c5b35",
        "3e073059c7b2cba761860229f8ac78e12d8f4cf388fb76f9fcd197c8c25a5da2",
        "b76ea6aec0b2788e06ee1a4a739a9464f6d1d3ff883cf121ae4f66cf0a61ff2b",
        "b1e10df5fb6534fa52d5a5eae7adb5d85984ce3d6894b4ce256311cd991ed3b0",
    ]:
        raise ValueError("Generated field bytes or source command ordinals changed")
    return dict(package_sha256=package_sha, building_snapshot_fields=points["point_count"],
                map_qualified_pings=ping_info["emitted"], beacon_owner_frames=owner_info["records"],
                verified_initial_camera_endpoints=len(expected), generated_sha256=hashes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "original-map", "map", "mechanics"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.source, args.original_map, args.map, args.mechanics), indent=2))
