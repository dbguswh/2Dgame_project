import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


def tap(player, code=pico2d.SDLK_w):
    key(player, code)
    key(player, code, False)


class GroundComboTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = Player(400, 96)

    def tick(self, seconds):
        remaining = seconds
        while remaining > 0.000001:
            dt = min(0.005, remaining)
            self.player.update(dt, 960)
            remaining -= dt

    def start(self):
        tap(self.player)
        self.player.update(0, 960)

    def second(self):
        self.start()
        self.tick(0.2)
        tap(self.player)
        self.player.update(0, 960)
        self.tick(0.17)
        self.assertEqual(self.player.attack_stage, 2)

    def test_early_second_press_waits_for_first_animation(self):
        self.start()
        self.tick(0.1)
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.attack_stage, 1)
        self.assertTrue(self.player.combo_queued)
        self.tick(0.27)
        self.assertEqual(self.player.attack_stage, 2)
        self.assertEqual(self.player.attack_id, 2)
        self.assertLess(self.player.attack_elapsed, 0.02)

    def test_late_press_inside_point_four_seconds_still_chains(self):
        self.start()
        self.tick(0.39)
        self.assertFalse(self.player.is_attacking)
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.attack_stage, 2)
        self.assertTrue(self.player.is_attacking)

    def test_held_w_does_not_chain_without_release(self):
        key(self.player, pico2d.SDLK_w)
        self.player.update(0, 960)
        for _ in range(100):
            key(self.player, pico2d.SDLK_w)
            self.tick(0.01)
        self.assertEqual(self.player.attack_id, 1)
        self.assertFalse(self.player.is_attacking)

    def test_missed_window_does_not_start_second_or_save_input(self):
        self.start()
        self.tick(0.42)
        tap(self.player)
        self.player.update(0, 960)
        self.tick(0.2)
        self.assertEqual(self.player.attack_id, 1)
        self.assertFalse(self.player.is_attacking)
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.attack_stage, 1)
        self.assertEqual(self.player.attack_id, 2)

    def test_second_cannot_chain_into_third_and_has_half_second_recovery(self):
        self.second()
        tap(self.player)
        self.player.update(0, 960)
        self.tick(0.44)
        self.assertFalse(self.player.is_attacking)
        self.assertEqual(self.player.attack_id, 2)
        self.tick(0.47)
        tap(self.player)
        self.player.update(0, 960)
        self.assertFalse(self.player.is_attacking)
        self.tick(0.04)
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.attack_stage, 1)
        self.assertEqual(self.player.attack_id, 3)

    def test_each_strike_hits_nearest_target_once_and_uses_no_battery(self):
        self.start()
        self.tick(0.13)
        targets = [(1, (430, 96, 454, 176)), (2, (438, 96, 462, 176))]
        self.assertEqual(self.player.get_attack_target(targets), 1)
        self.assertIsNone(self.player.get_attack_target(targets))
        tap(self.player)
        self.player.update(0, 960)
        self.tick(0.37)
        self.assertEqual(self.player.attack_stage, 2)
        self.assertEqual(self.player.get_attack_target(targets), 1)
        self.assertIsNone(self.player.get_attack_target(targets))
        self.assertEqual(self.player.battery, 100)

    def test_damage_cancels_buffered_second_strike(self):
        self.start()
        self.tick(0.15)
        tap(self.player)
        self.player.update(0, 960)
        self.player.take_damage()
        self.tick(0.5)
        self.assertFalse(self.player.is_attacking)
        self.assertFalse(self.player.combo_queued)
        self.assertEqual(self.player.attack_id, 1)

    def test_second_strike_blocks_jump_movement_and_facing_change(self):
        self.second()
        key(self.player, pico2d.SDLK_LEFT)
        tap(self.player, pico2d.SDLK_SPACE)
        self.tick(0.1)
        self.assertEqual(self.player.x, 400)
        self.assertEqual(self.player.face_dir, 1)
        self.assertTrue(self.player.motion.on_ground)
