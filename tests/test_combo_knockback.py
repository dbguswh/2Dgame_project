import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pico2d

from enemy import Shade
from physics import Solid
from player import Player
from stage import Stage
from world import update_world


class ComboKnockbackTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = Stage()
        self.player = Player(400, 96)
        self.enemy = Shade(440, 96, combat_bounds=self.stage.combat_bounds)

    def test_real_three_hit_combo_kills_once_with_outward_finish(self):
        self.enemy._enter('WINDUP')
        hits = []
        previous_health = 100
        for frame in range(185):
            if frame in (0, 24, 66):
                for event_type in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
                    event = pico2d.Event(event_type)
                    event.key = pico2d.SDLK_w
                    self.player.handle_event(event)
            update_world(1 / 120, self.player, [self.enemy], self.stage)
            if self.enemy.health != previous_health:
                hits.append(self.player.attack_stage)
                previous_health = self.enemy.health
        self.assertEqual(hits, [1, 2, 3])
        self.assertEqual(self.enemy.health, 0)
        self.assertAlmostEqual(self.enemy.x, 504)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.battery, 100)

    def test_nonfatal_second_hit_does_not_cancel_warning(self):
        self.enemy._enter('WINDUP')
        self.enemy.state_time = 0.4
        self.player.attack_stage = 2
        self.player.attack_elapsed = 0.12
        update_world(0.01, self.player, [self.enemy], self.stage)
        self.assertEqual(self.enemy.health, 65)
        self.assertEqual(self.enemy.state, 'WINDUP')
        self.assertAlmostEqual(self.enemy.state_time, 0.41)
        self.assertEqual(self.enemy.knockback_remaining, 32)

    def test_push_stops_at_wall_and_ledge(self):
        for solids, max_right in (([Solid(0, 0, 960, 96), Solid(470, 96, 486, 300)], 470),
                                   ([Solid(0, 0, 460, 96)], 460)):
            with self.subTest(edge=max_right):
                stage = SimpleNamespace(width=960, solids=solids)
                enemy = Shade(430, 96, combat_bounds=(0, 960))
                enemy.health = 0
                enemy._enter('DYING')
                enemy.apply_knockback(1)
                for _ in range(30):
                    enemy.update(1 / 120, self.player, stage)
                    self.assertLessEqual(enemy.get_bb()[2], max_right)
                    self.assertEqual(enemy.feet_y, 96)
                self.assertEqual(enemy.knockback_remaining, 0)

    def test_left_push_is_mirrored_and_reset_clears_pending_push(self):
        self.enemy.health = 0
        self.enemy._enter('DYING')
        self.enemy.apply_knockback(-1)
        for _ in range(20):
            self.enemy.update(1 / 120, self.player, self.stage)
        self.assertAlmostEqual(self.enemy.x, 408)
        self.enemy.apply_knockback(1)
        self.enemy.reset()
        self.assertEqual(self.enemy.knockback_remaining, 0)
        self.assertEqual(self.enemy.x, 440)
