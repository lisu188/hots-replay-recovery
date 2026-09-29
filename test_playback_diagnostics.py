import json
import struct
import unittest

from playback_diagnostics import active_installation, analyze_crash, minidump_exception


LOG = '''Heroes of the Storm (B98285)
Executable C:\\Games\\Versions\\Base98285\\HeroesOfTheStorm_x64.exe
Grandparent Executable C:\\Games\\Versions\\Base98297\\HeroesOfTheStorm_x64.exe
<Version> 2.57.0.98285
<BlizzardError.Summary> ACCESS_VIOLATION reading from 0x0000000000000078: DBG-ADDR<0000000000002000>("")
    RCX:0000000000000000
DBG-CODEBYTES< 0000000000002000: 48 8B 41 78 C3 CC CC CC >
'''


def dump_fixture():
    raw = bytearray(600)
    struct.pack_into('<4sIIIIIQ', raw, 0, b'MDMP', 0xA793, 2, 32, 0, 0, 0)
    struct.pack_into('<III', raw, 32, 6, 168, 64)
    struct.pack_into('<III', raw, 44, 7, 56, 232)
    struct.pack_into('<I', raw, 64, 123)
    struct.pack_into('<I', raw, 72, 0xC0000005)
    struct.pack_into('<Q', raw, 88, 0x2000)
    struct.pack_into('<I', raw, 96, 2)
    struct.pack_into('<QQ', raw, 104, 0, 0x78)
    struct.pack_into('<II', raw, 224, 256, 288)
    struct.pack_into('<H', raw, 232, 9)
    struct.pack_into('<I', raw, 336, 0x100003)
    struct.pack_into('<Q', raw, 416, 0)
    struct.pack_into('<Q', raw, 536, 0x2000)
    return raw


class PlaybackDiagnosticTests(unittest.TestCase):
    def test_actual_kind_of_switch_is_not_original_2016_build(self):
        report = analyze_crash(LOG)
        self.assertEqual(report['launcher_build'], 98297)
        self.assertEqual(report['executing_build'], 98285)
        self.assertTrue(report['version_switch_observed'])
        self.assertNotEqual(report['executing_build'], 41810)

    def test_null_read_requires_instruction_and_register_evidence(self):
        self.assertTrue(analyze_crash(LOG)['null_member_read_confirmed'])
        self.assertFalse(analyze_crash(LOG.replace('RCX:0000000000000000', 'RCX:0000000000000010'))['null_member_read_confirmed'])
        self.assertFalse(analyze_crash(LOG.replace('48 8B 41 78', '48 8B 41 70'))['null_member_read_confirmed'])

    def test_immediate_fault_is_not_claimed_as_root_cause(self):
        report = analyze_crash(LOG, bytes(dump_fixture()))
        self.assertTrue(report['minidump_confirms_text_exception'])
        self.assertFalse(report['root_cause_established'])
        self.assertFalse(report['client_playback_validated'])

    def test_private_account_paths_are_excluded(self):
        variables = 'LastAccountName=private@example.invalid\nlastReplayFilePath=C:\\Users\\secret\\OneDrive\\CONTROL.StormReplay\n'
        output = json.dumps(analyze_crash(LOG, variables=variables))
        self.assertIn('CONTROL.StormReplay', output)
        for value in ('private@example.invalid', 'secret', 'C:\\', 'OneDrive'):
            self.assertNotIn(value, output)

    def test_minidump_reads_amd64_registers(self):
        result = minidump_exception(bytes(dump_fixture()))
        self.assertEqual(result['exception_code'], '0xc0000005')
        self.assertEqual(result['access_address'], '0x78')
        self.assertEqual(result['access_operation'], 'read')
        self.assertEqual(result['rcx'], '0x0')
        self.assertEqual(result['rip'], '0x2000')

    def test_all_truncated_dumps_fail_closed(self):
        raw = dump_fixture()
        for length in (0, 4, 31, 50, 100, 167, 240, 400, 540):
            with self.subTest(length=length), self.assertRaises(ValueError):
                minidump_exception(bytes(raw[:length]))

    def test_rejects_out_of_bounds_directory(self):
        raw = dump_fixture()
        struct.pack_into('<I', raw, 12, 0xFFFFFFFF)
        with self.assertRaises(ValueError):
            minidump_exception(bytes(raw))

    def test_rejects_oversized_parameter_count(self):
        raw = dump_fixture()
        struct.pack_into('<I', raw, 96, 16)
        with self.assertRaises(ValueError):
            minidump_exception(bytes(raw))

    def test_rejects_short_context(self):
        raw = dump_fixture()
        struct.pack_into('<I', raw, 224, 255)
        with self.assertRaises(ValueError):
            minidump_exception(bytes(raw))

    def test_rejects_mismatched_text_and_dump(self):
        raw = dump_fixture()
        struct.pack_into('<Q', raw, 112, 0x80)
        with self.assertRaises(ValueError):
            analyze_crash(LOG, bytes(raw))

    def test_missing_registers_do_not_invent_null_read(self):
        report = analyze_crash(LOG.replace('    RCX:0000000000000000\n', ''))
        self.assertIsNone(report['exception']['rcx'])
        self.assertFalse(report['null_member_read_confirmed'])

    def test_partial_or_unrelated_log_is_not_accepted(self):
        with self.assertRaises(ValueError):
            analyze_crash('Graphics initialization succeeded')

    def test_version_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            analyze_crash(LOG.replace('<Version> 2.57.0.98285', '<Version> 2.57.0.98297'))

    def test_build_info_reports_only_selected_fields(self):
        text = 'Active!DEC:1|Version!STRING:0\x7cTags!STRING:0\n1|2.57.0.98297|private-geolocation\n'
        result = active_installation(text)
        self.assertEqual(result['build'], 98297)
        self.assertNotIn('private-geolocation', json.dumps(result))

    def test_build_info_rejects_multiple_active_rows(self):
        with self.assertRaises(ValueError):
            active_installation('Active!DEC:1|Version!STRING:0\n1|2.57.0.98285\n1|2.57.0.98297')

    def test_build_info_rejects_malformed_rows(self):
        with self.assertRaises(ValueError):
            active_installation('Active!DEC:1|Version!STRING:0\n1')

    def test_same_build_is_not_a_version_switch(self):
        self.assertFalse(analyze_crash(LOG.replace('Base98297', 'Base98285'))['version_switch_observed'])


if __name__ == '__main__':
    unittest.main()
