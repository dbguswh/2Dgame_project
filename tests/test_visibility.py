import unittest
from unittest.mock import Mock, patch

from lighting import LightRegion, PortableLight
from player import Player
from stage import Stage
from visibility import DARK_ALPHA, DarknessField, build_field, restoration_progress


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stage = Stage()
        self.player = Player(400, 96)

    def test_lantern_reveals_nearby_but_distant_world_stays_dark(self):
        field = build_field(self.stage, self.player, 0)
        self.assertLess(field.sample(416, 136), 90)
        self.assertEqual(field.sample(850, 350), DARK_ALPHA)
        self.assertEqual(self.player.battery, 100)
        self.assertIsNone(self.player.light)

    def test_fixed_r_light_is_brighter_and_vanishes_at_expiry(self):
        self.player.light = PortableLight(700, 120, self.stage.light_regions[0], remaining=7)
        field = build_field(self.stage, self.player, 0)
        self.assertLess(field.sample(700, 120), 12)
        self.assertEqual(field.sample(780, 120), DARK_ALPHA)
        self.player.light.update(7)
        self.assertEqual(build_field(self.stage, self.player, 0).sample(700, 120), DARK_ALPHA)

    def test_r_reveal_does_not_cross_light_region(self):
        self.player.light = PortableLight(700, 120, LightRegion(680, 96, 712, 540), remaining=7)
        field = build_field(self.stage, self.player, 0)
        self.assertLess(field.sample(700, 120), 12)
        self.assertEqual(field.sample(724, 120), DARK_ALPHA)

    def test_camera_moves_world_light_and_lantern_together(self):
        self.player.light = PortableLight(700, 120, self.stage.light_regions[0], remaining=7)
        first, shifted = build_field(self.stage, self.player, 0), build_field(self.stage, self.player, 80)
        self.assertEqual(first.sample(416, 136), shifted.sample(336, 136))
        self.assertEqual(first.sample(700, 120), shifted.sample(620, 120))

    def test_permanent_restoration_fades_whole_world_without_new_timer(self):
        self.stage.BRIDGE_TIME = 2.4
        self.stage.fixture_powered = True
        values = []
        for elapsed in (0, 0.6, 1.2, 2.4):
            self.stage.bridge_elapsed = elapsed
            values.append(build_field(self.stage, self.player, 0).sample(850, 350))
        self.assertEqual(values, [218, 109, 0, 0])
        self.stage.fixture_powered = False
        self.assertEqual(restoration_progress(self.stage), 0)

    def test_overlapping_sources_do_not_turn_weak_lantern_into_safe_light(self):
        field = DarknessField(960, 540)
        field.reveal(400, 140, 144, 136, 0.68)
        alpha = field.sample(400, 140)
        field.reveal(400, 140, 144, 136, 0.68)
        self.assertEqual(field.sample(400, 140), alpha)
        self.assertGreater(alpha, 60)

    def test_upload_has_sdl_top_origin_and_exact_buffer_dimensions(self):
        field = DarknessField(960, 540)
        field.reveal(4, 4, 20, 20, 1)
        pixels = field.rgba()
        self.assertEqual(len(pixels), field.cols * field.rows * 4)
        self.assertEqual(pixels[3], DARK_ALPHA)
        self.assertEqual(pixels[(field.rows - 1) * field.cols * 4 + 3], 0)
