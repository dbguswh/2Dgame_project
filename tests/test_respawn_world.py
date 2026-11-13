import unittest
from unittest.mock import Mock, patch

import pico2d

from lighting import PortableLight
from session import GameSession
from projectiles import ShadowBolt


class RespawnWorldTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', return_value=Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = GameSession()
        self.game.start_game()
        self.player = self.game.player
        self.stage = self.game.stage
        self.enemy = self.game.enemies[0]
        self.point = self.stage.respawns.points[0]

    def kill(self):
        self.enemy.take_damage()
        self.enemy.take_damage()
        self.game.update(0)

    def test_actual_roster_is_reused_and_spawn_is_not_an_immediate_attack(self):
        identities = [id(e) for e in self.game.enemies]
        self.kill()
        self.assertEqual(self.point.state, 'WAITING')
        self.game.update(9)
        self.assertEqual(self.point.state, 'WARNING')
        self.game.update(1)
        self.assertEqual(self.enemy.health, 2)
        self.assertEqual(self.enemy.state, 'PATROL')
        self.assertIsNone(self.enemy.consume_attack())
        self.assertEqual(identities, [id(e) for e in self.game.enemies])
        self.assertEqual(len(self.game.enemies), 8)
        self.assertEqual(self.player.fragments, 0)

    def test_repair_in_same_update_as_warning_completion_wins(self):
        self.kill()
        self.game.update(9)
        self.game.update(0.99)
        self.player.x, self.player.feet_y = self.stage.fixture_checkpoint
        self.stage.fuse_state = 'CARRIED'
        self.player.interaction_requested = True
        self.game.update(0.02)
        self.assertTrue(self.stage.fixture_powered)
        self.assertTrue(all(p.state == 'SEALED' for p in self.stage.respawns.points))
        self.assertTrue(all(not e.alive for e in self.game.enemies))
        self.assertEqual(self.point.generation, 0)

    def test_pause_and_focus_loss_freeze_wait_warning_and_effect_clock(self):
        self.kill()
        self.game.update(4)
        for state in ('WAITING', 'WARNING'):
            if state == 'WARNING':
                self.game.update(5)
                self.game.update(0.4)
            snapshot = (self.point.remaining, self.point.warning_elapsed, self.stage.respawns.visual_time)
            self.game.state = 'PAUSED'
            self.game.update(3)
            self.game.state = 'PLAY'
            self.game.update(3, focused=False)
            self.assertEqual(snapshot, (self.point.remaining, self.point.warning_elapsed,
                                        self.stage.respawns.visual_time))

    def test_death_preserves_progress_but_resets_unrepaired_roster_and_spawn_timers(self):
        self.player.battery = 30
        self.kill()
        self.game.update(4)
        self.player.health = 1
        self.game.enemies[1].bolts.append(ShadowBolt.aimed(
            (self.player.x, self.player.feet_y + 40), (self.player.x - 30, self.player.feet_y + 40)))
        self.game.update(0.01)
        self.assertEqual(self.player.respawn_count, 1)
        self.assertEqual(self.player.battery, 30)
        self.assertEqual(self.point.state, 'OCCUPIED')
        self.assertEqual(self.point.remaining, 9)
        self.assertEqual(self.enemy.health, 2)
        self.kill()
        self.game.restart_stage()
        self.assertEqual(self.player.battery, 100)
        self.assertEqual(self.point.state, 'OCCUPIED')
        self.assertEqual(self.point.generation, 0)

    def test_installed_r_freezes_generation_at_original_spawn_not_actor_death_location(self):
        self.enemy.motion.x = 700
        self.kill()
        self.player.light = PortableLight(self.point.x, self.point.feet_y + 24, self.stage.light_regions[0])
        self.game.update(2)
        self.assertEqual(self.point.remaining, 9)
        self.assertFalse(self.enemy.alive)
