import unittest

from lighting import LightRegion, PortableLight, find_region, constrain_region
from physics import Solid


class LightingTests(unittest.TestCase):
    def setUp(self):
        self.region = LightRegion(0, 96, 960, 540)
        self.light = PortableLight(160, 120, self.region)

    def test_range_uses_circle_and_body_overlap(self):
        self.assertTrue(self.light.illuminates((200, 96, 224, 184)))
        self.assertTrue(self.light.illuminates((320, 120, 336, 170)))
        self.assertFalse(self.light.illuminates((320, 184, 336, 200)))
        self.assertFalse(self.light.illuminates((321, 120, 336, 170)))

    def test_wall_separated_room_is_not_illuminated(self):
        light = PortableLight(140, 120, LightRegion(0, 96, 150, 540))
        self.assertTrue(light.illuminates((130, 100, 145, 180)))
        self.assertFalse(light.illuminates((160, 100, 180, 180)))

    def test_expiry_and_range_end_together(self):
        self.light.update(11.9)
        self.assertTrue(self.light.active)
        self.light.update(0.1 + 0.000001)
        self.assertEqual(self.light.remaining, 0)
        self.assertFalse(self.light.active)
        self.assertFalse(self.light.illuminates((150, 96, 174, 188)))

    def test_zero_elapsed_time_freezes_light(self):
        self.light.update(0)
        self.assertEqual(self.light.remaining, 12)

    def test_twelve_seconds_expires_at_different_frame_rates(self):
        for fps in (30, 60, 144):
            light = PortableLight(160, 120, self.region)
            for _ in range(12 * fps):
                light.update(1 / fps)
            self.assertFalse(light.active, fps)

    def test_outside_room_has_no_installation_region(self):
        self.assertIs(find_region([self.region], 160, 120), self.region)
        self.assertIsNone(find_region([self.region], 160, 70))

    def test_install_region_stops_at_wall_and_ceiling(self):
        room = constrain_region(self.region, 400, 120,
                                [Solid(480, 96, 496, 300), Solid(320, 224, 512, 240)])
        light = PortableLight(400, 120, room)
        self.assertTrue(light.illuminates((440, 96, 464, 184)))
        self.assertFalse(light.illuminates((500, 96, 524, 184)))
        self.assertFalse(light.illuminates((400, 240, 424, 328)))

    def test_upper_floor_light_does_not_pass_through_supporting_floor(self):
        room = constrain_region(self.region, 400, 312, [Solid(320, 268, 512, 288)])
        light = PortableLight(400, 312, room)
        self.assertTrue(light.illuminates((440, 288, 464, 376)))
        self.assertFalse(light.illuminates((400, 96, 424, 184)))


if __name__ == '__main__':
    unittest.main()
