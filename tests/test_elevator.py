import unittest
from unittest.mock import Mock, patch
from elevator import Elevator
from player import Player


class ElevatorTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock())
        loader.start();self.addCleanup(loader.stop)
        self.e=Elevator()
        self.p=Player(self.e.x+20,96)

    def test_boards_and_carries_both_directions_exactly_at_different_frame_rates(self):
        for fps in (30,60,120):
            with self.subTest(fps=fps):
                self.e.reset_lower()
                self.p.x,self.p.feet_y=self.e.x+20,96
                for destination in (352,96):
                    self.assertTrue(self.e.board(self.p))
                    for _ in range(int(fps*1.5)):
                        self.e.update(1/fps)
                        self.assertEqual(self.p.x,self.e.x+20)
                        self.assertEqual(self.p.feet_y,self.e.y)
                    self.assertAlmostEqual(self.p.feet_y,destination)
                    self.assertFalse(self.e.moving)
                    self.assertIsNone(self.e.rider)

    def test_call_is_empty_and_cannot_redirect_or_repeat_while_moving(self):
        self.assertFalse(self.e.call(96))
        self.assertFalse(self.e.call(224))
        self.assertTrue(self.e.call(352))
        self.e.update(.4)
        y=self.e.y
        self.assertFalse(self.e.call(96))
        self.assertFalse(self.e.board(self.p))
        self.assertEqual(self.e.y,y)
        self.assertIsNone(self.e.rider)
        self.e.update(2)
        self.assertEqual(self.e.y,352)
        self.assertEqual(self.p.feet_y,96)
        self.assertTrue(self.e.call(96))

    def test_board_requires_whole_body_on_platform_and_ground_contact(self):
        for x,y,grounded in ((self.e.x+56,96,True),(self.e.x,105,True),(self.e.x,96,False)):
            self.p.x,self.p.feet_y,self.p.motion.on_ground=x,y,grounded
            self.assertFalse(self.e.board(self.p))

    def test_death_reset_detaches_and_leaves_a_callable_lower_car(self):
        self.assertTrue(self.e.board(self.p))
        self.e.update(.5)
        self.e.reset_lower()
        self.assertEqual(self.e.y,96)
        self.assertFalse(self.e.moving)
        self.assertIsNone(self.e.rider)
        self.assertTrue(self.e.call(352))

    def test_snapshot_is_independent_and_empty_call_can_restore(self):
        self.e.call(352)
        self.e.update(.6)
        state=self.e.snapshot()
        self.e.update(.9)
        self.e.restore(state)
        self.assertTrue(self.e.moving)
        self.assertIsNone(self.e.rider)
        self.e.update(.9)
        self.assertAlmostEqual(self.e.y,352)
