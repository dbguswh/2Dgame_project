import unittest
from unittest.mock import Mock, patch

from enemy import Shade
from main import update_world
from player import Player
from stage import Stage


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


if __name__ == '__main__':
    unittest.main()
