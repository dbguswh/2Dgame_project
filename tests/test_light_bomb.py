import unittest
from unittest.mock import Mock, patch

import pico2d

from inventory import LIGHT_BOMB
from light_bomb import LightBomb
from physics import Solid
from projectiles import ShadowBolt
from session import GameSession
from world import update_world


def tap(player, code):
    for kind in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
        event = pico2d.Event(kind)
        event.key = code
        player.handle_event(event)


class BombGeometryTests(unittest.TestCase):
    def test_half_second_forward_arc_and_direction(self):
        for direction in (-1, 1):
            bomb = LightBomb(200, 140, direction)
            bomb.update(.25, [])
            self.assertFalse(bomb.exploded)
            self.assertAlmostEqual(bomb.x, 200 + 48 * direction)
            self.assertAlmostEqual(bomb.y, 156)
            bomb.update(.25, [])
            self.assertTrue(bomb.exploded)
            self.assertAlmostEqual(bomb.x, 200 + 96 * direction)
            self.assertAlmostEqual(bomb.y, 140)

    def test_large_delta_stops_at_fuse_instead_of_overtravelling(self):
        bomb = LightBomb(200, 140, 1)
        bomb.update(2, [])
        self.assertAlmostEqual(bomb.x, 296)
        self.assertTrue(bomb.exploded)

    def test_wall_contact_explodes_before_wall_without_tunnelling(self):
        bomb = LightBomb(100, 150, 1)
        wall = Solid(130, 100, 132, 220)
        bomb.update(.5, [wall])
        self.assertTrue(bomb.exploded)
        self.assertLess(bomb.x, 130)
        self.assertLess(bomb.age, .5)

    def test_circle_hits_every_overlapping_body_only_once(self):
        bomb = LightBomb(200, 140, 1)
        bomb.explode()
        bodies = [('left', (150, 100, 174, 190)), ('right', (225, 100, 249, 190)),
                  ('far', (250, 100, 274, 190)), ('diagonal', (240, 180, 260, 200))]
        self.assertEqual(bomb.consume_targets(bodies, []), ['left', 'right'])
        self.assertEqual(bomb.consume_targets(bodies, []), [])

    def test_wall_and_floor_block_blast(self):
        bomb = LightBomb(200, 140, 1)
        bomb.explode()
        wall, floor = Solid(212, 96, 216, 200), Solid(160, 112, 240, 120)
        targets = [('wall', (222, 100, 240, 180)), ('floor', (190, 70, 210, 110)),
                   ('same', (170, 125, 190, 180))]
        self.assertEqual(bomb.consume_targets(targets, [wall, floor]), ['same'])

    def test_thin_ledge_allows_upward_pass_and_catches_descent(self):
        bomb = LightBomb(200, 140, 1)
        ledge = Solid(0, 145, 500, 150, one_way=True)
        bomb.update(.25, [ledge])
        self.assertFalse(bomb.exploded)
        bomb.update(.25, [ledge])
        self.assertTrue(bomb.exploded)
        self.assertGreater(bomb.y, 150)


class BombWorldTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.p, self.stage = self.game.player, self.game.stage
        self.p.x, self.p.feet_y = 400, 96
        self.p.add_item(LIGHT_BOMB)
        self.p.add_item(LIGHT_BOMB)
        tap(self.p, pico2d.SDLK_3)

    def test_select_then_f_uses_bomb_instead_of_medkit_without_battery(self):
        self.p.medkits, self.p.health = 1, 2
        tap(self.p, pico2d.SDLK_f)
        self.p.update(0, self.stage.width, self.stage.solids)
        self.assertEqual(self.p.inventory.snapshot(), (1, 0, 1, 0))
        self.assertEqual((self.p.health, self.p.battery), (2, 100))
        self.assertEqual(len(self.p.bombs), 1)
        self.assertIsNone(self.p.get_attack_box())
        self.assertFalse(self.p.flash_pending)
        self.assertEqual(self.p.animation_state, 'flash')

    def test_f_keeps_item_selected_at_input_and_holding_does_not_repeat(self):
        event = pico2d.Event(pico2d.SDL_KEYDOWN)
        event.key = pico2d.SDLK_f
        self.p.handle_event(event)
        tap(self.p, pico2d.SDLK_1)
        for _ in range(90):
            self.p.handle_event(event)
            self.p.update(1 / 120, self.stage.width, self.stage.solids)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 1)
        self.assertEqual(len(self.p.bombs), 1)

    def test_empty_and_busy_actions_do_not_consume(self):
        self.p.attack_elapsed = .1
        self.assertFalse(self.p.use_selected_item(LIGHT_BOMB))
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)
        self.p.attack_elapsed = None
        self.p.light_cast = .1
        self.assertFalse(self.p.use_selected_item(LIGHT_BOMB))
        self.p.light_cast = 0
        self.p.inventory.counts[LIGHT_BOMB] = 0
        self.assertFalse(self.p.use_selected_item(LIGHT_BOMB))
        self.assertEqual(self.p.bombs, [])

    def test_q_or_r_has_priority_over_same_frame_bomb(self):
        for key in (pico2d.SDLK_q, pico2d.SDLK_r):
            self.p.reset_actions_after_return()
            self.p.battery = 100
            tap(self.p, pico2d.SDLK_f)
            tap(self.p, key)
            self.p.update(0, self.stage.width, self.stage.solids, self.stage.light_regions)
            self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 2)
            self.assertEqual(self.p.bombs, [])

    def test_airborne_throw_preserves_velocity_and_locks_direction(self):
        self.p.motion.jump()
        velocity = self.p.motion.velocity_y
        self.p.face_dir = -1
        self.assertTrue(self.p.use_selected_item(LIGHT_BOMB))
        self.p.update(0, self.stage.width, self.stage.solids)
        self.assertEqual(self.p.motion.velocity_y, velocity)
        self.p.face_dir = 1
        self.assertEqual(self.p.bombs[0].direction, -1)

    def test_same_frame_explosion_cancels_multiple_melee_and_ranged_attacks(self):
        enemies = self.game.enemies[:2]
        for enemy, x in zip(enemies, (468, 518)):
            enemy.motion.x, enemy.motion.feet_y = x, 96
            enemy.combat_bounds = (352, 752)
            def prepare(dt, player, stage, light, e=enemy):
                e.attack_event = player.get_bb()
                e.shot_event = ((e.x, 140), (player.x, 140))
            enemy.update = prepare
        self.p.bombs.append(LightBomb(496, 140, 1, age=.5))
        update_world(0, self.p, enemies, self.stage, self.game.records)
        self.assertEqual([e.health for e in enemies], [1, 1])
        self.assertEqual(self.p.health, 3)
        self.assertTrue(all(e.state == 'RECOVER' and e.shot_event is None and not e.bolts for e in enemies))
        update_world(0, self.p, [], self.stage, self.game.records)
        self.assertEqual([e.health for e in enemies], [1, 1])

    def test_already_fired_bolt_is_not_erased(self):
        enemy = self.game.enemies[0]
        bolt = ShadowBolt.aimed((700, 140), (400, 140))
        enemy.bolts.append(bolt)
        enemy.receive_bomb(1)
        self.assertIn(bolt, enemy.bolts)

    def test_consumption_persists_on_death_but_flying_bombs_are_cleared(self):
        enemy = self.game.enemies[0]
        self.p.health = 1
        enemy.bolts.append(ShadowBolt.aimed((400, 140), (401, 140)))
        tap(self.p, pico2d.SDLK_f)
        update_world(0, self.p, [enemy], self.stage, self.game.records)
        self.assertEqual(self.p.respawn_count, 1)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 1)
        self.assertEqual(self.p.bombs, [])
        self.game.restart_stage()
        self.assertEqual(self.p.inventory.snapshot(), (0, 0, 0, 0))

    def test_pause_and_focus_loss_freeze_fuse_and_clear_pending_input(self):
        self.p.use_selected_item(LIGHT_BOMB)
        bomb = self.p.bombs[0]
        self.game.state = 'PAUSED'
        self.game.update(1)
        self.game.state = 'PLAY'
        tap(self.p, pico2d.SDLK_f)
        self.game.update(1, focused=False)
        self.assertEqual(bomb.age, 0)
        self.game.enemies = []
        self.game.update(.1)
        self.assertAlmostEqual(bomb.age, .1)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB], 1)
