import unittest
from unittest.mock import patch,Mock
import pico2d
from halo import HALO_COST,HALO_COOLDOWN
from session import GameSession
from controls_view import weapon_status
from tests.test_management import tap,key


class HaloBalanceTests(unittest.TestCase):
    @patch('pico2d.load_image',return_value=Mock())
    def setUp(self,_):
        self.g=GameSession();self.g.start_game();self.enemy=self.g.enemies[0];self.g.enemies=[]
        self.p=self.g.player;self.p.unlock_ring();self.p.weapon='ring'

    def throw(self):
        tap(self.g,pico2d.SDLK_w);self.g.update(0)

    def recall(self):
        for _ in range(360):
            self.g.update(1/120)
            if self.p.halo is not None and not self.p.halo.active:return
        self.fail('광륜이 복귀하지 않음')

    def test_cost_at_release_only_and_cancel_is_free(self):
        key(self.g,pico2d.SDLK_w);self.g.update(.2)
        self.assertEqual(self.p.battery,100)
        self.assertIsNone(self.p.halo)
        self.g.clear_input();key(self.g,pico2d.SDLK_w,False)
        self.assertEqual(self.p.battery,100)
        self.throw();self.assertEqual(self.p.battery,100-HALO_COST)
        for _ in range(3):self.throw()
        self.assertEqual(self.p.battery,90)

    def test_insufficient_battery_blocks_aim_and_exact_cost_can_fire(self):
        self.p.battery=9;self.throw()
        self.assertIsNone(self.p.halo_aim);self.assertIsNone(self.p.halo)
        self.assertEqual(self.p.battery,9)
        self.assertIn('부족',weapon_status(self.p)[0])
        self.p.battery=10;self.throw()
        self.assertEqual(self.p.battery,0);self.assertIsNotNone(self.p.halo)

    def test_release_rechecks_battery_if_resource_changed_during_aim(self):
        key(self.g,pico2d.SDLK_w);self.g.update(0)
        self.p.battery=9;key(self.g,pico2d.SDLK_w,False);self.g.update(0)
        self.assertEqual(self.p.battery,9);self.assertIsNone(self.p.halo)

    def test_recall_starts_full_cooldown_and_switch_cannot_bypass_it(self):
        self.throw();self.assertEqual(self.p.halo_cooldown,0)
        self.recall();self.assertEqual(self.p.halo_cooldown,HALO_COOLDOWN)
        self.throw();self.assertIsNone(self.p.halo_aim)
        tap(self.g,pico2d.SDLK_a);self.g.update(0)
        tap(self.g,pico2d.SDLK_a);self.g.update(0)
        self.assertEqual(self.p.halo_cooldown,1)
        self.g.update(.99);self.throw();self.assertIsNone(self.p.halo_aim)
        self.assertEqual(self.p.battery,90)
        self.g.update(.02);self.throw();self.assertEqual(self.p.battery,80)

    def test_pause_and_focus_do_not_run_cooldown(self):
        self.p.halo_cooldown=.6
        self.g.state='PAUSED';self.g.update(2)
        self.g.state='PLAY';self.g.update(2,focused=False)
        self.assertEqual(self.p.halo_cooldown,.6)

    def test_death_preserves_spent_battery_and_restart_resets_it(self):
        self.throw();self.g.records.restore_after_death(self.p,self.g.stage)
        self.assertEqual(self.p.battery,90)
        self.assertIsNone(self.p.halo)
        self.assertEqual(self.p.halo_cooldown,1)
        self.g.restart_stage()
        self.assertEqual((self.p.battery,self.p.halo_cooldown),(100,0))

    def test_ground_sword_remains_free(self):
        self.p.weapon='sword';self.p.battery=0
        self.throw();self.assertTrue(self.p.is_attacking)
        self.assertEqual(self.p.battery,0)

    def test_world_and_enemy_keep_updating_while_aiming(self):
        self.p.x=450;self.p.invulnerability=5
        enemy=self.enemy;self.g.enemies=[enemy]
        key(self.g,pico2d.SDLK_w);self.g.update(0)
        for _ in range(60):self.g.update(1/120)
        self.assertIsNotNone(self.p.halo_aim)
        self.assertGreater(self.g.play_time,.49)
        self.assertNotEqual(enemy.state,'PATROL')
        self.assertLess(enemy.x,560)
