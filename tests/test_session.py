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

    def pause(self):
        key(self.game, pico2d.SDLK_ESCAPE)
        key(self.game, pico2d.SDLK_ESCAPE, False)

    def test_pause_freezes_world_effects_and_play_time(self):
        self.start()
        key(self.game, pico2d.SDLK_r)
        self.game.update(0.02)
        player, enemy = self.game.player, self.game.enemies[0]
        snapshot = (player.x, player.light.remaining, enemy.x, enemy.state_time, self.game.play_time)
        self.pause()
        self.game.update(3)
        self.assertEqual(self.game.state, 'PAUSED')
        self.assertEqual((player.x, player.light.remaining, enemy.x, enemy.state_time, self.game.play_time), snapshot)
        self.pause()
        self.game.update(0.02)
        self.assertEqual(self.game.state, 'PLAY')
        self.assertAlmostEqual(player.light.remaining, snapshot[1] - 0.02)

    def test_pause_menu_input_does_not_trigger_player_actions(self):
        self.start()
        self.pause()
        key(self.game, pico2d.SDLK_r)
        key(self.game, pico2d.SDLK_w)
        key(self.game, pico2d.SDLK_e)
        self.game.update(0.02)
        self.assertEqual(self.game.state, 'PLAY')
        self.assertEqual(self.game.player.battery, 100)
        self.assertFalse(self.game.player.is_attacking)

    def test_return_to_title_then_start_resets_the_run(self):
        self.start()
        self.game.player.battery = 0
        self.pause()
        self.game.selection = self.game.PAUSE_ITEMS.index('타이틀로')
        key(self.game, pico2d.SDLK_e)
        key(self.game, pico2d.SDLK_e, False)
        self.assertEqual(self.game.state, 'TITLE')
        self.assertIsNone(self.game.player)
        self.start()
        self.assertEqual(self.game.player.battery, 100)
        self.assertEqual(self.game.play_time, 0)


if __name__ == '__main__':
    unittest.main()
