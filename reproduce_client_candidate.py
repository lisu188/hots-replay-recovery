from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from bind_client_metadata import publish_binary
from migrate_replay import SOURCE_SHA256, write_json
from mpq_reader import MPQArchive
from mpq_rebuild import rebuild_replay, verify_container
from scripts.restore_artifact import restore

ROOT = Path(__file__).resolve().parent


def apply_edits(data: bytes, edits: list[dict]) -> bytes:
    if not isinstance(edits, list) or len(edits) > 10000:
        raise ValueError('Invalid edit list')
    result = bytearray(data)
    end = 0
    for edit in edits:
        offset = edit['offset']
        before = base64.b64decode(edit['before_base64'], validate=True)
        after = base64.b64decode(edit['after_base64'], validate=True)
        if type(offset) is not int or offset < end or not before or len(before) != len(after):
            raise ValueError('Edits must be ordered, nonoverlapping, nonempty and fixed-width')
        if offset + len(before) > len(data) or data[offset:offset + len(before)] != before:
            raise ValueError('Edit does not match its source bytes')
        result[offset:offset + len(before)] = after
        end = offset + len(before)
    return bytes(result)


def reproduce(recipe_path: Path, output: Path, root: Path = ROOT) -> dict:
    recipe_path, output, root = Path(recipe_path), Path(output), Path(root)
    if output.exists():
        raise FileExistsError('Use a new output directory')
    if recipe_path.stat().st_size > 1024 * 1024:
        raise ValueError('Recipe is too large')
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    if recipe.get('format') != 'hots-verified-member-patch-v1':
        raise ValueError('Unsupported recipe format')
    for key in ('base_build', 'declared_client_build'):
        if type(recipe.get(key)) is not int or not 0 < recipe[key] < 2**32:
            raise ValueError('Invalid recipe build')
    if recipe.get('client_playback_validated') is not False:
        raise ValueError('A reproduction recipe cannot assert playback validation')
    checkpoint = root / 'checkpoints' / str(recipe['base_build'])
    report = json.loads((checkpoint / 'report.json').read_text(encoding='utf-8'))
    if report.get('source_sha256') != SOURCE_SHA256 or report.get('output_sha256') != recipe['base_sha256']:
        raise ValueError('Recipe does not match the independently validated source checkpoint')
    if report.get('independent_validation', {}).get('blizzard_decoded_all_streams') is not True:
        raise ValueError('Independent checkpoint validation is required')
    base_name = f"TEN_GREYMANE_protocol{recipe['base_build']}.StormReplay"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.reproduce-', dir=output.parent) as temporary:
        stage = Path(temporary)
        source = stage / base_name
        restore(checkpoint / (base_name + '.base64'), source, checkpoint / (base_name + '.sha256'))
        if hashlib.sha256(source.read_bytes()).hexdigest() != recipe['base_sha256']:
            raise ValueError('Source replay digest mismatch')
        archive = MPQArchive(source)
        try:
            header = archive.header['user_data_header']['content']
            game = archive.read_file('replay.game.events')
            if hashlib.sha256(header).hexdigest() != recipe['header_before_sha256']:
                raise ValueError('Source header digest mismatch')
            if len(game) != recipe['game_bytes'] or hashlib.sha256(game).hexdigest() != recipe['game_before_sha256']:
                raise ValueError('Source game stream digest mismatch')
            changed = apply_edits(game, recipe['game_edits'])
            if hashlib.sha256(changed).hexdigest() != recipe['game_after_sha256']:
                raise ValueError('Patched game stream digest mismatch')
            target_header = base64.b64decode(recipe['header_after_base64'], validate=True)
            if not 1 <= len(target_header) <= 65536:
                raise ValueError('Invalid target header length')
            candidate_dir = stage / 'candidate'
            candidate_dir.mkdir()
            candidate = candidate_dir / f"TEN_GREYMANE_client{recipe['declared_client_build']}_EXPERIMENTAL.StormReplay"
            rebuild_replay(source, candidate, target_header, {'replay.game.events': changed})
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if digest != recipe['output_sha256']:
                raise ValueError(f'Candidate digest mismatch: {digest}; check recipe and zlib runtime')
            container = verify_container(candidate)
            artifact = publish_binary(candidate)
            result = {'format': 'hots-candidate-reproduction-v1', 'source_sha256': recipe['base_sha256'],
                      'artifact': artifact, 'container': container, 'recipe_sha256': hashlib.sha256(recipe_path.read_bytes()).hexdigest(),
                      'client_playback_validated': False, 'reference_revalidated_this_run': False,
                      'scope': 'Exact reproduction of an already inspected candidate; not a new reference or playback validation.'}
            write_json(candidate_dir / 'reproduction.json', result)
            shutil.copyfile(recipe_path, candidate_dir / 'recipe.json')
            if output.exists():
                raise FileExistsError(output)
            candidate_dir.rename(output)
            return result
        finally:
            archive.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('recipe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.recipe, args.output), indent=2))
