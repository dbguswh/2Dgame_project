"""진행 봉쇄는 실제 처치에만 반응하며 재출현/사망으로 초기화되지 않는다."""
import unittest
from unittest.mock import Mock,patch
import pico2d
from physics import Motion,RUN_SPEED
from projectiles import ShadowBolt
from session import GameSession
from world import update_world,restore_enemies


def tap(player,key):
    for kind in (pico2d.SDL_KEYDOWN,pico2d.SDL_KEYUP):
        event=pico2d.Event(kind);event.key=key;player.handle_event(event)


class CombatSealTests(unittest.TestCase):
    def setUp(self):
        loader=patch('pico2d.load_image',return_value=Mock());loader.start();self.addCleanup(loader.stop)
        self.game=GameSession();self.game.start_game()
        self.s,self.p,self.enemies=self.game.stage,self.game.player,self.game.enemies

    def defeat(self,index):
        enemy=self.enemies[index]
        enemy.take_damage();enemy.take_damage()
        self.s.update_combat_seals(self.enemies)

    def test_sprint_and_speed_boosted_jumps_cannot_cross_closed_routes(self):
        for seal,start in zip(self.s.combat_seals[:2],((700,96),(1740,288))):
            for speed in (RUN_SPEED,RUN_SPEED*1.3):
                body=Motion(*start)
                for _ in range(480):
                    if body.on_ground:body.jump()
                    body.step(1/120,1,self.s.solids,self.s.width,speed=speed)
                    self.assertLessEqual(body.get_bb()[2],seal.barrier.left+.001)

    def test_only_designated_defeat_opens_each_seal(self):
        self.defeat(1)
        self.assertEqual(self.s.capture_state(),(False,False,False))
        self.enemies[0].receive_flash(1)
        self.s.update_combat_seals(self.enemies)
        self.assertFalse(self.s.combat_seals[0].opened)
        self.enemies[0].take_damage()
        self.s.update_combat_seals(self.enemies)
        self.assertEqual(self.s.capture_state(),(True,False,False))
        self.assertNotIn(self.s.combat_seals[0].barrier,self.s.solids)

    def test_light_dissolution_does_not_count_as_defeat(self):
        self.enemies[0].dissolve();self.s.update_combat_seals(self.enemies)
        self.assertFalse(self.s.combat_seals[0].opened)

    def test_fuse_needs_all_three_encounters_even_if_player_reaches_cabinet(self):
        self.p.x,self.p.feet_y=self.s.fuse_checkpoint
        self.s.collect_pickups(self.p)
        self.assertEqual(self.s.fuse_state,'WORLD')
        self.defeat(7);self.s.collect_pickups(self.p)
        self.assertEqual(self.s.fuse_state,'WORLD')
        self.defeat(0);self.defeat(2);self.s.collect_pickups(self.p)
        self.assertEqual(self.s.fuse_state,'CARRIED')
        self.assertTrue(any(e.alive for e in self.enemies))

    def test_real_q_then_sword_kill_opens_first_route(self):
        enemy=self.enemies[0]
        self.p.x=enemy.x-100
        tap(self.p,pico2d.SDLK_q)
        update_world(0,self.p,self.enemies,self.s,self.game.records)
        self.assertEqual(enemy.health,1)
        for _ in range(42):update_world(1/120,self.p,self.enemies,self.s,self.game.records)
        self.p.x=enemy.x-40
        tap(self.p,pico2d.SDLK_w)
        for _ in range(24):update_world(1/120,self.p,self.enemies,self.s,self.game.records)
        self.assertFalse(enemy.alive)
        self.assertTrue(self.s.combat_seals[0].opened)
        self.assertEqual(self.p.battery,80)

    def test_death_and_enemy_reset_keep_open_route_but_stage_restart_resets_it(self):
        self.defeat(0);self.game.records.remember(self.p,self.s)
        self.game.records.restore_after_death(self.p,self.s);restore_enemies(self.enemies,self.s)
        self.assertTrue(self.enemies[0].alive)
        self.s.update_combat_seals(self.enemies)
        self.assertTrue(self.s.combat_seals[0].opened)
        self.game.restart_stage()
        self.assertEqual(self.s.capture_state(),(False,False,False))
        self.assertIn(self.s.combat_seals[0].barrier,self.s.solids)

    def test_fatal_hit_in_same_update_does_not_lose_completed_encounter(self):
        enemy=self.enemies[0];enemy.take_damage()
        self.p.x=enemy.x-100;self.p.health=1
        self.enemies[1].bolts.append(ShadowBolt.aimed((self.p.x,140),(self.p.x+1,140)))
        tap(self.p,pico2d.SDLK_q)
        update_world(0,self.p,self.enemies,self.s,self.game.records)
        self.assertEqual(self.p.respawn_count,1)
        self.assertTrue(self.s.combat_seals[0].opened)
        self.assertTrue(self.enemies[0].alive)

    def test_power_restore_removes_remaining_barriers(self):
        self.s.fixture_powered=True;self.s.update(0)
        self.assertTrue(self.s.fuse_unlocked)
        for seal in self.s.combat_seals:
            if seal.barrier:self.assertNotIn(seal.barrier,self.s.solids)
