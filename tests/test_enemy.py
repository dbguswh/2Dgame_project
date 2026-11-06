import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from enemy import Shade
from physics import Solid
from player import Player
from stage import Stage


class ShadeTests(unittest.TestCase):
    def setUp(self):
        image_patch = patch('pico2d.load_image', return_value=Mock())
        image_patch.start()
        self.addCleanup(image_patch.stop)
        self.stage = Stage()
        self.player = Player(*self.stage.start)
        self.enemy = Shade(*self.stage.enemy_spawn)

    def test_unseen_player_causes_patrol_at_48_pixels_per_second(self):
        self.enemy.update(1 / 60, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'PATROL')
        self.assertAlmostEqual(self.enemy.x, 440 - 48 / 60)

    def test_seen_player_causes_chase_at_80_pixels_per_second(self):
        self.player.x = 300
        self.enemy.update(1 / 60, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'CHASE')
        self.assertAlmostEqual(self.enemy.x, 440 - 80 / 60)

    def test_player_outside_section_or_on_other_floor_is_not_chased(self):
        self.player.x = 550
        self.enemy.update(1 / 60, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'PATROL')
        self.player.x, self.player.feet_y = 440, 250
        self.enemy.update(1 / 60, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'PATROL')

    def test_chase_does_not_pass_wall(self):
        self.player.x = 300
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, self.stage)
        self.assertGreaterEqual(self.enemy.get_bb()[0], 384)
        self.assertEqual(self.enemy.feet_y, 96)

    def test_patrol_turns_before_a_ledge(self):
        stage = SimpleNamespace(width=960, solids=[Solid(0, 0, 450, 96)])
        self.enemy = Shade(420, 96, combat_bounds=(0, 960))
        self.enemy.patrol_bounds = (100, 800)
        self.enemy.face_dir = 1
        self.player.x = 850
        for _ in range(120):
            self.enemy.update(1 / 60, self.player, stage)
            self.assertEqual(self.enemy.feet_y, 96)
            self.assertLess(self.enemy.get_bb()[2], 450)

    def test_body_overlap_has_no_contact_damage(self):
        self.player.x = self.enemy.x
        self.enemy.update(0.05, self.player, self.stage)
        self.assertEqual(self.player.health, 3)

    def test_attack_requires_warning_and_emits_only_one_event(self):
        self.player.x = 410
        self.enemy.update(0.01, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'WINDUP')
        for _ in range(40):
            self.enemy.update(1 / 60, self.player, self.stage)
            self.assertIsNone(self.enemy.consume_attack())
        self.enemy.update(0.04, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'STRIKE')
        self.assertIsNotNone(self.enemy.consume_attack())
        self.assertIsNone(self.enemy.consume_attack())
        self.enemy.update(0.01, self.player, self.stage)
        self.assertIsNone(self.enemy.consume_attack())

    def test_jumping_above_attack_causes_miss(self):
        self.player.x = 410
        self.enemy.update(0.01, self.player, self.stage)
        self.player.feet_y = 160
        self.enemy.update(0.71, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'CHASE')
        self.assertIsNone(self.enemy.consume_attack())

    def test_cannot_instantly_turn_attack_during_warning(self):
        self.player.x = 410
        self.enemy.update(0.01, self.player, self.stage)
        self.player.x = 470
        self.enemy.update(0.71, self.player, self.stage)
        self.assertEqual(self.enemy.face_dir, -1)
        self.assertIsNone(self.enemy.consume_attack())

    def test_leaving_section_cancels_warning(self):
        self.player.x = 410
        self.enemy.update(0.01, self.player, self.stage)
        self.player.x = 800
        self.enemy.update(0.1, self.player, self.stage)
        self.assertEqual(self.enemy.state, 'PATROL')
        self.assertIsNone(self.enemy.consume_attack())


if __name__ == '__main__':
    unittest.main()
