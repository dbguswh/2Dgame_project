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

    def test_ground_cannot_collect_upper_fuse_or_reward_battery(self):
        with patch('pico2d.load_image', return_value=Mock()):
            player = Player(self.stage.fuse_position[0], 96)
            player.battery = 50
            self.stage.collect_pickups(player)
            self.assertEqual(self.stage.fuse_state, 'WORLD')
            player.x = self.stage.battery_pack_position[0]
            self.stage.collect_pickups(player)
            self.assertEqual(player.battery, 50)
            self.assertFalse(self.stage.battery_pack_collected)

    def test_required_route_rises_through_ledges_and_crosses_upper_enemy_zone(self):
        body = Motion(*self.stage.start)
        heights, crossed_enemy_zone = set(), False
        for _ in range(2200):
            left, bottom, right, top = body.get_bb()
            obstacle = any(bottom < solid.top and top > solid.bottom
                           and right - 0.01 <= solid.left <= right + 8
                           for solid in self.stage.solids)
            edge = not any(solid.left <= body.x + 28 <= solid.right
                           and abs(solid.top - bottom) < 0.01 for solid in self.stage.solids)
            if body.on_ground:
                heights.add(round(body.feet_y))
                if obstacle or edge:
                    body.jump()
            body.step(1 / 120, 1, self.stage.solids, self.stage.width)
            if 1200 <= body.x <= 1600 and body.feet_y >= 288:
                crossed_enemy_zone = True
            if body.x >= self.stage.fuse_position[0]:
                break
        self.assertTrue(crossed_enemy_zone)
        self.assertTrue({144, 192, 240, 288}.issubset(heights), heights)
        self.assertGreaterEqual(body.feet_y, 288)

    def test_reward_ledge_cannot_be_used_to_jump_back_to_fuse_roof(self):
        body = Motion(1890, 192)
        body.jump()
        peak = body.feet_y
        for _ in range(100):
            body.step(1 / 120, -1, self.stage.solids, self.stage.width)
            peak = max(peak, body.feet_y)
        self.assertLess(peak, self.stage.UPPER_FLOOR_Y)

    def test_upper_checkpoint_is_safe_and_battery_is_after_upper_patrol(self):
        body = Motion(*self.stage.fuse_checkpoint)
        self.assertEqual(self.stage.safe_position(body), self.stage.fuse_checkpoint)
        upper_bounds = self.stage.enemy_placements[2].bounds
        self.assertGreater(self.stage.fuse_position[0], upper_bounds[1])
        self.assertGreater(self.stage.battery_pack_position[0], self.stage.fuse_position[0])
        for _ in range(60):
            body.step(1 / 120, 0, self.stage.solids, self.stage.width)
        self.assertEqual(body.feet_y, 288)

    def test_upper_enemies_stay_on_roof_and_lower_light_does_not_reach_them(self):
        with patch('pico2d.load_image', return_value=Mock()):
            player = Player(1400, 96)
            light = PortableLight(1400, 120, self.stage.light_regions[0])
            for placement in self.stage.enemy_placements[2:4]:
                enemy = Shade(placement.x, placement.feet_y, combat_bounds=placement.bounds)
                for _ in range(300):
                    enemy.update(1 / 120, player, self.stage, light)
                    self.assertEqual(enemy.feet_y, 288)
                    self.assertFalse(light.illuminates(enemy.get_bb()))
                    self.assertIsNone(enemy.consume_attack())

    def test_bridge_controls_and_exit_require_elevated_floor(self):
        with patch('pico2d.load_image', return_value=Mock()):
            player = Player(self.stage.fixture_position[0], 96)
            self.stage.fuse_state = 'CARRIED'
            self.assertFalse(self.stage.activate_fixture(player))
            player.feet_y = self.stage.BRIDGE_Y
            self.assertTrue(self.stage.activate_fixture(player))
            self.stage.update(self.stage.BRIDGE_TIME)
            player.x = self.stage.exit_position[0]
            player.feet_y = 96
            self.assertFalse(self.stage.activate_exit(player))
            player.feet_y = self.stage.BRIDGE_Y
            self.assertTrue(self.stage.activate_exit(player))
