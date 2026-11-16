import unittest
from unittest.mock import Mock, patch

import pico2d
from session import GameSession
from hospital import HospitalStage
from inventory import LIGHT_BOMB
from upgrades import CAPACITY
from tests.test_management import tap, key


class HospitalTransitionTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.g = GameSession()
        self.g.start_game()

    def management(self):
        g = self.g
        g.stage.completed = True
        g.update(0)
        g.player.fragments = 3
        g.open_city_map()
        g.open_management()
        tap(g,pico2d.SDLK_e)  # 첫 관리소 무기 획득 안내 확인

    def depart(self):
        self.management()
        tap(self.g, pico2d.SDLK_e)
        tap(self.g, pico2d.SDLK_RIGHT)
        self.assertEqual(self.g.selection, 3)
        key(self.g, pico2d.SDLK_e)

    def test_departure_requires_completion_and_upgrade_and_fades_without_world_time(self):
        g = self.g
        self.assertFalse(g.depart())
        self.management()
        self.assertFalse(g.depart())
        tap(g, pico2d.SDLK_e)
        self.assertTrue(g.can_depart)
        self.assertEqual(g.selection, 2)
        tap(g, pico2d.SDLK_RIGHT)
        key(g, pico2d.SDLK_e)
        self.assertEqual(g.state, 'TRANSITION')
        old_time, old_visual = g.play_time, g.stage.visual_time
        g.update(.2)
        self.assertEqual(g.stage.stage_id, 'residential')
        self.assertEqual(g.stage.visual_time, old_visual)
        g.update(5, focused=False)
        self.assertEqual(g.transition_elapsed, .2)
        g.update(.5)
        self.assertEqual(g.state,'TRANSITION')
        self.assertEqual(g.stage.stage_id,'residential')
        g.update(1.3)
        self.assertIsInstance(g.stage, HospitalStage)
        self.assertEqual(g.state, 'PLAY')
        self.assertEqual(g.play_time, old_time)

    def test_stage_entry_inherits_items_and_upgrade_restores_resources_and_restarts_here(self):
        g = self.g
        self.depart()
        p = g.player
        p.health, p.battery = 1, 0
        p.add_item(LIGHT_BOMB)
        p.item_effects.speed_remaining = 3
        g.update(2)
        self.assertIs(p, g.player)
        self.assertEqual((p.health, p.battery, p.max_battery), (3, 140, 140))
        self.assertEqual(p.core_upgrades, {CAPACITY})
        self.assertEqual(p.fragments, 1)
        self.assertEqual(p.inventory.counts[LIGHT_BOMB], 1)
        self.assertEqual(p.item_effects.speed_remaining, 0)
        self.assertIsNone(g.management_visit)
        self.assertEqual(g.completed_stage_ids, {'residential'})
        # 관리소에서 누른 E를 유지하거나 OS가 반복해도 병원 회로가 전환되지 않는다.
        p.x = g.stage.terminal_position[0]
        key(g, pico2d.SDLK_e)
        g.update(0)
        self.assertEqual(g.stage.circuit, 'A')
        key(g, pico2d.SDLK_e, False)
        tap(g, pico2d.SDLK_e)
        g.update(0)
        self.assertEqual(g.stage.circuit, 'B')
        g.stage.parts['B'] = True
        p.battery = 0
        p.inventory.counts[LIGHT_BOMB] = 0
        g.restart_stage()
        self.assertEqual(g.stage.circuit, 'A')
        self.assertEqual(g.stage.part_count, 0)
        self.assertEqual(p.inventory.counts[LIGHT_BOMB], 1)
        self.assertEqual((p.battery, p.fragments, p.face_dir), (140, 1, -1))
        self.assertEqual((p.x, p.feet_y), g.stage.start)

    def test_hospital_completion_allows_second_upgrade_and_substation_departure(self):
        g = self.g
        self.depart()
        g.update(2)
        g.stage.fixture_powered = g.stage.completed = True
        g.update(0)
        self.assertEqual(g.completed_stage_ids, {'residential', 'hospital'})
        self.assertIn('운하 병원', g.clear_items[1])
        self.assertTrue(g.open_city_map())
        self.assertTrue(g.open_management())
        self.assertIsNone(g.management_visit.chosen_upgrade)
        key(g, pico2d.SDLK_e, False)
        tap(g, pico2d.SDLK_RIGHT)
        tap(g, pico2d.SDLK_e)
        self.assertTrue(g.management_visit.completed)
        self.assertTrue(g.can_depart)
        self.assertTrue(g.depart())
        g.update(2)
        self.assertEqual(g.stage.stage_id, 'substation')
        self.assertEqual(g.player.core_upgrades, {CAPACITY,'focus'})
        self.assertEqual(g.completed_stage_ids, {'residential','hospital'})
        self.assertFalse(any(g.stage.breakers))
        self.assertFalse(g.can_depart)
