import unittest
from unittest.mock import Mock, patch

import pico2d

from inventory import LIGHT_BOMB, MEDKIT, SHIELD, SPEED
from residential import ResidentialStage
from session import GameSession


class SupplyLayoutTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.game = GameSession()
        self.game.start_game()
        self.game.enemies = []
        self.stage, self.player = self.game.stage, self.game.player

    def press_e(self):
        for event_type in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
            event = pico2d.Event(event_type)
            event.key = pico2d.SDLK_e
            self.game.handle_event(event)
        self.game.update(0)

    def test_no_free_entrance_supplies_and_first_heal_follows_ground_encounter(self):
        medkit = self.stage.supply_boxes[0]
        speed = next(b for b in self.stage.supply_boxes if b.item == SPEED)
        crate = next(s for s in self.stage.solids if s.bottom == 96 and not s.one_way)
        self.assertFalse(any(b.x < self.stage.enemy_placements[0].bounds[0]
                             for b in self.stage.supply_boxes))
        self.assertGreater(medkit.x, self.stage.enemy_placements[0].bounds[1])
        self.assertGreater(speed.x, self.stage.approach_ledges[0].right)
        self.assertEqual(speed.feet_y, 96)
        self.assertGreaterEqual(self.stage.enemy_placements[0].bounds[0], crate.right)

    def test_every_supply_has_room_for_box_lid_and_loot_on_same_support(self):
        for box in self.stage.supply_boxes:
            with self.subTest(box=box.identity):
                self.assertTrue(any(s.top == box.feet_y and s.left <= box.x - 34
                                    and s.right >= box.x + 34 for s in self.stage.solids))
                x, y = box.pickup_position
                self.assertGreater(y, box.feet_y)
                self.assertLess(abs(x - box.x), 34)

    def test_heal_on_first_landing_then_bomb_and_later_connector_shield(self):
        shield = next(b for b in self.stage.supply_boxes if b.item == SHIELD)
        bomb = next(b for b in self.stage.supply_boxes if b.item == LIGHT_BOMB)
        first = self.stage.approach_ledges[0]
        self.assertGreaterEqual(first.right - first.left, 128)
        medkit = self.stage.supply_boxes[0]
        self.assertEqual(medkit.feet_y, first.top)
        self.assertGreaterEqual(medkit.x - first.left, 48)
        self.assertGreaterEqual(first.right - medkit.x, 48)
        self.assertGreater(shield.x, self.stage.enemy_placements[4].bounds[1])
        self.assertLess(shield.x, self.stage.enemy_placements[5].bounds[0])
        self.assertEqual(shield.feet_y, self.stage.workshop_ledges[0].top)
        self.assertEqual(bomb.feet_y, self.stage.UPPER_FLOOR_Y)
        self.assertLess(bomb.x, self.stage.enemy_placements[2].bounds[0])

    def test_workshop_reward_stations_are_separated_and_supported(self):
        medkit = self.stage.supply_boxes[1]
        battery, fuse = self.stage.return_battery_position, self.stage.fuse_position
        self.assertEqual(medkit.item, MEDKIT)
        self.assertGreaterEqual(battery[0] - medkit.x, 64)
        self.assertGreaterEqual(fuse[0] - battery[0], 64)
        self.assertEqual(medkit.feet_y,96)
        for x in (battery[0], fuse[0]):
            self.assertTrue(any(s.top == self.stage.WORKSHOP_Y and s.left <= x - 24
                                and s.right >= x + 24 for s in self.stage.solids))

    def test_e_opens_closer_box_without_installing_carried_fuse(self):
        self.stage.fuse_state = 'CARRIED'
        box = self.stage.supply_boxes[2]
        self.player.x, self.player.feet_y = box.x - 24, box.feet_y
        self.assertIn('광탄', self.stage.interaction_prompt(self.player)[2])
        self.press_e()
        self.assertTrue(box.opened)
        self.assertEqual(self.stage.fuse_state, 'CARRIED')
        self.assertFalse(self.stage.fixture_powered)

    def test_e_installs_fuse_when_console_is_closer_than_box(self):
        self.stage.fuse_state = 'CARRIED'
        x, y = self.stage.fixture_position
        self.player.x, self.player.feet_y = x + 24, y
        self.assertIn('퓨즈 설치', self.stage.interaction_prompt(self.player)[2])
        self.press_e()
        self.assertTrue(self.stage.fixture_powered)
        self.assertFalse(self.stage.supply_boxes[2].opened)

    def test_opened_box_does_not_keep_stealing_e_or_hide_console_prompt(self):
        box = self.stage.supply_boxes[2]
        box.open()
        self.stage.fuse_state = 'CARRIED'
        self.player.x, self.player.feet_y = box.x - 24, box.feet_y
        self.assertIsNone(self.stage.nearby_supply(self.player))
        self.assertIn('퓨즈 설치', self.stage.interaction_prompt(self.player)[2])
        self.press_e()
        self.assertTrue(self.stage.fixture_powered)


if __name__ == '__main__':
    unittest.main()
