import unittest
from unittest.mock import Mock,patch

from player import Player
from physics import Solid


class AcrobatMotionTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock())
        loader.start();self.addCleanup(loader.stop)

    def run_attack(self,p,solids,fps=120):
        p._begin_attack(3)
        positions=[]
        for _ in range(fps):
            p.update(1/fps,960,solids)
            positions.append((p.x,p.feet_y))
        return positions

    def test_small_real_hop_and_step_are_bounded_and_land_at_all_frame_rates(self):
        for fps in (30,60,120):
            p=Player(400,96)
            positions=self.run_attack(p,[Solid(0,0,960,96)],fps)
            self.assertAlmostEqual(p.x,424,delta=.01)
            self.assertEqual(p.feet_y,96)
            self.assertTrue(p.motion.on_ground)
            self.assertGreater(max(y for _,y in positions),128)
            self.assertLessEqual(max(y for _,y in positions),132.01)

    def test_left_step_is_mirrored(self):
        p=Player(400,96);p.face_dir=p.combo_direction=-1
        self.run_attack(p,[Solid(0,0,960,96)])
        self.assertAlmostEqual(p.x,376,delta=.01)

    def test_ledge_end_hops_in_place_instead_of_forcing_player_into_gap(self):
        p=Player(430,96)
        self.run_attack(p,[Solid(300,0,450,96)])
        self.assertAlmostEqual(p.x,430)
        self.assertEqual(p.feet_y,96)

    def test_wall_and_low_ceiling_stop_real_body_without_clipping(self):
        p=Player(400,96)
        positions=self.run_attack(p,[Solid(0,0,960,96),Solid(420,96,440,300)])
        self.assertLessEqual(max(x for x,_ in positions),408.01)
        p=Player(400,96)
        positions=self.run_attack(p,[Solid(0,0,960,96),Solid(350,192,480,208)])
        self.assertLessEqual(max(y for _,y in positions),100.01)
        self.assertEqual(p.feet_y,96)

    def test_damage_stops_scripted_step_but_gravity_continues(self):
        p=Player(400,96);p._begin_attack(3)
        for _ in range(30):p.update(1/120,960)
        x=p.x
        self.assertGreater(p.feet_y,96)
        p.take_damage()
        for _ in range(120):p.update(1/120,960)
        self.assertIsNone(p.finisher_motion)
        self.assertAlmostEqual(p.x,x)
        self.assertEqual(p.feet_y,96)

    def test_airborne_hit_uses_origin_floor_to_exclude_other_floor(self):
        p=Player(400,96);p._begin_attack(3)
        for _ in range(45):p.update(1/120,960)
        self.assertGreater(p.feet_y,128)
        self.assertEqual(p.get_attack_targets([('floor',(430,96,454,184)),
                                               ('upstairs',(430,144,454,232))]),['floor'])
