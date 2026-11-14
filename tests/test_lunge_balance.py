import unittest
from unittest.mock import Mock, patch

import pico2d

from enemy import Shade, LUNGE_WINDUP
from lighting import PortableLight
from physics import Solid
from session import GameSession
from stage import Stage


def flat_stage():
    stage = Stage()
    stage.start = (400, 96)
    stage.solids = [Solid(0, 0, 1920, 96)]
    stage.combat_bounds = (0, 1920)
    return stage


def key(game, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    game.handle_event(event)


def tap(game, code):
    key(game, code)
    key(game, code, False)


class LungeBalanceTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)

    def encounter(self, mode='run', fps=120, direction=1, shooter=False):
        game = GameSession(stage_factory=flat_stage)
        game.start_game()
        player = game.player
        player.x = 400 if direction > 0 else 688
        enemy = Shade(544, 96, combat_bounds=(0, 1920), can_shoot=shooter)
        game.enemies = [enemy]
        if mode == 'boost':
            player.item_effects.speed_remaining = 5
        forward = pico2d.SDLK_RIGHT if direction > 0 else pico2d.SDLK_LEFT
        backward = pico2d.SDLK_LEFT if direction > 0 else pico2d.SDLK_RIGHT
        key(game, forward)
        key(game, pico2d.SDLK_LSHIFT)
        acted = False
        for _ in range(round(fps * 1.5)):
            if not acted and enemy.state == 'LUNGE_WINDUP' and enemy.state_time >= .1:
                if mode == 'jump':
                    tap(game, pico2d.SDLK_SPACE)
                elif mode == 'retreat':
                    key(game, forward, False)
                    key(game, backward)
                elif mode == 'flash':
                    tap(game, pico2d.SDLK_q)
                elif mode == 'light':
                    tap(game, pico2d.SDLK_r)
                acted = True
            game.update(1 / fps)
        return game, enemy

    def test_plain_and_boosted_straight_run_are_hit_in_both_directions(self):
        for fps in (30, 60, 120):
            for direction in (-1, 1):
                for mode in ('run', 'boost'):
                    with self.subTest(fps=fps, direction=direction, mode=mode):
                        game, _ = self.encounter(mode, fps, direction)
                        self.assertEqual(game.player.health, 2)
                        self.assertEqual(game.player.respawn_count, 0)

    def test_timed_jump_and_retreat_remain_valid_without_resources(self):
        for fps in (30, 60, 120):
            for mode in ('jump', 'retreat'):
                with self.subTest(fps=fps, mode=mode):
                    game, enemy = self.encounter(mode, fps)
                    self.assertEqual(game.player.health, 3)
                    self.assertEqual(game.player.battery, 100)
                    self.assertEqual(game.player.invulnerability, 0)
                    self.assertEqual(enemy.health, 2)

    def test_q_and_r_offer_distinct_paid_counters(self):
        for mode, battery in (('flash', 80), ('light', 50)):
            with self.subTest(mode=mode):
                game, enemy = self.encounter(mode)
                self.assertEqual(game.player.health, 3)
                self.assertEqual(game.player.battery, battery)
                self.assertEqual(enemy.health, 1 if mode == 'flash' else 2)

    def test_lunge_has_warning_and_locks_direction(self):
        game = GameSession(stage_factory=flat_stage)
        game.start_game()
        enemy = Shade(544, 96, combat_bounds=(0, 1920))
        enemy.update(0, game.player, game.stage)
        self.assertEqual(enemy.state, 'LUNGE_WINDUP')
        enemy.update(LUNGE_WINDUP - .01, game.player, game.stage)
        self.assertIsNone(enemy.consume_attack())
        self.assertEqual(enemy.x, 544)
        game.player.x = 620
        enemy.update(.01, game.player, game.stage)
        self.assertEqual(enemy.state, 'LUNGE')
        self.assertEqual(enemy.face_dir, -1)

    def test_one_lunge_cannot_hit_twice_even_if_invulnerability_expires(self):
        game = GameSession(stage_factory=flat_stage)
        game.start_game()
        game.player.x = 450
        enemy = Shade(500, 96, combat_bounds=(0, 1920))
        game.enemies = [enemy]
        enemy.face_dir = -1
        enemy._enter('LUNGE')
        game.update(.01)
        self.assertEqual(game.player.health, 2)
        game.player.invulnerability = 0
        game.update(.01)
        self.assertEqual(game.player.health, 2)

    def test_light_cancels_active_lunge_and_does_not_deal_damage(self):
        game = GameSession(stage_factory=flat_stage)
        game.start_game()
        enemy = Shade(544, 96, combat_bounds=(0, 1920))
        enemy._enter('LUNGE')
        light = PortableLight(544, 120, game.stage.light_regions[0])
        enemy.update(.01, game.player, game.stage, light)
        self.assertNotIn(enemy.state, ('LUNGE', 'LUNGE_WINDUP'))
        self.assertIsNone(enemy.consume_attack())
        self.assertEqual(enemy.health, 2)

    def test_dash_stops_at_walls_and_platform_edges(self):
        for wall in (True, False):
            with self.subTest(wall=wall):
                stage = flat_stage()
                if wall:
                    stage.solids.append(Solid(600, 96, 608, 280))
                else:
                    stage.solids = [Solid(0, 0, 600, 96)]
                game = GameSession(stage_factory=lambda: stage)
                game.start_game()
                game.player.x = 680
                enemy = Shade(544, 96, combat_bounds=(0, 1920))
                enemy.face_dir = 1
                enemy._enter('LUNGE')
                for _ in range(25):
                    enemy.update(1 / 120, game.player, stage)
                    self.assertLessEqual(enemy.x + 24, 600)
                    self.assertEqual(enemy.feet_y, 96)


if __name__ == '__main__':
    unittest.main()
