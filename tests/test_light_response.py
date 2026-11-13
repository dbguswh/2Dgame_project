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

    def test_zero_time_light_update_does_not_mistake_no_movement_for_blockage(self):
        self.enemy.update(0, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.state, 'RETREAT')
        self.enemy.update(0.1, self.player, self.stage, self.light)
        self.assertGreater(self.enemy.x, 440)
        for _ in range(120):
            self.enemy.update(1 / 120, self.player, self.stage, self.light)
        self.assertFalse(self.light.illuminates(self.enemy.get_bb()))

    def test_retreated_enemy_resumes_wide_patrol_in_darkness(self):
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
        self.assertEqual(self.enemy.state, 'DARK_PATROL')
        self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
        positions = []
        for _ in range(600):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            positions.append(self.enemy.x)
            self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
            self.assertIsNone(self.enemy.consume_attack())
            self.assertTrue(self.enemy.is_moving)
        self.assertGreater(max(positions) - min(positions), 150)

    def test_exposed_waiting_enemy_retries_escape_instead_of_freezing(self):
        self.enemy._enter('LIGHT_WAIT')
        self.enemy.retreat_light = self.light
        self.enemy.retreat_direction = 1
        self.enemy.update(0.02, self.player, self.stage, self.light)
        self.assertGreater(self.enemy.x, 440)
        for _ in range(120):
            self.enemy.update(1 / 120, self.player, self.stage, self.light)
        self.assertFalse(self.light.illuminates(self.enemy.get_bb()))

    def test_light_overrides_hurt_pause_and_moves_out_of_attack_range(self):
        self.enemy._enter('WINDUP')
        self.enemy.state_time = 0.69
        self.enemy.take_damage(direction=1)
        self.enemy.update(0.02, self.player, self.stage, self.light)
        self.assertGreater(self.enemy.x, 440)
        self.assertEqual(self.enemy.hit_pause.remaining, 0)
        self.assertIsNone(self.enemy.consume_attack())

    def test_blocked_enemy_retries_when_the_wall_is_removed(self):
        wall = Solid(480, 96, 512, 300)
        self.stage.solids.append(wall)
        light = PortableLight(440, 120, self.stage.light_regions[0])
        for _ in range(60):
            self.enemy.update(1 / 60, self.player, self.stage, light)
        self.assertEqual(self.enemy.state, 'LIGHT_WAIT')
        old_x = self.enemy.x
        self.stage.solids.remove(wall)
        for _ in range(120):
            self.enemy.update(1 / 120, self.player, self.stage, light)
        self.assertGreater(self.enemy.x, old_x)
        self.assertFalse(light.illuminates(self.enemy.get_bb()))

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

    def test_dark_patrol_moves_without_entering_light_when_view_is_blocked(self):
        self.stage.solids.append(Solid(460, 96, 472, 300))
        self.enemy.motion.x = 500
        self.enemy._enter('LIGHT_WAIT')
        self.enemy.retreat_light = self.light
        positions = []
        for _ in range(180):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            positions.append(self.enemy.x)
            self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
            self.assertEqual(self.enemy.state, 'DARK_PATROL')
            self.assertIsNone(self.enemy.consume_attack())
        self.assertGreater(max(positions) - min(positions), 80)

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

    def test_unexposed_enemy_patrols_instead_of_waiting_at_light_boundary(self):
        self.enemy.motion.x = 550
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
            self.assertIsNone(self.enemy.consume_attack())
        self.assertGreaterEqual(self.enemy.x, 488)
        self.assertEqual(self.enemy.state, 'DARK_PATROL')
        self.assertTrue(self.enemy.is_moving)
        self.assertEqual(self.enemy.health, 2)

    def test_light_between_two_dark_actors_cannot_be_walked_through(self):
        self.enemy.motion.x = 550
        self.player.x = 340
        for _ in range(180):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
        self.assertGreaterEqual(self.enemy.x, 488)
        self.assertEqual(self.enemy.state, 'DARK_PATROL')

    def test_boundary_guard_releases_when_light_expires(self):
        self.enemy.motion.x = 550
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
        self.light.remaining = 0
        self.enemy.update(0.01, self.player, self.stage, self.light)
        self.assertNotIn(self.enemy.state, ('DARK_PATROL', 'RETREAT', 'LIGHT_WAIT'))
        for _ in range(600):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            if self.enemy.state == 'WINDUP':
                self.assertEqual(self.enemy.state_time, 0)
                self.assertIsNone(self.enemy.consume_attack())
                break
        else:
            self.fail('소등 후 순찰·추적을 거쳐 공격 예고를 시작하지 않음')

    def test_dark_patrol_turns_smoothly_at_light_edge_without_recoil_loop(self):
        self.enemy.motion.x = 550
        directions, positions = set(), []
        for _ in range(900):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            directions.add(self.enemy.face_dir)
            positions.append(self.enemy.x)
            self.assertFalse(self.light.illuminates(self.enemy.get_bb()))
            self.assertIsNone(self.enemy.consume_attack())
            self.assertTrue(self.enemy.is_moving)
            self.assertEqual(self.enemy.state, 'DARK_PATROL')
        self.assertEqual(directions, {-1, 1})
        self.assertGreater(max(positions) - min(positions), 150)

    def test_reinstalled_light_does_not_freeze_enemy_at_old_boundary(self):
        self.enemy.motion.x = 550
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
        old_x = self.enemy.x
        self.player.x = 650
        replacement = PortableLight(650, 120, self.stage.light_regions[0])
        self.enemy.update(0.01, self.player, self.stage, replacement)
        self.assertNotEqual(self.enemy.x, old_x)
        self.assertEqual(self.enemy.state, 'RETREAT')

    def test_dark_patrol_cannot_pass_wall(self):
        self.enemy.motion.x = 550
        wall_left = 620
        self.stage.solids.append(Solid(wall_left, 96, wall_left + 16, 300))
        for _ in range(60):
            self.enemy.update(1 / 60, self.player, self.stage, self.light)
            self.assertLessEqual(self.enemy.get_bb()[2], wall_left)
        self.assertEqual(self.enemy.state, 'DARK_PATROL')

    def test_unseen_patrol_uses_walkable_section_instead_of_spawn_neighborhood(self):
        stage = SimpleNamespace(width=960, solids=[Solid(0, 0, 960, 96)])
        enemy = Shade(480, 96, combat_bounds=(0, 960))
        self.player.x = 1500
        positions = []
        for _ in range(600):
            enemy.update(1 / 60, self.player, stage)
            positions.append(enemy.x)
        self.assertGreater(max(positions) - min(positions), 350)


if __name__ == '__main__':
    unittest.main()
