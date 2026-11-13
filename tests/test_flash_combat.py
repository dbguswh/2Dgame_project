import unittest
from unittest.mock import Mock, patch

import pico2d

from enemy import Shade
from lighting import PortableLight
from physics import Solid
from player import Player
from progress import ProgressRecords
from projectiles import ShadowBolt
from session import GameSession
from stage import Stage
from world import update_world


def tap(player, code=pico2d.SDLK_q):
    for event_type in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
        event = pico2d.Event(event_type)
        event.key = code
        player.handle_event(event)


class FlashCombatTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = Stage()
        self.stage.solids = [Solid(0, 0, 960, 96)]
        self.player = Player(400, 96)
        self.enemy = Shade(450, 96, combat_bounds=(0, 960), can_shoot=True)

    def tick(self, seconds):
        while seconds > 0.000001:
            dt = min(1 / 120, seconds)
            update_world(dt, self.player, [self.enemy], self.stage)
            seconds -= dt

    def cast(self):
        tap(self.player)
        update_world(0, self.player, [self.enemy], self.stage)

    def test_flash_cancels_melee_becoming_active_in_same_update(self):
        self.enemy._enter('WINDUP')
        self.enemy.state_time = 0.69
        tap(self.player)
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual((self.enemy.health, self.player.health), (1, 3))
        self.assertEqual(self.enemy.state, 'STUNNED')
        self.assertIsNone(self.enemy.consume_attack())

    def test_flash_cancels_pending_ranged_release_in_same_update(self):
        self.enemy._enter('RANGED_WINDUP')
        self.enemy.state_time = 0.64
        self.enemy.shot_target = (400, 136)
        tap(self.player)
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.health, 1)
        self.assertEqual(self.enemy.bolts, [])
        self.assertIsNone(self.enemy.shot_target)

    def test_stun_pushes_48_pixels_then_holds_and_restarts_full_warning(self):
        self.cast()
        self.tick(0.3)
        self.assertAlmostEqual(self.enemy.x, 498)
        self.player.x = 450
        self.tick(0.89)
        self.assertEqual(self.enemy.state, 'STUNNED')
        self.assertAlmostEqual(self.enemy.x, 498)
        self.tick(0.03)
        self.assertEqual(self.enemy.state, 'WINDUP')
        self.assertLess(self.enemy.state_time, 0.03)
        self.assertEqual(self.player.health, 3)

    def test_knockback_respects_wall_and_platform_edge(self):
        for solids, limit in (([Solid(0, 0, 960, 96), Solid(490, 96, 500, 240)], 466),
                              ([Solid(0, 0, 490, 96)], 464)):
            with self.subTest(limit=limit):
                self.stage.solids = solids
                self.enemy.reset()
                self.enemy.solids = solids
                self.enemy.receive_flash(1)
                self.tick(0.3)
                self.assertLessEqual(self.enemy.x, limit)
                self.assertEqual(self.enemy.feet_y, 96)
                self.assertEqual(self.enemy.state, 'STUNNED')

    def test_light_retreat_waits_for_flash_stun_then_resumes(self):
        self.player.light = PortableLight(480, 120, self.stage.light_regions[0])
        self.cast()
        self.tick(1.1)
        self.assertEqual(self.enemy.state, 'STUNNED')
        self.tick(0.2)
        self.assertIn(self.enemy.state, ('RETREAT', 'DARK_PATROL'))
        self.assertGreater(self.enemy.x, 498)

    def test_q_then_w_kills_with_one_battery_payment(self):
        self.cast()
        self.tick(0.34)
        self.player.x = self.enemy.x - 40
        tap(self.player, pico2d.SDLK_w)
        self.tick(0.2)
        self.assertFalse(self.enemy.alive)
        self.assertEqual(self.player.battery, 80)
        self.assertEqual(self.player.health, 3)

    def test_two_flashes_kill_and_only_closest_enemy_is_damaged(self):
        farther = Shade(490, 96, identity=1, combat_bounds=(0, 960))
        tap(self.player)
        update_world(0, self.player, [farther, self.enemy], self.stage)
        self.assertEqual((self.enemy.health, farther.health), (1, 2))
        self.tick(0.61)
        self.cast()
        self.assertFalse(self.enemy.alive)
        self.assertEqual(self.player.battery, 60)

    def test_already_fired_bolt_is_not_erased_by_flash(self):
        bolt = ShadowBolt.aimed((470, 140), (400, 136))
        self.enemy.bolts.append(bolt)
        self.cast()
        self.tick(0.3)
        self.assertEqual(self.player.health, 2)
        self.assertFalse(bolt.active)

    def test_same_update_death_keeps_flash_cost_and_clears_stun(self):
        records = ProgressRecords(self.player, self.stage)
        self.player.health = 1
        self.enemy.bolts.append(ShadowBolt.aimed((400, 136), (360, 136)))
        tap(self.player)
        update_world(0.01, self.player, [self.enemy], self.stage, records)
        self.assertEqual(self.player.respawn_count, 1)
        self.assertEqual(self.player.battery, 80)
        self.assertEqual(self.enemy.stun_remaining, 0)
        self.assertEqual(self.enemy.health, 2)
        self.assertIsNone(self.player.flash_effect)

    def test_pause_and_focus_loss_freeze_flash_and_stun(self):
        game = GameSession(stage_factory=Stage)
        game.start_game()
        game.player, game.enemies, game.stage = self.player, [self.enemy], self.stage
        self.cast()
        snapshot = (self.player.attack_elapsed, self.player.flash_effect.age,
                    self.player.flash_cooldown, self.enemy.stun_remaining, self.enemy.x)
        game.state = 'PAUSED'
        game.update(1)
        game.state = 'PLAY'
        game.update(1, focused=False)
        self.assertEqual(snapshot, (self.player.attack_elapsed, self.player.flash_effect.age,
                                   self.player.flash_cooldown, self.enemy.stun_remaining, self.enemy.x))
