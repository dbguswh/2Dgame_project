import unittest
from unittest.mock import Mock, patch

from physics import Motion, MOVE_SPEED, camera_offset
from residential import ResidentialStage
from session import GameSession


class ResidentialLayoutTests(unittest.TestCase):
    def setUp(self):
        self.stage = ResidentialStage()

    def test_three_screens_and_separated_encounters(self):
        self.assertEqual(self.stage.width, 960 * 3)
        self.assertEqual(camera_offset(2800, self.stage.width, 960), 1920)
        placements = self.stage.enemy_placements
        self.assertEqual(len({e.identity for e in placements}), 6)
        for bounds in {e.bounds for e in placements}:
            self.assertEqual(sum(e.bounds == bounds for e in placements), 2)
        for checkpoint in (self.stage.start, self.stage.fuse_checkpoint,
                           self.stage.fixture_checkpoint):
            self.assertIsNotNone(self.stage.safe_position(Motion(*checkpoint)))
            for enemy in placements:
                self.assertGreaterEqual(abs(enemy.x - checkpoint[0]), 128)
                self.assertFalse(enemy.bounds[0] <= checkpoint[0] <= enemy.bounds[1])

    def test_basic_jumps_reach_fuse_shelf_and_control_side(self):
        motion = Motion(*self.stage.start)
        reached_shelf = False
        for _ in range(1400):
            left, bottom, right, top = motion.get_bb()
            obstacle = any(bottom < s.top and top > s.bottom
                           and right - 0.01 <= s.left <= right + 8
                           for s in self.stage.solids)
            if motion.on_ground and obstacle:
                motion.jump()
            motion.step(1 / 60, 1, self.stage.solids, self.stage.width)
            if 1280 <= motion.x <= 1376 and motion.feet_y >= 192:
                reached_shelf = True
            self.assertGreaterEqual(motion.feet_y, 96)
            if motion.x >= self.stage.fixture_position[0]:
                self.assertTrue(reached_shelf)
                return
        self.fail(f'제어함 쪽에 도달하지 못함: {motion}')

    def test_unpowered_canal_cannot_be_jumped_even_with_speed_item(self):
        left, right = self.stage.canal
        self.assertEqual(right - left, 12 * 32)
        for speed in (MOVE_SPEED, MOVE_SPEED * 1.3):
            for start_x in (left - 32, left - 1, left + 11):
                motion = Motion(start_x, 96)
                motion.jump()
                while motion.feet_y > -100:
                    motion.step(1 / 120, 1, self.stage.solids, self.stage.width, speed=speed)
                    if motion.feet_y >= 96:
                        self.assertLess(motion.x + motion.width / 2, right)
                    self.assertFalse(motion.on_ground and motion.x >= right)

    @patch('pico2d.load_image', return_value=Mock())
    def test_new_game_loads_residential_and_six_independent_enemies(self, _):
        game = GameSession()
        game.start_game()
        self.assertIsInstance(game.stage, ResidentialStage)
        self.assertEqual(len(game.enemies), 6)
        self.assertEqual(len({e.identity for e in game.enemies}), 6)
        # 한 번의 W는 여러 적이 겹쳐도 가장 가까운 한 마리만 친다.
        game.player.x = 450
        game.player.attack_elapsed = 0.11
        game.enemies[0].motion.x = 480
        game.enemies[1].motion.x = 482
        game.update(0.01)
        self.assertEqual(sorted(e.health for e in game.enemies[:2]), [1, 2])
        for _ in range(100):
            game.update(1 / 60)
        for enemy in game.enemies:
            self.assertGreaterEqual(enemy.x - 24, enemy.combat_bounds[0])
            self.assertLessEqual(enemy.x + 24, enemy.combat_bounds[1])


if __name__ == '__main__':
    unittest.main()
