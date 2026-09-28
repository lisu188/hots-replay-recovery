from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path


def read_base64(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="ascii")
    parts = sorted(path.parent.glob(path.name + ".part*"))
    if not parts:
        raise FileNotFoundError(path)
    return "".join(part.read_text(encoding="ascii") for part in parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base64_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--sha256", type=Path)
    args = parser.parse_args()

    raw = base64.b64decode(read_base64(args.base64_path))
    args.output_path.write_bytes(raw)

    if args.sha256:
        expected = args.sha256.read_text(encoding="ascii").split()[0].lower()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA-256 mismatch: expected {expected}, got {actual}")


if __name__ == "__main__":
    main()
