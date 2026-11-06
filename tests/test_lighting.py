import unittest

from lighting import LightRegion, PortableLight, find_region


class LightingTests(unittest.TestCase):
    def setUp(self):
        self.region = LightRegion(0, 96, 960, 540)
        self.light = PortableLight(160, 120, self.region)

    def test_range_uses_circle_and_body_overlap(self):
        self.assertTrue(self.light.illuminates((200, 96, 224, 184)))
        self.assertTrue(self.light.illuminates((224, 120, 240, 170)))
        self.assertFalse(self.light.illuminates((224, 184, 240, 200)))
        self.assertFalse(self.light.illuminates((225, 120, 240, 170)))

    def test_wall_separated_room_is_not_illuminated(self):
        light = PortableLight(140, 120, LightRegion(0, 96, 150, 540))
        self.assertTrue(light.illuminates((130, 100, 145, 180)))
        self.assertFalse(light.illuminates((160, 100, 180, 180)))

    def test_expiry_and_range_end_together(self):
        self.light.update(7.9)
        self.assertTrue(self.light.active)
        self.light.update(0.1 + 0.000001)
        self.assertEqual(self.light.remaining, 0)
        self.assertFalse(self.light.active)
        self.assertFalse(self.light.illuminates((150, 96, 174, 188)))

    def test_zero_elapsed_time_freezes_light(self):
        self.light.update(0)
        self.assertEqual(self.light.remaining, 8)

    def test_eight_seconds_expires_at_different_frame_rates(self):
        for fps in (30, 60, 144):
            light = PortableLight(160, 120, self.region)
            for _ in range(8 * fps):
                light.update(1 / fps)
            self.assertFalse(light.active, fps)

    def test_outside_room_has_no_installation_region(self):
        self.assertIs(find_region([self.region], 160, 120), self.region)
        self.assertIsNone(find_region([self.region], 160, 70))


if __name__ == '__main__':
    unittest.main()
