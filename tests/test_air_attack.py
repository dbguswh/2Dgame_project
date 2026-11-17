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

    def test_uppercut_uses_current_facing_instead_of_previous_combo(self):
        for grounded in (True,False):
            for facing in (-1,1):
                p=Player(400,96);p.face_dir=facing;p.combo_direction=-facing
                if not grounded:p.motion.jump();p.update(.05,960)
                key(p,pico2d.SDLK_UP);tap(p)
                p.update(0,960);p.update(.16,960)
                self.assertEqual((p.attack_kind,p.face_dir),('upper',facing))
                box=p.get_attack_box();self.assertIsNotNone(box)
                self.assertTrue(box[2]<=p.x if facing<0 else box[0]>=p.x)

    def test_new_left_input_and_air_attack_in_same_frame_face_left(self):
        self.jump();key(self.player,pico2d.SDLK_LEFT);tap(self.player)
        self.player.update(0,960)
        self.assertEqual(self.player.face_dir,-1)
        self.assertEqual(self.player.attack_kind,'air')

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

    def test_air_hit_is_single_nearest_target_without_upward_or_backward_reach(self):
        self.start_air_attack()
        self.tick(0.12)
        x, y = self.player.x, self.player.feet_y
        self.assertIsNone(self.player.get_attack_target([
            ('behind', (x - 45, y - 10, x - 20, y + 40)),
            ('above', (x + 20, y + 50, x + 40, y + 130)),
        ]))
        targets = [('far', (x + 34, y - 10, x + 50, y + 40)),
                   ('near', (x + 16, y - 10, x + 30, y + 40))]
        self.assertEqual(self.player.get_attack_target(targets), 'near')
        self.assertIsNone(self.player.get_attack_target(targets))

    def test_air_strike_is_blocked_by_wall_and_floor(self):
        self.start_air_attack()
        self.tick(0.12)
        x, y = self.player.x, self.player.feet_y
        self.player.solids = [Solid(x + 24, 96, x + 30, 300)]
        self.assertIsNone(self.player.get_attack_target([
            ('wall', (x + 31, y - 5, x + 45, y + 40))]))
        self.player.solids = [Solid(x - 100, y - 20, x + 100, y - 8)]
        self.assertIsNone(self.player.get_attack_target([
            ('under_floor', (x + 16, y - 40, x + 32, y - 9))]))
        self.assertAlmostEqual(self.player.get_attack_box()[1], y - 8)

    def test_air_six_poses_use_only_two_strike_frames_and_constant_body(self):
        self.start_air_attack()
        body = self.player.get_bb()
        for index, time in enumerate((0.025, 0.075, 0.13, 0.19, 0.25, 0.31)):
            with self.subTest(pose=index):
                self.player.attack_elapsed = time
                self.assertEqual(self.player.attack_frame, index)
                self.assertEqual(self.player.get_bb(), body)
                self.assertEqual(self.player.get_attack_box() is not None, index in (2, 3))
                if index in (2, 3):
                    box = self.player.get_attack_box()
                    self.assertEqual(box[2] - box[0], 80)

    def test_left_air_hit_and_sprite_are_mirrored(self):
        self.player.face_dir = -1
        self.start_air_attack()
        self.tick(0.12)
        x, y = self.player.x, self.player.feet_y
        self.assertEqual(self.player.get_attack_target([
            ('left', (x - 40, y - 10, x - 20, y + 40))]), 'left')
        self.player.draw()
        args = self.player.air_attack_image.clip_composite_draw.call_args.args
        self.assertEqual(args[5], 'h')

    def test_air_hit_does_not_cancel_nonfatal_enemy_warning_or_apply_push(self):
        from enemy import Shade
        from stage import Stage
        from world import update_world

        stage = Stage()
        enemy = Shade(440, 96, combat_bounds=stage.combat_bounds)
        enemy._enter('WINDUP')
        self.start_air_attack()
        for _ in range(25):
            update_world(1 / 120, self.player, [enemy], stage)
        self.assertEqual(enemy.health, 65)
        self.assertEqual(enemy.state, 'WINDUP')
        self.assertEqual(enemy.knockback_remaining, 0)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.battery, 100)

    def test_landing_attack_starts_new_ground_combo(self):
        self.start_air_attack()
        self.tick(0.7)
        tap(self.player)
        self.player.update(0, 960)
        self.tick(0.1)
        tap(self.player)
        self.player.update(0, 960)
        self.tick(0.27)
        self.assertEqual(self.player.attack_kind, 'ground')
        self.assertEqual(self.player.attack_stage, 2)
        self.assertEqual(self.player.attack_id, 3)
