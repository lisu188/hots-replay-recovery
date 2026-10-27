import unittest

from native_command_target_gate import selected_target_gate


class NativeCommandTargetGateTests(unittest.TestCase):
    def test_none_target_counterfactual_class_table(self):
        self.assertEqual([selected_target_gate(0x80100, 0, c) for c in range(4)],
                         [True, False, False, False])
        self.assertEqual([selected_target_gate(0x40100, 0, c) for c in range(4)],
                         [False, True, True, True])

    def test_context_bit2_changes_only_class2_result(self):
        self.assertFalse(selected_target_gate(0x80100, 0, 2, False))
        self.assertTrue(selected_target_gate(0x80100, 0, 2, True))
        self.assertFalse(selected_target_gate(0x40100, 0, 0, True))

    def test_point_and_unit_classes(self):
        self.assertEqual([selected_target_gate(0x100, 1, c) for c in range(4)],
                         [False, False, True, True])
        self.assertEqual([selected_target_gate(0x100, 2, c) for c in range(4)],
                         [False, True, False, True])

    def test_bit23_only_affects_selected_class0_branch(self):
        self.assertFalse(selected_target_gate(0x800100, 0, 0))
        for c in (1, 2, 3):
            self.assertEqual(selected_target_gate(0x100, 2, c), selected_target_gate(0x800100, 2, c))

    def test_bit19_is_not_an_input_to_this_selected_block(self):
        for target in range(4):
            for c in range(4):
                self.assertEqual(selected_target_gate(0x100, target, c), selected_target_gate(0x80100, target, c))

    def test_invalid_domains_are_rejected(self):
        for args in ((True, 0, 0), (-1, 0, 0), (1 << 26, 0, 0), (0, True, 0),
                     (0, 4, 0), (0, 0, True), (0, 0, 4), (0, 0, 0, 1)):
            with self.assertRaises(ValueError):
                selected_target_gate(*args)


if __name__ == '__main__':
    unittest.main()
