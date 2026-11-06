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

    def draw(self, camera_x=0):
        if not self.active:
            return
        from ctypes import byref, c_int
        from math import ceil, floor
        import pico2d
        from pico2d import pico2d as canvas
        import sdl2

        screen_width, screen_height = pico2d.get_canvas_width(), pico2d.get_canvas_height()
        left, right = max(0, self.region.left - camera_x), min(screen_width, self.region.right - camera_x)
        bottom, top = max(0, self.region.bottom), min(screen_height, self.region.top)
        if right <= left or top <= bottom:
            return
        clip = sdl2.SDL_Rect(floor(left), screen_height - ceil(top),
                            ceil(right) - floor(left), ceil(top) - floor(bottom))
        previous_clip = sdl2.SDL_Rect()
        had_clip = sdl2.SDL_RenderIsClipEnabled(canvas.renderer)
        sdl2.SDL_RenderGetClipRect(canvas.renderer, byref(previous_clip))
        previous_blend = c_int()
        sdl2.SDL_GetRenderDrawBlendMode(canvas.renderer, byref(previous_blend))
        try:
            sdl2.SDL_RenderSetClipRect(canvas.renderer, byref(clip))
            sdl2.SDL_SetRenderDrawBlendMode(canvas.renderer, sdl2.SDL_BLENDMODE_BLEND)
            x = self.x - camera_x
            for ratio, alpha in ((1.0, 28), (0.75, 30), (0.5, 34), (0.25, 45)):
                pico2d.draw_circle(x, self.y, int(self.radius * ratio),
                                   r=255, g=192, b=82, a=alpha, filled=True)
            # 밝은 테두리가 실제 반경을 나타내며 영역 경계 밖으로는 그리지 않는다.
            pico2d.draw_circle(x, self.y, int(self.radius), r=255, g=207, b=111, a=200)
            base_y = self.y - 24
            pico2d.draw_rectangle(x - 5, base_y, x + 5, base_y + 5,
                                  92, 76, 54, filled=True)
            pico2d.draw_rectangle(x - 3, base_y + 5, x + 3, base_y + 14,
                                  255, 224, 136, filled=True)
        finally:
            sdl2.SDL_RenderSetClipRect(canvas.renderer, byref(previous_clip) if had_clip else None)
            sdl2.SDL_SetRenderDrawBlendMode(canvas.renderer, previous_blend.value)
