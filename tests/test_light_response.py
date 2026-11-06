import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from enemy import Shade
from lighting import LightRegion, PortableLight
from physics import Solid
from player import Player
from stage import Stage


class LightResponseTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.stage = Stage()
        self.player = Player(400, 96)
        self.enemy = Shade(*self.stage.enemy_spawn, combat_bounds=self.stage.combat_bounds)
        self.light = PortableLight(400, 120, self.stage.light_regions[0])

    def test_light_cancels_warning_and_chooses_reachable_dark_side(self):
        self.enemy._enter('WINDUP')
        self.enemy.state_time = 0.69
        self.enemy.update(0.02, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.state, 'RETREAT')
        self.assertGreater(self.enemy.x, 440)
        self.assertIsNone(self.enemy.consume_attack())
        self.assertEqual(self.enemy.health, 2)

    def test_retreated_enemy_waits_without_boundary_oscillation(self):
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.state, 'LIGHT_WAIT')
        self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
        position = self.enemy.x
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            self.assertEqual(self.enemy.x, position)
            self.assertIsNone(self.enemy.consume_attack())

    def test_wall_blocked_retreat_stops_in_light_without_attacking(self):
        stage = SimpleNamespace(width=960, solids=[Solid(0, 0, 160, 96)])
        enemy = Shade(80, 96, combat_bounds=(0, 160))
        light = PortableLight(80, 120, LightRegion(0, 96, 160, 540))
        self.player.x = 80
        for _ in range(120):
            enemy.update(1 / 60, self.player, stage, light)
        self.assertEqual(enemy.state, 'LIGHT_WAIT')
        self.assertTrue(light.illuminates(enemy.get_bb()))
        self.assertEqual(enemy.feet_y, 96)
        self.assertIsNone(enemy.consume_attack())

    def test_expiry_resumes_with_new_warning_not_instant_strike(self):
        self.enemy.update(0.01, self.player, self.stage, self.light)
        self.light.remaining = 0
        self.enemy.update(0.01, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.state, 'WINDUP')
        self.assertEqual(self.enemy.state_time, 0)
        self.assertIsNone(self.enemy.consume_attack())

    def test_player_leaving_light_can_be_chased_again(self):
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
        self.player.x = self.enemy.x + 20
        self.enemy.update(0.01, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.state, 'WINDUP')
        self.assertIsNone(self.enemy.consume_attack())

    def test_dark_wait_does_not_walk_back_into_light_when_view_is_blocked(self):
        self.stage.solids.append(Solid(460, 96, 472, 300))
        self.enemy.motion.x = 500
        self.enemy._enter('LIGHT_WAIT')
        self.enemy.retreat_light = self.light
        for _ in range(60):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            self.assertEqual(self.enemy.x, 500)
            self.assertEqual(self.enemy.state, 'LIGHT_WAIT')

    def test_retreat_blocked_by_wall_never_attacks(self):
        self.stage.solids.append(Solid(480, 96, 512, 300))
        light = PortableLight(440, 120, self.stage.light_regions[0])
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, light)
        self.assertEqual(self.enemy.state, 'LIGHT_WAIT')
        self.assertTrue(light.illuminates(self.enemy.get_bb()))
        self.assertLessEqual(self.enemy.get_bb()[2], 480)
        self.assertIsNone(self.enemy.consume_attack())

    def test_retreat_stops_at_ledge_even_with_room_to_chase_beyond_it(self):
        stage = SimpleNamespace(width=960, solids=[Solid(0, 0, 160, 96)])
        enemy = Shade(80, 96, combat_bounds=(0, 960))
        light = PortableLight(80, 120, LightRegion(0, 96, 960, 540))
        self.player.x = 80
        for _ in range(120):
            enemy.update(1 / 60, self.player, stage, light)
            self.assertEqual(enemy.feet_y, 96)
        self.assertEqual(enemy.state, 'LIGHT_WAIT')
        self.assertIsNone(enemy.consume_attack())

    def test_reinstall_recalculates_retreat_direction(self):
        self.enemy.update(0.01, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.retreat_direction, 1)
        previous_x = self.enemy.x
        replacement = PortableLight(500, 120, self.stage.light_regions[0])
        self.enemy.update(0.01, self.player, self.stage, replacement)
        self.assertEqual(self.enemy.retreat_direction, -1)
        self.assertLess(self.enemy.x, previous_x)


if __name__ == '__main__':
    unittest.main()
