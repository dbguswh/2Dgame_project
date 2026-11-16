import unittest
from unittest.mock import Mock,patch
import pico2d
from session import GameSession
from tests.test_management import tap,key


class WeaponNoticeTests(unittest.TestCase):
    @patch('pico2d.load_image',return_value=Mock())
    def setUp(self,_):
        self.g=GameSession();self.g.start_game();self.g.stage.completed=True
        self.g.player.fragments=2;self.g.state='STAGE_CLEAR'
        self.g.open_city_map();self.g.open_management()

    def test_first_notice_blocks_purchase_and_repeats_require_new_e(self):
        g=self.g;self.assertTrue(g.weapon_tip_open)
        before=(g.play_time,g.stage.visual_time,g.player.battery)
        tap(g,pico2d.SDLK_RIGHT);g.update(2)
        self.assertEqual(g.selection,0)
        self.assertEqual((g.play_time,g.stage.visual_time,g.player.battery),before)
        key(g,pico2d.SDLK_e)
        self.assertFalse(g.weapon_tip_open)
        for _ in range(5):key(g,pico2d.SDLK_e)
        self.assertEqual(g.player.fragments,2)
        self.assertFalse(g.management_visit.completed)
        key(g,pico2d.SDLK_e,False);tap(g,pico2d.SDLK_e)
        self.assertEqual(g.player.fragments,0)
        self.assertTrue(g.management_visit.completed)

    def test_notice_does_not_repeat_on_revisit_or_death(self):
        g=self.g;tap(g,pico2d.SDLK_e);g.open_city_map();g.open_management()
        self.assertFalse(g.weapon_tip_open)
        g.records.restore_after_death(g.player,g.stage)
        self.assertTrue(g.player.ring_unlocked)
        g.return_to_title();self.assertFalse(g.weapon_tip_open)
