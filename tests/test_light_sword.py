import unittest
from unittest.mock import Mock, patch

from light_sword import sword_box
from physics import Solid
from player import Player


class SwordRangeTests(unittest.TestCase):
    def test_forward_reach_is_eighty_from_body_edge_and_mirrors(self):
        self.assertEqual(sword_box(400, 96, 1, False, []), (412, 108, 492, 176))
        self.assertEqual(sword_box(400, 96, -1, False, []), (308, 108, 388, 176))

    def test_wall_clips_range_in_both_directions(self):
        wall = Solid(450, 96, 458, 240)
        self.assertEqual(sword_box(400, 96, 1, False, [wall])[2], 450)
        self.assertEqual(sword_box(500, 96, -1, False, [wall])[0], 458)

    def test_air_reaches_down_but_cannot_cut_through_platform(self):
        self.assertEqual(sword_box(400, 200, 1, True, []), (412, 168, 492, 248))
        floor = Solid(390, 174, 490, 182)
        self.assertEqual(sword_box(400, 200, 1, True, [floor])[1], 182)

    def test_rising_cut_reaches_up_but_stops_below_ceiling(self):
        self.assertEqual(sword_box(400,96,1,False,[],True)[3],208)
        ceiling=Solid(380,190,510,210)
        self.assertEqual(sword_box(400,96,1,False,[ceiling],True)[3],190)


class SwordCombatTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Player(400, 96)
        self.p._begin_attack(1)
        self.p.attack_elapsed = .13

    def test_enemy_beyond_old_knife_range_can_be_hit_but_not_outside_sword(self):
        self.assertEqual(self.p.get_attack_target([('farther', (460, 96, 484, 184))]), 'farther')
        self.p.attack_hits.clear()
        self.assertIsNone(self.p.get_attack_target([('outside', (492, 96, 516, 184))]))

    def test_still_nearest_single_target_once_without_battery_cost(self):
        targets = [('far', (460, 96, 484, 184)), ('near', (425, 96, 449, 184))]
        self.assertEqual(self.p.get_attack_target(targets), 'near')
        self.assertIsNone(self.p.get_attack_target(targets))
        self.assertEqual(self.p.battery, 100)

    def test_no_sword_hit_during_preparation_recovery_or_flash(self):
        for elapsed in (.03, .08, .21, .3):
            self.p.attack_elapsed = elapsed
            self.assertIsNone(self.p.get_attack_box())
        self.p.attack_kind = 'flash'
        self.p.attack_elapsed = .13
        self.assertIsNone(self.p.get_attack_box())

    def test_uppercut_hits_higher_target_while_horizontal_cut_does_not(self):
        target=[('high',(445,190,469,215))]
        self.assertIsNone(self.p.get_attack_target(target))
        self.p._begin_attack(2)
        self.p.attack_elapsed=.17
        self.assertEqual(self.p.get_attack_target(target),'high')

    def test_lingering_trace_is_cosmetic_and_disappears_on_cancel(self):
        from sword_visuals import stroke_state
        self.p.attack_elapsed=.24
        self.assertIsNotNone(stroke_state(self.p))
        self.assertIsNone(self.p.get_attack_box())
        self.p.take_damage()
        self.assertIsNone(stroke_state(self.p))

    def test_trace_freezes_with_actor_hit_pause_and_uses_wall_clip(self):
        from sword_visuals import stroke_state
        self.p.solids=[Solid(450,96,460,240)]
        before=stroke_state(self.p)
        self.assertEqual(before[0][2],450)
        self.p.hit_pause.trigger(.06)
        self.p.update(.03,960,self.p.solids)
        self.assertEqual(stroke_state(self.p),before)

    def test_flash_and_bomb_have_no_sword_trace(self):
        from sword_visuals import stroke_state
        for kind in ('flash','bomb'):
            self.p.attack_kind=kind
            self.assertIsNone(stroke_state(self.p))
