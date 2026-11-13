import unittest
from unittest.mock import Mock, patch

from enemy import Shade
from lighting import PortableLight
from physics import Motion
from player import Player
from residential import ResidentialStage


class ResidentialLevelsTests(unittest.TestCase):
    def setUp(self):
        self.stage = ResidentialStage()

    def test_lower_hall_is_walkable_and_does_not_pick_up_upper_fuse(self):
        with patch('pico2d.load_image', return_value=Mock()):
            player = Player(1760, 96)
            for _ in range(480):
                player.motion.step(1 / 120, -1, self.stage.solids, self.stage.width)
                self.stage.collect_pickups(player)
                self.assertEqual(player.feet_y, 96)
            self.assertLess(player.x, self.stage.fuse_position[0])
            self.assertEqual(self.stage.fuse_state, 'WORLD')

    def test_upper_gap_can_be_jumped_or_used_to_descend_into_lower_hall(self):
        for jump in (True, False):
            with self.subTest(jump=jump):
                body = Motion(1428, 288)
                if jump:
                    body.jump()
                for _ in range(100):
                    body.step(1 / 120, 1, self.stage.solids, self.stage.width)
                if jump:
                    self.assertEqual(body.feet_y, 288)
                    self.assertGreater(body.x, 1504)
                else:
                    self.assertEqual(body.feet_y, 96)
                    self.assertGreater(body.x, 1504)

    def test_upper_checkpoint_returns_to_safe_floor(self):
        body = Motion(*self.stage.fuse_checkpoint)
        self.assertEqual(self.stage.safe_position(body), self.stage.fuse_checkpoint)
        for _ in range(60):
            body.step(1 / 120, 0, self.stage.solids, self.stage.width)
        self.assertEqual(body.feet_y, 288)

    def test_upper_enemies_stay_on_walkway_and_lower_light_does_not_reach_them(self):
        with patch('pico2d.load_image', return_value=Mock()):
            player = Player(1600, 96)
            light = PortableLight(1600, 120, self.stage.light_regions[0])
            for placement in self.stage.enemy_placements[2:4]:
                enemy = Shade(placement.x, placement.feet_y, combat_bounds=placement.bounds)
                for _ in range(300):
                    enemy.update(1 / 120, player, self.stage, light)
                    self.assertEqual(enemy.feet_y, 288)
                    self.assertFalse(light.illuminates(enemy.get_bb()))
                    self.assertIsNone(enemy.consume_attack())
