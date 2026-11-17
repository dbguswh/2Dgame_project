import unittest
from unittest.mock import Mock, patch

from physics import Motion, RUN_SPEED
from session import GameSession
from world import update_world


class ResidentialLoopTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.stage, self.player = self.game.stage, self.game.player

    def test_console_discovery_objectives_and_checkpoint_are_restored(self):
        for seal in self.stage.combat_seals:seal.opened=True
        self.stage.sync_combat_seals()
        self.assertIn('중앙 제어함', self.stage.objective)
        self.player.x, self.player.feet_y = self.stage.fixture_position
        update_world(0, self.player, [], self.stage, self.game.records)
        self.assertTrue(self.stage.fixture_seen)
        self.assertIn('정비실 계단 꼭대기', self.stage.objective)
        self.player.x, self.player.feet_y = self.stage.fuse_checkpoint
        update_world(0, self.player, [], self.stage, self.game.records)
        self.assertEqual(self.stage.fuse_state, 'CARRIED')
        self.assertIn('왼쪽 중앙 제어함', self.stage.objective)
        self.game.records.restore_after_death(self.player, self.stage)
        self.assertTrue(self.stage.fixture_seen)
        self.assertEqual((self.player.x, self.player.feet_y), self.stage.fuse_checkpoint)
        self.game.restart_stage()
        self.assertFalse(self.stage.fixture_seen)
        self.assertEqual(self.stage.fuse_state, 'WORLD')

    def test_fuse_must_be_returned_to_central_control_not_bridge(self):
        self.stage.fuse_state = 'CARRIED'
        self.player.x, self.player.feet_y = self.stage.bridge_approach_position
        self.assertFalse(self.stage.activate_fixture(self.player))
        self.assertFalse(self.stage.fixture_powered)
        self.player.x, self.player.feet_y = self.stage.fixture_position
        self.assertTrue(self.stage.activate_fixture(self.player))
        self.assertEqual(self.stage.fuse_state, 'INSTALLED')

    def test_walking_retrieval_loop_allows_killed_roof_guard_to_reappear_on_return(self):
        self.stage.combat_seals[0].opened=True
        self.stage.combat_seals[2].opened=True
        guard = self.game.enemies[2]
        guard.take_damage()
        guard.take_damage()
        guard.take_damage()
        self.stage.update_combat_seals(self.game.enemies)
        self.player.motion = Motion(guard.x, self.stage.UPPER_FLOOR_Y)
        director = self.stage.respawns
        point = director.points[2]
        director.update(0, self.player, self.game.enemies)
        direction = 1
        respawn_phase = None
        for _ in range(3600):
            body = self.player.motion
            left, bottom, right, top = body.get_bb()
            obstacle = any(bottom < s.top and top > s.bottom and
                           (right - .01 <= s.left <= right + 8 if direction > 0
                            else left - 8 <= s.right <= left + .01) for s in self.stage.solids)
            support = any(s.left <= body.x + direction * 28 <= s.right and abs(s.top - bottom) < .01
                          for s in self.stage.solids)
            if body.on_ground and (obstacle or not support):
                body.jump()
            body.step(1 / 120, direction, self.stage.solids, self.stage.width)
            self.stage.collect_pickups(self.player)
            director.update(1 / 120, self.player, self.game.enemies)
            if point.generation and respawn_phase is None:
                respawn_phase = direction
            if self.stage.fuse_state == 'CARRIED':
                direction = -1
            if direction < 0 and body.x <= self.stage.fixture_position[0]:
                break
        self.assertEqual(self.stage.fuse_state, 'CARRIED')
        self.assertEqual(respawn_phase, -1)
        self.assertTrue(guard.alive)
        self.assertTrue(self.stage.activate_fixture(self.player))

    def test_higher_workshop_does_not_allow_unpowered_canal_bypass(self):
        body = Motion(self.stage.canal[0] - 1, self.stage.WORKSHOP_Y)
        body.jump()
        while body.feet_y > -100:
            body.step(1 / 120, 1, self.stage.solids, self.stage.width, speed=RUN_SPEED * 1.3)
            self.assertFalse(body.on_ground and body.x >= self.stage.canal[1])
