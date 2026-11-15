import unittest
from unittest.mock import Mock,patch
import pico2d
from substation import SubstationStage
from player import Player
from progress import ProgressRecords
from world import update_world
from physics import Motion,RUN_SPEED
from session import GameSession
from tests.test_management import tap


class SubstationTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock())
        loader.start();self.addCleanup(loader.stop)
        self.s=SubstationStage()
        self.p=Player(*self.s.start)

    def at(self,pos):
        self.p.x,self.p.feet_y=pos
        self.p.motion.on_ground=True

    def interact(self,pos):
        self.at(pos)
        return self.s.interact(self.p)

    def test_initial_map_has_ten_guards_three_supplies_and_no_upper_jump_bypass(self):
        self.assertEqual(len(self.s.enemy_placements),10)
        self.assertEqual(len(self.s.supply_boxes),3)
        self.assertFalse(any(self.s.breakers))
        m=Motion(1800,96)
        m.jump()
        highest=96
        for _ in range(120):
            m.step(1/120,1,self.s.solids,self.s.width,speed=RUN_SPEED*1.3)
            highest=max(highest,m.feet_y)
        self.assertLess(highest,self.s.upper_gallery.top)
        self.assertFalse(self.s.core_gate.is_open)

    def test_lower_power_required_for_ride_and_upper_breaker(self):
        self.interact((1792,96))
        self.assertFalse(self.s.controls_locked)
        self.interact(self.s.breaker_positions[1])
        self.assertFalse(self.s.breakers[1])
        self.interact(self.s.breaker_positions[0])
        self.assertEqual(self.p.checkpoint_position,self.s.checkpoints[0])
        self.interact((1792,96))
        self.assertTrue(self.s.controls_locked)
        self.s.update(1.5)
        self.assertEqual(self.p.feet_y,352)
        self.interact(self.s.breaker_positions[1])
        self.assertTrue(self.s.both_breakers)
        self.assertEqual(self.p.checkpoint_position,self.s.checkpoints[1])
        self.assertFalse(self.s.core_gate.is_open)
        self.s.update(.55)
        self.assertTrue(self.s.core_gate.is_open)
        self.assertFalse(self.s.fixture_powered)
        self.assertFalse(self.s.completed)

    def test_empty_call_does_not_move_caller_or_retarget(self):
        self.s.breakers[0]=True
        self.interact(self.s.call_positions[1])
        self.s.update(.4)
        self.assertEqual((self.p.x,self.p.feet_y),self.s.call_positions[1])
        old=self.s.lift.target_y
        self.interact(self.s.call_positions[0])
        self.assertEqual(self.s.lift.target_y,old)
        self.s.update(1.1)
        self.assertEqual(self.s.lift.y,352)

    def test_ride_blocks_controls_but_escape_and_effect_timers_work(self):
        g=GameSession(SubstationStage);g.start_game()
        p,s=g.player,g.stage
        s.breakers[0]=True
        p.x,p.feet_y=1792,96
        p.item_effects.speed_remaining=5
        tap(g,pico2d.SDLK_e);g.update(1/120)
        self.assertTrue(s.controls_locked)
        battery=p.battery
        for code in (pico2d.SDLK_RIGHT,pico2d.SDLK_SPACE,pico2d.SDLK_w,pico2d.SDLK_q,pico2d.SDLK_r,pico2d.SDLK_f):
            tap(g,code)
        for _ in range(60):g.update(1/120)
        self.assertEqual(p.x,1792)
        self.assertEqual(p.feet_y,s.lift.y)
        self.assertEqual(p.battery,battery)
        self.assertFalse(p.is_attacking)
        self.assertLess(p.item_effects.speed_remaining,5)
        tap(g,pico2d.SDLK_ESCAPE)
        y=s.lift.y
        g.update(2)
        self.assertEqual(s.lift.y,y)
        tap(g,pico2d.SDLK_ESCAPE)
        for _ in range(120):g.update(1/120)
        self.assertEqual(p.feet_y,352)
        self.assertFalse(s.controls_locked)

    def test_zero_battery_death_at_upper_checkpoint_can_call_lift_and_charge(self):
        records=ProgressRecords(self.p,self.s)
        self.interact(self.s.breaker_positions[0])
        self.interact((1792,96));self.s.update(1.5)
        self.interact(self.s.breaker_positions[1])
        self.p.battery=0
        records.remember(self.p,self.s)
        records.restore_after_death(self.p,self.s)
        self.assertEqual(self.p.battery,0)
        self.assertTrue(self.s.both_breakers)
        self.assertEqual((self.p.x,self.p.feet_y),self.s.checkpoints[1])
        self.assertEqual(self.s.lift.y,96)
        self.s.interact(self.p);self.s.update(1.5)
        self.assertEqual(self.s.lift.y,352)
        self.interact((1792,352));self.s.update(1.5)
        self.assertEqual(self.p.feet_y,96)
        self.interact(self.s.charger_position)
        self.assertEqual(self.p.battery,self.p.max_battery)
        self.p.battery=20
        self.s.interact(self.p)
        self.assertEqual(self.p.battery,self.p.max_battery)
        records.restore_entry(self.p,self.s)
        self.assertFalse(any(self.s.breakers))
        self.assertEqual(self.s.lift.y,96)
        self.assertFalse(self.s.core_gate.is_open)

    def test_moving_empty_car_carries_a_player_who_lands_on_it(self):
        self.s.breakers[0]=True
        self.s.lift.call(352)
        self.s.update(.4)
        self.at((1792,self.s.lift.y))
        update_world(1/120,self.p,[],self.s)
        self.assertIs(self.s.lift.rider,self.p)
        self.assertEqual(self.p.feet_y,self.s.lift.y)
