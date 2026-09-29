from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

from runtime_catalog_probe import BUILD, MAP_SHA256, MAX_ENTRIES, Storm

TOKEN = 'HRC98285_20260929_J2'
MAP_NAME = 'TEN_GREYMANE_CATALOG_JOURNAL_98285.StormMap'
LOG_NAME = TOKEN + '.txt'
MAX_BYTES = 8 * 1024 * 1024
BATCH = 64
ANCHORS_SHA256 = '53f70fecc2343f355f67774e9d9694e6dc5f0ac4e0083c83680611da5a2bb7a9'


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def galaxy_source() -> str:
    return r'''
trigger HRCJ_Trigger;
string HRCJ_Session;
int HRCJ_Phase;
int HRCJ_Index;
int HRCJ_Count;
int HRCJ_UnitCount;
int HRCJ_AbilCount;

void HRCJ_Write (string record) {
    TriggerDebugOutput(1, StringToText("@TOKEN@|" + HRCJ_Session + "|" + record), false);
}

void HRCJ_Stop (string reason) {
    HRCJ_Write("FAIL|" + reason);
    TriggerEnable(HRCJ_Trigger, false);
    UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("HOTS CATALOG JOURNAL: FAILED " + reason));
}

bool HRCJ_Tick (bool testConds, bool runActions) {
    int catalog;
    int budget;
    int valid;
    string label;
    string entry;
    if (!runActions) {
        return true;
    }
    if (HRCJ_Phase == 0) {
        HRCJ_Session = IntToString(RandomInt(1, 1073741823)) + "_" + IntToString(RandomInt(1, 1073741823));
        TriggerDebugOutputEnable(true);
        TriggerDebugEnableType(1, true);
        TriggerDebugSetTypeFile(1, "@LOG@");
        HRCJ_Write("BEGIN|@BUILD@|@MAP@");
        HRCJ_UnitCount = CatalogEntryCount(c_gameCatalogUnit);
        HRCJ_AbilCount = CatalogEntryCount(c_gameCatalogAbil);
        if (HRCJ_UnitCount < 1 || HRCJ_UnitCount > @MAX@ || HRCJ_AbilCount < 1 || HRCJ_AbilCount > @MAX@) {
            HRCJ_Stop("catalog_count_out_of_range");
            return true;
        }
        HRCJ_Write("COUNT|Unit|" + IntToString(c_gameCatalogUnit) + "|" + IntToString(HRCJ_UnitCount));
        HRCJ_Write("COUNT|Abil|" + IntToString(c_gameCatalogAbil) + "|" + IntToString(HRCJ_AbilCount));
        HRCJ_Phase = 1;
        HRCJ_Index = 1;
        UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("HOTS CATALOG JOURNAL: exporting Unit and Abil. This is NOT the recovered match."));
        return true;
    }
    if (HRCJ_Phase == 1) {
        catalog = c_gameCatalogUnit;
        label = "Unit";
        HRCJ_Count = HRCJ_UnitCount;
    }
    else {
        catalog = c_gameCatalogAbil;
        label = "Abil";
        HRCJ_Count = HRCJ_AbilCount;
    }
    budget = 0;
    while (HRCJ_Index <= HRCJ_Count && budget < @BATCH@) {
        entry = CatalogEntryGet(catalog, HRCJ_Index);
        if (StringLength(entry) > 240) {
            HRCJ_Stop("entry_name_too_long");
            return true;
        }
        valid = 0;
        if (CatalogEntryIsValid(catalog, entry)) {
            valid = 1;
        }
        HRCJ_Write("ENTRY|" + label + "|" + IntToString(HRCJ_Index) + "|" + IntToString(valid) + "|" + IntToString(StringLength(entry)) + "|" + entry);
        HRCJ_Index = HRCJ_Index + 1;
        budget = budget + 1;
    }
    if (HRCJ_Index > HRCJ_Count) {
        HRCJ_Write("DONE|" + label + "|" + IntToString(HRCJ_Count));
        if (HRCJ_Phase == 1) {
            HRCJ_Phase = 2;
            HRCJ_Index = 1;
            UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("HOTS CATALOG JOURNAL: Unit done, exporting Abil."));
        }
        else {
            HRCJ_Write("END|" + IntToString(HRCJ_UnitCount) + "|" + IntToString(HRCJ_AbilCount));
            HRCJ_Phase = 3;
            TriggerEnable(HRCJ_Trigger, false);
            UIDisplayMessage(PlayerGroupAll(), c_messageAreaSubtitle, StringToText("HOTS CATALOG JOURNAL: export requested. Exit the map, then press Enter in the launcher. File completeness still requires validation."));
        }
    }
    return true;
}

bool HRCJ_Start (bool testConds, bool runActions) {
    if (!runActions) {
        return true;
    }
    HRCJ_Phase = 0;
    HRCJ_Trigger = TriggerCreate("HRCJ_Tick");
    TriggerAddEventTimePeriodic(HRCJ_Trigger, 0.0625, c_timeGame);
    return true;
}

void InitMap () {
    HRCJ_OriginalInitMap();
    TriggerAddEventTimeElapsed(TriggerCreate("HRCJ_Start"), 1.0, c_timeGame);
}
'''.replace('@TOKEN@', TOKEN).replace('@LOG@', LOG_NAME).replace('@BUILD@', str(BUILD)).replace('@MAP@', MAP_SHA256).replace('@MAX@', str(MAX_ENTRIES)).replace('@BATCH@', str(BATCH))


