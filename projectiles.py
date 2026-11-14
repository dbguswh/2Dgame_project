"""예고한 방향으로만 날아가는 Shade의 그림자 탄."""

from dataclasses import dataclass
from math import ceil, cos, sin, hypot, pi

import pico2d

from combat import overlaps
from effects import blended, glow, segment


BOLT_SPEED = 240
BOLT_RADIUS = 6


@dataclass
class ShadowBolt:
    x: float
    y: float
    vx: float
    vy: float
    remaining: float = 3.0
    active: bool = True
    hit_event: bool = False
    fade: float = 0.14
    absorbed: bool = False

    @classmethod
    def aimed(cls, origin, target):
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        length = max(1.0, hypot(dx, dy))
        return cls(*origin, dx / length * BOLT_SPEED, dy / length * BOLT_SPEED)

    def get_bb(self):
        return (self.x - BOLT_RADIUS, self.y - BOLT_RADIUS,
                self.x + BOLT_RADIUS, self.y + BOLT_RADIUS)

    def update(self, delta_time, solids, player, light=None, fixed_light=None):
        if not self.active:
            self.fade = max(0.0, self.fade - delta_time)
            return
        travel_time = min(delta_time, self.remaining)
        steps = max(1, ceil(BOLT_SPEED * travel_time / 3))
        dt = travel_time / steps
        for _ in range(steps):
            self.x += self.vx * dt
            self.y += self.vy * dt
            box = self.get_bb()
            if any(overlaps(box, (s.left, s.bottom, s.right, s.top)) for s in solids):
                self.active = False
                break
            if ((light is not None and light.illuminates(box))
                    or (fixed_light is not None and fixed_light(box))):
                self.active = False
                self.absorbed = True
                self.fade = 0.32
                break
            if overlaps(box, player.get_bb()):
                self.active = False
                self.hit_event = True
                break
        self.remaining = max(0.0, self.remaining - delta_time)
        if self.remaining <= 0:
            self.active = False

    def consume_hit(self):
        hit, self.hit_event = self.hit_event, False
        return hit

    def draw(self, camera_x=0):
        if not self.active and self.fade <= 0:
            return
        x, y = self.x - camera_x, self.y
        with blended():
            if not self.active:
                if self.absorbed:
                    progress = 1 - self.fade / 0.32
                    glow(x, y, 24 * (1 - progress), (255, 222, 158), alpha=210 * (1 - progress))
                    for index in range(7):
                        angle = index * 2 * pi / 7
                        radius = 5 + progress * (19 + index % 3 * 4)
                        fx, fy = x + cos(angle) * radius, y + sin(angle) * radius
                        pico2d.draw_line(fx, fy, fx + cos(angle) * 4, fy + sin(angle) * 4,
                                          194, 107, 234, a=int(230 * (1 - progress)))
                    return
                glow(x, y, 14, (194, 100, 239), alpha=90 * self.fade / 0.14)
                return
            glow(x, y, 17, (182, 70, 233), alpha=140)
            length = max(1, hypot(self.vx, self.vy))
            tail = (x - self.vx / length * 20, y - self.vy / length * 20)
            segment(tail, (x, y), (140, 58, 194), width=5)
            pico2d.draw_circle(x, y, BOLT_RADIUS, 207, 110, 245, filled=True)
            pico2d.draw_circle(x, y, 3, 255, 220, 255, filled=True)
