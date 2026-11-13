import unittest
from unittest.mock import Mock, patch

import pico2d

from physics import RUN_SPEED, Solid
from player import Player


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


class RunningTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_running_speed_is_frame_rate_independent_and_release_returns_to_walk(self):
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                player = Player(400, 96)
                key(player, pico2d.SDLK_RIGHT)
                key(player, pico2d.SDLK_LSHIFT)
                for _ in range(fps):
                    player.update(1 / fps, 1920)
                self.assertAlmostEqual(player.x, 400 + RUN_SPEED)
                self.assertTrue(player.is_running)
                key(player, pico2d.SDLK_LSHIFT, False)
                player.update(0.1, 1920)
                self.assertAlmostEqual(player.x, 400 + RUN_SPEED + 12.8)
                self.assertFalse(player.is_running)

    def test_running_jump_keeps_height_and_gravity_while_covering_more_distance(self):
        walk, run = Player(400, 96), Player(400, 96)
        for player in (walk, run):
            key(player, pico2d.SDLK_RIGHT)
            key(player, pico2d.SDLK_SPACE)
        key(run, pico2d.SDLK_LSHIFT)
        for _ in range(30):
            walk.update(1 / 120, 1920)
            run.update(1 / 120, 1920)
            self.assertAlmostEqual(walk.feet_y, run.feet_y)
            self.assertAlmostEqual(walk.motion.velocity_y, run.motion.velocity_y)
        self.assertGreater(run.x, walk.x)
        self.assertEqual(run.invulnerability, 0)
        self.assertTrue(run.take_damage())

    def test_run_obeys_wall_and_attack_lock_and_input_clear(self):
        player = Player(400, 96)
        key(player, pico2d.SDLK_RIGHT)
        key(player, pico2d.SDLK_LSHIFT)
        solids = [Solid(0, 0, 1920, 96), Solid(440, 96, 480, 300)]
        for _ in range(30):
            player.update(1 / 120, 1920, solids)
        self.assertEqual(player.get_bb()[2], 440)
        key(player, pico2d.SDLK_w)
        position = player.x
        player.update(0.1, 1920, solids)
        self.assertEqual(player.x, position)
        self.assertFalse(player.is_running)
        player.clear_input()
        self.assertFalse(player.run_held)
