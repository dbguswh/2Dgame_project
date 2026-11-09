import unittest
from unittest.mock import Mock, patch

from player import Player
from stage import Stage
from enemy import Shade
from world import update_world
import pico2d


class InteractionTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.stage = Stage()
        self.player = Player(*self.stage.start)

    def test_fixture_requires_nearby_same_floor(self):
        self.assertFalse(self.stage.activate_fixture(self.player))
        self.player.x, self.player.feet_y = 640, 160
        self.assertFalse(self.stage.activate_fixture(self.player))
        self.player.feet_y = 96
        self.player.motion.on_ground = False
        self.assertFalse(self.stage.activate_fixture(self.player))
        self.player.motion.on_ground = True
        self.assertTrue(self.stage.activate_fixture(self.player))

    def test_fixture_is_one_time_and_does_not_recharge_player(self):
        self.player.x = 640
        self.player.battery = 0
        self.player.health = 2
        self.assertTrue(self.stage.activate_fixture(self.player))
        self.assertFalse(self.stage.activate_fixture(self.player))
        self.assertTrue(self.stage.fixture_powered)
        self.assertEqual(self.player.battery, 0)
        self.assertEqual(self.player.health, 2)

    def test_combat_animation_blocks_interaction(self):
        self.player.x = 640
        self.player.attack_elapsed = 0.1
        self.assertFalse(self.stage.activate_fixture(self.player))
        self.player.attack_elapsed = None
        self.player.light_cast = 0.1
        self.assertFalse(self.stage.activate_fixture(self.player))

    def press_e(self, down=True):
        event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
        event.key = pico2d.SDLK_e
        self.player.handle_event(event)

    def test_e_repairs_zone_cancels_enemy_and_sets_checkpoint(self):
        self.player.x = 640
        self.player.battery = 0
        enemy = Shade(*self.stage.enemy_spawn)
        enemy._enter('WINDUP')
        enemy.state_time = 0.69
        self.press_e()
        update_world(0.02, self.player, [enemy], self.stage)
        self.assertTrue(self.stage.fixture_powered)
        self.assertEqual(self.player.checkpoint_position, self.stage.fixture_checkpoint)
        self.assertEqual(self.player.battery, 0)
        self.assertEqual(self.player.health, 3)
        self.assertFalse(enemy.alive)
        self.assertIsNone(enemy.consume_attack())

    def test_holding_e_while_approaching_does_not_activate_without_new_press(self):
        self.press_e()
        update_world(0.01, self.player, [], self.stage)
        self.player.x = 640
        self.press_e()
        update_world(0.01, self.player, [], self.stage)
        self.assertFalse(self.stage.fixture_powered)
        self.press_e(False)
        self.press_e()
        update_world(0.01, self.player, [], self.stage)
        self.assertTrue(self.stage.fixture_powered)

    def test_death_after_repair_keeps_zone_and_checkpoint(self):
        self.player.x = 640
        self.press_e()
        enemy = Shade(*self.stage.enemy_spawn)
        update_world(0.01, self.player, [enemy], self.stage)
        self.player.health = 1
        self.player.battery = 20
        self.player.feet_y = -200
        update_world(0.01, self.player, [enemy], self.stage)
        self.assertEqual((self.player.x, self.player.feet_y), self.stage.fixture_checkpoint)
        self.assertEqual(self.player.battery, 20)
        self.assertTrue(self.stage.fixture_powered)
        self.assertFalse(enemy.alive)


if __name__ == '__main__':
    unittest.main()
