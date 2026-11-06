import unittest
from unittest.mock import Mock, patch

from enemy import Shade
from main import update_world
from player import Player
from stage import Stage
from lighting import PortableLight
import pico2d


class CombatLoopTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.stage = Stage()
        self.player = Player(400, 96)
        self.enemy = Shade(*self.stage.enemy_spawn)
        self.enemy._enter('WINDUP')
        self.enemy.state_time = 0.69

    def test_lethal_w_hit_cancels_same_frame_enemy_strike(self):
        self.player.attack_elapsed = 0.1
        self.enemy.health = 1
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.health, 0)
        self.assertEqual(self.player.health, 3)

    def test_nonfatal_w_hit_does_not_cancel_enemy_strike(self):
        self.player.attack_elapsed = 0.1
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.health, 1)
        self.assertEqual(self.player.health, 2)
        self.assertFalse(self.player.is_attacking)

    def test_combat_death_restores_both_actors(self):
        self.player.health = 1
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.player.respawn_count, 1)
        self.assertEqual(self.player.health, 3)
        self.assertEqual((self.player.x, self.player.feet_y), self.player.spawn_position)
        self.assertEqual(self.enemy.health, 2)
        self.assertEqual(self.enemy.state, 'PATROL')
        self.assertEqual((self.enemy.x, self.enemy.feet_y), self.enemy.spawn_position)

    def request_r(self):
        event = pico2d.Event(pico2d.SDL_KEYDOWN)
        event.key = pico2d.SDLK_r
        self.player.handle_event(event)

    def test_r_cancels_same_frame_enemy_strike_before_damage(self):
        self.request_r()
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.battery, 50)
        self.assertEqual(self.enemy.state, 'RETREAT')
        self.assertEqual(self.enemy.health, 2)
        self.assertIsNone(self.enemy.consume_attack())

    def test_r_does_not_undo_damage_from_previous_frame(self):
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.player.health, 2)
        self.request_r()
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.player.health, 2)
        self.assertEqual(self.enemy.state, 'RETREAT')

    def test_light_expiry_requires_full_new_warning(self):
        self.player.light = PortableLight(400, 120, self.stage.light_regions[0], remaining=0.01)
        self.enemy._enter('LIGHT_WAIT')
        self.enemy.retreat_light = self.player.light
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertIsNone(self.player.light)
        self.assertEqual(self.enemy.state, 'WINDUP')
        self.assertEqual(self.enemy.state_time, 0)
        self.assertEqual(self.player.health, 3)
        update_world(0.69, self.player, [self.enemy], self.stage)
        self.assertEqual(self.player.health, 3)
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.player.health, 2)


if __name__ == '__main__':
    unittest.main()
