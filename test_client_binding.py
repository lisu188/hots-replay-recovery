import base64
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from bind_client_metadata import apply_metadata, bind, publish_binary
from encoders import encode_header
from migrate_replay import decode_events, encode_events, write_json
from mpq_reader import MPQArchive
from mpq_rebuild import rebuild_replay
from reference_replay import inspect_reference
import protocol44256

FIXTURE = Path('checkpoints/44256/TEN_GREYMANE_protocol44256.StormReplay')


class MetadataBindingTests(unittest.TestCase):
    def setUp(self):
        self.header = {'m_version': {'m_build': 96477}, 'm_dataBuildNum': 41810,
                       'm_ngdpRootKey': {'m_data': b'A' * 16},
                       'm_replayCompatibilityHash': {'m_data': b'B' * 16},
                       'm_elapsedGameLoops': 19732}
        self.events = [{'_event': 'NNet.Game.SUserOptionsEvent', 'm_buildNum': 96477,
                        'm_baseBuildNum': 96477, 'm_versionFlags': 0, '_gameloop': 0}
                       for _ in range(10)]
        self.events.append({'_event': 'NNet.Game.SCmdEvent', 'm_cmdFlags': 2097408,
                            'm_abil': {'m_abilLink': 7}, '_gameloop': 41810})
        self.profile = {'observed_payload_roundtrip': True, 'file_sha256': '1' * 64,
                        'target': {'m_version': {'m_build': 98025}, 'm_dataBuildNum': 98025,
                                   'm_ngdpRootKey': {'m_data': b'C' * 16},
                                   'm_replayCompatibilityHash': {'m_data': b'D' * 16}},
                        'user_options': {'m_buildNum': 98025, 'm_baseBuildNum': 98025,
                                         'm_versionFlags': 1}}

    def test_changes_only_header_identifiers_and_player_version_options(self):
        original_header, original_events = copy.deepcopy(self.header), copy.deepcopy(self.events)
        header, events, changes = apply_metadata(self.header, self.events, self.profile)
        self.assertEqual(self.header, original_header)
        self.assertEqual(self.events, original_events)
        self.assertEqual(header['m_elapsedGameLoops'], 19732)
        self.assertEqual(events[-1], original_events[-1])
        self.assertEqual(len(events), len(original_events))
        self.assertEqual(len(changes), 34)

    def test_requires_validated_reference_bytes(self):
        self.profile['observed_payload_roundtrip'] = False
        with self.assertRaises(ValueError):
            apply_metadata(self.header, self.events, self.profile)

    def test_requires_reference_hash(self):
        self.profile['file_sha256'] = ''
        with self.assertRaises(ValueError):
            apply_metadata(self.header, self.events, self.profile)

    def test_requires_exactly_ten_source_players(self):
        with self.assertRaises(ValueError):
            apply_metadata(self.header, self.events[1:], self.profile)

    def test_existing_experiment_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileExistsError):
            bind(Path('missing'), Path('missing'), Path(directory), 98025)

    def test_base64_parts_reconstruct_the_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test-only.StormReplay'
            raw = bytes(range(256)) * 300
            path.write_bytes(raw)
            report = publish_binary(path)
            parts = sorted(path.parent.glob('*.base64.part*'))
            self.assertGreater(len(parts), 1)
            actual = base64.b64decode(''.join(''.join(p.read_text().split()) for p in parts), validate=True)
            self.assertEqual(actual, raw)
            self.assertEqual(report['sha256'], hashlib.sha256(raw).hexdigest())


@unittest.skipUnless(FIXTURE.is_file() and importlib.util.find_spec('mpyq'), 'Restore fixture and install mpyq')
class BindingIntegrationTests(unittest.TestCase):
    def test_synthetic_donor_is_a_test_fixture_not_a_playback_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            donor = root / 'SYNTHETIC_TEST_ONLY.StormReplay'
            archive = MPQArchive(FIXTURE)
            try:
                header = protocol44256.decode_replay_header(archive.header['user_data_header']['content'])
                header['m_version']['m_build'] = 44257
                header['m_version']['m_baseBuild'] = 44257
                header['m_dataBuildNum'] = 44257
                header['m_ngdpRootKey']['m_data'] = b'SYNTHETIC_ONLY_1'
                header['m_fixedFileHash']['m_data'] = b'SYNTHETIC_ONLY_2'
                events = list(decode_events(archive.read_file('replay.game.events'), protocol44256, 'game'))
                for event in events:
                    if event['_event'] == 'NNet.Game.SUserOptionsEvent':
                        event['m_buildNum'] = event['m_baseBuildNum'] = 44257
                rebuild_replay(FIXTURE, donor, encode_header(header, protocol44256),
                               {'replay.game.events': encode_events(events, protocol44256, 'game')})
            finally:
                archive.close()
            output = root / 'TEST_ONLY_result'
            result = bind(FIXTURE.parent, donor, output, 44257, local=True)
            self.assertFalse(result['client_playback_validated'])
            self.assertFalse(result['simulation_compatibility_validated'])
            self.assertEqual(result['events']['game'], 104257)
            self.assertTrue(result['checks']['untouched_members_equal'])
            self.assertTrue(result['checks']['mpyq_all_members_equal'])
            inspected = inspect_reference(output / 'TEN_GREYMANE_client44257_EXPERIMENTAL.StormReplay',
                                          44256, 44257, local=True)
            self.assertEqual(inspected['file_sha256'], result['artifact']['sha256'])
            write_json(Path('work') / 'binding-integration-test.json',
                       {'synthetic_test_only': True, 'source_fixture': 44256, 'candidate': result,
                        'this_is_not_a_real_target_build_validation': True})


if __name__ == '__main__':
    unittest.main()
