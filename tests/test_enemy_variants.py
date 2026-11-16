import unittest
from unittest.mock import Mock,patch
from collections import Counter
from types import SimpleNamespace
from brute import Brute
from wraith import Wraith
from enemy_factory import create_enemy
from hospital import HospitalStage
from substation import SubstationStage
from player import Player
from physics import Solid
from lighting import PortableLight,LightRegion
from halo import Halo


class EnemyVariantTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock());loader.start();self.addCleanup(loader.stop)
        self.p=Player(400,96)
        self.s=SimpleNamespace(width=1000,solids=[Solid(0,0,1000,96)])

    def test_stage_compositions_and_respawn_actor_types(self):
        for stage,expected in ((HospitalStage(),{'shade':6,'wraith':2}),
                               (SubstationStage(),{'shade':4,'brute':5,'wraith':1})):
            self.assertEqual(Counter(e.kind for e in stage.enemy_placements),expected)
            for placement in stage.enemy_placements:
                actor=create_enemy(placement)
                actor.health=0;actor.reset()
                self.assertEqual(actor.health,3 if placement.kind=='brute' else 2)

    def test_brute_front_blocks_but_rear_and_recovery_are_vulnerable(self):
        b=Brute(500,96,combat_bounds=(0,1000));b.face_dir=-1
        self.assertFalse(b.receive_weapon(1,(480,140),'ring'))
        self.assertEqual(b.health,3)
        self.assertTrue(b.receive_weapon(-1,(520,140),'ring'))
        b._enter('RECOVER')
        self.assertTrue(b.receive_weapon(1,(480,140),'sword'))
        self.assertEqual(b.health,1)

    def test_ring_block_does_not_consume_hit_and_return_hits_brute_back(self):
        b=Brute(250,96,combat_bounds=(0,1000));b.face_dir=-1
        p=SimpleNamespace(x=100,feet_y=96)
        h=Halo(100,140,1)
        blocked=landed=False
        for _ in range(160):
            h.update(1/120,p,self.s.solids)
            for direction,point in h.candidates([('brute',b.get_bb())],self.s.solids).values():
                if b.receive_weapon(direction,point,'ring'):
                    h.hits.add('brute');landed=True
                else:blocked=True
        self.assertTrue(blocked and landed)
        self.assertEqual(b.health,2)

    def test_flash_and_bomb_keep_their_effect_on_armored_enemy(self):
        b=Brute(500,96,combat_bounds=(0,1000))
        b.receive_flash(1)
        self.assertEqual((b.health,b.state),(2,'STUNNED'))
        b.receive_bomb(1)
        self.assertEqual((b.health,b.state),(1,'RECOVER'))

    def test_wraith_dive_locks_target_then_offers_low_recovery(self):
        w=Wraith(500,96,combat_bounds=(200,800))
        w.dive_cooldown=0
        w.update(0,self.p,self.s)
        self.assertEqual(w.state,'DIVE_WINDUP')
        target=w.dive_target
        self.p.x=700
        for _ in range(91):w.update(1/120,self.p,self.s)
        self.assertEqual(w.dive_target,target)
        for _ in range(61):w.update(1/120,self.p,self.s)
        self.assertEqual(w.state,'RECOVER')
        self.assertLess(w.feet_y,130)
        self.assertIsNone(w.get_attack_box())

    def test_wraith_light_cancels_dive_and_retreats_without_reentering(self):
        w=Wraith(500,96,combat_bounds=(200,800));w.state='DIVE';w.dive_target=(400,106)
        light=PortableLight(500,120,LightRegion(0,96,1000,540))
        for _ in range(360):
            w.update(1/120,self.p,self.s,light)
            self.assertIsNone(w.consume_attack())
        self.assertFalse(light.illuminates(w.get_bb()))
        self.assertNotEqual(w.state,'DIVE')

    def test_dive_cannot_cross_closed_wall_or_hurt_through_light(self):
        wall=Solid(440,96,460,400);self.s.solids.append(wall)
        w=Wraith(500,96,combat_bounds=(200,800));w.dive_cooldown=0
        w.update(0,self.p,self.s)
        self.assertNotEqual(w.state,'DIVE_WINDUP')
        w.state='DIVE';w.dive_target=(400,106)
        for _ in range(100):
            w.update(1/120,self.p,self.s)
            self.assertGreaterEqual(w.x-24,460)

    def test_wraith_flash_cancel_and_reset_restore_hover(self):
        w=Wraith(500,96,combat_bounds=(200,800));w.state='DIVE'
        w.receive_flash(1)
        w.update(.1,self.p,self.s)
        self.assertEqual(w.state,'STUNNED')
        self.assertIsNone(w.consume_attack())
        w.reset()
        self.assertEqual((w.state,w.health,w.feet_y),('FLY_PATROL',2,208))

    def test_wraith_weapon_hit_pause_freezes_motion_but_light_has_priority(self):
        w=Wraith(500,96,combat_bounds=(200,800))
        w.receive_weapon(1,(500,230),'ring')
        before=(w.x,w.feet_y,w.state_time)
        w.update(.01,self.p,self.s)
        self.assertEqual((w.x,w.feet_y,w.state_time),before)
        self.assertGreater(w.hit_pause.remaining,0)
        light=PortableLight(500,120,LightRegion(0,96,1000,540))
        w.update(.01,self.p,self.s,light)
        self.assertEqual(w.hit_pause.remaining,0)
        self.assertEqual(w.state,'RETREAT')
        self.assertNotEqual((w.x,w.feet_y),before[:2])
