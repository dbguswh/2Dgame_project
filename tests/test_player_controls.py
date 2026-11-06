import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player
from physics import Solid


def key(player, value, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = value
    player.handle_event(event)


class PlayerControlsTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.player = Player(160, 96)

    def test_space_does_not_auto_jump_when_held(self):
        key(self.player, pico2d.SDLK_SPACE)
        for _ in range(70):
            self.player.update(1 / 60, 960)
        self.assertTrue(self.player.motion.on_ground)
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(1 / 60, 960)
        self.assertTrue(self.player.motion.on_ground)
        key(self.player, pico2d.SDLK_SPACE, False)
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(1 / 60, 960)
        self.assertFalse(self.player.motion.on_ground)

    def test_air_jump_input_does_not_restart_upward_velocity(self):
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(0.05, 960)
        key(self.player, pico2d.SDLK_SPACE, False)
        key(self.player, pico2d.SDLK_SPACE)
        velocity = self.player.motion.velocity_y
        self.player.update(0.05, 960)
        self.assertLess(self.player.motion.velocity_y, velocity)

    def test_air_movement_uses_jump_pose_instead_of_walking(self):
        key(self.player, pico2d.SDLK_RIGHT)
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(0.05, 960)
        self.assertGreater(self.player.x, 160)
        self.assertFalse(self.player.is_moving)

    def test_focus_loss_cancels_pending_jump_and_movement(self):
        key(self.player, pico2d.SDLK_RIGHT)
        key(self.player, pico2d.SDLK_SPACE)
        self.player.clear_input()
        self.player.update(0.05, 960)
        self.assertEqual(self.player.x, 160)
        self.assertEqual(self.player.feet_y, 96)

    def test_fall_costs_health_and_restores_last_safe_position(self):
        self.player.last_safe_position = (600, 160)
        self.player.feet_y = -200
        self.player.update(0.01, 1920, [])
        self.assertEqual(self.player.health, 2)
        self.assertEqual((self.player.x, self.player.feet_y), (600, 160))
        self.assertEqual(self.player.invulnerability, 1)
        self.assertFalse(self.player.jump_requested)
        self.assertFalse(self.player.is_moving)

    def test_health_exhaustion_restores_start(self):
        self.player.health = 1
        self.player.last_safe_position = (600, 160)
        self.player.feet_y = -200
        self.player.update(0.01, 1920, [])
        self.assertEqual(self.player.health, 3)
        self.assertEqual((self.player.x, self.player.feet_y), (160, 96))

    def test_jump_selects_rise_apex_fall_then_idle(self):
        key(self.player, pico2d.SDLK_SPACE)
        states = set()
        for _ in range(60):
            self.player.update(1 / 60, 960)
            states.add(self.player.animation_state)
        self.assertEqual(states, {'jump_rise', 'jump_apex', 'jump_fall', 'idle'})
        self.assertEqual(self.player.animation_state, 'idle')

    def test_w_is_one_ground_attack_per_new_press(self):
        key(self.player, pico2d.SDLK_w)
        self.player.update(1 / 60, 960)
        self.assertEqual(self.player.animation_state, 'attack')
        first_id = self.player.attack_id
        for _ in range(60):
            key(self.player, pico2d.SDLK_w)
            self.player.update(1 / 60, 960)
        self.assertEqual(self.player.attack_id, first_id)
        self.assertFalse(self.player.is_attacking)
        key(self.player, pico2d.SDLK_w, False)
        key(self.player, pico2d.SDLK_w)
        self.player.update(1 / 60, 960)
        self.assertEqual(self.player.attack_id, first_id + 1)

    def test_attack_holds_facing_and_blocks_overlapping_jump(self):
        key(self.player, pico2d.SDLK_LEFT)
        key(self.player, pico2d.SDLK_w)
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(1 / 60, 960)
        self.assertEqual(self.player.x, 160)
        self.assertEqual(self.player.face_dir, 1)
        self.assertTrue(self.player.motion.on_ground)

    def test_week_one_w_does_not_trigger_air_attack(self):
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(1 / 60, 960)
        key(self.player, pico2d.SDLK_w)
        self.player.update(1 / 60, 960)
        self.assertFalse(self.player.is_attacking)

    def start_active_attack(self, solids=None):
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960, solids)
        self.player.update(0.11, 960, solids)

    def test_attack_box_only_exists_during_strike(self):
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960)
        self.assertIsNone(self.player.get_attack_box())
        self.player.update(0.11, 960)
        self.assertIsNotNone(self.player.get_attack_box())
        self.player.update(0.11, 960)
        self.assertIsNone(self.player.get_attack_box())

    def test_only_closest_target_is_selected_once_per_attack(self):
        self.start_active_attack()
        targets = [(2, (190, 96, 214, 176)), (1, (175, 96, 185, 176))]
        self.assertEqual(self.player.get_attack_target(targets), 1)
        self.assertIsNone(self.player.get_attack_target(targets))

    def test_wall_blocks_attack_target(self):
        self.start_active_attack([Solid(0, 0, 960, 96), Solid(176, 96, 192, 240)])
        self.assertIsNone(self.player.get_attack_target([(1, (193, 96, 210, 176))]))

    def test_other_floor_is_not_hit_and_left_attack_is_mirrored(self):
        self.player.face_dir = -1
        self.start_active_attack()
        self.assertIsNone(self.player.get_attack_target([(1, (130, 200, 145, 280))]))
        self.assertEqual(self.player.get_attack_target([(2, (125, 96, 145, 176))]), 2)

    def test_six_attack_poses_match_the_active_hit_window(self):
        body = self.player.get_bb()
        for index, time in enumerate((0.025, 0.075, 0.125, 0.175, 0.24, 0.32)):
            with self.subTest(pose=index):
                self.player.attack_elapsed = time
                self.assertEqual(self.player.attack_frame, index)
                self.assertEqual(self.player.get_bb(), body)
                self.assertEqual(self.player.get_attack_box() is not None, index in (2, 3))
                if index in (2, 3):
                    box = self.player.get_attack_box()
                    self.assertEqual(box[2] - box[0], 32)

    def test_attack_finishes_after_visible_recovery(self):
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960)
        for _ in range(3):
            self.player.update(0.1, 960)
        self.assertTrue(self.player.is_attacking)
        self.assertEqual(self.player.attack_frame, 5)
        self.player.update(0.07, 960)
        self.assertFalse(self.player.is_attacking)

    def test_enemy_damage_grants_one_second_invulnerability(self):
        self.assertTrue(self.player.take_damage())
        self.assertEqual(self.player.health, 2)
        self.assertFalse(self.player.take_damage())
        self.assertEqual(self.player.health, 2)
        for _ in range(61):
            self.player.update(1 / 60, 960)
        self.assertTrue(self.player.take_damage())
        self.assertEqual(self.player.health, 1)

    def test_enemy_damage_cancels_player_attack(self):
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960)
        self.assertTrue(self.player.is_attacking)
        self.player.take_damage()
        self.assertFalse(self.player.is_attacking)
        self.assertIsNone(self.player.get_attack_box())

    def test_fatal_enemy_hit_restores_start_and_changes_life_counter(self):
        self.player.health = 1
        self.player.x = 410
        self.player.take_damage()
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.respawn_count, 1)
        self.assertEqual((self.player.x, self.player.feet_y), (160, 96))
        self.assertEqual(self.player.invulnerability, 1)

    def install_light(self):
        key(self.player, pico2d.SDLK_r, False)
        key(self.player, pico2d.SDLK_r)
        self.player.update(0.01, 960)

    def test_r_costs_50_only_once_when_held(self):
        self.install_light()
        first_light = self.player.light
        for _ in range(30):
            key(self.player, pico2d.SDLK_r)
            self.player.update(1 / 60, 960)
        self.assertEqual(self.player.battery, 50)
        self.assertIs(self.player.light, first_light)

    def test_second_install_replaces_old_light_and_third_is_rejected(self):
        self.install_light()
        old_light = self.player.light
        for _ in range(12):
            self.player.update(1 / 60, 960)
        self.player.x = 240
        self.install_light()
        self.assertEqual(self.player.battery, 0)
        self.assertIsNot(self.player.light, old_light)
        self.assertEqual(self.player.light.x, 240)
        current_light = self.player.light
        for _ in range(12):
            self.player.update(1 / 60, 960)
        self.install_light()
        self.assertIs(self.player.light, current_light)
        self.assertEqual(self.player.battery, 0)

    def test_battery_zero_still_allows_move_jump_and_w(self):
        self.player.battery = 0
        key(self.player, pico2d.SDLK_RIGHT)
        key(self.player, pico2d.SDLK_SPACE)
        self.player.update(0.05, 960)
        self.assertGreater(self.player.x, 160)
        self.assertFalse(self.player.motion.on_ground)
        key(self.player, pico2d.SDLK_SPACE, False)
        key(self.player, pico2d.SDLK_RIGHT, False)
        for _ in range(60):
            self.player.update(1 / 60, 960)
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960)
        self.assertTrue(self.player.is_attacking)

    def test_same_frame_r_takes_priority_over_w_without_double_action(self):
        key(self.player, pico2d.SDLK_w)
        key(self.player, pico2d.SDLK_r)
        self.player.update(0.01, 960)
        self.assertIsNotNone(self.player.light)
        self.assertEqual(self.player.battery, 50)
        self.assertFalse(self.player.is_attacking)

    def test_r_is_ignored_during_an_existing_w_attack(self):
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960)
        self.install_light()
        self.assertIsNone(self.player.light)
        self.assertEqual(self.player.battery, 100)

    def test_death_ends_light_without_recharging_battery(self):
        self.install_light()
        self.player.health = 1
        self.player.take_damage()
        self.assertEqual(self.player.battery, 50)
        self.assertIsNone(self.player.light)
        self.player.invulnerability = 0
        self.player.battery = 0
        self.player.health = 1
        self.player.feet_y = -200
        self.player.update(0.01, 960, [])
        self.assertEqual(self.player.battery, 0)
        self.assertEqual(self.player.health, 3)


if __name__ == '__main__':
    unittest.main()
