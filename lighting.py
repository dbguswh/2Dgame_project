"""휴대 조명의 수명과 방·통로로 제한한 원형 점등 범위를 계산한다."""

from dataclasses import dataclass


LIGHT_RADIUS = 64
LIGHT_DURATION = 8.0
LIGHT_COST = 50


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


@dataclass
class PortableLight:
    x: float
    y: float
    region: LightRegion
    remaining: float = LIGHT_DURATION
    radius: float = LIGHT_RADIUS

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
        from math import sin
        import pico2d
        from effects import blended, glow
        screen_width, screen_height = pico2d.get_canvas_width(), pico2d.get_canvas_height()
        left, right = max(0, self.region.left - camera_x), min(screen_width, self.region.right - camera_x)
        bottom, top = max(0, self.region.bottom), min(screen_height, self.region.top)
        if right <= left or top <= bottom:
            return
        age = LIGHT_DURATION - self.remaining
        strength = min(1.0, age / 0.16) * min(1.0, self.remaining / 0.65)
        shimmer = 1 + sin(age * 5.2) * 0.025
        with blended((left, bottom, right, top)):
            x = self.x - camera_x
            glow(x, self.y, self.radius, alpha=150 * strength * shimmer)
            glow(x, self.y, 22, (255, 213, 133), alpha=160 * strength)
            base_y = self.y - 24
            glow(x, base_y + 2, 44, alpha=90 * strength, squash=0.14)
            # 펼친 세 발과 금속 케이스로 설치 장치를 표시한다.
            pico2d.draw_line(x, base_y + 10, x - 11, base_y + 1, 119, 126, 137)
            pico2d.draw_line(x, base_y + 10, x + 11, base_y + 1, 119, 126, 137)
            pico2d.draw_rectangle(x - 6, base_y + 9, x + 6, base_y + 29,
                                  44, 51, 63, filled=True)
            pico2d.draw_rectangle(x - 6, base_y + 9, x + 6, base_y + 29, 151, 136, 104)
            lens = (255, int(164 + 58 * strength), int(72 + 82 * strength))
            pico2d.draw_rectangle(x - 3, base_y + 15, x + 3, base_y + 25,
                                  *lens, filled=True)
            pico2d.draw_rectangle(x - 8, base_y + 29, x + 8, base_y + 32,
                                  91, 101, 112, filled=True)
