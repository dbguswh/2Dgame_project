import unittest
from types import SimpleNamespace

from lighting import LightRegion, PortableLight
from respawn import RespawnDirector


class FakeEnemy:
    def __init__(self, identity):
        self.identity, self.alive, self.resets = identity, True, 0

    def reset(self):
        self.alive = True
        self.resets += 1


class RespawnTests(unittest.TestCase):
    def setUp(self):
        self.director = RespawnDirector([SimpleNamespace(identity='a', x=500, feet_y=96)])
        self.enemy = FakeEnemy('a')
        self.player = SimpleNamespace(x=200, feet_y=96, light=None)
        self.point = self.director.points[0]

    def tick(self, dt, powered=False):
        self.director.update(dt, self.player, [self.enemy], powered)

    def kill(self):
        self.enemy.alive = False
        self.tick(0.1)

    def test_alive_actor_walking_away_never_vacates_its_slot(self):
        for _ in range(30):
            self.tick(1)
        self.assertEqual(self.enemy.resets, 0)
        self.assertEqual(self.point.state, 'OCCUPIED')

    def test_event_warning_runs_full_countdown_then_returns_to_normal_cycle(self):
        self.kill()
        self.director.arm_warning(['a'],4)
        self.tick(3.99)
        self.assertFalse(self.enemy.alive)
        self.assertEqual(self.point.state,'WARNING')
        self.tick(.01)
        self.assertTrue(self.enemy.alive)
        self.assertEqual(self.point.warning_duration,1)
        self.kill()
        self.tick(9)
        self.tick(.99)
        self.assertFalse(self.enemy.alive)
        self.tick(.01)
        self.assertTrue(self.enemy.alive)

    def test_event_warning_cannot_spawn_under_light_or_next_to_player(self):
        self.kill()
        self.director.arm_warning(['a'],4)
        self.player.x=450
        self.tick(5)
        self.assertFalse(self.enemy.alive)
        self.assertEqual(self.point.state,'WAITING')
        self.player.x=200
        self.player.light=PortableLight(500,120,LightRegion(0,96,960,540))
        self.tick(5)
        self.assertFalse(self.enemy.alive)
        self.player.light=None
        self.tick(0)
        self.tick(3.99)
        self.assertFalse(self.enemy.alive)
        self.tick(.01)
        self.assertTrue(self.enemy.alive)

    def test_event_warning_ignores_living_and_sealed_slots_and_reset_clears_duration(self):
        self.tick(0)
        self.director.arm_warning(['a'],4)
        self.assertEqual(self.point.state,'OCCUPIED')
        self.kill()
        self.director.arm_warning(['a'],4)
        self.director.reset(powered=True)
        self.director.arm_warning(['a'],4)
        self.assertEqual(self.point.state,'SEALED')
        self.assertEqual(self.point.warning_duration,1)

    def test_full_nine_second_wait_then_full_one_second_warning(self):
        self.kill()
        self.assertEqual(self.point.remaining, 9)
        self.tick(8.99)
        self.assertEqual(self.point.state, 'WAITING')
        self.tick(0.01)
        self.assertEqual(self.point.state, 'WARNING')
        self.tick(0.99)
        self.assertFalse(self.enemy.alive)
        self.tick(0.01)
        self.assertTrue(self.enemy.alive)
        self.assertEqual(self.enemy.resets, 1)
        self.assertEqual(self.point.generation, 1)

    def test_r_freezes_remaining_wait_and_resumes_after_expiry(self):
        self.kill()
        self.tick(4)
        light = PortableLight(500, 120, LightRegion(0, 96, 960, 540))
        self.player.light = light
        self.tick(20)
        self.assertEqual(self.point.remaining, 5)
        light.remaining = 0
        self.tick(4.99)
        self.assertEqual(self.point.state, 'WAITING')
        self.tick(0.01)
        self.assertEqual(self.point.state, 'WARNING')

    def test_nearby_player_holds_warning_at_exact_safety_boundary(self):
        self.kill()
        self.player.x = 500 - 127.9
        self.tick(9)
        self.assertEqual(self.point.state, 'WAITING')
        self.assertEqual(self.point.remaining, 0)
        self.player.x = 500 - 128
        self.tick(0)
        self.assertEqual(self.point.state, 'WARNING')

    def test_light_or_proximity_cancels_warning_and_restarts_full_duration(self):
        for reason in ('light', 'near'):
            with self.subTest(reason=reason):
                self.setUp()
                self.kill()
                self.tick(9)
                self.tick(0.9)
                if reason == 'light':
                    self.player.light = PortableLight(500, 120, LightRegion(0, 96, 960, 540))
                else:
                    self.player.x = 500
                self.tick(0.1)
                self.assertFalse(self.enemy.alive)
                self.assertEqual(self.point.warning_elapsed, 0)
                self.player.x, self.player.light = 200, None
                self.tick(0)
                self.tick(0.9)
                self.assertFalse(self.enemy.alive)
                self.tick(0.1)
                self.assertTrue(self.enemy.alive)

    def test_repair_cancels_warning_and_permanently_seals_slot(self):
        self.kill()
        self.tick(9)
        self.tick(0.99)
        self.tick(1, powered=True)
        self.assertEqual(self.point.state, 'SEALED')
        self.tick(100)
        self.assertEqual(self.enemy.resets, 0)

    def test_light_in_different_region_does_not_stop_wait(self):
        self.kill()
        self.player.light = PortableLight(450, 120, LightRegion(0, 96, 460, 540))
        self.tick(9)
        self.assertEqual(self.point.state, 'WARNING')

    def test_reset_restores_initial_slots_or_sealed_slots(self):
        self.kill()
        self.tick(4)
        self.director.reset()
        self.assertEqual(self.point.state, 'OCCUPIED')
        self.assertEqual(self.point.remaining, 9)
        self.director.reset(powered=True)
        self.assertEqual(self.point.state, 'SEALED')

    def test_zero_time_never_advances_warning(self):
        self.kill()
        self.tick(9)
        self.tick(0.4)
        for _ in range(100):
            self.tick(0)
        self.assertEqual(self.point.warning_elapsed, 0.4)
        self.assertFalse(self.enemy.alive)

    def test_respawn_timing_is_consistent_at_different_frame_rates(self):
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                self.setUp()
                self.kill()
                for _ in range(9 * fps):
                    self.tick(1 / fps)
                self.assertEqual(self.point.state, 'WARNING')
                for _ in range(fps - 1):
                    self.tick(1 / fps)
                self.assertFalse(self.enemy.alive)
                self.tick(1 / fps)
                self.assertTrue(self.enemy.alive)

    def test_repeated_replacement_never_grows_actor_list_or_slot_count(self):
        for _ in range(10):
            self.kill()
            self.tick(9)
            self.tick(1)
        self.assertEqual(len(self.director.points), 1)
        self.assertEqual(self.point.generation, 10)
        self.assertEqual(self.enemy.resets, 10)
