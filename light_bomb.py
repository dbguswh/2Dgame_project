"""0.5초 동안 96px를 날아가 반경 48px에 한 번 타격하는 광탄."""

from dataclasses import dataclass, field
from math import ceil, cos, hypot, pi, sin

from combat import overlaps


FUSE_TIME = 0.5
THROW_SPEED = 96 / FUSE_TIME
BLAST_RADIUS = 48
EXPLOSION_TIME = 0.32


def blocked_segment(start, end, solids):
    distance = hypot(end[0] - start[0], end[1] - start[1])
    steps = max(1, ceil(distance / 2))
    for index in range(1, steps + 1):
        t = index / steps
        x, y = start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t
        if any(s.left < x < s.right and s.bottom < y < s.top for s in solids):
            return True
    return False


@dataclass
class LightBomb:
    x: float
    y: float
    direction: int
    age: float = 0.0
    velocity_y: float = 128.0
    exploded: bool = False
    blast_pending: bool = False
    fade: float = EXPLOSION_TIME
    trail: list = field(default_factory=list)

    @property
    def active(self):
        return not self.exploded or self.fade > 0

    def explode(self):
        if not self.exploded:
            self.exploded = True
            self.blast_pending = True

    def update(self, delta_time, solids):
        dt = max(0, delta_time)
        if self.exploded:
            self.fade = max(0, self.fade - dt)
            return
        travel = min(dt, max(0, FUSE_TIME - self.age))
        steps = max(1, ceil(travel * (THROW_SPEED + abs(self.velocity_y) + 512 * travel) / 2))
        step = travel / steps
        for _ in range(steps):
            nx = self.x + self.direction * THROW_SPEED * step
            ny = self.y + self.velocity_y * step - 256 * step * step
            body = (nx - 4, ny - 4, nx + 4, ny + 4)
            def collides(s):
                if s.one_way:
                    return (ny < self.y and self.y - 4 >= s.top and ny - 4 <= s.top
                            and nx + 4 > s.left and nx - 4 < s.right)
                return overlaps(body, (s.left, s.bottom, s.right, s.top))
            if any(collides(s) for s in solids):
                self.explode()
                break
            self.x, self.y = nx, ny
            self.velocity_y -= 512 * step
            self.age += step
        self.trail.append((self.x, self.y))
        self.trail[:] = self.trail[-6:]
        if self.age >= FUSE_TIME - 1e-9:
            self.explode()

    def consume_targets(self, targets, solids):
        if not self.blast_pending:
            return []
        self.blast_pending = False
        result = []
        for identity, body in targets:
            px = max(body[0], min(self.x, body[2]))
            py = max(body[1], min(self.y, body[3]))
            if (hypot(px - self.x, py - self.y) <= BLAST_RADIUS
                    and not blocked_segment((self.x, self.y), (px, py), solids)):
                result.append(identity)
        return result

    def draw(self, camera_x=0):
        import pico2d
        from effects import blended, glow
        from item_art import draw_item
        from inventory import LIGHT_BOMB
        x, y = self.x - camera_x, self.y
        with blended():
            if not self.exploded:
                for index, (tx, ty) in enumerate(self.trail):
                    glow(tx - camera_x, ty, 3 + index / 2, (255, 211, 125), alpha=18 + index * 12)
                glow(x, y, 16, (255, 218, 131), alpha=100)
                draw_item(LIGHT_BOMB, x, y, 18)
                return
            progress = 1 - self.fade / EXPLOSION_TIME
            alpha = int(255 * (1 - progress))
            glow(x, y, BLAST_RADIUS * (0.7 + progress * .3), (255, 222, 148), alpha=alpha)
            glow(x, y, 18 * (1 - progress), (255, 249, 221), alpha=alpha)
            for offset in (0, 3):
                pico2d.draw_circle(round(x), round(y), round(min(BLAST_RADIUS, 12 + progress * 36 + offset)),
                                  255, 229, 171, a=alpha)
            for index in range(12):
                angle = index * 2 * pi / 12
                radius = 9 + progress * (24 + index % 3 * 5)
                dx, dy = cos(angle), sin(angle)
                pico2d.draw_line(x + dx * radius, y + dy * radius,
                                  x + dx * (radius + 7), y + dy * (radius + 7),
                                  255, 237, 185, a=alpha)
