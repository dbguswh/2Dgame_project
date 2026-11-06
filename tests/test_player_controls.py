import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player


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


if __name__ == '__main__':
    unittest.main()
