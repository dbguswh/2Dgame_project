import unittest
from unittest.mock import Mock, patch

import pico2d

from inventory import SPEED, SHIELD
from item_effects import ItemEffects
from player import Player
from projectiles import ShadowBolt
from session import GameSession


def key(player, code, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = code
    player.handle_event(event)


def tap(player, code):
    key(player, code)
    key(player, code, False)


class EffectLifetimeTests(unittest.TestCase):
    def test_both_effects_are_independent_and_do_not_refresh(self):
        effects = ItemEffects()
        self.assertTrue(effects.activate(SPEED))
        effects.update(1)
        self.assertTrue(effects.activate(SHIELD))
        self.assertFalse(effects.activate(SPEED))
        self.assertFalse(effects.activate(SHIELD))
        self.assertEqual((effects.speed_remaining, effects.shield_remaining), (4, 6))

    def test_expiry_frame_weights_movement_by_active_fraction(self):
        effects = ItemEffects(speed_remaining=.025)
        self.assertAlmostEqual(effects.update(.1), 1.075)
        self.assertEqual(effects.speed_multiplier, 1)
        self.assertEqual(effects.update(.1), 1)

    def test_one_attack_breaks_shield_without_touching_speed(self):
        effects = ItemEffects(speed_remaining=3, shield_remaining=4)
        self.assertTrue(effects.absorb_attack())
        self.assertFalse(effects.absorb_attack())
        self.assertEqual(effects.speed_remaining, 3)
        self.assertEqual(effects.shield_remaining, 0)
        self.assertGreater(effects.shield_flash, 0)
        effects.update(.35)
        self.assertEqual(effects.shield_flash, 0)

    def test_natural_expiry_does_not_play_hit_break(self):
        effects = ItemEffects(shield_remaining=6)
        effects.update(6)
        self.assertFalse(effects.absorb_attack())
        self.assertEqual(effects.shield_flash, 0)

    def test_clear_discards_effects_and_visual_timers(self):
        effects = ItemEffects(2, 3, .1, .1, 20)
        effects.clear()
        self.assertEqual(effects, ItemEffects())


class TimedItemPlayerTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Player(400, 96)

    def use(self, slot):
        self.p.add_item(slot)
        tap(self.p, pico2d.SDLK_1 + slot)
        tap(self.p, pico2d.SDLK_f)
        self.p.update(0, 960)

    def test_selection_and_f_consume_one_without_health_or_battery_change(self):
        self.use(SPEED)
        self.use(SHIELD)
        self.assertEqual(self.p.inventory.snapshot(), (0, 0, 0, 0))
        self.assertEqual((self.p.item_effects.speed_remaining, self.p.item_effects.shield_remaining), (5, 6))
        self.assertEqual((self.p.health, self.p.battery), (3, 100))

    def test_reusing_active_effect_preserves_quantity_and_remaining_time(self):
        for slot in (SPEED, SHIELD):
            self.use(slot)
            self.p.update(.1, 960)
            self.p.add_item(slot)
            before = (self.p.item_effects.speed_remaining, self.p.item_effects.shield_remaining)
            self.assertFalse(self.p.use_selected_item(slot))
            self.assertEqual(self.p.inventory.counts[slot], 1)
            self.assertEqual((self.p.item_effects.speed_remaining, self.p.item_effects.shield_remaining), before)

    def test_empty_slot_does_not_create_effect(self):
        for slot in (SPEED, SHIELD):
            self.assertFalse(self.p.use_selected_item(slot))
        self.assertEqual(self.p.item_effects, ItemEffects())

    def test_walk_and_shift_are_both_thirty_percent_faster(self):
        self.use(SPEED)
        key(self.p, pico2d.SDLK_RIGHT)
        self.p.update(.1, 960)
        self.assertAlmostEqual(self.p.x - 400, 128 * 1.3 * .1)
        previous = self.p.x
        key(self.p, pico2d.SDLK_LSHIFT)
        self.p.update(.1, 960)
        self.assertAlmostEqual(self.p.x - previous, 208 * 1.3 * .1)

    def test_expiry_restores_current_shift_state_and_partial_frame_distance(self):
        self.p.item_effects.speed_remaining = .05
        key(self.p, pico2d.SDLK_RIGHT)
        key(self.p, pico2d.SDLK_LSHIFT)
        self.p.update(.1, 960)
        self.assertAlmostEqual(self.p.x - 400, 208 * .1 * 1.15)
        before = self.p.x
        self.p.update(.1, 960)
        self.assertAlmostEqual(self.p.x - before, 208 * .1)

    def test_jump_height_and_vertical_motion_do_not_change(self):
        normal = Player(400, 96)
        self.use(SPEED)
        for p in (self.p, normal):
            tap(p, pico2d.SDLK_SPACE)
            key(p, pico2d.SDLK_RIGHT)
        for _ in range(85):
            for p in (self.p, normal):
                p.update(1/120, 960)
            self.assertAlmostEqual(self.p.feet_y, normal.feet_y)
            self.assertAlmostEqual(self.p.motion.velocity_y, normal.motion.velocity_y)
        self.assertGreater(self.p.x, normal.x)

    def test_held_f_does_not_reuse_after_five_second_expiry(self):
        self.p.add_item(SPEED)
        self.p.add_item(SPEED)
        tap(self.p, pico2d.SDLK_2)
        key(self.p, pico2d.SDLK_f)
        for _ in range(720):
            key(self.p, pico2d.SDLK_f)
            self.p.update(1/120, 960)
        self.assertEqual(self.p.inventory.counts[SPEED], 1)
        self.assertEqual(self.p.item_effects.speed_remaining, 0)
        key(self.p, pico2d.SDLK_f, False)
        key(self.p, pico2d.SDLK_f)
        self.p.update(0, 960)
        self.assertEqual(self.p.inventory.counts[SPEED], 0)

    def test_activation_does_not_cancel_air_attack_or_existing_motion(self):
        self.p.motion.jump()
        tap(self.p, pico2d.SDLK_w)
        self.p.update(.02, 960)
        elapsed, velocity = self.p.attack_elapsed, self.p.motion.velocity_y
        self.use(SHIELD)
        self.use(SPEED)
        self.assertEqual(self.p.attack_elapsed, elapsed)
        self.assertEqual(self.p.motion.velocity_y, velocity)

    def test_block_keeps_health_motion_and_player_attack_and_grants_one_second_invulnerability(self):
        self.use(SHIELD)
        self.p.motion.jump()
        tap(self.p, pico2d.SDLK_w)
        self.p.update(.02, 960)
        elapsed, velocity = self.p.attack_elapsed, self.p.motion.velocity_y
        self.assertFalse(self.p.take_damage())
        self.assertEqual(self.p.health, 3)
        self.assertEqual(self.p.invulnerability, 1)
        self.assertEqual(self.p.item_effects.shield_remaining, 0)
        self.assertEqual(self.p.attack_elapsed, elapsed)
        self.assertEqual(self.p.motion.velocity_y, velocity)
        self.assertFalse(self.p.take_damage())
        self.p.update(1, 960)
        self.assertTrue(self.p.take_damage())
        self.assertEqual(self.p.health, 2)

    def test_invulnerable_attack_does_not_consume_active_shield(self):
        self.use(SHIELD)
        self.p.invulnerability = .5
        self.assertFalse(self.p.take_damage())
        self.assertEqual(self.p.item_effects.shield_remaining, 6)
        self.p.update(.5, 960)
        self.assertFalse(self.p.take_damage())
        self.assertEqual(self.p.item_effects.shield_remaining, 0)
        self.assertEqual(self.p.health, 3)

    def test_six_second_expiry_allows_normal_damage(self):
        self.use(SHIELD)
        self.p.update(6, 960)
        self.assertTrue(self.p.take_damage())
        self.assertEqual(self.p.health, 2)

    def test_nonfatal_fall_costs_health_without_consuming_or_clearing_shield(self):
        self.use(SPEED)
        self.use(SHIELD)
        self.p.feet_y = -200
        self.p.update(.01, 960)
        self.assertEqual(self.p.health, 2)
        self.assertEqual(self.p.respawn_count, 0)
        self.assertAlmostEqual(self.p.item_effects.speed_remaining, 4.99)
        self.assertAlmostEqual(self.p.item_effects.shield_remaining, 5.99)
        self.assertEqual(self.p.item_effects.shield_flash, 0)

    def test_effect_clock_keeps_running_during_actor_hit_pause(self):
        self.use(SPEED)
        self.use(SHIELD)
        self.p.hit_pause.trigger(.05)
        self.p.update(.03, 960)
        self.assertAlmostEqual(self.p.item_effects.speed_remaining, 4.97)
        self.assertAlmostEqual(self.p.item_effects.shield_remaining, 5.97)


class TimedItemWorldTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.p = self.game.player
        self.enemy = self.game.enemies[0]
        self.game.enemies = []
        self.p.x, self.p.feet_y = 400, 96
        for slot in (SPEED, SHIELD):
            self.p.add_item(slot)
            tap(self.p, pico2d.SDLK_1 + slot)
            tap(self.p, pico2d.SDLK_f)
            self.game.update(0)

    def test_pause_and_lost_focus_freeze_both_effects(self):
        self.game.state = 'PAUSED'
        self.game.update(2)
        self.game.state = 'PLAY'
        self.game.update(2, focused=False)
        self.assertEqual((self.p.item_effects.speed_remaining, self.p.item_effects.shield_remaining), (5, 6))
        self.game.update(.1)
        self.assertAlmostEqual(self.p.item_effects.speed_remaining, 4.9)

    def test_fatal_fall_clears_effects_but_does_not_refund_items(self):
        self.p.health, self.p.feet_y = 1, -200
        self.game.update(.01)
        self.assertEqual(self.p.respawn_count, 1)
        self.assertEqual(self.p.item_effects, ItemEffects())
        self.assertEqual(self.p.inventory.snapshot(), (0, 0, 0, 0))

    def test_restart_clears_effects_and_restores_entry_stock(self):
        self.game.restart_stage()
        self.assertEqual(self.p.item_effects, ItemEffects())
        self.assertEqual(self.p.inventory.snapshot(), (0, 0, 0, 0))

    def test_same_frame_melee_and_bolts_use_one_shield_without_health_loss(self):
        self.game.enemies = [self.enemy]
        def strike(dt, player, stage, light):
            self.enemy.attack_event = player.get_bb()
        self.enemy.update = strike
        self.enemy.bolts.extend(ShadowBolt.aimed((400, 140), (401, 140)) for _ in range(2))
        self.game.update(0)
        self.assertEqual(self.p.health, 3)
        self.assertEqual(self.p.item_effects.shield_remaining, 0)
        self.assertEqual(self.p.invulnerability, 1)
        self.assertEqual(self.p.item_effects.shield_flash, .35)

    def test_each_new_supply_has_one_item_and_survives_death_without_duplication(self):
        stage = self.game.stage
        for slot in (SPEED, SHIELD):
            with self.subTest(slot=slot):
                self.game.restart_stage()
                self.game.enemies = []
                box = next(b for b in stage.supply_boxes if b.item == slot)
                self.p.x, self.p.feet_y = box.x, box.feet_y
                tap(self.p, pico2d.SDLK_e)
                self.game.update(0)
                self.game.update(.3)
                self.assertTrue(box.claimed)
                self.assertEqual(self.p.inventory.counts[slot], 1)
                self.game.records.restore_after_death(self.p, stage)
                self.assertTrue(box.claimed)
                self.assertEqual(self.p.inventory.counts[slot], 1)
                self.p.x, self.p.feet_y = box.x, box.feet_y
                tap(self.p, pico2d.SDLK_e)
                self.game.update(.3)
                self.assertEqual(self.p.inventory.counts[slot], 1)

    def test_full_speed_and_shield_slots_leave_supplies_until_use(self):
        for slot in (SPEED, SHIELD):
            with self.subTest(slot=slot):
                self.game.restart_stage()
                self.game.enemies = []
                self.p.inventory.counts[slot] = 2
                box = next(b for b in self.game.stage.supply_boxes if b.item == slot)
                self.p.x, self.p.feet_y = box.x, box.feet_y
                tap(self.p, pico2d.SDLK_e)
                self.game.update(0)
                self.game.update(.3)
                self.assertFalse(box.claimed)
                tap(self.p, pico2d.SDLK_1 + slot)
                tap(self.p, pico2d.SDLK_f)
                self.game.update(0)
                self.assertTrue(box.claimed)
                self.assertEqual(self.p.inventory.counts[slot], 2)

    def test_fully_boosted_run_jump_cannot_cross_unpowered_canal(self):
        from physics import Motion, RUN_SPEED
        motion = Motion(self.game.stage.canal[0]-14, self.game.stage.BRIDGE_Y)
        motion.jump()
        for _ in range(180):
            motion.step(1/120, 1, self.game.stage.solids, self.game.stage.width, speed=RUN_SPEED*1.3)
            if motion.feet_y < self.game.stage.BRIDGE_Y-2:
                break
        self.assertLess(motion.x + motion.width/2, self.game.stage.canal[1])
