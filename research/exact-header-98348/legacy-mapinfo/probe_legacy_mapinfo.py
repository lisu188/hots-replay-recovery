"""Three pinned sources, one explicit count-width hypothesis; no conversion.

The authenticated CURRENT graph is not an authenticated historical schema.
Only type1828 bounds.bits=7/max=127 are changed in a private research copy.
The production reader/schema and all source archives remain unchanged.
"""
from collections import Counter
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0] = [str(WORK/'native-mapinfo-ready'), str(REPO), str(WORK/'heroprotocol'),
               str(WORK/'python-deps'), str(WORK/'native-mapinfo-review')]
import native_mapinfo as native
from audit_battlelobby_mod_metadata import audit_member
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from verify_native_mapinfo_review import reconstruct, scalar

sha = lambda raw: hashlib.sha256(raw).hexdigest()
CASES = [
    ('original41810', WORK/'TEN_GREYMANE_source_41810.StormReplay',
     'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824', 41810, 41810,
     '83d43a8647bb5ca5caa6f2f09064da55'),
    ('R8', WORK/'native-20261018/TEN_GREYMANE_client98285_RESUMABLE_R8_PARTIAL.StormReplay',
     '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19', 96477, 98285, None),
    ('authenticated39445', WORK/'legacy-39445-control/htc39445.private.StormReplay',
     '32803cf56e4377a18ea74c908af3d840637faeb7803aaca943f8807ade70ba87', 39445, 39445,
     'b3959e128489be464b4ef50eb6259480')]
