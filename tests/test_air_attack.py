import unittest
from unittest.mock import Mock, patch

import pico2d

from physics import Solid
from player import Player


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


def tap(player, code=pico2d.SDLK_w):
    key(player, code)
    key(player, code, False)


class AirAttackTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = Player(400, 96)

    def tick(self, seconds, player=None, solids=None):
        player = player or self.player
        remaining = seconds
        while remaining > 0.000001:
            dt = min(1 / 120, remaining)
            player.update(dt, 960, solids)
            remaining -= dt

    def jump(self):
        tap(self.player, pico2d.SDLK_SPACE)
        self.tick(0.05)
        self.assertFalse(self.player.motion.on_ground)

    def start_air_attack(self):
        self.jump()
        tap(self.player)
        self.player.update(0, 960)

    def test_air_attack_keeps_jump_trajectory_and_horizontal_control(self):
        control = Player(400, 96)
        for player in (self.player, control):
            tap(player, pico2d.SDLK_SPACE)
            key(player, pico2d.SDLK_RIGHT)
            self.tick(0.05, player)
        tap(self.player)
        self.tick(0.2)
        self.tick(0.2, control)
        self.assertAlmostEqual(self.player.x, control.x)
        self.assertAlmostEqual(self.player.feet_y, control.feet_y)
        self.assertAlmostEqual(self.player.motion.velocity_y, control.motion.velocity_y)
        self.assertEqual(self.player.battery, 100)
        self.assertEqual(self.player.invulnerability, 0)
        self.assertFalse(self.player.combo_queued)

    def test_air_attack_can_only_start_once_until_landing(self):
        self.start_air_attack()
        self.tick(0.4)
        self.assertFalse(self.player.is_attacking)
        self.assertFalse(self.player.motion.on_ground)
        tap(self.player)
        self.tick(0.01)
        self.assertEqual(self.player.attack_id, 1)
        self.tick(0.3)
        self.jump()
        tap(self.player)
        self.player.update(0, 960)
        self.assertEqual(self.player.attack_id, 2)
        self.assertEqual(self.player.attack_kind, 'air')

    def test_landing_cancels_air_pose_and_requires_new_ground_press(self):
        self.jump()
        self.tick(0.58)
        key(self.player, pico2d.SDLK_w)
        self.tick(0.12)
        self.assertTrue(self.player.motion.on_ground)
        self.assertFalse(self.player.is_attacking)
        self.assertFalse(self.player.air_attack_used)
        self.tick(0.1)
        self.assertEqual(self.player.attack_id, 1)
        key(self.player, pico2d.SDLK_w, False)
        tap(self.player)
        self.player.update(0, 960)
        self.assertTrue(self.player.is_attacking)
        self.assertEqual(self.player.attack_kind, 'ground')
        self.assertEqual(self.player.attack_stage, 1)

    def test_air_damage_cancels_pose_without_allowing_second_air_attack(self):
        self.start_air_attack()
        self.assertTrue(self.player.take_damage())
        tap(self.player)
        self.tick(0.01)
        self.assertFalse(self.player.is_attacking)
        self.assertTrue(self.player.air_attack_used)
        self.assertEqual(self.player.attack_id, 1)

    def test_air_direction_is_locked_but_movement_can_reverse(self):
        self.start_air_attack()
        key(self.player, pico2d.SDLK_LEFT)
        self.tick(0.1)
        self.assertLess(self.player.x, 400)
        self.assertEqual(self.player.face_dir, 1)
        self.assertTrue(self.player.is_attacking)

    def test_pause_input_clear_does_not_rearm_and_return_resets_attack(self):
        self.start_air_attack()
        self.player.clear_input()
        self.assertTrue(self.player.air_attack_used)
        self.assertTrue(self.player.is_attacking)
        self.player.reset_actions_after_return()
        self.assertFalse(self.player.air_attack_used)
        self.assertFalse(self.player.is_attacking)
        self.assertEqual(self.player.attack_kind, 'ground')

    def test_jump_does_not_bypass_ground_combo_recovery(self):
        self.player.attack_cooldown = 0.5
        self.jump()
        tap(self.player)
        self.tick(0.01)
        self.assertFalse(self.player.is_attacking)
        self.assertFalse(self.player.air_attack_used)

    def test_walk_off_ledge_allows_one_air_attack(self):
        solids = [Solid(0, 0, 390, 96), Solid(0, -100, 960, -80)]
        self.player.x = 420
        self.player.update(0.02, 960, solids)
        self.assertFalse(self.player.motion.on_ground)
        tap(self.player)
        self.player.update(0, 960, solids)
        self.assertTrue(self.player.is_attacking)
        self.assertEqual(self.player.attack_kind, 'air')
