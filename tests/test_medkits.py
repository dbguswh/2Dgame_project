import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


class MedkitTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = Player(400, 96)

    def test_stock_limit_is_two(self):
        self.assertTrue(self.player.add_medkit())
        self.assertTrue(self.player.add_medkit())
        self.assertFalse(self.player.add_medkit())
        self.assertEqual(self.player.medkits, 2)

    def test_f_heals_one_without_battery_or_invulnerability(self):
        self.player.medkits, self.player.health = 2, 1
        key(self.player, pico2d.SDLK_f)
        self.player.update(0, 960)
        self.assertEqual((self.player.health, self.player.medkits), (2, 1))
        self.assertEqual(self.player.battery, 100)
        self.assertEqual(self.player.invulnerability, 0)
        self.assertGreater(self.player.heal_effect, 0)

    def test_holding_f_and_os_key_repeat_do_not_consume_again(self):
        self.player.medkits, self.player.health = 2, 1
        key(self.player, pico2d.SDLK_f)
        for _ in range(120):
            key(self.player, pico2d.SDLK_f)
            self.player.update(1 / 120, 960)
        self.assertEqual((self.player.health, self.player.medkits), (2, 1))
        key(self.player, pico2d.SDLK_f, False)
        key(self.player, pico2d.SDLK_f)
        self.player.update(0, 960)
        self.assertEqual((self.player.health, self.player.medkits), (3, 0))

    def test_full_health_or_empty_stock_does_not_consume(self):
        self.player.medkits = 1
        self.assertFalse(self.player.use_medkit())
        self.assertEqual(self.player.medkits, 1)
        self.player.medkits, self.player.health = 0, 1
        self.assertFalse(self.player.use_medkit())
        self.assertEqual(self.player.health, 1)

    def test_healing_preserves_air_motion_and_existing_attack(self):
        self.player.medkits, self.player.health = 1, 2
        self.player.motion.jump()
        key(self.player, pico2d.SDLK_w)
        self.player.update(0.01, 960)
        elapsed, velocity = self.player.attack_elapsed, self.player.motion.velocity_y
        key(self.player, pico2d.SDLK_f)
        self.player.update(0, 960)
        self.assertEqual(self.player.health, 3)
        self.assertEqual(self.player.attack_elapsed, elapsed)
        self.assertEqual(self.player.motion.velocity_y, velocity)

    def test_clear_input_discards_pending_use_without_deleting_stock(self):
        self.player.medkits, self.player.health = 1, 2
        key(self.player, pico2d.SDLK_f)
        self.player.reset_actions_after_return()
        self.player.update(0, 960)
        self.assertEqual((self.player.health, self.player.medkits), (2, 1))