def instrument(raw: bytes) -> bytes:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 1024 * 1024:
        raise ValueError('Unsupported original script size')
    source = raw.decode('utf-8-sig')
    pattern = r'\bvoid\s+InitMap\s*\(\s*\)\s*\{\s*InitLibs\(\);\s*InitGlobals\(\);\s*InitTriggers\(\);\s*\}\s*\Z'
    match = re.search(pattern, source)
    if match is None or 'HRC' in source or len(re.findall(r'\bInitMap\s*\(', source)) != 1:
        raise ValueError('Original initialization differs from the inspected hook')
    pos = source.index('InitMap', match.start())
    return (source[:pos] + 'HRCJ_OriginalInitMap' + source[pos + 7:] + galaxy_source()).encode('utf-8')


def build(source: Path, output: Path, library: str | None = None) -> dict:
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError('A bounded regular source map is required')
    raw = source.read_bytes()
    if digest(raw) != MAP_SHA256:
        raise ValueError('Source is not the hash-bound Dragon Shire map')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output must be a new directory')
    storm = Storm(library)
    before = storm.members(source)
    script = instrument(before['MapScript.galaxy'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.catalog-journal-') as temporary:
        stage = Path(temporary) / 'result'
        stage.mkdir()
        target = stage / MAP_NAME
        target.write_bytes(raw)
        storm.replace(target, {'MapScript.galaxy': script})
        after = storm.members(target)
        if set(before) != set(after):
            raise AssertionError('Map member names changed')
        for name, value in before.items():
            if name not in ('(attributes)', '(listfile)') and after[name] != (script if name == 'MapScript.galaxy' else value):
                raise AssertionError('Unexpected map member change: ' + name)
        report = {'format': 'hots-catalog-journal-map-v1', 'token': TOKEN, 'expected_build': BUILD,
                  'source_sha256': MAP_SHA256, 'map_sha256': digest(target.read_bytes()),
                  'map_bytes': target.stat().st_size, 'members_compared': len(before),
                  'changed_payload_members': ['MapScript.galaxy'], 'bank_list_unchanged': True,
                  'log_name': LOG_NAME, 'max_entries_per_callback': BATCH,
                  'bank_functions_called_by_exporter': False, 'uses_random_session_nonce': True,
                  'debug_channel_one_redirected_in_diagnostic_map': True,
                  'client_playback_validated': False, 'native_galaxy_compilation_verified': False,
                  'runtime_export_observed': False, 'replay_modified': False}
        (stage / 'probe-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        (stage / 'catalog-journal.galaxy').write_text(galaxy_source(), encoding='utf-8')
        (stage / 'MapScript.galaxy').write_bytes(script)
        if source.read_bytes() != raw or output.exists():
            raise ValueError('Source or destination changed during generation')
        stage.rename(output)
    return report


def number(value: str, maximum: int = MAX_ENTRIES) -> int:
    if not isinstance(value, str) or re.fullmatch(r'0|[1-9][0-9]{0,9}', value) is None or int(value) > maximum:
        raise ValueError('Noncanonical or excessive integer')
    return int(value)


def parse_journal(raw: bytes, anchors: dict[str, int]) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError('Journal must be bounded nonempty bytes')
    if not anchors or any(not isinstance(k, str) or not k or type(v) is not int or not 1 <= v <= MAX_ENTRIES for k, v in anchors.items()):
        raise ValueError('Independent unit anchors are required')
    text = raw.decode('utf-8-sig')
    if not text.endswith('\n'):
        raise ValueError('Journal has an unterminated final line')
    session = None
    state = 'begin'
    catalogs = {'Unit': [], 'Abil': []}
    counts, native_ids = {}, {}
    records = 0
    for line in text.splitlines():
        if len(line) > 2048:
            raise ValueError('Journal line exceeds the limit')
        if TOKEN not in line:
            continue
        if line.count(TOKEN) != 1:
            raise ValueError('Ambiguous journal marker')
        fields = line[line.index(TOKEN):].split('|')
        if len(fields) < 3 or fields[0] != TOKEN or re.fullmatch(r'[1-9][0-9]{0,9}_[1-9][0-9]{0,9}', fields[1]) is None:
            raise ValueError('Malformed journal identity')
        a, b = fields[1].split('_')
        number(a, 1073741823)
        number(b, 1073741823)
        if session is None:
            session = fields[1]
        if fields[1] != session:
            raise ValueError('Mixed journal sessions')
        data = fields[2:]
        kind = data[0]
        records += 1
        if records > 2 * MAX_ENTRIES + 6:
            raise ValueError('Too many journal records')
        if kind == 'FAIL':
            raise ValueError('Exporter reported failure')
        if state == 'begin':
            if data != ['BEGIN', str(BUILD), MAP_SHA256]:
                raise ValueError('Missing or wrong journal BEGIN')
            state = 'count_unit'
        elif state in ('count_unit', 'count_abil'):
            label = 'Unit' if state == 'count_unit' else 'Abil'
            if len(data) != 4 or data[:2] != ['COUNT', label]:
                raise ValueError('Missing or reordered catalog count')
            native_ids[label] = number(data[2], 127)
            counts[label] = number(data[3])
            if counts[label] == 0 or (label == 'Abil' and native_ids['Unit'] == native_ids['Abil']):
                raise ValueError('Empty or duplicated native catalog')
            state = 'count_abil' if label == 'Unit' else 'unit'
        elif state in ('unit', 'abil'):
            label = 'Unit' if state == 'unit' else 'Abil'
            rows = catalogs[label]
            if kind == 'ENTRY':
                if len(data) != 6 or data[1] != label or number(data[2]) != len(rows) + 1 or len(rows) >= counts[label]:
                    raise ValueError('Missing, duplicated or reordered catalog index')
                flag = number(data[3], 1)
                length = number(data[4], 240)
                if len(data[5]) != length or re.fullmatch(r'[A-Za-z0-9_@.#:+\-]*', data[5]) is None:
                    raise ValueError('Invalid or truncated catalog identifier')
                rows.append({'index': len(rows) + 1, 'id': data[5], 'valid': bool(flag)})
            elif data == ['DONE', label, str(counts[label])] and len(rows) == counts[label]:
                names = [row['id'] for row in rows if row['id']]
                if len(names) != len(set(names)):
                    raise ValueError('Duplicate nonempty catalog identifier')
                state = 'abil' if label == 'Unit' else 'end'
            else:
                raise ValueError('Incomplete catalog or unexpected record')
        elif state == 'end':
            if data != ['END', str(counts['Unit']), str(counts['Abil'])]:
                raise ValueError('Missing or inconsistent journal END')
            state = 'finished'
        else:
            raise ValueError('Extra journal records after END')
    if state != 'finished':
        raise ValueError('Journal export is incomplete')
    by_id = {row['id']: row['index'] for row in catalogs['Unit'] if row['valid'] and row['id']}
    mismatches = [{'id': name, 'expected_index': index, 'observed_index': by_id.get(name)}
                  for name, index in sorted(anchors.items()) if by_id.get(name) != index]
    return {'format': 'hots-catalog-journal-export-v1', 'token': TOKEN, 'session': session,
            'expected_build': BUILD, 'source_map_sha256': MAP_SHA256, 'journal_sha256': digest(raw),
            'catalogs': catalogs, 'native_catalog_ids': native_ids, 'records': records,
            'reference_anchor_count': len(anchors), 'anchor_mismatches': mismatches,
            'all_unit_anchors_match': not mismatches, 'complete_sequence': True,
            'actual_build_verified': False, 'evidence_is_authenticated': False,
            'ready_for_unit_catalog_review': False,
            'blocking_checks': ['fresh_launch_context_requires_separate_verification'] + ([] if not mismatches else ['unit_anchors_mismatch']),
            'ability_indices_independently_validated': False, 'automatically_applied_to_replay': False,
            'client_playback_validated': False}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    generator = sub.add_parser('build')
    generator.add_argument('source', type=Path)
    generator.add_argument('--output', required=True, type=Path)
    reader = sub.add_parser('read')
    reader.add_argument('journal', type=Path)
    reader.add_argument('--anchors', type=Path, default=Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json')
    reader.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'build':
        result = build(args.source, args.output)
    else:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError('Output already exists')
        if args.journal.is_symlink() or not args.journal.is_file() or not 0 < args.journal.stat().st_size <= MAX_BYTES:
            raise ValueError('A bounded regular journal file is required')
        anchor_bytes = args.anchors.read_bytes()
        if digest(anchor_bytes) != ANCHORS_SHA256:
            raise ValueError('Independent anchors differ from the pinned observation')
        result = parse_journal(args.journal.read_bytes(), json.loads(anchor_bytes)['unit_anchors'])
        with args.output.open('x', encoding='utf-8') as target:
            target.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'catalogs'}, indent=2))


if __name__ == '__main__':
    main()
