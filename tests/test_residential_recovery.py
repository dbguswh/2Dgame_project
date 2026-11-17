import unittest

from physics import Motion
from residential import ResidentialStage


class ResidentialRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.stage = ResidentialStage()

    def walk_to(self, body, target):
        for _ in range(1800):
            if abs(target - body.x) <= 1.1:
                return
            body.step(1 / 120, 1 if target > body.x else -1, self.stage.solids, self.stage.width)
        self.fail(f'복귀 이동 막힘: {body.x}, {body.feet_y} -> {target}')

    def jump_to(self, body, target_x, target_y):
        self.assertTrue(body.jump())
        for _ in range(150):
            direction = 0 if abs(target_x - body.x) < 1.1 else 1 if target_x > body.x else -1
            body.step(1 / 120, direction, self.stage.solids, self.stage.width)
            if body.on_ground:
                break
        self.assertAlmostEqual(body.feet_y, target_y, msg=f'x={body.x}')
        self.assertTrue(body.on_ground)

    def test_ground_below_ascent_and_roof_can_return_to_first_ledge(self):
        for x in (800, 880, 1008, 1136, 1400, 1800):
            with self.subTest(x=x):
                body = Motion(x, 96)
                self.walk_to(body, 800)
                self.jump_to(body, 800, 144)
                self.walk_to(body, 844)
                self.jump_to(body, 904, 192)
                self.walk_to(body, 972)
                self.jump_to(body, 1040, 240)
                self.walk_to(body, 1100)
                self.jump_to(body, 1160, 288)

    def test_ground_below_bridge_controls_has_return_steps(self):
        body = Motion(2224, 96)
        self.jump_to(body, 2256, 144)
        self.walk_to(body, 2270)
        self.jump_to(body, 2328, 192)
        self.jump_to(body, 2328, self.stage.BRIDGE_Y)

    def test_far_shore_ground_can_return_to_exit_level(self):
        body = Motion(2792, 96)
        self.jump_to(body, 2792, 144)
        self.walk_to(body, 2800)
        self.jump_to(body, 2856, 192)
        self.jump_to(body, 2856, self.stage.BRIDGE_Y)

    def test_bridge_recovery_cannot_jump_back_into_locked_workshop_route(self):
        body = Motion(*self.stage.bridge_approach_position)
        body.jump()
        peak = body.feet_y
        for _ in range(300):
            body.step(1 / 120, -1, self.stage.solids, self.stage.width)
            peak = max(peak, body.feet_y)
        self.assertLess(peak, self.stage.FUSE_PEAK_Y)
