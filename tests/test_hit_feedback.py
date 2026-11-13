import unittest
from unittest.mock import Mock, patch

import pico2d

from combat_feedback import HitPause, Impact
from enemy import Shade
from lighting import PortableLight
from player import Player
from stage import Stage
from world import update_world


class HitFeedbackTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = Stage()
        self.player = Player(400, 96)
        self.enemy = Shade(440, 96, combat_bounds=self.stage.combat_bounds)
        self.enemy._enter('WINDUP')

    def hit(self, stage=1, lethal=False):
        self.player.attack_stage = stage
        self.player.attack_elapsed = 0.12
        self.enemy.health = 1 if lethal else 2
        update_world(0.01, self.player, [self.enemy], self.stage)
        return self.enemy.impact

    def test_hit_pause_consumes_only_stopped_portion_of_frame(self):
        pause = HitPause()
        pause.trigger(0.04)
        self.assertEqual(pause.consume(0.025), 0)
        self.assertAlmostEqual(pause.consume(0.025), 0.01)
        self.assertEqual(pause.remaining, 0)

    def test_freeze_is_local_to_attacker_and_hit_enemy(self):
        impact = self.hit()
        other = Shade(700, 96, identity='other', combat_bounds=(0, 960))
        other._enter('WINDUP')
        before = (self.player.x, self.player.feet_y, self.player.attack_elapsed, self.enemy.state_time)
        update_world(0.02, self.player, [self.enemy, other], self.stage)
        self.assertEqual(before, (self.player.x, self.player.feet_y,
                                  self.player.attack_elapsed, self.enemy.state_time))
        self.assertAlmostEqual(other.state_time, 0.02)
        self.assertIs(self.enemy.impact, impact)
        self.assertEqual(self.enemy.health, 1)

    def test_empty_swing_does_not_freeze(self):
        self.player.attack_elapsed = 0.12
        update_world(0.01, self.player, [], self.stage)
        self.assertEqual(self.player.hit_pause.remaining, 0)

    def test_light_lifetime_continues_during_actor_hitstop(self):
        self.player.light = PortableLight(160, 120, self.stage.light_regions[0])
        self.hit()
        remaining = self.player.light.remaining
        update_world(0.02, self.player, [self.enemy], self.stage)
        self.assertAlmostEqual(self.player.light.remaining, remaining - 0.02)

    def test_combo_input_during_hitstop_is_kept_until_resume(self):
        self.player._begin_attack(1)
        self.player.attack_elapsed = 0.12
        update_world(0.01, self.player, [self.enemy], self.stage)
        for kind in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
            event = pico2d.Event(kind)
            event.key = pico2d.SDLK_w
            self.player.handle_event(event)
        self.player.update(0.02, self.stage.width, self.stage.solids)
        self.assertTrue(self.player.attack_requested)
        for _ in range(40):
            self.player.update(0.01, self.stage.width, self.stage.solids)
        self.assertEqual(self.player.attack_id, 2)
        self.assertEqual(self.player.attack_stage, 2)

    def test_heavy_and_lethal_hits_have_stronger_feedback(self):
        normal = Impact(0, 0, 1)
        heavy = Impact(0, 0, 1, heavy=True)
        lethal = self.hit(stage=2, lethal=True)
        self.assertLess(normal.hitstop, heavy.hitstop)
        self.assertLess(heavy.hitstop, lethal.hitstop)
        self.assertTrue(lethal.lethal)
        self.assertEqual(self.enemy.state, 'DYING')
        self.assertIsNone(self.enemy.consume_attack())

    def test_reset_and_return_remove_feedback_state(self):
        self.hit()
        self.enemy.reset()
        self.player.reset_actions_after_return()
        self.assertIsNone(self.enemy.impact)
        self.assertEqual(self.enemy.hit_pause.remaining, 0)
        self.assertEqual(self.player.hit_pause.remaining, 0)

    def test_impact_origin_is_contact_and_effect_expires(self):
        impact = self.hit()
        self.assertGreaterEqual(impact.x, self.enemy.get_bb()[0])
        self.assertLessEqual(impact.x, self.player.get_attack_box()[2])
        self.assertGreater(impact.y, self.enemy.feet_y)
        self.enemy.update(0.3, self.player, self.stage)
        self.assertIsNone(self.enemy.impact)
