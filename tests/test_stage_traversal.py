import unittest
from unittest.mock import Mock, patch

import pico2d

from player import Player
from stage import Stage


def key(player, value, down=True):
    event = pico2d.Event(pico2d.SDL_KEYDOWN if down else pico2d.SDL_KEYUP)
    event.key = value
    player.handle_event(event)


class StageTraversalTests(unittest.TestCase):
    @patch('pico2d.load_image', return_value=Mock())
    def test_stairs_and_gap_are_reachable_with_basic_jump(self, _):
        stage = Stage()
        player = Player(*stage.start)
        key(player, pico2d.SDLK_RIGHT)
        for _ in range(1200):
            left, bottom, right, top = player.get_bb()
            obstacle_ahead = any(
                bottom < s.top and top > s.bottom and right - 0.01 <= s.left <= right + 8
                for s in stage.solids
            )
            support_ahead = any(
                s.left <= player.x + 32 <= s.right and abs(s.top - bottom) < 0.01
                for s in stage.solids
            )
            if player.motion.on_ground and (obstacle_ahead or not support_ahead):
                key(player, pico2d.SDLK_SPACE, False)
                key(player, pico2d.SDLK_SPACE)
            player.update(1 / 60, stage.width, stage.solids)
            safe = stage.safe_position(player.motion)
            if safe is not None:
                player.last_safe_position = safe
            self.assertEqual(player.health, 3, '필수 경로에서 낙하 피해 발생')
            if player.x > 1800:
                return
        self.fail(f'구간을 통과하지 못함: x={player.x}, y={player.feet_y}')

    def test_safe_position_does_not_update_in_air_or_at_ledge(self):
        from physics import Motion
        stage = Stage()
        self.assertIsNone(stage.safe_position(Motion(955, 96)))
        self.assertIsNone(stage.safe_position(Motion(400, 160, on_ground=False)))
        self.assertEqual(stage.safe_position(Motion(400, 96)), (400, 96))


if __name__ == '__main__':
    unittest.main()
