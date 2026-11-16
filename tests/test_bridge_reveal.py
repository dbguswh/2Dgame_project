import unittest
from unittest.mock import Mock,patch
import pico2d
from session import GameSession


def tap(g,code):
    for kind in (pico2d.SDL_KEYDOWN,pico2d.SDL_KEYUP):
        e=pico2d.Event(kind);e.key=code;g.handle_event(e)


class BridgeRevealTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock());loader.start();self.addCleanup(loader.stop)
        self.g=GameSession();self.g.start_game();self.g.enemies=[]
        self.p,self.s=self.g.player,self.g.stage
        self.p.x,self.p.feet_y=self.s.fixture_position
        self.s.fuse_state='CARRIED'

    def start(self):
        tap(self.g,pico2d.SDLK_e);self.g.update(0)
        self.assertTrue(self.g.bridge_reveal.active)

    def test_camera_out_bridge_unfold_and_return_freeze_world(self):
        self.start();original=(self.p.x,self.p.feet_y,self.g.play_time)
        reveal=self.g.bridge_reveal
        self.g.update(.6)
        self.assertEqual(reveal.camera_x,reveal.destination)
        self.assertEqual(self.s.bridge_elapsed,0)
        self.g.update(1.2)
        self.assertAlmostEqual(self.s.bridge_elapsed,1.2)
        self.assertFalse(self.s.bridge_ready)
        self.g.update(1.2)
        self.assertTrue(self.s.bridge_ready)
        self.g.update(.6)
        self.assertFalse(reveal.active)
        self.assertAlmostEqual(reveal.camera_x,reveal.origin)
        self.assertEqual((self.p.x,self.p.feet_y,self.g.play_time),original)
        self.assertEqual(self.p.fragments,2)
        self.assertIn('다리를 건너',self.p.notice)

    def test_skip_once_no_jump_or_duplicate_reward_and_restart_resets(self):
        self.start();tap(self.g,pico2d.SDLK_SPACE)
        self.assertFalse(self.g.bridge_reveal.active)
        self.assertTrue(self.s.bridge_ready)
        self.assertEqual(self.p.fragments,2)
        self.g.update(0)
        self.assertTrue(self.p.motion.on_ground)
        self.assertEqual(self.p.fragments,2)
        self.g.restart_stage()
        self.assertIsNone(self.g.bridge_reveal)
        self.assertFalse(self.s.fixture_powered)

    def test_pause_focus_loss_and_movement_input_do_not_advance_world(self):
        self.start();tap(self.g,pico2d.SDLK_RIGHT);tap(self.g,pico2d.SDLK_w)
        self.g.update(.2)
        elapsed=self.g.bridge_reveal.elapsed;position=self.p.x
        tap(self.g,pico2d.SDLK_ESCAPE);self.g.update(1)
        self.assertEqual(self.g.bridge_reveal.elapsed,elapsed)
        tap(self.g,pico2d.SDLK_ESCAPE)
        self.g.update(1,focused=False)
        self.assertEqual(self.g.bridge_reveal.elapsed,elapsed)
        self.assertEqual(self.p.x,position)
        self.assertFalse(self.p.is_attacking)

    def test_death_after_restore_keeps_bridge_without_replaying(self):
        self.start();tap(self.g,pico2d.SDLK_SPACE)
        self.g.records.restore_after_death(self.p,self.s)
        self.assertTrue(self.s.bridge_ready)
        self.g.update(0)
        self.assertFalse(self.g.bridge_reveal.active)
        self.assertEqual(self.p.fragments,2)
