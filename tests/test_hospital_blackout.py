import unittest
from unittest.mock import Mock,patch
import pico2d
from hospital import HospitalStage
from session import GameSession
from player import Player
from enemy import Shade
from progress import ProgressRecords
from world import update_world,restore_enemies
from lighting import PortableLight
from inventory import MEDKIT,LIGHT_BOMB
from physics import Motion
from projectiles import ShadowBolt
from tests.test_management import tap


class HospitalBlackoutTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock())
        loader.start();self.addCleanup(loader.stop)
        self.s=HospitalStage()
        self.p=Player(*self.s.start)

    def at(self,pos):
        self.p.x,self.p.feet_y=pos
        self.p.motion.on_ground=True

    def take(self,key):
        x,y=self.s.part_positions[key]
        self.at((x,y-16))
        self.s.room_cleared[key]=True;self.s.circuit=key
        self.s.interact(self.p)

    def actors(self):
        enemies=[Shade(e.x,e.feet_y,identity=e.identity,combat_bounds=e.bounds,can_shoot=e.ranged)
                 for e in self.s.enemy_placements]
        restore_enemies(enemies,self.s)
        return enemies

    def test_take_part_cuts_corridor_and_requires_inside_latch_in_both_orders(self):
        for first,second in (('A','B'),('B','A')):
            self.s=HospitalStage()
            self.p=Player(*self.s.start)
            if first=='B':
                self.at(self.s.terminal_position);self.s.interact(self.p);self.s.update(.55)
            self.at(self.s.latch_positions[first]);self.s.interact(self.p)
            self.assertFalse(self.s.return_open[first])
            self.take(first)
            self.assertIsNone(self.s.powered_circuit)
            self.assertEqual(self.s.returning_key,first)
            self.assertEqual(self.p.checkpoint_position,self.s.return_checkpoints[first])
            self.assertTrue(all(p.state=='WARNING' and p.warning_duration==4 for p in self.s.corridor_points(first)))
            self.s.update(.55)
            self.assertFalse(self.s.doors[first].is_open)
            self.at(self.s.latch_positions[first]);self.s.interact(self.p);self.s.update(.55)
            self.assertTrue(self.s.doors[first].is_open)
            self.assertFalse(self.s.is_temporarily_lit((1100,96,1140,180) if first=='A' else (2300,96,2340,180)))
            self.at(self.s.start);self.s.collect_pickups(self.p)
            self.assertTrue(self.s.returned[first])
            self.assertEqual(self.p.checkpoint_position,self.s.start)
            self.at(self.s.terminal_position);self.s.interact(self.p)
            self.assertEqual(self.s.powered_circuit,second)
            # 분리한 부품은 회로를 다시 선택해도 복도의 전력을 살리지 않는다.
            self.s.interact(self.p)
            self.assertIsNone(self.s.powered_circuit)
            self.s.interact(self.p)
            self.assertEqual(self.s.powered_circuit,second)

    def test_four_second_outage_warning_spawns_only_corridor_guards_at_all_frame_rates(self):
        for fps in (30,60,120):
            self.s=HospitalStage();self.p=Player(*self.s.start)
            enemies=self.actors()
            update_world(0,self.p,enemies,self.s)
            self.take('A')
            self.at((880,96))
            for _ in range(fps*4-1):update_world(1/fps,self.p,enemies,self.s)
            self.assertFalse(enemies[2].alive or enemies[3].alive)
            update_world(1/fps+.0001,self.p,enemies,self.s)
            self.assertTrue(enemies[2].alive and enemies[3].alive)
            self.assertEqual([p.generation for p in self.s.respawns.points],[0,0,1,1,0,0,0,0])
            self.assertEqual(self.p.health,3)

    def test_r_can_hold_one_return_spawn_without_powering_door_or_corridor(self):
        enemies=self.actors()
        update_world(0,self.p,enemies,self.s)
        self.take('A');self.at((880,96))
        self.p.light=PortableLight(1000,120,self.s.light_regions[1])
        for _ in range(481):update_world(1/120,self.p,enemies,self.s)
        self.assertFalse(enemies[2].alive)
        self.assertTrue(enemies[3].alive)
        self.assertIsNone(self.s.powered_circuit)
        self.assertFalse(self.s.doors['A'].is_open)

    def test_death_keeps_part_and_outage_but_does_not_extract_player_to_hub(self):
        records=ProgressRecords(self.p,self.s)
        self.take('A');self.s.update(.2)
        self.p.battery=0
        records.remember(self.p,self.s)
        records.restore_after_death(self.p,self.s)
        self.assertEqual((self.p.x,self.p.feet_y),self.s.return_checkpoints['A'])
        self.assertNotEqual((self.p.x,self.p.feet_y),self.s.start)
        self.assertTrue(self.s.parts['A'])
        self.assertFalse(self.s.returned['A'])
        self.assertIsNone(self.s.powered_circuit)
        self.assertEqual(self.p.battery,0)
        self.assertFalse(self.s.doors['A'].is_open)
        self.at(self.s.latch_positions['A']);self.s.interact(self.p);self.s.update(.55)
        records.remember(self.p,self.s)
        records.restore_after_death(self.p,self.s)
        self.assertTrue(self.s.doors['A'].is_open)
        records.restore_entry(self.p,self.s)
        self.assertEqual(self.s.powered_circuit,'A')
        self.assertFalse(any(self.s.parts.values()) or any(self.s.returned.values()) or any(self.s.return_open.values()))
        self.assertEqual(self.p.battery,100)

    def test_return_supplies_unlock_only_for_corresponding_recovered_part_and_do_not_duplicate(self):
        med=next(b for b in self.s.supply_boxes if b.item==MEDKIT)
        bomb=next(b for b in self.s.supply_boxes if b.item==LIGHT_BOMB)
        self.at((med.x,med.feet_y));self.s.interact(self.p)
        self.assertFalse(med.opened)
        self.take('A')
        self.at((med.x,med.feet_y));self.s.interact(self.p);self.s.update(.3);self.s.collect_pickups(self.p)
        self.assertEqual(self.p.medkits,1)
        self.at((bomb.x,bomb.feet_y));self.s.interact(self.p)
        self.assertFalse(bomb.opened)
        self.take('B')
        self.at((bomb.x,bomb.feet_y));self.s.interact(self.p);self.s.update(.3);self.s.collect_pickups(self.p)
        self.assertEqual(self.p.inventory.counts[LIGHT_BOMB],1)
        records=ProgressRecords(self.p,self.s)
        self.p.health=2;self.p.use_selected_item(MEDKIT)
        records.remember(self.p,self.s);records.restore_after_death(self.p,self.s)
        self.assertEqual(self.p.medkits,0)
        self.at((med.x,med.feet_y));self.s.interact(self.p);self.s.update(1);self.s.collect_pickups(self.p)
        self.assertEqual(self.p.medkits,0)
        self.assertTrue(med.claimed and bomb.claimed)

    def test_pause_freezes_outage_countdown_and_all_return_state(self):
        g=GameSession(HospitalStage);g.start_game();g.update(0)
        self.s,self.p=g.stage,g.player
        self.take('A')
        tap(g,pico2d.SDLK_ESCAPE)
        old=self.s.capture_state()
        counts=[(p.state,p.warning_elapsed) for p in self.s.respawns.points]
        g.update(5)
        self.assertEqual(self.s.capture_state(),old)
        self.assertEqual([(p.state,p.warning_elapsed) for p in self.s.respawns.points],counts)
        g.restart_stage()
        self.assertEqual(self.s.powered_circuit,'A')
        self.assertTrue(all(p.warning_duration==1 for p in self.s.respawns.points))

    def test_b_return_cover_blocks_bolts_and_is_reachable_with_basic_jump(self):
        m=Motion(1792,96)
        m.jump()
        for _ in range(80):m.step(1/120,1 if m.x<1856 else 0,self.s.solids,self.s.width)
        self.assertEqual(m.feet_y,144)
        self.at((1776,96))
        bolt=ShadowBolt.aimed((1952,140),(1776,140))
        bolt.update(1,self.s.solids,self.p)
        self.assertFalse(bolt.consume_hit())
        self.assertFalse(bolt.active)

    def test_a_descent_reaches_ground_switch_then_medkit_without_crossing_closed_gate(self):
        self.take('A');self.s.update(.55)
        m=Motion(704,336)
        for _ in range(400):
            m.step(1/120,1 if m.x<912 else 0,self.s.solids,self.s.width)
        self.assertEqual(m.feet_y,96)
        self.assertLessEqual(m.x+12,self.s.doors['A'].solid.left+1e-5)
        self.at((m.x,m.feet_y))
        target=self.s._target(self.p)
        self.assertEqual((target[0],target[2]),('latch','A'))
        self.s.interact(self.p);self.s.update(.55)
        for _ in range(100):m.step(1/120,1 if m.x<1000 else 0,self.s.solids,self.s.width)
        self.assertGreaterEqual(m.x,998)
        self.at((m.x,m.feet_y))
        target=self.s._target(self.p)
        self.assertEqual(target[0],'supply')
        self.assertEqual(target[2].item,MEDKIT)
