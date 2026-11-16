import unittest
from unittest.mock import Mock,patch
from player import Player
from halo import Halo,HaloAim
from halo_view import carried_halo_pose


class HaloCarryTests(unittest.TestCase):
    @patch('pico2d.load_image',return_value=Mock())
    def test_ready_weapon_is_visible_and_tracks_mirrored_hands(self,_):
        p=Player(400,96);p.unlock_ring();p.weapon='ring'
        right=carried_halo_pose(p);p.face_dir=-1;left=carried_halo_pose(p)
        self.assertIsNotNone(right);self.assertEqual(left[1],right[1])
        self.assertAlmostEqual(left[0]-400,400-right[0])
        p.x+=50;p.feet_y+=48
        self.assertEqual(carried_halo_pose(p),(left[0]+50,left[1]+48))

    @patch('pico2d.load_image',return_value=Mock())
    def test_flight_aim_and_other_actions_never_duplicate_held_ring(self,_):
        p=Player(400,96);p.unlock_ring();p.weapon='ring'
        p.halo=Halo(500,144,1);self.assertIsNone(carried_halo_pose(p))
        p.halo.active=False;self.assertIsNotNone(carried_halo_pose(p))
        p.halo_aim=HaloAim(1);self.assertIsNone(carried_halo_pose(p))
        p.halo_aim=None;p.attack_elapsed=.1;self.assertIsNone(carried_halo_pose(p))
        p.attack_elapsed=None;p.weapon='sword';self.assertIsNone(carried_halo_pose(p))
