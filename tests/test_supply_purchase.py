import unittest
from unittest.mock import Mock, patch

from inventory import MEDKIT, LIGHT_BOMB
from player import Player
from upgrades import ManagementVisit


class SupplyPurchaseTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.player = Player(400, 96)
        self.player.fragments = 5
        self.visit = ManagementVisit()

    def test_upgrade_first_keeps_compulsory_upgrade_funds(self):
        for selection in (0, 1):
            self.assertFalse(self.visit.purchase_supply(self.player, selection))
        self.assertEqual(self.player.fragments, 5)
        self.assertEqual(self.player.inventory.snapshot(), (0, 0, 0, 0))
        self.assertIn('강화', self.visit.notice)

    def test_each_supply_costs_one_and_does_not_use_item_or_change_selected_slot(self):
        self.visit.purchase(self.player, 1)
        self.player.health, self.player.battery = 1, 30
        self.player.inventory.select(3)
        for selection, slot in ((0, MEDKIT), (1, LIGHT_BOMB)):
            self.assertTrue(self.visit.purchase_supply(self.player, selection))
            self.assertEqual(self.player.inventory.counts[slot], 1)
        self.assertEqual((self.player.fragments, self.player.health, self.player.battery), (1, 1, 30))
        self.assertEqual(self.player.inventory.selected, 3)
        self.assertEqual(self.player.core_upgrades, {'focus'})

    def test_repeat_purchases_stop_at_per_type_limit_without_cost(self):
        self.visit.purchase(self.player, 0)
        for _ in range(2):
            self.assertTrue(self.visit.purchase_supply(self.player, 0))
        before = self.player.fragments
        self.assertFalse(self.visit.purchase_supply(self.player, 0))
        self.assertEqual((self.player.medkits, self.player.fragments), (2, before))
        self.assertIn('한도', self.visit.notice)
        self.assertTrue(self.visit.purchase_supply(self.player, 1))

    def test_insufficient_and_invalid_selections_leave_currency_and_inventory_unchanged(self):
        self.visit.purchase(self.player, 2)
        self.player.fragments = 0
        for selection in (0, 1, -1, 2, 10):
            self.assertFalse(self.visit.purchase_supply(self.player, selection))
        self.assertEqual(self.player.fragments, 0)
        self.assertEqual(self.player.inventory.snapshot(), (0, 0, 0, 0))


if __name__ == '__main__':
    unittest.main()
