import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player
from physics import Motion
from progress import ProgressRecords
from residential import ResidentialStage
from session import GameSession
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

    def test_bridge_collision_is_added_only_after_deployment_completes(self):
        self.repair()
        self.assertFalse(self.stage.bridge_ready)
        self.assertNotIn(self.stage.bridge_solid, self.stage.solids)
        self.stage.update(1.19)
        self.assertFalse(self.stage.bridge_ready)
        self.assertNotIn(self.stage.bridge_solid, self.stage.solids)
        self.stage.update(0.02)
        self.assertTrue(self.stage.bridge_ready)
        self.assertIn(self.stage.bridge_solid, self.stage.solids)
        self.stage.update(1)
        self.assertEqual(self.stage.solids.count(self.stage.bridge_solid), 1)
        motion = Motion(*self.stage.fixture_checkpoint)
        for _ in range(200):
            motion.step(1 / 60, 1, self.stage.solids, self.stage.width)
            self.assertEqual(motion.feet_y, 96)
        self.assertGreater(motion.x, self.stage.exit_position[0])

    def test_death_finishes_repaired_bridge_and_restart_removes_it(self):
        self.repair()
        self.player.health = 1
        self.player.battery = 0
        self.player.feet_y = -200
        update_world(0.01, self.player, [], self.stage, self.records)
        self.assertTrue(self.stage.bridge_ready)
        self.assertIn(self.stage.bridge_solid, self.stage.solids)
        self.assertEqual(self.player.battery, 0)
        self.assertEqual((self.player.x, self.player.feet_y), self.stage.fixture_checkpoint)
        self.records.restore_entry(self.player, self.stage)
        self.assertFalse(self.stage.bridge_ready)
        self.assertNotIn(self.stage.bridge_solid, self.stage.solids)

    def test_pause_freezes_bridge_deployment(self):
        game = GameSession()
        game.start_game()
        game.stage.fixture_powered = True
        game.stage.fuse_state = 'INSTALLED'
        game.update(0.1)
        game.state = 'PAUSED'
        elapsed = game.stage.bridge_elapsed
        game.update(2)
        self.assertEqual(game.stage.bridge_elapsed, elapsed)
        game.state = 'PLAY'
        game.update(0.1)
        self.assertGreater(game.stage.bridge_elapsed, elapsed)

    def test_reward_is_given_once_and_death_does_not_duplicate_it(self):
        self.repair()
        self.assertEqual(self.player.fragments, 0)
        for _ in range(130):
            update_world(0.01, self.player, [], self.stage, self.records)
        self.assertEqual(self.player.fragments, 2)
        self.assertTrue(self.stage.reward_claimed)
        press_e(self.player)
        update_world(0.01, self.player, [], self.stage, self.records)
        self.player.health = 1
        self.player.feet_y = -200
        update_world(0.01, self.player, [], self.stage, self.records)
        for _ in range(5):
            update_world(0.01, self.player, [], self.stage, self.records)
        self.assertEqual(self.player.fragments, 2)
        self.assertTrue(self.records.latest.reward_claimed)
        self.assertFalse(self.records.entry.reward_claimed)
        self.records.restore_entry(self.player, self.stage)
        self.assertEqual(self.player.fragments, 0)
        self.assertFalse(self.stage.reward_claimed)
