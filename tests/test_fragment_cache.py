import unittest
from unittest.mock import Mock, patch

import pico2d

from physics import Motion
from session import GameSession


def tap(game, code):
    for kind in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
        event = pico2d.Event(kind)
        event.key = code
        game.handle_event(event)


class FragmentCacheTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.game = GameSession()
        self.game.start_game()
        self.game.enemies = []
        self.p, self.s = self.game.player, self.game.stage
        self.cache = self.s.fragment_cache

    def stand_by_cache(self):
        self.p.x, self.p.feet_y = self.cache.x, self.cache.feet_y

    def open_cache(self):
        self.stand_by_cache()
        tap(self.game, pico2d.SDLK_e)
        self.game.update(0)

    def complete_stage(self):
        self.s.fixture_powered = True
        self.s.fuse_state = 'INSTALLED'
        self.s.update(self.s.BRIDGE_TIME)
        self.p.x, self.p.feet_y = self.s.exit_position
        tap(self.game, pico2d.SDLK_e)
        self.game.update(0)

    def test_cache_grants_one_immediately_without_using_inventory_or_healing(self):
        self.p.health = 1
        self.p.medkits = 2
        self.open_cache()
        self.assertTrue(self.cache.opened)
        self.assertEqual(self.cache.opening_elapsed, 0)
        self.assertEqual((self.p.fragments, self.p.health, self.p.battery, self.p.medkits), (1, 1, 100, 2))
        self.assertEqual(self.game.records.latest.fragment_cache_state[1], True)
        self.assertEqual(self.game.records.latest.fragments, 1)
        for _ in range(3):
            tap(self.game, pico2d.SDLK_e)
            self.game.update(.1)
        self.assertEqual(self.p.fragments, 1)

    def test_air_other_floor_or_combat_cannot_reach_cache(self):
        self.stand_by_cache()
        for scenario in ('air', 'upper', 'attack'):
            self.p.motion.on_ground = scenario != 'air'
            self.p.feet_y = 288 if scenario == 'upper' else 96
            self.p.attack_elapsed = .1 if scenario == 'attack' else None
            self.assertIsNot(self.s.nearby_supply(self.p), self.cache)
        self.assertFalse(self.cache.opened)
        self.assertEqual(self.p.fragments, 0)

    def test_spent_fragment_and_opening_progress_do_not_return_after_death(self):
        self.open_cache()
        self.game.update(.1)
        self.p.fragments = 0
        self.game.records.remember(self.p, self.s)
        self.p.health, self.p.feet_y = 1, -200
        self.game.update(.01)
        self.assertTrue(self.cache.opened)
        self.assertAlmostEqual(self.cache.opening_elapsed, .11)
        self.open_cache()
        self.assertEqual(self.p.fragments, 0)
        self.game.restart_stage()
        self.assertFalse(self.cache.opened)
        self.assertEqual(self.cache.opening_elapsed, 0)

    def test_held_e_cannot_duplicate_reward_and_pause_freezes_door(self):
        self.stand_by_cache()
        event = pico2d.Event(pico2d.SDL_KEYDOWN)
        event.key = pico2d.SDLK_e
        for _ in range(5):
            self.game.handle_event(event)
            self.game.update(.01)
        self.assertEqual(self.p.fragments, 1)
        before = self.cache.opening_elapsed
        self.game.state = 'PAUSED'
        self.game.update(2)
        self.assertEqual(self.cache.opening_elapsed, before)

    def test_opening_and_fatal_hit_in_same_update_preserve_one_reward(self):
        from enemy import Shade
        from projectiles import ShadowBolt
        self.stand_by_cache()
        self.p.health = 1
        enemy = Shade(560, 96, combat_bounds=(448, 752))
        enemy.bolts.append(ShadowBolt.aimed((self.p.x, 140), (self.p.x + 1, 140)))
        self.game.enemies = [enemy]
        tap(self.game, pico2d.SDLK_e)
        self.game.update(0)
        self.assertEqual(self.p.respawn_count, 1)
        self.assertTrue(self.cache.opened)
        self.assertEqual(self.p.fragments, 1)
        self.assertTrue(self.game.records.latest.fragment_cache_state[1])
        self.game.enemies = []
        self.open_cache()
        self.assertEqual(self.p.fragments, 1)

    def test_optional_cache_funds_one_purchase_after_upgrade_without_extra_currency(self):
        self.open_cache()
        self.complete_stage()
        self.assertEqual(self.p.fragments, 3)
        tap(self.game, pico2d.SDLK_e)
        tap(self.game, pico2d.SDLK_e)
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual(self.p.fragments, 1)
        tap(self.game, pico2d.SDLK_LEFT)
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual((self.p.fragments, self.p.inventory.counts[2]), (0, 1))
        self.assertEqual(self.game.records.latest.inventory_counts[2], 1)

    def test_skipping_cache_still_funds_upgrade_and_does_not_require_shopping(self):
        self.complete_stage()
        self.assertEqual(self.p.fragments, 2)
        for _ in range(3):
            tap(self.game, pico2d.SDLK_e)
        self.assertTrue(self.game.management_visit.completed)
        self.assertEqual(self.p.fragments, 0)
        self.assertFalse(self.cache.opened)
        tap(self.game, pico2d.SDLK_e)
        self.assertEqual(self.game.state, 'CITY_MAP')

    def test_lower_detour_can_return_to_ascent_with_basic_movement(self):
        body = Motion(800, 96)
        for direction, target in ((1, self.cache.x), (-1, 800)):
            for _ in range(600):
                if abs(body.x - target) < 1.1:
                    break
                body.step(1 / 120, direction, self.s.solids, self.s.width)
                self.assertEqual(body.feet_y, 96)
            self.assertLess(abs(body.x - target), 1.1)
        self.assertTrue(body.jump())
        for _ in range(120):
            body.step(1 / 120, 0, self.s.solids, self.s.width)
            if body.on_ground:
                break
        self.assertEqual(body.feet_y, self.s.approach_ledges[0].top)


if __name__ == '__main__':
    unittest.main()
