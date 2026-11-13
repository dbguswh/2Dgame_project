import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from enemy import Shade
from lighting import LightRegion, PortableLight
from physics import Solid
from player import Player
from projectiles import ShadowBolt
from stage import Stage
from world import update_world


class FloodlightTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = Stage()
        self.stage.solids = [Solid(0, 0, 1920, 96)]
        self.player = Player(600, 96)
        self.enemy = Shade(650, 96, combat_bounds=(0, 1200), can_shoot=True)
        self.player.light = PortableLight(600, 120, self.stage.light_regions[0])

    def tick(self, seconds):
        while seconds > 0.000001:
            dt = min(1 / 120, seconds)
            update_world(dt, self.player, [self.enemy], self.stage)
            seconds -= dt

    def test_deployment_pushes_96_without_damage_and_cancels_ranged_aim(self):
        self.enemy._enter('RANGED_WINDUP')
        self.enemy.shot_target = (600, 136)
        self.enemy.state_time = 0.64
        self.tick(0.3)
        self.assertAlmostEqual(self.enemy.x, 746)
        self.assertEqual(self.enemy.health, 2)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.enemy.bolts, [])
        self.assertEqual(self.enemy.state, 'RETREAT')
        self.tick(0.5)
        self.assertFalse(self.player.light.illuminates(self.enemy.get_bb()))
        self.assertEqual(self.enemy.state, 'DARK_PATROL')

    def test_later_exposure_retreats_without_repeating_deployment_push(self):
        light = self.player.light
        light.remaining = 10
        self.enemy.update(0.1, self.player, self.stage, light)
        self.assertAlmostEqual(self.enemy.x, 660)
        self.assertEqual(self.enemy.light_push_remaining, 0)

    def test_wall_limits_pulse_and_fully_lit_ledge_cowers_without_jitter(self):
        stage = SimpleNamespace(width=960, solids=[Solid(0, 0, 160, 96)])
        enemy = Shade(80, 96, combat_bounds=(0, 160))
        light = PortableLight(80, 120, LightRegion(0, 96, 160, 540))
        positions = []
        for frame in range(600):
            enemy.update(1 / 120, self.player, stage, light)
            self.assertIsNone(enemy.consume_attack())
            self.assertEqual(enemy.feet_y, 96)
            if frame > 120:
                positions.append(enemy.x)
                self.assertFalse(enemy.is_moving)
        self.assertEqual(max(positions), min(positions))
        self.assertEqual(enemy.state, 'LIGHT_WAIT')
        self.assertEqual(enemy.health, 2)

    def test_light_blocks_bolt_with_fragment_fade_and_no_hit(self):
        bolt = ShadowBolt.aimed((900, 140), (600, 136))
        bolt.update(1, self.stage.solids, self.player, self.player.light)
        self.assertTrue(bolt.absorbed)
        self.assertFalse(bolt.active)
        self.assertFalse(bolt.consume_hit())
        self.assertGreater(bolt.x, 740)
        self.assertAlmostEqual(bolt.fade, 0.32)
        bolt.update(0.33, self.stage.solids, self.player, self.player.light)
        self.assertEqual(bolt.fade, 0)

    def test_one_light_cannot_restart_push_when_enemy_reenters(self):
        self.tick(0.8)
        self.enemy.motion.x = 650
        self.enemy._enter('PATROL')
        self.enemy.update(0.1, self.player, self.stage, self.player.light)
        self.assertAlmostEqual(self.enemy.x, 660)
        self.assertEqual(self.enemy.light_push_remaining, 0)

    def test_replacement_can_repel_again_and_reset_clears_recoil(self):
        self.tick(0.1)
        old = self.enemy.repelled_light
        self.player.light = PortableLight(650, 120, self.stage.light_regions[0])
        self.enemy.update(0.01, self.player, self.stage, self.player.light)
        self.assertIsNot(self.enemy.repelled_light, old)
        self.assertGreater(self.enemy.light_push_remaining, 0)
        self.enemy.reset()
        self.assertIsNone(self.enemy.repelled_light)
        self.assertEqual(self.enemy.light_push_remaining, 0)

    def test_expiry_releases_cowering_enemy_into_full_warning(self):
        self.tick(0.1)
        self.player.light = None
        self.enemy.motion.x = 650
        self.enemy.update(0.01, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'WINDUP')
        self.assertEqual(self.enemy.state_time, 0)
        self.assertEqual(self.enemy.light_push_remaining, 0)
        self.assertIsNone(self.enemy.consume_attack())
