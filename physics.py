"""이미지와 독립적으로 이동·점프·지형 충돌을 계산한다."""

from dataclasses import dataclass
from math import sqrt


MOVE_SPEED = 128
GRAVITY = 1024
JUMP_HEIGHT = 64
JUMP_SPEED = sqrt(2 * GRAVITY * JUMP_HEIGHT)
MAX_FALL_SPEED = 512
EPSILON = 0.00001


@dataclass(frozen=True)
class Solid:
    left: float
    bottom: float
    right: float
    top: float


@dataclass
class Motion:
    x: float
    feet_y: float
    width: float = 24
    height: float = 80
    velocity_y: float = 0
    on_ground: bool = True

    def get_bb(self):
        return (self.x - self.width / 2, self.feet_y,
                self.x + self.width / 2, self.feet_y + self.height)

    def jump(self):
        if not self.on_ground:
            return False
        self.velocity_y = JUMP_SPEED
        self.on_ground = False
        return True

    def step(self, delta_time, direction, solids, area_width, edge_margin=12):
        # 작은 간격으로 분할해 낮은 프레임에서도 얇은 발판을 건너뛰지 않는다.
        remaining = max(0.0, min(delta_time, 0.1))
        while remaining > EPSILON:
            dt = min(remaining, 1 / 120)
            self._move_x(direction * MOVE_SPEED * dt, solids, area_width, edge_margin)
            next_velocity = max(-MAX_FALL_SPEED, self.velocity_y - GRAVITY * dt)
            dy = (self.velocity_y + next_velocity) * dt / 2
            self.velocity_y = next_velocity
            self._move_y(dy, solids)
            remaining -= dt

    def _move_x(self, dx, solids, area_width, edge_margin):
        old_left, bottom, old_right, top = self.get_bb()
        self.x += dx
        for solid in solids:
            if bottom >= solid.top - EPSILON or top <= solid.bottom + EPSILON:
                continue
            if dx > 0 and old_right <= solid.left + EPSILON:
                if self.x + self.width / 2 > solid.left:
                    self.x = solid.left - self.width / 2
            elif dx < 0 and old_left >= solid.right - EPSILON:
                if self.x - self.width / 2 < solid.right:
                    self.x = solid.right + self.width / 2
        margin = max(self.width / 2, edge_margin)
        self.x = max(margin, min(area_width - margin, self.x))

    def _move_y(self, dy, solids):
        left, old_bottom, right, old_top = self.get_bb()
        self.feet_y += dy
        self.on_ground = False
        for solid in solids:
            if right <= solid.left + EPSILON or left >= solid.right - EPSILON:
                continue
            if dy <= 0 and old_bottom >= solid.top - EPSILON:
                if self.feet_y <= solid.top:
                    self.feet_y = solid.top
                    self.velocity_y = 0
                    self.on_ground = True
            elif dy > 0 and old_top <= solid.bottom + EPSILON:
                if self.feet_y + self.height >= solid.bottom:
                    self.feet_y = solid.bottom - self.height
                    self.velocity_y = 0


def camera_offset(player_x, stage_width, screen_width):
    return max(0.0, min(stage_width - screen_width, player_x - screen_width / 2))
