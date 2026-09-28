from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def stream_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def diff_jsonl(before: Path, after: Path, out: Path) -> dict:
    changed = 0
    total = 0
    with before.open(encoding='utf-8') as a, after.open(encoding='utf-8') as b, out.open('w', encoding='utf-8', newline='\n') as o:
        for idx, (la, lb) in enumerate(zip(a, b)):
            total += 1
            if la != lb:
                changed += 1
                o.write(json.dumps({'index': idx, 'before': json.loads(la), 'after': json.loads(lb)}, sort_keys=True, separators=(',', ':')) + '\n')
        if a.readline() or b.readline():
            raise SystemExit('stream lengths differ')
    return {
        'total_events': total,
        'changed_events': changed,
        'before_sha256': stream_hash(before),
        'after_sha256': stream_hash(after),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('before', type=Path)
    p.add_argument('after', type=Path)
    p.add_argument('output_dir', type=Path)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in ['game.events.jsonl', 'message.events.jsonl', 'tracker.events.jsonl']:
        target = args.output_dir / f'{name}.changes.jsonl'
        report[name] = diff_jsonl(args.before / name, args.after / name, target)
    for name in ['header.json', 'details.json', 'initData.json', 'attributes.events.json']:
        a = json.loads((args.before / name).read_text(encoding='utf-8'))
        b = json.loads((args.after / name).read_text(encoding='utf-8'))
        if a != b:
            (args.output_dir / f'{name}.before.json').write_text(json.dumps(a, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            (args.output_dir / f'{name}.after.json').write_text(json.dumps(b, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        report[name] = {'changed': a != b}
    (args.output_dir / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
