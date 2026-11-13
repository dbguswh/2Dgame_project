"""명중 표현의 시간과 입자. 피해·사거리·충돌 판정과는 독립적이다."""

from dataclasses import dataclass
from math import cos, sin

import pico2d

from effects import blended, glow


@dataclass
class HitPause:
    remaining: float = 0.0

    def trigger(self, duration):
        self.remaining = max(self.remaining, duration)

    def consume(self, delta_time):
        stopped = min(self.remaining, delta_time)
        self.remaining = max(0.0, self.remaining - stopped)
        return max(0.0, delta_time - stopped)

    def reset(self):
        self.remaining = 0.0


@dataclass
class Impact:
    x: float
    y: float
    direction: int
    heavy: bool = False
    lethal: bool = False
    age: float = 0.0

    @property
    def hitstop(self):
        return 0.065 if self.lethal else 0.055 if self.heavy else 0.04

    @property
    def duration(self):
        return 0.65 if self.lethal else 0.32 if self.heavy else 0.24

    @property
    def active(self):
        return self.age < self.duration

    @property
    def shake_x(self):
        duration = 0.16 if self.lethal else 0.12
        amplitude = 3 if self.lethal else 2 if self.heavy else 0
        decay = max(0.0, 1 - self.age / duration)
        return sin(self.age * 105) * amplitude * decay

    def update(self, delta_time):
        self.age += delta_time

    def draw(self, camera_x=0):
        if not self.active:
            return
        x, y, t = self.x - camera_x, self.y, self.age
        count = 13 if self.lethal else 9 if self.heavy else 6
        with blended():
            # 접점에만 짧은 섬광을 그려 캐릭터의 자세가 가려지지 않도록 한다.
            if t < 0.10:
                strength = 1 - t / 0.10
                radius = (19 if self.heavy or self.lethal else 13) * (0.6 + strength * 0.4)
                glow(x, y, radius, (255, 218, 148), alpha=185 * strength)
                for angle in (0.25, 1.3, 2.4):
                    dx, dy = cos(angle) * radius, sin(angle) * radius
                    pico2d.draw_line(x - dx, y - dy, x + dx, y + dy,
                                      255, 240, 200, int(230 * strength))
            for index in range(count):
                angle = -0.55 + index * 2.3 / max(1, count - 1)
                speed = 48 + (index * 29 % 75) + (24 if self.lethal else 0)
                vx = self.direction * cos(angle) * speed
                vy = sin(angle) * speed + 15
                px, py = x + vx * t, y + vy * t - 110 * t * t
                opacity = int(230 * max(0.0, 1 - t / self.duration))
                if index % 3 == 0:
                    pico2d.draw_line(px, py, px - vx * 0.035, py - vy * 0.035,
                                      255, 204, 115, opacity)
                else:
                    size = 2.8 if self.lethal else 1.8
                    for offset in range(-int(size), int(size) + 1):
                        span = size - abs(offset) * 0.6
                        pico2d.draw_line(px - span, py + offset, px + span,
                                          py + offset, 163, 83, 210, opacity)
