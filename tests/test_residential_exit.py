import unittest
from unittest.mock import Mock, patch

import pico2d
from session import GameSession


def key(game, value, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = value
    game.handle_event(event)


class ResidentialExitTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.game.player.x, self.game.player.feet_y = self.game.stage.exit_position

    def open_bridge(self):
        self.game.stage.fuse_state = 'INSTALLED'
        self.game.stage.fixture_powered = True
        self.game.stage.update(self.game.stage.BRIDGE_TIME)

    def exit(self):
        key(self.game, pico2d.SDLK_e)
        self.game.update(0.01)

    def test_exit_requires_repair_deployment_ground_and_fresh_e(self):
        self.exit()
        self.assertFalse(self.game.stage.completed)
        key(self.game, pico2d.SDLK_e, False)
        self.open_bridge()
        self.game.update(0.01)
        self.assertEqual(self.game.state, 'PLAY')
        self.game.player.motion.on_ground = False
        self.assertFalse(self.game.stage.activate_exit(self.game.player))
        self.game.player.motion.on_ground = True
        self.exit()
        self.assertEqual(self.game.state, 'STAGE_CLEAR')
        self.assertTrue(self.game.records.latest.completed)
        self.assertFalse(self.game.records.entry.completed)

    def test_clear_freezes_time_and_held_e_cannot_advance_then_fresh_e_opens_map(self):
        self.open_bridge()
        self.exit()
        elapsed = self.game.play_time
        key(self.game, pico2d.SDLK_e)
        self.game.update(2)
        self.assertEqual(self.game.state, 'STAGE_CLEAR')
        self.assertEqual(self.game.play_time, elapsed)
        key(self.game, pico2d.SDLK_e, False)
        key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'CITY_MAP')
        self.assertTrue(self.game.stage.completed)
        self.assertEqual(self.game.play_time, elapsed)
        key(self.game, pico2d.SDLK_e, False)
        key(self.game, pico2d.SDLK_ESCAPE)
        key(self.game, pico2d.SDLK_ESCAPE, False)
        key(self.game, pico2d.SDLK_DOWN)
        key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'PLAY')
        self.assertFalse(self.game.stage.completed)
        self.assertFalse(self.game.stage.bridge_ready)
        self.assertEqual(self.game.stage.fuse_state, 'WORLD')
        self.assertEqual(self.game.player.battery, 100)
        self.assertEqual(self.game.play_time, elapsed)

    def test_clear_can_return_to_title(self):
        self.open_bridge()
        self.exit()
        key(self.game, pico2d.SDLK_e, False)
        key(self.game, pico2d.SDLK_DOWN)
        key(self.game, pico2d.SDLK_DOWN, False)
        key(self.game, pico2d.SDLK_DOWN)
        key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'TITLE')
        self.assertIsNone(self.game.player)
