import unittest
from unittest.mock import Mock, patch

from player import Player
from stage import Stage


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


if __name__ == '__main__':
    unittest.main()
