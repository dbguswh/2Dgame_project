import unittest
from unittest.mock import Mock, patch

from player import Player
from progress import ProgressRecords
from residential import ResidentialStage
from upgrades import CAPACITY, FOCUS, SPREAD, CORE_UPGRADES, ManagementVisit


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Player(400, 96)
        self.p.fragments = 2
        self.visit = ManagementVisit()

    def test_capacity_consumes_two_and_changes_maximum_without_free_charge(self):
        self.p.battery = 40
        self.assertTrue(self.visit.purchase(self.p, 0))
        self.assertEqual((self.p.fragments, self.p.max_battery, self.p.battery), (0, 140, 40))
        self.assertEqual(self.p.core_upgrades, {CAPACITY})
        self.assertTrue(self.visit.completed)

    def test_one_purchase_per_visit_even_with_more_fragments(self):
        self.p.fragments = 6
        self.visit.purchase(self.p, 1)
        for choice in (1, 0, 2):
            self.assertFalse(self.visit.purchase(self.p, choice))
        self.assertEqual((self.p.fragments, self.p.core_upgrades), (4, {FOCUS}))

    def test_second_visit_rejects_owned_upgrade_but_allows_another(self):
        self.visit.purchase(self.p, 1)
        self.p.fragments = 2
        second = ManagementVisit()
        self.assertFalse(second.purchase(self.p, 1))
        self.assertEqual(self.p.fragments, 2)
        self.assertTrue(second.purchase(self.p, 2))
        self.assertEqual(self.p.core_upgrades, {FOCUS, SPREAD})

    def test_insufficient_and_invalid_choices_do_not_mutate(self):
        self.p.fragments = 1
        for choice in (0, 1, 2, -1, 3):
            self.assertFalse(self.visit.purchase(self.p, choice))
        self.assertEqual(self.p.fragments, 1)
        self.assertEqual(self.p.core_upgrades, set())
        self.assertFalse(self.visit.completed)

    def test_all_pairs_apply_exact_stats_without_stacking(self):
        for first, second in ((0, 1), (0, 2), (1, 2)):
            with self.subTest(pair=(first, second)):
                p = Player(400, 96)
                p.fragments = 4
                self.assertTrue(ManagementVisit().purchase(p, first))
                self.assertTrue(ManagementVisit().purchase(p, second))
                self.assertEqual(p.fragments, 0)
                self.assertEqual(p.max_battery, 140 if 0 in (first, second) else 100)
                self.assertEqual(p.flash_range, 120 if 1 in (first, second) else 96)
                self.assertEqual(p.light_radius, 200 if 2 in (first, second) else 160)
                self.assertFalse(p.apply_core_upgrade(CORE_UPGRADES[first].key))

    def test_focus_reaches_farther_but_respects_wall_and_keeps_cost(self):
        from physics import Solid
        self.visit.purchase(self.p, 1)
        self.p.update(0, 960, [Solid(0, 0, 960, 96)])
        self.p._cast_flash()
        self.assertEqual(self.p.flash_effect.box[2], 532)
        self.assertEqual(self.p.battery, 80)
        self.assertEqual(self.p.consume_flash_target([('far', (526, 96, 550, 184))]), 'far')
        self.p.reset_actions_after_return()
        self.p.solids = [Solid(500, 96, 510, 200)]
        self.p._cast_flash()
        self.assertEqual(self.p.flash_effect.box[2], 500)
        self.assertIsNone(self.p.consume_flash_target([('hidden', (526, 96, 550, 184))]))

    def test_spread_changes_suppression_radius_without_cost_or_duration_change(self):
        stage = ResidentialStage()
        self.visit.purchase(self.p, 2)
        self.p.update(0, stage.width, stage.solids, stage.light_regions)
        self.assertTrue(self.p._install_light(stage.light_regions))
        light = self.p.light
        self.assertEqual((light.radius, light.remaining, self.p.battery), (200, 12, 50))
        self.assertTrue(light.illuminates((590, 96, 614, 188)))
        self.assertFalse(light.illuminates((605, 96, 629, 188)))

    def test_progress_preserves_latest_upgrade_and_restart_restores_entry(self):
        stage = ResidentialStage()
        records = ProgressRecords(self.p, stage)
        self.visit.purchase(self.p, 0)
        self.p.battery = 30
        records.remember(self.p, stage)
        records.restore_after_death(self.p, stage)
        self.assertEqual((self.p.core_upgrades, self.p.max_battery, self.p.battery), ({CAPACITY}, 140, 30))
        records.restore_entry(self.p, stage)
        self.assertEqual((self.p.core_upgrades, self.p.max_battery, self.p.battery, self.p.fragments), (set(), 100, 100, 2))

    def test_entry_can_preserve_inherited_upgrade_for_future_stage(self):
        stage = ResidentialStage()
        self.p.apply_core_upgrade(FOCUS)
        records = ProgressRecords(self.p, stage)
        self.p.apply_core_upgrade(SPREAD)
        records.restore_entry(self.p, stage)
        self.assertEqual(self.p.core_upgrades, {FOCUS})
