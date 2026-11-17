import unittest
from unittest.mock import Mock,patch
import pico2d

from player import Player,SPIN_RECOVERY
from physics import Solid
from enemy import Shade
from stage import Stage
from world import update_world
from tests.test_ground_combo import tap,key


class SpinFinisherTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock())
        loader.start();self.addCleanup(loader.stop)
        self.p=Player(400,96)

    def tick(self,seconds):
        for _ in range(round(seconds*200)):self.p.update(.005,960)

    def combo(self):
        tap(self.p);self.p.update(0,960)
        self.tick(.2);tap(self.p);self.p.update(0,960)
        self.tick(.36)  # 2타의 타격 구간에서 새 입력으로 마무리 예약
        self.assertEqual(self.p.attack_stage,2)
        tap(self.p);self.p.update(0,960)
        self.assertTrue(self.p.combo_queued)
        self.tick(.25)
        self.assertEqual(self.p.attack_stage,3)

    def test_three_fresh_presses_chain_and_block_manual_movement_before_takeoff(self):
        self.combo()
        key(self.p,pico2d.SDLK_LEFT)
        tap(self.p,pico2d.SDLK_SPACE)
        self.tick(.1)
        self.assertEqual((self.p.x,self.p.feet_y,self.p.face_dir),(400,96,1))
        self.assertEqual(self.p.battery,100)
        self.assertEqual(self.p.attack_id,3)
        self.assertEqual(self.p.health,3)

    def test_finisher_has_recovery_and_cannot_chain_or_auto_repeat(self):
        self.combo();self.tick(.75)
        self.assertFalse(self.p.is_attacking)
        self.assertGreater(self.p.attack_cooldown,SPIN_RECOVERY-.04)
        key(self.p,pico2d.SDLK_w);self.p.update(0,960)
        self.tick(.7)
        self.assertEqual(self.p.attack_id,3)
        key(self.p,pico2d.SDLK_w,False);tap(self.p);self.p.update(0,960)
        self.assertEqual((self.p.attack_id,self.p.attack_stage),(4,1))

    def test_same_floor_targets_on_both_sides_hit_once_but_higher_floor_is_safe(self):
        self.p._begin_attack(3);self.p.attack_elapsed=.22
        targets=[('left',(330,96,354,184)),('right',(450,96,474,184)),
                 ('other-floor',(430,144,454,232))]
        self.assertCountEqual(self.p.get_attack_targets(targets),['left','right'])
        self.assertEqual(self.p.get_attack_targets(targets),[])

    def test_walls_and_ceiling_clip_finisher_in_both_directions(self):
        self.p.solids=[Solid(450,96,460,250),Solid(340,96,350,250),Solid(360,170,430,190)]
        self.p._begin_attack(3);self.p.attack_elapsed=.22
        self.assertEqual(self.p.get_attack_box(),(350,108,450,170))
        targets=[('behind-wall',(465,96,489,184)),('above-ceiling',(400,180,424,260))]
        self.assertEqual(self.p.get_attack_targets(targets),[])

    def test_windup_linger_and_damage_cancel_cannot_deal_damage(self):
        self.p._begin_attack(3)
        for elapsed in (.1,.18,.47,.65):
            self.p.attack_elapsed=elapsed
            self.assertIsNone(self.p.get_attack_box())
        self.p.attack_elapsed=.22
        self.p.take_damage()
        self.assertIsNone(self.p.get_attack_box())
        self.assertEqual(self.p.health,2)

    def test_world_applies_one_damage_and_outward_push_to_both_targets(self):
        s=Stage()
        s.solids=[Solid(0,0,960,96)]
        enemies=[Shade(x,96,identity=str(x),combat_bounds=(0,960)) for x in (340,460)]
        self.p._begin_attack(3);self.p.attack_elapsed=.22
        update_world(0,self.p,enemies,s)
        self.assertEqual([e.health for e in enemies],[65,65])
        self.assertEqual([e.knockback_direction for e in enemies],[-1,1])
        update_world(0,self.p,enemies,s)
        self.assertEqual([e.health for e in enemies],[65,65])

    def test_new_sprite_pose_mirrors_and_keeps_body_anchored(self):
        self.p._begin_attack(3);self.p.attack_elapsed=.25
        body=self.p.get_bb()
        for direction in (1,-1):
            self.p.face_dir=direction;self.p.draw(100)
            args=self.p.spin_attack_image.clip_composite_draw.call_args.args
            self.assertEqual(args[5],'h' if direction<0 else '')
            self.assertEqual(self.p.get_bb(),body)
