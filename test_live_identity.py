from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repair_live_identity import latest_observation, observe_graphics, repair, restore_json, validate_target


def log(build=98285, when='2026-09-29 08:11:46.680'):
    lines = [f'Executable C:\\Game\\Versions\\Base{build}\\HeroesOfTheStorm_x64.exe',
             f'<Version> 2.57.0.{build}', f'<DataBuild> B{build}',
             'Grandparent Executable C:\\Battle.net\\Battle.net.exe',
             '<Parameters> -sso=1 -launch -uid heroes',
             f'LocalTime {when}', '<CodeRevision> 668324',
             '<ComputerUser> private-user', '<ComputerName> private-machine']
    return ('\ufeff' + '\n'.join('GFX  08:11:46.680 ' + line for line in lines) + '\n').encode('utf-8')


class ObservationTests(unittest.TestCase):
    def test_current_live_build_is_98285(self):
        value = observe_graphics(log())
        self.assertEqual((value['version'], value['data_build']), ('2.57.0.98285', 98285))

    def test_later_lower_build_wins_over_larger_installed_build(self):
        earlier = observe_graphics(log(98297, '2026-09-29 06:28:13.216'))
        later = observe_graphics(log())
        self.assertEqual(latest_observation([later, earlier])['executable_build'], 98285)

    def test_empty_observations_rejected(self):
        with self.assertRaises(ValueError):
            latest_observation([])

    def test_conflicting_timestamps_rejected(self):
        with self.assertRaises(ValueError):
            latest_observation([observe_graphics(log()), observe_graphics(log(98297))])

    def test_replay_switch_is_not_ordinary_launch(self):
        raw = log().replace(b'Grandparent Executable C:\\Battle.net\\Battle.net.exe',
                            b'Grandparent Executable C:\\Game\\Versions\\Base98297\\HeroesOfTheStorm_x64.exe')
        with self.assertRaises(ValueError):
            observe_graphics(raw)

    def test_version_conflicts_rejected(self):
        with self.assertRaises(ValueError):
            observe_graphics(log().replace(b'<Version> 2.57.0.98285', b'<Version> 2.57.0.98297'))

    def test_data_conflicts_rejected(self):
        with self.assertRaises(ValueError):
            observe_graphics(log().replace(b'<DataBuild> B98285', b'<DataBuild> B98297'))

    def test_duplicate_field_rejected(self):
        with self.assertRaises(ValueError):
            observe_graphics(log() + b'GFX  08:11:46.680 <Version> 2.57.0.98285\n')

    def test_partial_log_rejected(self):
        with self.assertRaises(ValueError):
            observe_graphics(b'GFX  08:11:46.680 <Version> 2.57.0.98285\n')

    def test_oversized_log_rejected(self):
        with self.assertRaises(ValueError):
            observe_graphics(b'X' * 1048577)

    def test_private_fields_are_not_exported(self):
        raw = json.dumps(observe_graphics(log()))
        for private in ('private-user', 'private-machine', 'C:', 'parameters'):
            self.assertNotIn(private, raw)

    def test_no_live_arguments_rejected(self):
        with self.assertRaises(ValueError):
            observe_graphics(log().replace(b'-sso=1 -launch -uid heroes', b'-LocaleIdData enUS'))


class TargetTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parent / 'client-checkpoints/98285/reference-profile.json'
        self.profile = restore_json(json.loads(path.read_text()))
        self.observation = observe_graphics(log())

    def test_real_reference_profile_matches_newer_observation(self):
        validate_target(self.profile, self.observation)

    def test_stale_98297_observation_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(self.profile, observe_graphics(log(98297)))

    def test_config_hash_is_not_substituted_for_observed_zero_hash(self):
        self.profile['target']['m_replayCompatibilityHash']['m_data'] = bytes.fromhex('417671b923a5ca0bad0f5bec63c2a68e')
        with self.assertRaises(ValueError):
            validate_target(self.profile, self.observation)

    def test_wrong_reference_digest_rejected(self):
        self.profile['file_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            validate_target(self.profile, self.observation)

    def test_wrong_reference_root_rejected(self):
        self.profile['target']['m_ngdpRootKey']['m_data'] = b'X' * 16
        with self.assertRaises(ValueError):
            validate_target(self.profile, self.observation)

    def test_unvalidated_profile_rejected(self):
        self.profile['observed_payload_roundtrip'] = False
        with self.assertRaises(ValueError):
            validate_target(self.profile, self.observation)

    def test_malformed_base64_rejected(self):
        with self.assertRaises(ValueError):
            restore_json({'$bytes_base64': 'NOT!BASE64'})

    def test_existing_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                repair(Path('missing'), Path('missing'), Path('missing'), Path('missing'), Path(directory))

    def test_wrong_input_produces_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / 'invalid'
            source.write_bytes(b'wrong source')
            with self.assertRaises(ValueError):
                repair(source, Path('missing'), Path('missing'), Path('missing'), path / 'output')
            self.assertFalse((path / 'output').exists())


if __name__ == '__main__':
    unittest.main()
