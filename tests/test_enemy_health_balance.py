import unittest
from unittest.mock import Mock,patch

from enemy import Shade
from wraith import Wraith
from brute import Brute


class EnemyHealthBalanceTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock())
        loader.start();self.addCleanup(loader.stop)

    def test_normal_and_flying_enemies_take_exactly_three_sword_hits(self):
        for kind in (Shade,Wraith):
            enemy=kind(500,96)
            self.assertEqual((enemy.health,enemy.max_health),(100,100))
            for expected in (65,30,0):
                self.assertTrue(enemy.receive_weapon(1,(500,140)))
                self.assertEqual(enemy.health,expected)
            self.assertFalse(enemy.alive)
            self.assertFalse(enemy.receive_weapon(1,(500,140)))

    def test_bomb_is_seventy_then_one_sword_hit_finishes(self):
        enemy=Shade(500,96)
        enemy.receive_bomb(1)
        self.assertEqual(enemy.health,30)
        self.assertEqual(enemy.health_before_hit,100)
        enemy.receive_weapon(1,(500,140))
        self.assertEqual(enemy.health,0)

    def test_flash_damages_thirty_five_and_keeps_its_control_effect(self):
        enemy=Shade(500,96)
        enemy.receive_flash(1)
        self.assertEqual((enemy.health,enemy.state),(65,'STUNNED'))
        self.assertEqual(enemy.stun_remaining,1.2)

    def test_armored_guard_still_blocks_then_requires_four_unblocked_sword_hits(self):
        enemy=Brute(500,96);enemy.face_dir=-1
        self.assertFalse(enemy.receive_weapon(1,(500,140)))
        self.assertEqual(enemy.health,140)
        enemy._enter('RECOVER')
        for expected in (105,70,35,0):
            enemy.receive_weapon(1,(500,140))
            self.assertEqual(enemy.health,expected)

    def test_reset_restores_each_species_maximum_and_clears_damage_trail(self):
        for kind,maximum in ((Shade,100),(Wraith,100),(Brute,140)):
            enemy=kind(500,96)
            enemy.receive_bomb(1);enemy.reset()
            self.assertEqual((enemy.health,enemy.max_health,enemy.health_before_hit),
                             (maximum,maximum,maximum))

    def test_ring_uses_same_thirty_five_damage_without_extra_hit_on_same_call(self):
        enemy=Shade(500,96)
        enemy.receive_weapon(1,(500,140),'ring')
        self.assertEqual(enemy.health,65)
