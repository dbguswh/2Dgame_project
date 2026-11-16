import unittest
from math import sin,radians
from types import SimpleNamespace
from unittest.mock import patch,Mock
import pico2d
from halo import Halo,HaloAim,preview_path
from player import Player
from physics import Solid


def event(p,key,down=True):
    e=pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP);e.key=key;p.handle_event(e)


class HaloAimTests(unittest.TestCase):
    def test_angle_range_and_prediction_match_actual_flight(self):
        for angle in (0,15,30,45,60,75):
            for fps in (30,60,120):
                points=preview_path(100,144,1,angle,[])
                h=Halo(100,144,1,angle=angle);p=SimpleNamespace(x=100,feet_y=100)
                remaining=.45
                while remaining>1e-9:
                    dt=min(remaining,1/fps);h.update(dt,p,[]);remaining-=dt
                self.assertAlmostEqual(h.x,points[-1][0],places=6)
                self.assertAlmostEqual(h.y,144+216*sin(radians(angle)),places=6)
        a=HaloAim(1);a.update(10,-1,1);self.assertEqual((a.angle,a.direction),(75,-1))
        a.update(10,0,-1);self.assertEqual(a.angle,0)

    def test_preview_and_live_obstruction_and_top_limit(self):
        for solids in ([],[Solid(180,96,192,500)]):
            points=preview_path(100,430,1,75,solids)
            self.assertLessEqual(max(y for x,y in points),508)
            h=Halo(100,430,1,angle=75);owner=SimpleNamespace(x=100,feet_y=386)
            for _ in range(54):
                h.update(1/120,owner,solids)
                if h.phase!='OUT':break
            self.assertEqual((h.x,h.y),points[-1])

    @patch('pico2d.load_image',return_value=Mock())
    def test_hold_adjust_release_and_no_auto_repeat(self,_):
        p=Player(400,96);p.unlock_ring();p.weapon='ring';p.battery=0
        event(p,pico2d.SDLK_w);p.update(0,1000)
        event(p,pico2d.SDLK_UP);p.update(.5,1000)
        self.assertIsNone(p.halo);self.assertEqual(p.halo_aim.angle,45)
        event(p,pico2d.SDLK_w,False);p.update(0,1000)
        self.assertEqual(p.halo.angle,45);self.assertIsNone(p.halo_aim);self.assertEqual(p.battery,0)
        p.update(1,1000);self.assertIsNotNone(p.halo)

    @patch('pico2d.load_image',return_value=Mock())
    def test_cancel_actions_never_throw_and_require_new_press(self,_):
        for code in (pico2d.SDLK_q,pico2d.SDLK_r,pico2d.SDLK_SPACE,pico2d.SDLK_e,pico2d.SDLK_a,pico2d.SDLK_f):
            p=Player(400,96);p.unlock_ring();p.weapon='ring'
            event(p,pico2d.SDLK_w);p.update(0,1000)
            event(p,code);p.update(0,1000)
            self.assertIsNone(p.halo_aim,code);self.assertIsNone(p.halo,code)
            event(p,pico2d.SDLK_w,False);p.update(0,1000)
            self.assertIsNone(p.halo)

    @patch('pico2d.load_image',return_value=Mock())
    def test_focus_clear_and_damage_cancel_aim(self,_):
        p=Player(400,96);p.unlock_ring();p.weapon='ring'
        event(p,pico2d.SDLK_w);p.update(0,1000);p.clear_input()
        self.assertIsNone(p.halo_aim)
        event(p,pico2d.SDLK_w);p.update(0,1000);p.take_damage()
        self.assertIsNone(p.halo_aim);self.assertIsNone(p.halo)
