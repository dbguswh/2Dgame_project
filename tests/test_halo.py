import unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock
import pico2d
from halo import Halo
from physics import Solid
from session import GameSession
from hospital import HospitalStage


def tap(p,code):
    for kind in (pico2d.SDL_KEYDOWN,pico2d.SDL_KEYUP):
        e=pico2d.Event(kind);e.key=code;p.handle_event(e)


class HaloGeometryTests(unittest.TestCase):
    def setUp(self):self.p=SimpleNamespace(x=100,feet_y=96)

    def test_outward_then_returns_and_catches(self):
        h=Halo(100,140,1)
        h.update(.45,self.p,[])
        self.assertAlmostEqual(h.x,316)
        for _ in range(100):h.update(1/120,self.p,[])
        self.assertFalse(h.active)

    def test_upward_and_return_follow_moving_player(self):
        h=Halo(100,140,1,True);h.update(.4,self.p,[])
        self.assertGreater(h.y,270)
        self.p.x=20;self.p.feet_y=180
        h.update(.1,self.p,[]);old=h.x
        h.update(.1,self.p,[])
        self.assertLess(h.x,old)
        for _ in range(120):h.update(1/120,self.p,[])
        self.assertFalse(h.active)

    def test_wall_reverses_outbound_and_blocks_damage_behind_it(self):
        wall=Solid(180,96,188,300)
        h=Halo(100,140,1);h.update(.2,self.p,[wall])
        self.assertEqual(h.phase,'RETURN')
        self.assertLess(h.x,180)
        self.assertNotIn('behind',h.candidates([('behind',(188,100,210,180))],[wall]))

    def test_successful_hit_once_but_blocked_target_can_be_hit_on_return(self):
        h=Halo(100,140,1);h.update(.25,self.p,[])
        target=[('x',(190,96,230,180))]
        self.assertIn('x',h.candidates(target,[]))
        # 방어 실패는 hits에 추가하지 않으므로 복귀 후보로 다시 검사한다.
        h.update(.5,self.p,[])
        self.assertIn('x',h.candidates(target,[]))
        h.hits.add('x')
        self.assertFalse(h.candidates(target,[]))

    def test_return_obstruction_recalls_without_wall_penetration(self):
        h=Halo(200,140,1,phase='RETURN')
        h.update(1,self.p,[Solid(150,96,160,300)])
        self.assertFalse(h.active)
        self.assertGreater(h.x,160)


class HaloControlsTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock());loader.start();self.addCleanup(loader.stop)
        self.g=GameSession();self.g.start_game();self.p=self.g.player
        self.g.enemies=[]

    def test_first_management_unlock_and_entry_restart_reset(self):
        self.g.stage.completed=True;self.g.stage.fixture_powered=True
        self.g.state='STAGE_CLEAR';self.g.open_city_map();self.g.open_management()
        self.assertTrue(self.p.ring_unlocked)
        self.g.records.restore_after_death(self.p,self.g.stage)
        self.assertTrue(self.p.ring_unlocked)
        self.g.restart_stage()
        self.assertFalse(self.p.ring_unlocked)

    def test_switch_and_one_throw_pays_once_without_auto_repeat(self):
        self.p.unlock_ring();tap(self.p,pico2d.SDLK_a);self.g.update(0)
        self.assertEqual(self.p.weapon,'ring')
        self.p.battery=10
        tap(self.p,pico2d.SDLK_w);self.g.update(0)
        h=self.p.halo
        self.assertIsNotNone(h)
        self.g.update(.4);tap(self.p,pico2d.SDLK_w);self.g.update(0)
        self.assertIs(self.p.halo,h)
        self.assertEqual(self.p.battery,0)
        self.g.update(2)
        self.g.update(0)
        self.assertIsNone(self.p.halo)

    def test_upper_sword_reaches_overhead_and_ceiling_blocks_it(self):
        tap(self.p,pico2d.SDLK_UP);e=pico2d.Event(pico2d.SDL_KEYDOWN);e.key=pico2d.SDLK_UP;self.p.handle_event(e)
        tap(self.p,pico2d.SDLK_w);self.p.update(0,2000,[]);self.p.update(.15,2000,[])
        box=self.p.get_attack_box()
        self.assertIsNotNone(box);self.assertEqual(self.p.attack_kind,'upper')
        self.assertGreater(box[3],self.p.feet_y+140)
        self.p.solids=[Solid(self.p.x-20,self.p.feet_y+120,self.p.x+140,self.p.feet_y+130)]
        self.assertLessEqual(self.p.get_attack_box()[3],self.p.feet_y+120)

    def test_busy_switch_is_rejected_and_pause_freezes_halo(self):
        self.p.unlock_ring();self.p.weapon='ring';tap(self.p,pico2d.SDLK_w);self.g.update(0)
        tap(self.p,pico2d.SDLK_a);self.g.update(0)
        self.assertEqual(self.p.weapon,'ring')
        h=self.p.halo;self.g.state='PAUSED';self.g.update(1)
        self.assertEqual(h.age,0)

    def test_hospital_restart_and_death_preserve_unlock_but_clear_flight(self):
        g=GameSession(HospitalStage);g.start_game();p=g.player
        p.weapon='ring';tap(p,pico2d.SDLK_w);g.enemies=[];g.update(0)
        g.records.remember(p,g.stage);g.records.restore_after_death(p,g.stage)
        self.assertTrue(p.ring_unlocked);self.assertIsNone(p.halo)
        g.restart_stage();self.assertTrue(p.ring_unlocked)
