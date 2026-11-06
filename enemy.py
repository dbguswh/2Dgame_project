"""Shade의 위치·이미지와 전투 상태를 관리한다."""

from pathlib import Path

import pico2d

from physics import EPSILON, Motion
from combat import front_box, overlaps


IMAGE_PATH = Path(__file__).resolve().parent / 'assets/images/characters/shade.png'
DRAW_HEIGHT = 104
BODY_WIDTH = 36
BODY_HEIGHT = 88


class Shade:
    def __init__(self, x, feet_y, identity=0, combat_bounds=(288, 544)):
        self.identity = identity
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.image = pico2d.load_image(str(IMAGE_PATH))
        self.face_dir = -1
        self.health = 2
        self.spawn_position = (x, feet_y)
        self.combat_bounds = combat_bounds
        self.patrol_bounds = (x - 28, x + 16)
        self.state = 'PATROL'
        self.is_moving = False
        self.walk_distance = 0.0
        self.solids = []

    @property
    def x(self):
        return self.motion.x

    @property
    def feet_y(self):
        return self.motion.feet_y

    @property
    def alive(self):
        return self.health > 0

    def get_bb(self):
        return self.motion.get_bb()

    def can_see(self, player):
        if not self.combat_bounds[0] <= player.x <= self.combat_bounds[1]:
            return False
        if abs(player.x - self.x) > 192 or abs(player.feet_y - self.feet_y) > 48:
            return False
        line_y = min(self.feet_y + BODY_HEIGHT / 2, player.feet_y + 46)
        left, right = sorted((self.x, player.x))
        return not any(s.left < right and s.right > left and s.bottom < line_y < s.top
                       for s in self.solids)

    def _reach_box(self):
        # 몸이 겹쳐도 앞쪽 팔의 타격에는 맞는다. 몸 접촉 자체로는 피해를 주지 않는다.
        return front_box(self.x, self.face_dir, -4, BODY_WIDTH / 2 + 32,
                         self.feet_y + 10, self.feet_y + 58, self.solids)

    def _move(self, delta_time, direction, speed, stage):
        old_x = self.x
        probe = self.x + direction * (BODY_WIDTH / 2 + 2 + speed * delta_time)
        has_floor = any(s.left <= probe <= s.right and abs(s.top - self.feet_y) < EPSILON
                        for s in self.solids)
        next_x = self.x + direction * speed * delta_time
        inside = (self.combat_bounds[0] + BODY_WIDTH / 2 <= next_x
                  <= self.combat_bounds[1] - BODY_WIDTH / 2)
        if not has_floor or not inside:
            direction = 0
        self.motion.step(delta_time, direction, self.solids, stage.width,
                         edge_margin=BODY_WIDTH / 2, speed=speed)
        distance = abs(self.x - old_x)
        self.is_moving = distance > EPSILON
        self.walk_distance += distance
        return self.is_moving

    def update(self, delta_time, player, stage):
        self.solids = stage.solids
        if self.can_see(player):
            self.state = 'CHASE'
            if abs(player.x - self.x) > 1:
                self.face_dir = 1 if player.x > self.x else -1
            direction = 0 if overlaps(self._reach_box(), player.get_bb()) else self.face_dir
            self._move(delta_time, direction, 80, stage)
        else:
            self.state = 'PATROL'
            if self.x <= self.patrol_bounds[0]:
                self.face_dir = 1
            elif self.x >= self.patrol_bounds[1]:
                self.face_dir = -1
            if not self._move(delta_time, self.face_dir, 48, stage):
                self.face_dir *= -1

    def draw(self, camera_x=0):
        scale = DRAW_HEIGHT / 1101
        # 기본 이미지는 왼쪽을 본다. 긴 팔을 제외하고 양발 기준으로 정렬한다.
        self.image.clip_composite_draw(
            103, 12, 1265, 1101, 0, 'h' if self.face_dir > 0 else '',
            self.x - camera_x + (1265 / 2 - 803) * scale * -self.face_dir,
            self.feet_y + DRAW_HEIGHT / 2, 1265 * scale, DRAW_HEIGHT,
        )
        for index in range(2):
            left = self.x - camera_x - 12 + index * 13
            color = (202, 91, 214) if index < self.health else (69, 57, 78)
            pico2d.draw_rectangle(left, self.feet_y + 112, left + 10,
                                  self.feet_y + 116, *color, filled=True)

    def draw_debug(self, camera_x=0):
        left, bottom, right, top = self.get_bb()
        pico2d.draw_rectangle(left - camera_x, bottom, right - camera_x, top,
                              r=195, g=119, b=230)
