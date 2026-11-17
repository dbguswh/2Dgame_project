import unittest
from unittest.mock import Mock,patch
import pico2d
from hospital import HospitalStage
from session import GameSession
from world import update_world,restore_enemies
from tests.test_air_attack import tap
from hospital_ui import circuit_status


class HospitalFlowTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock());loader.start();self.addCleanup(loader.stop)
        self.g=GameSession(HospitalStage);self.g.start_game();self.g.update(0)
        self.s,self.p=self.g.stage,self.g.player

    def at(self,position):
        self.p.x,self.p.feet_y=position;self.p.motion.on_ground=True
        self.p.motion.velocity_y=0

    def test_compact_layout_reduces_empty_lit_walk_but_preserves_eight_enemies(self):
        self.assertEqual(self.s.width,2880)
        self.assertEqual([r.right-r.left for r in (self.s.light_regions[1],self.s.light_regions[3])],[384,384])
        self.assertEqual(len(self.g.enemies),8)
        self.assertEqual(sum(e.kind=='wraith' for e in self.s.enemy_placements),2)
        for e in self.s.enemy_placements:
            self.assertTrue(e.bounds[1]<=1344 or e.bounds[0]>=1664)

    def test_contact_and_e_without_combat_cannot_remove_part(self):
        for key,(x,y) in self.s.part_positions.items():
            self.at((x,y-16));self.s.collect_pickups(self.p)
            self.assertFalse(self.s.parts[key])
            self.assertIn('처치',self.s.interaction_prompt(self.p)[2])
            self.s.interact(self.p)
            self.assertFalse(self.s.parts[key])

    def test_stun_or_light_dissolution_does_not_unlock_part(self):
        target=self.g.enemies[0];target.receive_flash(1)
        self.s.update_combat_seals(self.g.enemies)
        self.assertFalse(self.s.room_cleared['A'])
        target.dissolve();self.s.update_combat_seals(self.g.enemies)
        self.assertFalse(self.s.room_cleared['A'])

    def test_unlocked_part_still_needs_e_and_warns_about_outage(self):
        target=self.g.enemies[0];target.take_damage();target.take_damage();target.take_damage()
        self.s.update_combat_seals(self.g.enemies)
        x,y=self.s.part_positions['A'];self.at((x,y-16));self.s.collect_pickups(self.p)
        self.assertFalse(self.s.parts['A'])
        self.assertIn('정전',self.s.interaction_prompt(self.p)[2])
        self.assertTrue(self.s.interact(self.p));self.assertTrue(self.s.parts['A'])
        self.assertIsNone(self.s.powered_circuit)
        self.assertIn('정전',circuit_status(self.s,'A'))

    def test_real_q_kills_unlock_both_orders_and_exit_after_dark_returns(self):
        for order in (('A','B'),('B','A')):
            self.g=GameSession(HospitalStage);self.g.start_game();self.g.update(0)
            self.s,self.p=self.g.stage,self.g.player
            for key in order:
                self.s.circuit=key;self.s.update(.6)
                target=self.g.enemies[0 if key=='A' else 6]
                self.at((target.x+100,target.feet_y));self.p.face_dir=-1
                tap(self.p,pico2d.SDLK_q)
                update_world(0,self.p,[target],self.s,self.g.records)
                for _ in range(42):update_world(1/120,self.p,[target],self.s,self.g.records)
                self.at((target.x+40,target.feet_y));self.p.face_dir=-1
                tap(self.p,pico2d.SDLK_w)
                for _ in range(24):update_world(1/120,self.p,[target],self.s,self.g.records)
                tap(self.p,pico2d.SDLK_w)
                for _ in range(96):update_world(1/120,self.p,[target],self.s,self.g.records)
                self.assertTrue(self.s.room_cleared[key],(key,target.health,self.p.x,self.p.feet_y,target.x,target.feet_y,self.p.attack_id))
                x,y=self.s.part_positions[key];self.at((x,y-16));self.s.interact(self.p)
                self.assertTrue(self.s.parts[key]);self.s.update(.6)
                self.assertFalse(self.s.doors[key].is_open)
                self.at(self.s.latch_positions[key]);self.s.interact(self.p);self.s.update(.6)
                self.assertTrue(self.s.doors[key].is_open)
                self.at(self.s.start);self.s.collect_pickups(self.p)
                self.assertTrue(self.s.returned[key])
            self.at(self.s.fixture_position);self.s.interact(self.p);self.s.update(1.2)
            self.at(self.s.exit_position);self.s.interact(self.p)
            self.assertTrue(self.s.completed)
            self.assertEqual((self.p.fragments,self.p.battery),(2,60))

    def test_guard_unlock_survives_death_respawn_but_stage_restart_resets(self):
        target=self.g.enemies[0];target.take_damage();target.take_damage();target.take_damage()
        self.s.update_combat_seals(self.g.enemies);self.g.records.remember(self.p,self.s)
        self.g.records.restore_after_death(self.p,self.s);restore_enemies(self.g.enemies,self.s)
        self.assertTrue(target.alive);self.assertTrue(self.s.room_cleared['A'])
        self.g.restart_stage();self.assertFalse(any(self.s.room_cleared.values()))

    def test_remote_or_airborne_e_does_not_remove_unlocked_part(self):
        self.s.room_cleared['A']=True
        self.assertIsNone(self.s._target(self.p))
        x,y=self.s.part_positions['A'];self.at((x,y-16));self.p.motion.on_ground=False
        self.assertFalse(self.s.interact(self.p));self.assertFalse(self.s.parts['A'])
