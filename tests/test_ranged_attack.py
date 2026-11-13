import unittest
from unittest.mock import Mock, patch

import pico2d

from enemy import Shade
from lighting import PortableLight
from physics import Solid
from player import Player
from projectiles import ShadowBolt
from session import GameSession
from stage import Stage
from world import update_world


class RangedAttackTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = Stage()
        self.player = Player(400, 96)
        self.enemy = Shade(640, 96, combat_bounds=self.stage.combat_bounds, can_shoot=True)

    def test_aim_warning_locks_target_then_releases_one_shot(self):
        update_world(0.01, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.state, 'RANGED_WINDUP')
        target = self.enemy.shot_target
        self.player.x = 460
        update_world(0.64, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.bolts, [])
        self.assertEqual(self.enemy.shot_target, target)
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(len(self.enemy.bolts), 1)
        self.assertEqual(self.enemy.state, 'RANGED_RELEASE')
        self.assertLess(self.enemy.bolts[0].vx, 0)
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(len(self.enemy.bolts), 1)
        self.assertGreater(self.enemy.shot_cooldown, 0)

    def test_jump_timed_before_impact_avoids_bolt_but_standing_is_hit(self):
        for jump in (False, True):
            with self.subTest(jump=jump):
                player = Player(400, 96)
                bolt = ShadowBolt.aimed((600, 140), (400, 136))
                hit = False
                for frame in range(132):
                    if jump and frame == 66:
                        player.motion.jump()
                    player.update(1 / 120, 960)
                    bolt.update(1 / 120, [Solid(0, 0, 960, 96)], player)
                    hit = bolt.consume_hit() or hit
                self.assertEqual(hit, not jump)
                self.assertEqual(player.invulnerability, 0)

    def test_thin_wall_and_light_block_bolt_before_player(self):
        for light in (None, PortableLight(500, 120, self.stage.light_regions[0])):
            with self.subTest(light=light is not None):
                bolt = ShadowBolt.aimed((600, 140), (400, 136))
                solids = [] if light else [Solid(500, 96, 501, 200)]
                bolt.update(1.0, solids, self.player, light)
                self.assertFalse(bolt.active)
                self.assertFalse(bolt.consume_hit())
                self.assertGreater(bolt.x, self.player.x + 12)

    def test_light_interrupts_ranged_warning(self):
        self.enemy.update(0.01, self.player, self.stage)
        light = PortableLight(640, 120, self.stage.light_regions[0])
        self.enemy.update(0.7, self.player, self.stage, light)
        self.enemy.launch_pending_shot()
        self.assertNotIn(self.enemy.state, ('RANGED_WINDUP', 'RANGED_RELEASE'))
        self.assertEqual(self.enemy.bolts, [])

    def test_other_floor_and_wall_are_not_targeted(self):
        self.player.feet_y = 288
        self.enemy.update(0.01, self.player, self.stage)
        self.assertNotEqual(self.enemy.state, 'RANGED_WINDUP')
        self.player.feet_y = 96
        self.stage.solids.append(Solid(500, 96, 516, 260))
        self.enemy.update(0.01, self.player, self.stage)
        self.assertNotEqual(self.enemy.state, 'RANGED_WINDUP')

    def test_repair_and_restart_remove_existing_projectiles(self):
        self.enemy.bolts.append(ShadowBolt.aimed((600, 140), (400, 136)))
        self.stage.fixture_powered = True
        update_world(0.01, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.bolts, [])
        self.enemy.bolts.append(ShadowBolt.aimed((600, 140), (400, 136)))
        self.enemy.reset()
        self.assertEqual(self.enemy.bolts, [])
        self.assertEqual(self.enemy.shot_cooldown, 0)

    def test_fatal_hit_cancels_pending_release(self):
        self.enemy.health = 1
        self.enemy.shot_event = ((610, 140), (400, 136))
        self.enemy.take_damage(direction=1)
        self.enemy.launch_pending_shot()
        self.assertEqual(self.enemy.bolts, [])

    def test_pause_and_focus_loss_freeze_bolt_position_and_lifetime(self):
        game = GameSession(stage_factory=Stage)
        game.start_game()
        game.enemies = [self.enemy]
        bolt = ShadowBolt.aimed((600, 140), (400, 136))
        self.enemy.bolts.append(bolt)
        snapshot = (bolt.x, bolt.y, bolt.remaining)
        game.state = 'PAUSED'
        game.update(1)
        self.assertEqual(snapshot, (bolt.x, bolt.y, bolt.remaining))
        game.state = 'PLAY'
        game.update(1, focused=False)
        self.assertEqual(snapshot, (bolt.x, bolt.y, bolt.remaining))

    def test_running_behind_shooter_during_locked_aim_avoids_hit_without_invulnerability(self):
        stage = Stage()
        stage.solids = [Solid(0, 0, 960, 96)]
        player = Player(400, 96)
        enemy = Shade(520, 96, combat_bounds=(0, 960), can_shoot=True)
        for code in (pico2d.SDLK_RIGHT, pico2d.SDLK_LSHIFT):
            event = pico2d.Event(pico2d.SDL_KEYDOWN)
            event.key = code
            player.handle_event(event)
        for _ in range(144):
            update_world(1 / 120, player, [enemy], stage)
        self.assertGreater(player.x, enemy.x)
        self.assertEqual(player.health, 3)
        self.assertEqual(player.invulnerability, 0)
