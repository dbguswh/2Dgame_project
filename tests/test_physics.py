import unittest

from physics import Motion, Solid, camera_offset


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.floor = [Solid(0, 0, 1920, 96)]

    def test_jump_height_and_landing_at_different_frame_rates(self):
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                body = Motion(160, 96)
                self.assertTrue(body.jump())
                highest = body.feet_y
                for _ in range(fps):
                    body.step(1 / fps, 0, self.floor, 1920)
                    highest = max(highest, body.feet_y)
                self.assertAlmostEqual(highest - 96, 64, delta=0.12)
                self.assertEqual(body.feet_y, 96)
                self.assertTrue(body.on_ground)

    def test_cannot_jump_again_until_landing(self):
        body = Motion(160, 96)
        self.assertTrue(body.jump())
        body.step(0.05, 0, self.floor, 1920)
        velocity = body.velocity_y
        self.assertFalse(body.jump())
        self.assertEqual(body.velocity_y, velocity)
        for _ in range(60):
            body.step(1 / 60, 0, self.floor, 1920)
        self.assertTrue(body.jump())

    def test_can_change_horizontal_direction_in_air(self):
        body = Motion(160, 96)
        body.jump()
        body.step(0.1, 1, self.floor, 1920)
        self.assertAlmostEqual(body.x, 172.8)
        body.step(0.1, -1, self.floor, 1920)
        self.assertAlmostEqual(body.x, 160)
        self.assertFalse(body.on_ground)

    def test_wall_stops_body_from_both_sides(self):
        wall = self.floor + [Solid(200, 96, 232, 240)]
        body = Motion(180, 96)
        body.step(0.1, 1, wall, 1920)
        self.assertEqual(body.get_bb()[2], 200)
        body = Motion(250, 96)
        body.step(0.1, -1, wall, 1920)
        self.assertEqual(body.get_bb()[0], 232)

    def test_ceiling_cancels_upward_velocity(self):
        ceiling = self.floor + [Solid(100, 208, 200, 224)]
        body = Motion(160, 96)
        body.jump()
        highest = 96
        for _ in range(20):
            body.step(1 / 60, 0, ceiling, 1920)
            highest = max(highest, body.feet_y)
        self.assertLessEqual(highest + body.height, 208.00001)
        self.assertLessEqual(body.velocity_y, 0)

    def test_falling_lands_on_highest_platform(self):
        solids = self.floor + [Solid(100, 112, 200, 128)]
        body = Motion(160, 220, on_ground=False)
        for _ in range(60):
            body.step(1 / 60, 0, solids, 1920)
        self.assertEqual(body.feet_y, 128)
        self.assertTrue(body.on_ground)

    def test_fast_fall_cannot_pass_thin_platform(self):
        body = Motion(160, 120, velocity_y=-512, on_ground=False)
        body.step(0.05, 0, [Solid(100, 96, 200, 104)], 1920)
        self.assertEqual(body.feet_y, 104)
        self.assertTrue(body.on_ground)

    def test_walking_off_an_edge_starts_falling(self):
        body = Motion(112, 96)
        body.step(0.1, 1, [Solid(0, 0, 112, 96)], 1920)
        self.assertFalse(body.on_ground)
        self.assertLess(body.feet_y, 96)

    def test_camera_stops_at_both_map_edges(self):
        self.assertEqual(camera_offset(160, 1920, 960), 0)
        self.assertEqual(camera_offset(960, 1920, 960), 480)
        self.assertEqual(camera_offset(1880, 1920, 960), 960)


if __name__ == '__main__':
    unittest.main()
