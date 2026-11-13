"""휴대 조명의 수명과 방·통로로 제한한 원형 점등 범위를 계산한다."""

from dataclasses import dataclass, field
import json
from math import pi, sin, sqrt
from pathlib import Path


LIGHT_RADIUS = 160
LIGHT_DURATION = 12.0
LIGHT_COST = 50
LIGHT_CAST_TIME = 0.18
LIGHT_PUSH_DISTANCE = 96
LIGHT_PUSH_SPEED = 320
DEPLOY_DATA_PATH = Path(__file__).resolve().parent / 'assets/images/characters/player_light_deploy.json'
DEPLOY_DATA = json.loads(DEPLOY_DATA_PATH.read_text(encoding='utf-8'))


def load_deploy_image():
    import pico2d
    return pico2d.load_image(str(DEPLOY_DATA_PATH.with_name(DEPLOY_DATA['image'])))


@dataclass(frozen=True)
class LightRegion:
    left: float
    bottom: float
    right: float
    top: float

    def contains(self, x, y):
        return self.left <= x <= self.right and self.bottom <= y <= self.top


def find_region(regions, x, y):
    return next((region for region in regions if region.contains(x, y)), None)


def constrain_region(region, x, y, solids):
    """설치 좌표에서 만나는 벽과 상하 바닥으로 방의 빛을 제한한다."""
    left, bottom, right, top = region.left, region.bottom, region.right, region.top
    for solid in solids:
        if solid.bottom < y < solid.top:
            if solid.right <= x:
                left = max(left, solid.right)
            elif solid.left >= x:
                right = min(right, solid.left)
        if solid.left <= x <= solid.right:
            if solid.top <= y:
                bottom = max(bottom, solid.top)
            elif solid.bottom >= y:
                top = min(top, solid.bottom)
    return LightRegion(left, bottom, right, top)


@dataclass
class PortableLight:
    x: float
    y: float
    region: LightRegion
    remaining: float = LIGHT_DURATION
    radius: float = LIGHT_RADIUS
    art: object = field(default=None, repr=False, compare=False)

    @property
    def age(self):
        return max(0.0, LIGHT_DURATION - self.remaining)

    @property
    def device_frame(self):
        return 0 if self.age < 0.06 else 1 if self.age < 0.16 else 2

    @property
    def visual_strength(self):
        progress = min(1.0, self.age / 0.22)
        ignition = 0.4 + 0.6 * progress * progress * (3 - 2 * progress)
        shutdown = min(1.0, self.remaining / 0.45)
        warning = 0.88 + 0.12 * sin(self.age * 6 * pi) if self.remaining < 2 else 1
        return max(0.0, ignition * shutdown * warning)

    @property
    def active(self):
        return self.remaining > 0

    def update(self, delta_time):
        self.remaining = max(0.0, self.remaining - max(0.0, delta_time))
        if self.remaining < 0.000000001:
            self.remaining = 0.0

    def illuminates(self, box):
        if not self.active:
            return False
        left = max(box[0], self.region.left)
        bottom = max(box[1], self.region.bottom)
        right = min(box[2], self.region.right)
        top = min(box[3], self.region.top)
        if left >= right or bottom >= top:
            return False
        nearest_x = max(left, min(right, self.x))
        nearest_y = max(bottom, min(top, self.y))
        return (nearest_x - self.x) ** 2 + (nearest_y - self.y) ** 2 <= self.radius ** 2

    def draw(self, camera_x=0):
        if not self.active:
            return
        import pico2d
        from effects import blended, glow, light_beam
        screen_width, screen_height = pico2d.get_canvas_width(), pico2d.get_canvas_height()
        left, right = max(0, self.region.left - camera_x), min(screen_width, self.region.right - camera_x)
        bottom, top = max(0, self.region.bottom), min(screen_height, self.region.top)
        if right <= left or top <= bottom:
            return
        age, strength = self.age, self.visual_strength
        shimmer = 1 + sin(age * 5.2) * 0.018
        with blended((left, bottom, right, top)):
            x = self.x - camera_x
            base_y = self.y - 24
            glow(x, self.y, self.radius, (255, 184, 78), alpha=160 * strength * shimmer)
            glow(x, self.y, self.radius * 0.65, (255, 207, 125), alpha=92 * strength)
            floor_radius = sqrt(max(0, self.radius ** 2 - 24 ** 2))
            glow(x, base_y + 1, floor_radius, (255, 195, 101),
                 alpha=145 * strength, squash=0.13)
            glow(x, base_y + 1, 21, (255, 229, 175), alpha=90 * strength, squash=0.10)
            for first, second in (((-38, 44), (-22, 54)), ((-7, 60), (7, 60)),
                                  ((22, 54), (38, 44))):
                light_beam((x, base_y + 30), (x + first[0], self.y + first[1]),
                           (x + second[0], self.y + second[1]), alpha=48 * strength)
            # 점등 순간의 짧은 섬광도 억제 반경 안에만 표시한다.
            if age < 0.32:
                flash = sin(pi * min(1.0, age / 0.32))
                glow(x, base_y + 19, 18 + 16 * min(1.0, age / 0.22),
                     (255, 234, 182), alpha=100 * flash)
            if self.art is None:
                self.art = load_deploy_image()
            frame = DEPLOY_DATA['frames'][DEPLOY_DATA['device'][self.device_frame]]
            sx, sy, width, height = frame['rect']
            feet_x, feet_y = frame['feet']
            scale = 38 / DEPLOY_DATA['device_reference_height']
            self.art.opacify(min(1.0, self.remaining / 0.25))
            self.art.clip_composite_draw(
                sx, sy, width, height, 0, '', x + (width / 2 - feet_x) * scale,
                base_y + (height / 2 - feet_y) * scale, width * scale, height * scale)
            self.art.opacify(1.0)
            glow(x, base_y + 18, 10, (255, 232, 168), alpha=175 * strength)
            for index in range(3):
                phase = (age * 0.7 + index / 3) % 1
                mote_x = x + sin(age * 1.4 + index * 2.1) * 9
                mote_y = base_y + 24 + phase * 23
                pico2d.draw_circle(mote_x, mote_y, 1, 255, 223, 153,
                                   a=int(95 * strength * sin(pi * phase)), filled=True)
            # 장치 밑의 세 칸은 HUD를 읽지 않아도 남은 전력을 알려준다.
            for index in range(3):
                color = (255, 206, 111) if self.remaining > index * LIGHT_DURATION / 3 else (73, 65, 51)
                pico2d.draw_line(x - 9 + index * 7, base_y + 2,
                                  x - 5 + index * 7, base_y + 2, *color,
                                  a=int(220 * min(1.0, self.remaining / 0.45)))
