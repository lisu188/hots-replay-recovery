from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import tempfile
from pathlib import Path


def read_base64(path: Path) -> str:
    parts = sorted(path.parent.glob(path.name + '.part*'))
    if path.is_file():
        if parts:
            raise ValueError('Ambiguous artifact: both a full file and parts exist')
        return path.read_text(encoding='ascii')
    if not parts:
        raise FileNotFoundError(path)
    expected = [path.name + f'.part{i:03d}' for i in range(len(parts))]
    if [part.name for part in parts] != expected:
        raise ValueError('Base64 parts are missing, misnumbered or unexpectedly named')
    return ''.join(part.read_text(encoding='ascii') for part in parts)


def restore(base64_path: Path, output_path: Path, sha256_path: Path | None = None) -> str:
    base64_path, output_path = Path(base64_path), Path(output_path)
    encoded = ''.join(read_base64(base64_path).split())
    raw = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if sha256_path is not None:
        tokens = Path(sha256_path).read_text(encoding='ascii').split()
        if not tokens or not re.fullmatch(r'[0-9a-fA-F]{64}', tokens[0]):
            raise ValueError('Invalid SHA-256 sidecar')
        if digest != tokens[0].lower():
            raise ValueError(f'SHA-256 mismatch: expected {tokens[0].lower()}, got {digest}')
    inputs = [base64_path] + list(base64_path.parent.glob(base64_path.name + '.part*'))
    if sha256_path is not None:
        inputs.append(Path(sha256_path))
    if output_path.resolve() in {p.resolve() for p in inputs}:
        raise ValueError('Output cannot overwrite an artifact input')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output_path.parent, prefix=output_path.name + '.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('base64_path', type=Path)
    parser.add_argument('output_path', type=Path)
    parser.add_argument('--sha256', type=Path)
    args = parser.parse_args()
    print(restore(args.base64_path, args.output_path, args.sha256))


if __name__ == '__main__':
    main()
