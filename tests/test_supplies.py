import unittest
from unittest.mock import Mock, patch

import pico2d

from projectiles import ShadowBolt
from session import GameSession


def key(game, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    game.handle_event(event)


def tap(game, code):
    key(game, code)
    key(game, code, False)


class SupplyTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.enemy = self.game.enemies[0]
        self.game.enemies = []
        self.p, self.stage = self.game.player, self.game.stage
        self.box = self.stage.supply_boxes[0]
        self.p.x, self.p.feet_y = self.box.x, self.box.feet_y

    def open(self):
        tap(self.game, pico2d.SDLK_e)
        self.game.update(0)

    def test_e_opens_once_then_delivers_one_medkit_after_animation(self):
        self.open()
        self.assertTrue(self.box.opened)
        self.assertFalse(self.box.claimed)
        self.game.update(0.29)
        self.assertEqual(self.p.medkits, 0)
        self.game.update(0.01)
        self.assertEqual(self.p.medkits, 1)
        self.assertTrue(self.box.claimed)
        key(self.game, pico2d.SDLK_e)
        for _ in range(20):
            key(self.game, pico2d.SDLK_e)
            self.game.update(0.1)
        self.assertEqual(self.p.medkits, 1)

    def test_full_stock_leaves_item_and_using_one_allows_later_pickup(self):
        self.p.medkits = 2
        self.open()
        self.game.update(0.3)
        self.assertTrue(self.box.pickup_ready)
        self.assertFalse(self.box.claimed)
        self.p.health = 2
        tap(self.game, pico2d.SDLK_f)
        self.game.update(0)
        self.assertEqual(self.p.health, 3)
        self.assertEqual(self.p.medkits, 2)
        self.assertTrue(self.box.claimed)

    def test_opened_unclaimed_item_survives_death(self):
        self.p.medkits = 2
        self.open()
        self.game.update(0.3)
        self.p.health, self.p.feet_y = 1, -200
        self.game.update(0.01)
        self.assertTrue(self.box.opened)
        self.assertTrue(self.box.pickup_ready)
        self.assertFalse(self.box.claimed)
        self.assertEqual(self.p.medkits, 2)

    def test_death_during_opening_preserves_partial_open_and_delivers_only_once(self):
        self.open()
        self.game.update(0.1)
        self.p.health, self.p.feet_y = 1, -200
        self.game.update(0.01)
        self.assertTrue(self.box.opened)
        self.assertFalse(self.box.claimed)
        self.assertAlmostEqual(self.box.opening_elapsed, 0.11)
        self.game.update(0.2)
        self.assertTrue(self.box.pickup_ready)
        self.p.x, self.p.feet_y = self.box.x, self.box.feet_y
        self.game.update(0)
        self.assertEqual(self.p.medkits, 1)
        self.game.update(1)
        self.assertEqual(self.p.medkits, 1)

    def test_pickup_and_opening_are_recorded_before_same_update_death(self):
        self.open()
        self.p.health = 1
        self.game.enemies = [self.enemy]
        self.enemy.bolts.append(ShadowBolt.aimed((self.p.x, self.p.feet_y + 40), (100, 136)))
        self.game.update(0.3)
        self.assertEqual(self.p.respawn_count, 1)
        self.assertEqual(self.p.medkits, 1)
        self.assertTrue(self.box.opened and self.box.claimed)
        self.assertEqual(self.game.records.latest.medkits, 1)

    def test_used_medkit_does_not_return_after_death_and_restart_resets_all(self):
        self.open()
        self.game.update(0.3)
        self.p.health = 2
        tap(self.game, pico2d.SDLK_f)
        self.game.update(0)
        self.assertEqual(self.p.medkits, 0)
        self.p.health, self.p.feet_y = 1, -200
        self.game.update(0.01)
        self.assertEqual(self.p.medkits, 0)
        self.assertTrue(self.box.claimed)
        self.game.restart_stage()
        self.assertFalse(self.box.opened or self.box.claimed)
        self.assertEqual(self.p.medkits, 0)

    def test_return_battery_is_separate_single_use_and_preserved_on_death(self):
        self.p.x, y = self.stage.return_battery_position
        self.p.feet_y = y - 16
        self.game.update(0)
        self.assertFalse(self.stage.return_battery_collected)
        self.p.battery = 90
        self.game.update(0)
        self.assertEqual(self.p.battery, 100)
        self.assertTrue(self.stage.return_battery_collected)
        self.assertFalse(self.stage.battery_pack_collected)
        self.p.battery = 20
        self.game.update(0)
        self.p.health, self.p.feet_y = 1, -200
        self.game.update(0.01)
        self.assertEqual(self.p.battery, 20)
        self.assertTrue(self.stage.return_battery_collected)
        self.game.restart_stage()
        self.assertFalse(self.stage.return_battery_collected)

    def test_pause_and_focus_loss_stop_opening_and_f_does_not_use_item(self):
        self.open()
        self.game.update(0.1)
        self.p.medkits, self.p.health = 1, 2
        self.game.state = 'PAUSED'
        tap(self.game, pico2d.SDLK_f)
        self.game.update(1)
        self.game.state = 'PLAY'
        self.game.update(1, focused=False)
        self.assertEqual(self.box.opening_elapsed, 0.1)
        self.assertEqual((self.p.health, self.p.medkits), (2, 1))

    def test_airborne_or_attacking_player_cannot_open_box(self):
        self.p.motion.on_ground = False
        self.open()
        self.assertFalse(self.box.opened)
        self.p.motion.on_ground = True
        self.p.attack_elapsed = 0.1
        self.open()
        self.assertFalse(self.box.opened)