SCHEMAS = {41810:'879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',
           96477:'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84',
           39445:'0898b2e8608c58b24a4a8f71585af7a028a0265d4d61a8074c124de97a577148'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounded(path, limit):
    require(not path.is_symlink(), 'Symlink input refused')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(1 <= before.st_size <= limit, 'Input size bound differs')
        raw = stream.read(limit+1)
        after = os.fstat(stream.fileno())
    require(len(raw) == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
            'Input changed during read')
    return raw


class RAMArchive(MPQArchive):
    def __init__(self, raw):
        self.file = BytesIO(raw)
        self.header = self.read_header()
        self.hash_table = self.read_table('hash')
        self.block_table = self.read_table('block')


class TracedDecoder(native.shared._Decoder):
    def __init__(self, schema, raw, start):
        super().__init__(schema, raw, start)
        self.failure = None
    def decode(self, identifier, path='', depth=0):
        position = self.reader.position
        record = self.schema.records[identifier]
        try:
            return super().decode(identifier, path, depth)
        except Exception as error:
            if self.failure is None:
                self.failure = {'field_path': path, 'type_id': identifier, 'kind': record['kind'],
                                'start_bit': position, 'reader_bit_at_failure': self.reader.position,
                                'exception_class': type(error).__name__, 'exception_message_emitted': False}
                if identifier == 1828 and len(self.tokens) and self.tokens[-1].width == 31:
                    count = self.tokens[-1].value
                    self.failure.update(permission_count_positive=count > 0,
                        implied_permission_payload_bits=count*96,
                        implied_payload_exceeds_remaining_member=self.reader.position+count*96 > len(self.reader.raw)*8)
            raise


def protocol_for(version):
    if version != 39445:
        result = load_protocol(version)
        require(result.recovery_schema_sha256 == SCHEMAS[version], 'Official pinned protocol differs')
        return result
    path = WORK/'legacy-39445-control/protocol39445.canonical-private.py'
    require(sha(bounded(path, 64*1024)) == SCHEMAS[39445], 'Canonical39445 source differs')
    spec = importlib.util.spec_from_file_location('_hypothesis_protocol39445', path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def fields_by_path(decoder):
    return {field.path: field for field in decoder.fields if field.kind != 'USER'}


def analyze():
    pinned_paths = [Path(__file__), Path(native.__file__), Path(native.shared.__file__),
        WORK/'native-mapinfo-ready/native_mapinfo_schema_98348.json',
        WORK/'native-mapinfo-review/verify_native_mapinfo_review.py',
        REPO/'audit_battlelobby_mod_metadata.py', REPO/'battlelobby_arcade_sections.py',
        REPO/'battlelobby_attribute_layer.py', REPO/'mpq_reader.py']
    source_pins = {path.name: sha(bounded(path, 256*1024)) for path in pinned_paths}
    authenticated = native._schema()
    modified = deepcopy(authenticated.records)
    modified[1828]['bounds']['bits'] = 7
    modified[1828]['bounds']['max'] = 127
    expected = deepcopy(authenticated.records)
    expected[1828]['bounds'].update(bits=7, max=127)
    require(modified == expected, 'Unexpected research graph change')
    hypothesis = SimpleNamespace(records=modified)
    rows = []
    disk_reads = 0
    private_candidate_tokens = []
    for label, path, expected_sha, protocol_version, build, root in CASES:
        source = bounded(path, 3*1024*1024)
        disk_reads += len(source)
        require(sha(source) == expected_sha, 'Pinned archive differs')
        archive = RAMArchive(source)
        try:
            protocol = protocol_for(protocol_version)
            header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
            require(header['m_version']['m_build'] == build, 'Executable header differs')
            if root is not None:
                require(header['m_ngdpRootKey']['m_data'].hex() == root, 'Header root differs')
            require(all(block.size <= 8*1024*1024 for block in archive.block_table), 'Decoded member cap differs')
            raw = archive.read_file('replay.server.battlelobby')
            require(type(raw) is bytes and 1 <= len(raw) <= 8*1024*1024, 'Member bound differs')
            baseline = audit_member(raw, 'legacy-10', 'historical-fixed')
            expected_entries = 6 if protocol_version == 39445 else 5
            require(baseline['same_profile_full_member_roundtrip_exact'] and len(baseline['entries']) == expected_entries,
                    'Historical baseline entry count differs')
            outcomes = []
            case_tokens = []
            for entry in baseline['entries']:
                unmodified = TracedDecoder(authenticated, raw, entry['start_bit'])
                try:
                    unmodified.decode(5852)
                except Exception:
                    current_result = {'status': 'failed', **unmodified.failure}
                else:
                    current_result = {'status': 'decoded', 'end_bit': unmodified.reader.position,
                                      'historical_entry_end_equal': unmodified.reader.position == entry['end_bit']}
                candidate = TracedDecoder(hypothesis, raw, entry['start_bit'])
                try:
                    candidate.decode(5852)
                except Exception:
                    candidate_result = {'status': 'failed', **candidate.failure}
                else:
                    typed = fields_by_path(candidate)
                    position = entry['start_bit']
                    for name in modified[5852]['field_names']:
                        field = typed['/'+name]
                        require(field.start_bit == position, 'Hypothesis root fields not contiguous')
                        position = field.end_bit
                    handle = typed['/m_handle'].value
                    identity_exact = (handle['m_id'],handle['m_version']) == (
                        scalar(raw, entry['start_bit'], 32),scalar(raw, entry['start_bit']+32, 32))
                    view = SimpleNamespace(start_bit=entry['start_bit'], end_bit=candidate.reader.position,
                                           source=raw, tokens=tuple(candidate.tokens))
                    reconstruct(view)
                    section_bindings = []
                    if entry['has_static_arcade_info']:
                        section_bindings = [typed['/m_arcadeGameInfo/value/m_howToPlaySections'].start_bit == entry['how_to_play_section_start_bit'],
                            typed['/m_arcadeGameInfo/value/m_howToPlaySections'].end_bit == entry['how_to_play_section_end_bit'],
                            typed['/m_arcadeGameInfo/value/m_patchNoteSections'].start_bit == entry['patch_note_section_start_bit'],
                            typed['/m_arcadeGameInfo/value/m_patchNoteSections'].end_bit == entry['patch_note_section_end_bit']]
                    end_exact = position == candidate.reader.position == entry['end_bit']
                    require(end_exact and identity_exact and all(section_bindings), 'Derived graph disagrees with baseline boundaries')
                    candidate_result = {'status': 'structurally_consistent', 'all_32_root_fields_contiguous': True,
                        'end_and_handle_pair_equal_baseline': True, 'independent_token_span_reconstruction_exact': True,
                        'arcade_section_boundaries_match_where_present': all(section_bindings),
                        'final_two_widths': [typed['/m_addMultiMod'].end_bit-typed['/m_addMultiMod'].start_bit,
                                             typed['/m_requiredPermissions'].end_bit-typed['/m_requiredPermissions'].start_bit],
                        'permission_count': typed['/m_requiredPermissions'].value}
                    case_tokens.append([(token.width, token.value) for token in candidate.tokens])
                outcomes.append({'index': entry['index'], 'baseline_start_bit': entry['start_bit'],
                    'baseline_end_bit': entry['end_bit'], 'unmodified_current_graph': current_result,
                    'derived_7bit_count_graph': candidate_result})
            private_candidate_tokens.append(case_tokens)
            rows.append({'id': label, 'replay_sha256': expected_sha, 'actual_header_build': build,
                'member_sha256': sha(raw), 'historical_profile': 'historical-fixed',
                'baseline_full_member_roundtrip_exact': True, 'baseline_entries': expected_entries, 'entries': outcomes})
        finally:
            archive.close()
        after = bounded(path, 3*1024*1024)
        disk_reads += len(after)
        require(sha(after) == expected_sha, 'Archive changed after research probe')
    for path in pinned_paths:
        require(sha(bounded(path, 256*1024)) == source_pins[path.name], 'Research source changed')
    return {'format': 'hots-derived-legacy-MapInfo-count-width-hypothesis-v1',
        'changed_current_graph_paths_only': {'records/1828/bounds/bits': {'from': 31, 'to': 7},
                                           'records/1828/bounds/max': {'from': 2147483647, 'to': 127}},
        'authenticated_current_schema_sha256': native.SCHEMA_SHA256, 'source_hashes': source_pins,
        'cases': rows, 'replay_disk_read_bytes_including_before_after_guards': disk_reads,
        'original_R8_hypothesis_wire_tokens_equal_in_order': private_candidate_tokens[0] == private_candidate_tokens[1],
        'all_three_source_before_after_sha256_guards_passed': True,
        'production_profiles_or_schema_modified': False, 'old_schema_authenticated': False,
        'old_to_current_conversion_rule_proven': False, 'client_network_or_PE_used': False,
        'replay_header_or_private_data_written': False,
        'interpretation': 'Only one derived current-graph alteration was tested. A structural fit and exact source-span reencoding do not authenticate historical field names, permission semantics or a transformation. The frozen historical metadata baseline remains independent.'}


if __name__ == '__main__':
    target = HERE/'legacy-MapInfo-count-width-hypothesis.json'
    require(not target.exists() and not target.is_symlink(), 'Refuse replacing report')
    data = (json.dumps(analyze(), indent=2, sort_keys=True)+'\n').encode()
    require(len(data) <= 64*1024, 'Sanitized report exceeds cap')
    with target.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': sha(data)}))
