import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from combat import overlaps
from enemy import Shade
from lighting import PortableLight, LightRegion, constrain_region
from physics import Solid
from player import Player
from residential import ResidentialStage


class WorkshopRetreatTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.stage = ResidentialStage()
        self.player = Player(2240, 304)

    def enemy(self, x=1904):
        return Shade(x, 304, identity='residential-shade-5', combat_bounds=(1872, 2064))

    def light(self, x):
        region = constrain_region(self.stage.light_regions[0], x, 328, self.stage.solids)
        return PortableLight(x, 328, region)

    def test_left_of_workshop_light_uses_connected_platform_and_resumes_patrol(self):
        for fps in (30, 60, 120):
            for x in (2000, 2020, 2050):
                with self.subTest(fps=fps, x=x):
                    enemy, light = self.enemy(), self.light(x)
                    positions, heights = [], []
                    for frame in range(8*fps):
                        enemy.update(1/fps, self.player, self.stage, light)
                        heights.append(enemy.feet_y)
                        self.assertGreaterEqual(enemy.feet_y, 256-1e-5)
                        self.assertFalse(any(overlaps(enemy.get_bb(), (s.left,s.bottom,s.right,s.top))
                                             for s in self.stage.solids))
                        self.assertIsNone(enemy.consume_attack())
                        if frame >= 3*fps:
                            positions.append(enemy.x)
                    self.assertEqual(enemy.state, 'DARK_PATROL')
                    self.assertFalse(light.illuminates(enemy.get_bb()))
                    self.assertLess(min(heights), 304)
                    self.assertGreater(max(positions)-min(positions), 100)

    def test_no_light_does_not_expand_initial_patrol(self):
        enemy = self.enemy()
        for _ in range(480):
            enemy.update(1/60, self.player, self.stage)
            self.assertGreaterEqual(enemy.x, 1896)
        self.assertIsNone(enemy.escape_bounds)

    def test_reset_restores_original_bounds_after_platform_escape(self):
        enemy, light = self.enemy(), self.light(2020)
        for _ in range(360):
            enemy.update(1/120, self.player, self.stage, light)
        self.assertLess(enemy.x, 1872)
        enemy.reset()
        self.assertIsNone(enemy.escape_bounds)
        self.assertEqual((enemy.x,enemy.feet_y), enemy.spawn_position)
        self.assertEqual(enemy.patrol_bounds, (1900,2036))

    def test_declared_route_cannot_drop_into_deep_pit(self):
        stage = SimpleNamespace(width=1200,
            solids=[Solid(0,0,1200,32), Solid(300,280,500,304)],
            light_retreat_bounds={'test':(0,1200)})
        enemy = Shade(400,304,identity='test',combat_bounds=(300,500))
        light = PortableLight(400,328,LightRegion(0,304,1200,540))
        for _ in range(600):
            enemy.update(1/120,self.player,stage,light)
            self.assertEqual(enemy.feet_y,304)
            self.assertIsNone(enemy.consume_attack())
        self.assertEqual(enemy.state,'LIGHT_WAIT')

    def test_connector_step_does_not_pass_tall_wall_or_low_ceiling(self):
        for obstacle in (Solid(1808,288,1820,440),Solid(1760,365,1900,390)):
            enemy = self.enemy()
            enemy.escape_bounds=(1280,2064)
            enemy.motion.x,enemy.motion.feet_y=1834,256
            enemy.solids=[*self.stage.solids,obstacle]
            self.assertFalse(enemy._step_onto_connector(1833,-1))
            self.assertEqual(enemy.feet_y,256)

    def test_light_expiry_allows_connector_return_without_freezing(self):
        enemy,light=self.enemy(),self.light(2050)
        for _ in range(360):
            enemy.update(1/120,self.player,self.stage,light)
        light.remaining=0
        self.player.x,self.player.feet_y=2020,304
        positions=[]
        for _ in range(1440):
            enemy.update(1/120,self.player,self.stage,light)
            positions.append(enemy.x)
        self.assertGreater(max(positions),1896)
        self.assertGreaterEqual(enemy.feet_y,288)

    def test_unseen_enemy_returns_to_original_post_after_light_ends(self):
        enemy,light=self.enemy(),self.light(2020)
        for _ in range(960):enemy.update(1/120,self.player,self.stage,light)
        self.player.x=2800
        light.remaining=0
        for _ in range(1440):enemy.update(1/120,self.player,self.stage,light)
        self.assertIsNone(enemy.escape_bounds)
        self.assertGreaterEqual(enemy.x,1896)
        self.assertEqual(enemy.feet_y,304)
