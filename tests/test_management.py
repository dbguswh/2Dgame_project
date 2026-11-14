import unittest
from unittest.mock import Mock, patch

import pico2d

from session import GameSession
from upgrades import CAPACITY, FOCUS


def key(game, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    game.handle_event(event)


def tap(game, code):
    key(game, code)
    key(game, code, False)


class ManagementTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.p, self.s = self.game.player, self.game.stage

    def finish(self):
        self.s.fixture_powered = True
        self.s.fuse_state = 'INSTALLED'
        self.s.update(self.s.BRIDGE_TIME)
        self.p.x, self.p.feet_y = self.s.exit_position
        tap(self.game, pico2d.SDLK_e)
        self.game.update(0)
        self.assertEqual(self.game.state, 'STAGE_CLEAR')
        self.assertEqual(self.p.fragments, 2)

    def enter(self):
        self.finish()
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'CITY_MAP')
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'MANAGEMENT')

    def test_map_is_unavailable_before_stage_clear(self):
        self.assertFalse(self.game.open_city_map())
        self.assertFalse(self.game.open_management())
        self.assertEqual(self.game.state, 'PLAY')

    def test_held_exit_and_menu_e_does_not_buy_without_new_press(self):
        self.finish()
        key(self.game, pico2d.SDLK_e)
        for _ in range(3): key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'CITY_MAP')
        key(self.game, pico2d.SDLK_e, False)
        key(self.game, pico2d.SDLK_e)
        for _ in range(3): key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'MANAGEMENT')
        self.assertEqual((self.p.fragments, self.p.core_upgrades), (2, set()))

    def test_purchase_records_choice_cost_and_capacity(self):
        self.enter()
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual((self.p.fragments, self.p.max_battery), (0, 140))
        self.assertEqual(self.game.records.latest.core_upgrades, (CAPACITY,))
        self.assertEqual(self.game.records.latest.fragments, 0)
        self.assertEqual(self.game.records.entry.core_upgrades, ())

    def test_reopening_preserves_upgrade_limit_and_allows_supply_purchase(self):
        self.enter()
        self.p.fragments = 6
        tap(self.game, pico2d.SDLK_RIGHT)
        tap(self.game, pico2d.SDLK_e)
        visit = self.game.management_visit
        self.assertEqual(self.p.core_upgrades, {FOCUS})
        tap(self.game, pico2d.SDLK_ESCAPE)
        tap(self.game, pico2d.SDLK_ESCAPE)
        tap(self.game, pico2d.SDLK_e)
        tap(self.game, pico2d.SDLK_e)
        self.assertIs(self.game.management_visit, visit)
        tap(self.game, pico2d.SDLK_RIGHT)
        tap(self.game, pico2d.SDLK_RIGHT)  # 병원 출발 항목 다음 치료제로 순환
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual((self.p.fragments, self.p.core_upgrades), (3, {FOCUS}))
        self.assertEqual(self.p.medkits, 1)

    def test_supply_purchase_updates_latest_counts_and_preserves_entry(self):
        self.enter()
        self.p.fragments = 3
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.selection, 2)
        tap(self.game, pico2d.SDLK_RIGHT)
        tap(self.game, pico2d.SDLK_RIGHT)
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual((self.p.fragments, self.p.medkits), (0, 1))
        self.assertEqual(self.game.records.latest.inventory_counts, (1, 0, 0, 0))
        self.assertEqual(self.game.records.latest.fragments, 0)
        self.assertEqual(self.game.records.entry.inventory_counts, (0, 0, 0, 0))
        self.game.restart_stage()
        self.assertEqual((self.p.fragments, self.p.medkits), (0, 0))

    def test_repeated_e_neither_exits_after_upgrade_nor_buys_extra_supply(self):
        self.enter()
        self.p.fragments = 6
        key(self.game, pico2d.SDLK_e)
        for _ in range(3):
            key(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'MANAGEMENT')
        self.assertEqual((self.game.selection, self.p.fragments, self.p.medkits), (2, 4, 0))
        key(self.game, pico2d.SDLK_e, False)
        tap(self.game, pico2d.SDLK_RIGHT)
        tap(self.game, pico2d.SDLK_RIGHT)
        key(self.game, pico2d.SDLK_e)
        for _ in range(3):
            key(self.game, pico2d.SDLK_e)
        self.assertEqual((self.p.fragments, self.p.medkits), (3, 1))

    def test_map_and_management_freeze_world_timers_and_do_not_heal_or_charge(self):
        self.enter()
        self.p.item_effects.speed_remaining = 4
        self.p.item_effects.shield_remaining = 5
        self.p.health, self.p.battery = 1, 20
        before = (self.game.play_time, self.s.visual_time, self.p.x, self.p.feet_y)
        for state in ('CITY_MAP', 'MANAGEMENT'):
            self.game.state = state
            for code in (pico2d.SDLK_f, pico2d.SDLK_r, pico2d.SDLK_SPACE): tap(self.game, code)
            self.game.update(3)
            self.game.update(3, focused=False)
            self.assertEqual((self.game.play_time, self.s.visual_time, self.p.x, self.p.feet_y), before)
            self.assertEqual((self.p.item_effects.speed_remaining, self.p.item_effects.shield_remaining), (4, 5))
            self.assertEqual((self.p.health, self.p.battery), (1, 20))

    def test_arrow_repeat_is_not_a_second_choice_and_wraps(self):
        self.enter()
        key(self.game, pico2d.SDLK_LEFT)
        key(self.game, pico2d.SDLK_LEFT)
        self.assertEqual(self.game.selection, 2)
        key(self.game, pico2d.SDLK_LEFT, False)
        tap(self.game, pico2d.SDLK_RIGHT)
        self.assertEqual(self.game.selection, 0)

    def test_insufficient_fragments_gives_reason_without_marking_completed(self):
        self.enter()
        self.p.fragments = 1
        tap(self.game, pico2d.SDLK_e)
        self.assertFalse(self.game.management_visit.completed)
        self.assertEqual(self.p.fragments, 1)
        self.assertIn('부족', self.game.management_visit.notice)

    def test_restart_resets_visit_and_upgrade_with_entire_stage_entry(self):
        self.enter()
        tap(self.game, pico2d.SDLK_e)
        self.game.restart_stage()
        self.assertIsNone(self.game.management_visit)
        self.assertEqual(self.p.core_upgrades, set())
        self.assertEqual((self.p.fragments, self.p.max_battery), (0, 100))
        self.assertFalse(self.s.completed or self.s.reward_claimed)

    def test_title_then_new_run_clears_management_and_upgrade(self):
        self.enter()
        tap(self.game, pico2d.SDLK_e)
        self.game.return_to_title()
        self.assertIsNone(self.game.management_visit)
        self.game.clear_input()
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual(self.p.core_upgrades, {CAPACITY})
        self.assertEqual(self.game.player.core_upgrades, set())
