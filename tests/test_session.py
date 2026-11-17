import unittest
from unittest.mock import Mock, patch

import pico2d

from session import GameSession
from stage import Stage


def key(game, value, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = value
    game.handle_event(event)


class SessionTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        # 기존의 짧은 구간으로 메뉴·복귀 규칙을 독립 검증한다.
        self.game = GameSession(stage_factory=Stage)

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
        self.assertEqual(self.game.enemies[0].health, 100)

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

    def test_start_menu_e_cannot_leak_into_fixture_interaction(self):
        key(self.game, pico2d.SDLK_e)
        self.game.player.x = 640
        key(self.game, pico2d.SDLK_e)
        self.game.update(0.01)
        self.assertFalse(self.game.stage.fixture_powered)

    def repair(self):
        self.game.player.x = 640
        key(self.game, pico2d.SDLK_e)
        key(self.game, pico2d.SDLK_e, False)
        self.game.update(0.01)

    def test_manual_restart_restores_progress_and_battery_together(self):
        self.start()
        self.game.player.battery = 0
        self.repair()
        self.assertTrue(self.game.records.latest.fixture_powered)
        elapsed = self.game.play_time
        self.pause()
        self.game.selection = self.game.PAUSE_ITEMS.index('스테이지 재시작')
        key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'PLAY')
        self.assertEqual(self.game.player.battery, 100)
        self.assertFalse(self.game.stage.fixture_powered)
        self.assertEqual(self.game.player.checkpoint_position, (160, 96))
        self.assertEqual(self.game.enemies[0].health, 100)
        self.assertEqual(self.game.enemies[0].state, 'PATROL')
        self.assertEqual(self.game.play_time, elapsed)
        self.assertEqual(self.game.records.latest, self.game.records.entry)

    def test_death_uses_latest_battery_after_checkpoint_not_old_value(self):
        self.start()
        self.repair()
        self.assertEqual(self.game.records.latest.battery, 100)
        key(self.game, pico2d.SDLK_r)
        self.game.update(0.01)
        self.assertEqual(self.game.records.latest.battery, 50)
        self.game.player.health = 1
        self.game.player.feet_y = -200
        self.game.update(0.01)
        self.assertEqual(self.game.player.health, 3)
        self.assertEqual(self.game.player.battery, 50)
        self.assertIsNone(self.game.player.light)
        self.assertTrue(self.game.stage.fixture_powered)
        self.assertFalse(self.game.enemies[0].alive)
        self.assertEqual((self.game.player.x, self.game.player.feet_y), (608, 96))
        self.assertEqual(self.game.records.entry.battery, 100)

    def test_pause_menu_e_cannot_activate_fixture_after_resume(self):
        self.start()
        self.game.player.x = 640
        self.pause()
        key(self.game, pico2d.SDLK_e)
        key(self.game, pico2d.SDLK_e)
        self.game.update(0.01)
        self.assertFalse(self.game.stage.fixture_powered)


if __name__ == '__main__':
    unittest.main()
