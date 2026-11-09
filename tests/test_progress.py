import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from player import Player
from progress import ProgressRecords
from stage import Stage


class ProgressTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.stage = Stage()
        self.player = Player(*self.stage.start)
        self.records = ProgressRecords(self.player, self.stage)

    def change_progress(self):
        self.player.battery = 0
        self.player.health = 1
        self.player.x = 900
        self.player.checkpoint_position = self.stage.fixture_checkpoint
        self.stage.fixture_powered = True
        self.records.remember(self.player, self.stage)

    def test_latest_changes_never_mutate_entry(self):
        self.change_progress()
        self.assertEqual(self.records.entry.battery, 100)
        self.assertFalse(self.records.entry.fixture_powered)
        self.assertEqual(self.records.entry.checkpoint, self.stage.start)
        self.assertEqual(self.records.latest.battery, 0)
        self.assertIsNot(self.records.entry, self.records.latest)
        with self.assertRaises(FrozenInstanceError):
            self.records.entry.battery = 0

    def test_death_restores_only_health_and_preserves_latest_progress(self):
        self.change_progress()
        self.records.restore_after_death(self.player, self.stage)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.battery, 0)
        self.assertEqual((self.player.x, self.player.feet_y), self.stage.fixture_checkpoint)
        self.assertTrue(self.stage.fixture_powered)
        self.assertEqual(self.player.invulnerability, 1)

    def test_restart_restores_all_entry_values_and_clears_effects(self):
        self.change_progress()
        self.player.light_cast = 0.18
        self.player.attack_elapsed = 0.1
        self.records.restore_entry(self.player, self.stage)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.battery, 100)
        self.assertEqual((self.player.x, self.player.feet_y), self.stage.start)
        self.assertFalse(self.stage.fixture_powered)
        self.assertEqual(self.player.checkpoint_position, self.stage.start)
        self.assertIsNone(self.player.light)
        self.assertFalse(self.player.is_attacking)
        self.assertEqual(self.player.light_cast, 0)
        self.assertEqual(self.player.invulnerability, 0)
        self.assertEqual(self.records.latest, self.records.entry)
        self.assertIsNot(self.records.latest, self.records.entry)
