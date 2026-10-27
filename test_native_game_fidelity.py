from collections import Counter
import unittest

from audit_native_game_fidelity import _anonymous, _recipe_payload, _tag, audit_game_fidelity, PREFIX
from native_game_events import Choice


class NativeGameFidelityTests(unittest.TestCase):
    def test_tag_repack_preserves_index_and_recycle(self):
        for index, recycle in ((1, 1), (1023, (1 << 18) - 1), (0, 1)):
            old = (index << 18) | recycle
            current = _tag(old)
            self.assertEqual(current >> 22, index)
            self.assertEqual(current & ((1 << 22) - 1), recycle)
        self.assertEqual(_tag(0), 0)
        self.assertEqual(_tag(0xffffffff), 0xffffffff)

    def test_tag_overflow_and_wrong_types_rejected(self):
        for value in ((1024 << 18) | 1, True, -1, 1 << 32):
            with self.assertRaises(ValueError):
                _tag(value)

    def test_existing_flag_collision_is_retained_and_not_hidden(self):
        for before in (0x100100, 0x80100):
            counts = Counter()
            value = {'m_cmdFlags': before, 'm_data': {'None': None}, 'm_otherUnit': None}
            after = _recipe_payload(PREFIX + 'SCmdEvent', value, counts)
            self.assertEqual(after['m_cmdFlags'], 0x80100)
            self.assertNotIn('m_vector', value)
            self.assertIsNone(after['m_vector'])
            self.assertEqual(counts['command_flags_changed'], before == 0x100100)

    def test_mouse_assumption_is_explicit_and_source_unchanged(self):
        value = {'m_eventData': {'MouseButton': 1}}
        counts = Counter()
        after = _recipe_payload(PREFIX + 'STriggerDialogControlEvent', value, counts)
        self.assertEqual(after, {'m_eventData': {'MouseEvent': {'m_button': 1, 'm_metaKeyFlags': 0}}})
        self.assertEqual(value, {'m_eventData': {'MouseButton': 1}})
        self.assertEqual(counts['assumed_zero_mouse_modifier_fields_added'], 1)

    def test_non_mouse_fields_are_not_defaulted(self):
        value = {'m_eventData': {'Checked': False}, 'extra': b'unchanged'}
        self.assertEqual(_recipe_payload(PREFIX + 'STriggerDialogControlEvent', value, Counter()), value)

    def test_only_original_builds_admitted(self):
        value = {'m_buildNum': 41810, 'm_baseBuildNum': 41810}
        self.assertEqual(_recipe_payload(PREFIX + 'SUserOptionsEvent', value, Counter()),
                         {'m_buildNum': 98285, 'm_baseBuildNum': 98285})
        for bad in (True, 98285):
            with self.assertRaises(ValueError):
                _recipe_payload(PREFIX + 'SUserOptionsEvent', {'m_buildNum': bad, 'm_baseBuildNum': 41810}, Counter())

    def test_projection_refuses_extra_missing_or_wrong_choice(self):
        types = [('_struct', [[('value', 1, 0)]]), ('_int', [(0, 3)]),
                 ('_choice', [(0, 1), {0: ('None', 3)}]), ('_null', [])]
        self.assertEqual(_anonymous({'value': 3}, types, 0), (3,))
        self.assertEqual(_anonymous({'None': None}, types, 2), Choice(0, None))
        for value in ({}, {'value': 3, 'extra': 1}):
            with self.assertRaises(ValueError):
                _anonymous(value, types, 0)
        with self.assertRaises(ValueError):
            _anonymous({'Other': None}, types, 2)

    def test_exact_member_gate_precedes_dependencies(self):
        for before, after in ((b'', b''), (bytearray(), b''), (b'x', b'y')):
            with self.assertRaisesRegex(ValueError, 'exact preserved'):
                audit_game_fidelity(before, after)


if __name__ == '__main__':
    unittest.main()
