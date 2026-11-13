import unittest

from inventory import Inventory, MEDKIT, LIGHT_BOMB


class InventoryTests(unittest.TestCase):
    def test_independent_slots_start_empty(self):
        first, second = Inventory(), Inventory()
        first.add(MEDKIT)
        self.assertEqual(first.snapshot(), (1, 0, 0, 0))
        self.assertEqual(second.snapshot(), (0, 0, 0, 0))

    def test_selection_does_not_use_item_and_empty_slot_can_be_selected(self):
        bag = Inventory()
        bag.add(MEDKIT)
        self.assertTrue(bag.select(LIGHT_BOMB))
        self.assertEqual(bag.selected, LIGHT_BOMB)
        self.assertEqual(bag.snapshot(), (1, 0, 0, 0))

    def test_each_type_has_its_own_limit(self):
        bag = Inventory()
        for slot in range(4):
            self.assertTrue(bag.add(slot))
            self.assertTrue(bag.add(slot))
            self.assertFalse(bag.add(slot))
        self.assertEqual(bag.snapshot(), (2, 2, 2, 2))

    def test_empty_use_and_invalid_selection_do_not_mutate(self):
        bag = Inventory()
        self.assertFalse(bag.consume(MEDKIT))
        for slot in (-1, 4):
            self.assertFalse(bag.select(slot))
            self.assertFalse(bag.add(slot))
            self.assertFalse(bag.consume(slot))
        self.assertEqual(bag.selected, MEDKIT)

    def test_snapshot_is_detached_and_restore_validates(self):
        bag = Inventory()
        bag.restore((1, 0, 2, 0))
        saved = bag.snapshot()
        self.assertTrue(bag.consume(LIGHT_BOMB))
        self.assertEqual(saved, (1, 0, 2, 0))
        for invalid in ((1, 0), (0, 0, 3, 0), (True, 0, 0, 0)):
            with self.assertRaises(ValueError):
                bag.restore(invalid)
