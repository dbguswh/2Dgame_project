import unittest
from unittest.mock import Mock, patch

import pico2d

from session import GameSession


def key(game, value, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = value
    game.handle_event(event)


class SessionTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.game = GameSession()

    def start(self):
        key(self.game, pico2d.SDLK_e)
        key(self.game, pico2d.SDLK_e, False)

    def test_title_start_creates_fresh_world(self):
        self.assertEqual(self.game.state, 'TITLE')
        self.assertIsNone(self.game.player)
        self.start()
        self.assertEqual(self.game.state, 'PLAY')
        self.assertEqual(self.game.player.health, 3)
        self.assertEqual(self.game.player.battery, 100)
        self.assertEqual(self.game.enemies[0].health, 2)

    def test_title_menu_ignores_held_key_repeat(self):
        key(self.game, pico2d.SDLK_DOWN)
        key(self.game, pico2d.SDLK_DOWN)
        self.assertEqual(self.game.selection, 1)
        key(self.game, pico2d.SDLK_e)
        self.assertFalse(self.game.running)

    def test_title_and_unfocused_world_do_not_accumulate_time(self):
        self.game.update(1)
        self.assertEqual(self.game.play_time, 0)
        self.start()
        self.game.update(0.02)
        elapsed = self.game.play_time
        key(self.game, pico2d.SDLK_RIGHT)
        self.game.update(1, focused=False)
        self.assertEqual(self.game.play_time, elapsed)
        self.assertEqual(self.game.player.x, 160)


if __name__ == '__main__':
    unittest.main()
