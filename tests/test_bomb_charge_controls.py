import unittest
from unittest.mock import Mock, patch

import pico2d

from inventory import LIGHT_BOMB, SHIELD
from physics import Solid
from session import GameSession


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


def tap(player, code):
    key(player, code)
    key(player, code, False)


class ChargedThrowTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.game = GameSession()
        self.game.start_game()
        self.p = self.game.player
        self.p.x, self.p.feet_y = 400, 96
        self.p.inventory.counts[LIGHT_BOMB] = 2
        self.p.inventory.select(LIGHT_BOMB)

    def update(self, dt=0):
        self.p.update(dt, 2000, [Solid(0, 0, 2000, 96)])

    def charge(self, dt=.5):
        key(self.p, pico2d.SDLK_f)
        self.update(dt)

    def test_hold_charges_without_spending_or_auto_throwing_at_maximum(self):
        self.charge(.5)
        self.assertEqual(self.p.bomb_aim.charge, .5)
        for _ in range(5):
            key(self.p, pico2d.SDLK_f)
            self.update(.5)
        self.assertEqual(self.p.bomb_aim.charge, 1)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)
        self.assertFalse(self.p.bombs or self.p.is_attacking)
        self.assertEqual(self.p.animation_state, 'bomb_aim')
        key(self.p, pico2d.SDLK_f, False)
        self.update()
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 1)
        self.assertEqual(self.p.bombs[0].charge, 1)
        self.update(1)
        self.assertEqual(len(self.p.bombs), 1)

    def test_quick_tap_throws_one_minimum_charge_even_in_large_update(self):
        tap(self.p, pico2d.SDLK_f)
        self.update(.1)
        self.assertEqual(len(self.p.bombs), 1)
        self.assertEqual(self.p.bombs[0].charge, 0)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 1)

    def test_ground_aim_locks_movement_but_allows_direction_and_angle(self):
        key(self.p, pico2d.SDLK_RIGHT)
        key(self.p, pico2d.SDLK_LSHIFT)
        self.charge(.1)
        self.assertEqual(self.p.x, 400)
        key(self.p, pico2d.SDLK_RIGHT, False)
        key(self.p, pico2d.SDLK_LEFT)
        key(self.p, pico2d.SDLK_UP)
        self.update(.5)
        self.assertEqual((self.p.bomb_aim.direction, self.p.bomb_aim.angle), (-1, 75))
        key(self.p, pico2d.SDLK_f, False)
        self.update()
        self.assertEqual((self.p.bombs[0].direction, self.p.bombs[0].angle), (-1, 75))
        self.assertEqual(self.p.x, 400)

    def test_air_aim_keeps_initial_horizontal_motion_and_gravity(self):
        key(self.p, pico2d.SDLK_RIGHT)
        self.p.motion.jump()
        velocity = self.p.motion.velocity_y
        self.charge(.05)
        previous_x = self.p.x
        key(self.p, pico2d.SDLK_RIGHT, False)
        key(self.p, pico2d.SDLK_LEFT)
        self.update(.05)
        self.assertGreater(self.p.x, previous_x)
        self.assertLess(self.p.motion.velocity_y, velocity)
        self.assertEqual(self.p.bomb_aim.direction, -1)

    def test_other_actions_cancel_without_consuming_and_release_does_not_throw(self):
        for code in (pico2d.SDLK_w, pico2d.SDLK_q, pico2d.SDLK_r,
                     pico2d.SDLK_SPACE, pico2d.SDLK_e, pico2d.SDLK_1):
            with self.subTest(code=code):
                self.p.reset_actions_after_return(invulnerability=0)
                self.p.battery = 100
                self.p.inventory.select(LIGHT_BOMB)
                self.charge()
                tap(self.p, code)
                self.update()
                self.assertIsNone(self.p.bomb_aim)
                key(self.p, pico2d.SDLK_f, False)
                self.update()
                self.assertFalse(self.p.bombs)
                self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)

    def test_hit_cancels_charge_and_held_key_does_not_restart_it(self):
        self.charge()
        self.assertTrue(self.p.take_damage())
        key(self.p, pico2d.SDLK_f)
        self.update()
        self.assertIsNone(self.p.bomb_aim)
        key(self.p, pico2d.SDLK_f, False)
        self.update()
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)
        self.charge()
        self.assertIsNotNone(self.p.bomb_aim)

    def test_shield_block_keeps_aim_and_does_not_spend_bomb(self):
        self.charge()
        self.p.item_effects.activate(SHIELD)
        self.assertFalse(self.p.take_damage())
        self.assertIsNotNone(self.p.bomb_aim)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)

    def test_pause_focus_loss_and_return_cancel_aim_without_spending(self):
        self.charge()
        event = pico2d.Event(pico2d.SDL_KEYDOWN)
        event.key = pico2d.SDLK_ESCAPE
        self.game.handle_event(event)
        self.assertIsNone(self.p.bomb_aim)
        self.assertEqual(self.game.state, 'PAUSED')
        self.game.state = 'PLAY'
        self.charge()
        self.game.update(.5, focused=False)
        self.assertIsNone(self.p.bomb_aim)
        self.charge()
        self.p.reset_actions_after_return()
        self.assertIsNone(self.p.bomb_aim)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)

    def test_busy_press_is_rejected_instead_of_queued(self):
        self.p.attack_elapsed = .1
        self.charge(0)
        self.assertIsNone(self.p.bomb_aim)
        self.update(1)
        self.assertIsNone(self.p.bomb_aim)
        key(self.p, pico2d.SDLK_f, False)
        self.update()
        self.assertFalse(self.p.bombs)
        self.p.inventory.counts[LIGHT_BOMB] = 0
        self.charge()
        self.assertIsNone(self.p.bomb_aim)

    def test_releasing_does_not_spend_battery_or_create_melee_hit(self):
        self.p.battery = 0
        self.charge()
        key(self.p, pico2d.SDLK_f, False)
        self.update()
        self.assertEqual(self.p.battery, 0)
        self.assertIsNone(self.p.get_attack_box())
        self.assertFalse(self.p.flash_pending)

    def test_next_aim_resets_angle_to_45_degrees(self):
        self.charge()
        key(self.p, pico2d.SDLK_UP)
        self.update(1)
        self.p.clear_input()
        self.charge(0)
        self.assertEqual(self.p.bomb_aim.angle, 45)
