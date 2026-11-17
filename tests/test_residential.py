import unittest
from unittest.mock import Mock, patch

from physics import Motion, MOVE_SPEED, RUN_SPEED, camera_offset
from residential import ResidentialStage
from session import GameSession


class ResidentialLayoutTests(unittest.TestCase):
    def setUp(self):
        self.stage = ResidentialStage()

    def test_three_screens_and_separated_encounters(self):
        self.assertEqual(self.stage.width, 960 * 3)
        self.assertEqual(camera_offset(2800, self.stage.width, 960), 1920)
        placements = self.stage.enemy_placements
        self.assertEqual(len({e.identity for e in placements}), 8)
        self.assertEqual(sum(e.ranged for e in placements), 3)
        self.assertEqual(sorted(sum(e.bounds == bounds for e in placements)
                                for bounds in {e.bounds for e in placements}), [2, 2, 2, 2])
        for checkpoint in (self.stage.start, self.stage.fuse_checkpoint,
                           self.stage.fixture_checkpoint):
            self.assertIsNotNone(self.stage.safe_position(Motion(*checkpoint)))
            for enemy in placements:
                if abs(enemy.feet_y-checkpoint[1])>48:continue
                self.assertGreaterEqual(abs(enemy.x - checkpoint[0]), 128)
                self.assertFalse(enemy.bounds[0] <= checkpoint[0] <= enemy.bounds[1])

    def test_basic_jumps_reach_fuse_then_return_to_central_control(self):
        # 전투 이후의 지형 검증. 봉쇄 조건은 test_combat_seals에서 검증한다.
        for seal in self.stage.combat_seals:seal.opened=True
        self.stage.sync_combat_seals()
        motion = Motion(*self.stage.start)
        reached_shelf = False
        for _ in range(1400):
            left, bottom, right, top = motion.get_bb()
            obstacle = any(bottom < s.top and top > s.bottom
                           and right - 0.01 <= s.left <= right + 8
                           for s in self.stage.solids)
            edge = not any(s.left <= motion.x + 28 <= s.right and abs(s.top - bottom) < 0.01
                           for s in self.stage.solids)
            if motion.on_ground and (obstacle or edge):
                motion.jump()
            motion.step(1 / 60, 1, self.stage.solids, self.stage.width)
            if abs(motion.x - self.stage.fuse_position[0]) <= 24 and motion.feet_y >= 288:
                reached_shelf = True
            self.assertGreaterEqual(motion.feet_y, 96)
            if motion.x >= self.stage.fuse_position[0]:
                break
        self.assertTrue(reached_shelf)
        for _ in range(120):
            if motion.on_ground:break
            motion.step(1/120,0,self.stage.solids,self.stage.width)
        self.assertEqual(motion.feet_y, self.stage.FUSE_PEAK_Y)
        for _ in range(1600):
            left, bottom, right, top = motion.get_bb()
            obstacle = any(bottom < s.top and top > s.bottom
                           and left - 8 <= s.right <= left + 0.01 for s in self.stage.solids)
            edge = not any(s.left <= motion.x - 28 <= s.right and abs(s.top - bottom) < 0.01
                           for s in self.stage.solids)
            if motion.on_ground and (obstacle or edge):
                motion.jump()
            motion.step(1 / 60, -1, self.stage.solids, self.stage.width)
            if motion.x <= self.stage.fixture_position[0]:
                self.assertEqual(motion.feet_y, self.stage.UPPER_FLOOR_Y)
                return
        self.fail(f'중앙 제어함으로 복귀하지 못함: {motion}')

    def test_lower_alley_has_combat_healing_and_basic_jump_return_to_roof(self):
        from inventory import MEDKIT
        lower=[e for e in self.stage.enemy_placements if e.feet_y==96 and e.x>1000]
        self.assertEqual(len(lower),2)
        medkit=next(b for b in self.stage.supply_boxes if b.item==MEDKIT and b.x>1000)
        self.assertEqual(medkit.feet_y,96)
        self.assertGreater(medkit.x,max(e.bounds[1] for e in lower))
        body=Motion(1648,96)
        for x,y in ((1710,144),(1775,192),(1798,240),(1760,288)):
            self.assertTrue(body.jump())
            for _ in range(180):
                direction=0 if abs(x-body.x)<1.2 else 1 if x>body.x else -1
                body.step(1/120,direction,self.stage.solids,self.stage.width)
                if body.on_ground:break
            self.assertEqual(body.feet_y,y,(x,y,body))

    def test_speed_supply_has_own_ledge_and_can_return_to_lower_alley(self):
        from inventory import SPEED
        box=next(b for b in self.stage.supply_boxes if b.item==SPEED)
        body=Motion(box.x,96)
        self.assertTrue(body.jump())
        for _ in range(180):
            body.step(1/120,0,self.stage.solids,self.stage.width)
            if body.on_ground:break
        self.assertEqual(body.feet_y,box.feet_y)
        for _ in range(240):
            body.step(1/120,1 if body.x<1600 else 0,self.stage.solids,self.stage.width)
        self.assertEqual(body.feet_y,96)
        self.assertAlmostEqual(body.x,1600,delta=2)

    @patch('pico2d.load_image',return_value=Mock())
    def test_rooftop_flyer_does_not_attack_lower_route(self,_):
        from enemy_factory import create_enemy
        from player import Player
        w=create_enemy(next(e for e in self.stage.enemy_placements if e.kind=='wraith'))
        p=Player(1500,96)
        for _ in range(500):
            w.update(1/120,p,self.stage)
            self.assertIsNone(w.consume_attack())
            self.assertNotIn(w.state,('DIVE','DIVE_WINDUP'))

    def test_unpowered_canal_cannot_be_jumped_even_with_speed_item(self):
        left, right = self.stage.canal
        self.assertEqual(right - left, 12 * 32)
        for speed in (MOVE_SPEED, RUN_SPEED, RUN_SPEED * 1.3):
            for start_x in (left - 32, left - 1, left + 11):
                motion = Motion(start_x, self.stage.BRIDGE_Y)
                motion.jump()
                while motion.feet_y > -100:
                    motion.step(1 / 120, 1, self.stage.solids, self.stage.width, speed=speed)
                    if motion.feet_y >= self.stage.BRIDGE_Y:
                        self.assertLess(motion.x + motion.width / 2, right)
                    self.assertFalse(motion.on_ground and motion.x >= right)

    def test_higher_fuse_peak_still_cannot_bypass_unpowered_canal(self):
        # 새 최고 지점에서 달리기·속도 보급을 사용해도 미복구 교량을 건너뛰지 못한다.
        motion=Motion(self.stage.fuse_ledges[-1].right-1,self.stage.FUSE_PEAK_Y)
        motion.jump()
        for _ in range(300):
            motion.step(1/120,1,self.stage.solids,self.stage.width,speed=RUN_SPEED*1.3)
            self.assertFalse(motion.on_ground and motion.x>=self.stage.canal[1])
            if motion.feet_y<0:break
        self.assertLess(motion.x,self.stage.canal[1])

    @patch('pico2d.load_image', return_value=Mock())
    def test_new_game_loads_residential_and_six_independent_enemies(self, _):
        game = GameSession()
        game.start_game()
        self.assertIsInstance(game.stage, ResidentialStage)
        self.assertEqual(len(game.enemies), 8)
        self.assertEqual(len({e.identity for e in game.enemies}), 8)
        # 한 번의 W는 여러 적이 겹쳐도 가장 가까운 한 마리만 친다.
        game.player.x = 450
        game.player.attack_elapsed = 0.11
        game.enemies[0].motion.x = 480
        game.enemies[1].motion.x = 482
        game.update(0.01)
        self.assertEqual(sorted(e.health for e in game.enemies[:2]), [65, 100])
        for _ in range(100):
            game.update(1 / 60)
        for enemy in game.enemies:
            self.assertGreaterEqual(enemy.x - 24, enemy.combat_bounds[0])
            self.assertLessEqual(enemy.x + 24, enemy.combat_bounds[1])


if __name__ == '__main__':
    unittest.main()
