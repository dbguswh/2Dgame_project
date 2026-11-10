import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player
from progress import ProgressRecords
from residential import ResidentialStage
from world import update_world


def press_e(player):
    for event_type in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
        event = pico2d.Event(event_type)
        event.key = pico2d.SDLK_e
        player.handle_event(event)


class ResidentialProgressTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = ResidentialStage()
        self.player = Player(*self.stage.start)
        self.records = ProgressRecords(self.player, self.stage)

    def collect_fuse(self):
        self.player.x = self.stage.fuse_position[0]
        self.player.feet_y = 192
        self.player.motion.on_ground = True
        update_world(0.01, self.player, [], self.stage, self.records)

    def repair(self):
        self.collect_fuse()
        self.player.x, self.player.feet_y = self.stage.fixture_position
        self.player.motion.on_ground = True
        press_e(self.player)
        update_world(0.01, self.player, [], self.stage, self.records)

    def test_fixture_without_fuse_gives_hint_without_consuming_battery(self):
        self.player.x, self.player.feet_y = self.stage.fixture_position
        press_e(self.player)
        update_world(0.01, self.player, [], self.stage, self.records)
        self.assertFalse(self.stage.fixture_powered)
        self.assertEqual(self.player.battery, 100)
        self.assertIn('퓨즈가 필요', self.player.notice)

    def test_fuse_contact_and_death_preserve_acquisition_and_new_checkpoint(self):
        self.collect_fuse()
        self.assertEqual(self.stage.fuse_state, 'CARRIED')
        self.assertEqual(self.records.latest.fuse_state, 'CARRIED')
        self.assertEqual(self.records.entry.fuse_state, 'WORLD')
        self.player.health = 1
        self.player.battery = 0
        self.player.feet_y = -200
        update_world(0.01, self.player, [], self.stage, self.records)
        self.assertEqual(self.stage.fuse_state, 'CARRIED')
        self.assertEqual((self.player.x, self.player.feet_y), self.stage.fuse_checkpoint)
        self.assertEqual(self.player.battery, 0)

    def test_ground_below_shelf_does_not_collect_fuse(self):
        self.player.x = self.stage.fuse_position[0]
        self.stage.collect_pickups(self.player)
        self.assertEqual(self.stage.fuse_state, 'WORLD')

    def test_installation_is_one_time_and_restart_returns_fuse_to_world(self):
        self.repair()
        self.assertTrue(self.stage.fixture_powered)
        self.assertEqual(self.stage.fuse_state, 'INSTALLED')
        self.assertEqual(self.player.checkpoint_position, self.stage.fixture_checkpoint)
        press_e(self.player)
        update_world(0.01, self.player, [], self.stage, self.records)
        self.assertEqual(self.stage.fuse_state, 'INSTALLED')
        self.records.restore_entry(self.player, self.stage)
        self.assertFalse(self.stage.fixture_powered)
        self.assertEqual(self.stage.fuse_state, 'WORLD')
        self.assertEqual(self.player.checkpoint_position, self.stage.start)
