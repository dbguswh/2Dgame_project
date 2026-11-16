import unittest
from unittest.mock import Mock, patch

import pico2d

from physics import Solid
from player import Player


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


def tap(player, code=pico2d.SDLK_q):
    key(player, code)
    key(player, code, False)


class FlashInputTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = Player(400, 96)

    def tick(self, seconds):
        remaining = seconds
        while remaining > 0.000001:
            dt = min(1 / 120, remaining)
            self.player.update(dt, 960)
            remaining -= dt

    def test_new_press_costs_once_and_holding_does_not_repeat(self):
        key(self.player, pico2d.SDLK_q)
        self.player.update(0, 960)
        self.assertEqual(self.player.battery, 80)
        self.assertEqual(self.player.animation_state, 'flash')
        for _ in range(180):
            key(self.player, pico2d.SDLK_q)
            self.player.update(1 / 120, 960)
        self.assertEqual(self.player.battery, 80)
        self.assertEqual(self.player.attack_id, 1)

    def test_whiff_costs_energy_but_cooldown_and_low_battery_do_not(self):
        tap(self.player)
        self.player.update(0, 960)
        self.assertIsNone(self.player.consume_flash_target([]))
        self.tick(0.4)
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.battery, 80)
        self.tick(0.41)
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.battery, 60)
        self.tick(0.9)
        self.player.battery = 19
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.battery, 19)
        self.assertFalse(self.player.is_attacking)
        self.assertEqual(self.player.flash_cooldown, 0)

    def test_only_closest_front_target_can_be_hit_once(self):
        tap(self.player)
        self.player.update(0, 960)
        targets = [('far', (480, 96, 504, 184)), ('near', (440, 96, 464, 184))]
        self.assertEqual(self.player.consume_flash_target(targets), 'near')
        self.assertIsNone(self.player.consume_flash_target(targets))
        self.assertIsNone(self.player.get_attack_box())

    def test_wall_other_floor_and_behind_are_excluded(self):
        tap(self.player)
        self.player.update(0, 960, [Solid(0, 0, 960, 96), Solid(460, 96, 472, 280)])
        self.assertIsNone(self.player.consume_flash_target([
            ('wall', (474, 96, 498, 184)), ('above', (420, 288, 444, 376)),
            ('behind', (360, 96, 384, 184))]))

    def test_simultaneous_priority_is_r_then_q_then_w(self):
        for codes, battery, kind in (((pico2d.SDLK_r, pico2d.SDLK_q, pico2d.SDLK_w), 50, None),
                                      ((pico2d.SDLK_q, pico2d.SDLK_w), 80, 'flash')):
            with self.subTest(codes=codes):
                self.player = Player(400, 96)
                for code in codes:
                    tap(self.player, code)
                self.player.update(0, 960)
                self.assertEqual(self.player.battery, battery)
                self.assertEqual(self.player.attack_kind if self.player.is_attacking else None, kind)

    def test_existing_attack_rejects_q_without_storing_it(self):
        tap(self.player, pico2d.SDLK_w)
        self.player.update(0, 960)
        tap(self.player)
        self.player.update(0.01, 960)
        self.tick(0.8)
        self.assertEqual(self.player.battery, 100)
        self.assertFalse(self.player.flash_pending)

    def test_ground_cast_locks_motion_and_direction_without_invulnerability(self):
        tap(self.player)
        key(self.player, pico2d.SDLK_LEFT)
        key(self.player, pico2d.SDLK_LSHIFT)
        tap(self.player, pico2d.SDLK_SPACE)
        self.player.update(0.1, 960)
        self.assertEqual((self.player.x, self.player.feet_y, self.player.face_dir), (400, 96, 1))
        self.assertEqual(self.player.invulnerability, 0)

    def test_air_cast_preserves_trajectory_and_return_clears_pending_flash(self):
        control = Player(400, 96)
        for player in (self.player, control):
            player.motion.jump()
            key(player, pico2d.SDLK_RIGHT)
        tap(self.player)
        for _ in range(20):
            self.player.update(1 / 120, 960)
            control.update(1 / 120, 960)
        self.assertAlmostEqual(self.player.x, control.x)
        self.assertAlmostEqual(self.player.feet_y, control.feet_y)
        self.player.reset_actions_after_return()
        self.assertFalse(self.player.flash_pending)
        self.assertIsNone(self.player.flash_effect)
