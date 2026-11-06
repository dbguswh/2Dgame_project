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
