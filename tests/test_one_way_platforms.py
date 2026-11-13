import unittest

from physics import Motion, Solid


class OneWayPlatformTests(unittest.TestCase):
    def test_jump_from_underneath_lands_on_top_at_different_frame_rates(self):
        solids = [Solid(0, 0, 960, 96), Solid(320, 128, 448, 144, one_way=True)]
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                body = Motion(384, 96)
                body.jump()
                for _ in range(fps):
                    body.step(1 / fps, 0, solids, 960)
                self.assertEqual(body.feet_y, 144)
                self.assertTrue(body.on_ground)

    def test_walking_below_platform_does_not_hit_its_side(self):
        solids = [Solid(0, 0, 960, 96), Solid(320, 128, 448, 144, one_way=True)]
        for direction, start, end in ((1, 280, 536), (-1, 536, 280)):
            body = Motion(start, 96)
            for _ in range(240):
                body.step(1 / 120, direction, solids, 960)
            self.assertAlmostEqual(body.x, end)
            self.assertEqual(body.feet_y, 96)

    def test_jump_not_reaching_platform_top_does_not_snap_up(self):
        solids = [Solid(0, 0, 960, 96), Solid(320, 176, 448, 192, one_way=True)]
        body = Motion(384, 96)
        body.jump()
        for _ in range(120):
            body.step(1 / 120, 0, solids, 960)
        self.assertEqual(body.feet_y, 96)

    def test_regular_ceiling_and_wall_remain_solid(self):
        solids = [Solid(0, 0, 960, 96), Solid(320, 200, 448, 216), Solid(500, 96, 516, 400)]
        body = Motion(384, 96)
        body.jump()
        highest = 96
        for _ in range(240):
            body.step(1 / 120, 1, solids, 960)
            highest = max(highest, body.feet_y)
        self.assertLessEqual(highest, 108)
        self.assertEqual(body.x, 488)
