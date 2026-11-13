from math import cos, sin
import unittest
from unittest.mock import Mock, patch

from player import Player, DRAW_HEIGHT


class AttackVisualTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', side_effect=lambda path: Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = Player(400, 96)

    def test_lean_loads_back_then_snaps_forward_and_mirrors(self):
        self.player._begin_attack(1)
        self.player.attack_elapsed = 0.10
        self.assertGreater(self.player.attack_lean, 0)
        self.player.attack_elapsed = 0.135
        right = self.player.attack_lean
        self.assertLess(right, 0)
        self.player.face_dir = -1
        self.assertAlmostEqual(self.player.attack_lean, -right)

    def test_rotated_sprite_keeps_virtual_feet_and_body_fixed(self):
        self.player._begin_attack(1)
        body = self.player.get_bb()
        for direction in (1, -1):
            for time in (0.08, 0.135, 0.24):
                with self.subTest(direction=direction, time=time):
                    self.player.face_dir = direction
                    self.player.attack_elapsed = time
                    self.player.draw(camera_x=100)
                    args = self.player.attack_image.clip_composite_draw.call_args.args
                    frame = self.player.attack_data['frames'][self.player.attack_frame]
                    _, _, width, height = frame['rect']
                    fx, fy = frame['feet']
                    scale = DRAW_HEIGHT / self.player.attack_data['reference_height']
                    dx, dy = (width / 2 - fx) * scale * direction, (height / 2 - fy) * scale
                    angle, cx, cy = args[4], args[6], args[7]
                    self.assertAlmostEqual(cx - dx * cos(angle) + dy * sin(angle), 300)
                    self.assertAlmostEqual(cy - dx * sin(angle) - dy * cos(angle), 96)
                    self.assertEqual(self.player.get_bb(), body)
