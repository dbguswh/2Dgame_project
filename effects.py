"""월드 조명에 사용하는 부드러운 SDL 그라데이션. 범위 판정과 독립적이다."""

from contextlib import contextmanager
from ctypes import byref, c_int
from math import ceil, cos, floor, sin, tau

import pico2d
from pico2d import pico2d as canvas
import sdl2


@contextmanager
def blended(clip=None):
    previous_clip = sdl2.SDL_Rect()
    had_clip = sdl2.SDL_RenderIsClipEnabled(canvas.renderer)
    sdl2.SDL_RenderGetClipRect(canvas.renderer, byref(previous_clip))
    previous_blend = c_int()
    sdl2.SDL_GetRenderDrawBlendMode(canvas.renderer, byref(previous_blend))
    try:
        sdl2.SDL_SetRenderDrawBlendMode(canvas.renderer, sdl2.SDL_BLENDMODE_BLEND)
        if clip is not None:
            left, bottom, right, top = clip
            if had_clip:
                height = pico2d.get_canvas_height()
                left = max(left, previous_clip.x)
                right = min(right, previous_clip.x + previous_clip.w)
                bottom = max(bottom, height - previous_clip.y - previous_clip.h)
                top = min(top, height - previous_clip.y)
            rect = sdl2.SDL_Rect(floor(left), pico2d.get_canvas_height() - ceil(top),
                                max(0, ceil(right) - floor(left)), max(0, ceil(top) - floor(bottom)))
            sdl2.SDL_RenderSetClipRect(canvas.renderer, byref(rect))
        yield
    finally:
        sdl2.SDL_RenderSetClipRect(canvas.renderer, byref(previous_clip) if had_clip else None)
        sdl2.SDL_SetRenderDrawBlendMode(canvas.renderer, previous_blend.value)


def glow(x, y, radius, color=(255, 187, 86), alpha=100, squash=1.0):
    """경계에서 완전히 투명해지는 여러 겹의 빛. blended 안에서 호출한다."""
    if radius <= 0 or alpha <= 0:
        return
    segments = 48
    stops = ((0, 1), (0.18, 0.9), (0.42, 0.62), (0.72, 0.2), (1, 0))
    vertices = (sdl2.SDL_Vertex * (segments * (len(stops) - 1) * 6))()
    index = 0
    height = pico2d.get_canvas_height()
    for (inner, inner_alpha), (outer, outer_alpha) in zip(stops, stops[1:]):
        for segment in range(segments):
            a, b = segment * tau / segments, (segment + 1) * tau / segments
            for distance, angle, opacity in ((inner, a, inner_alpha), (outer, a, outer_alpha),
                                             (outer, b, outer_alpha), (inner, a, inner_alpha),
                                             (outer, b, outer_alpha), (inner, b, inner_alpha)):
                position = (x + cos(angle) * radius * distance,
                            height - 1 - y - sin(angle) * radius * distance * squash)
                vertices[index] = sdl2.SDL_Vertex(position, (*color, int(alpha * opacity)))
                index += 1
    if sdl2.SDL_RenderGeometry(canvas.renderer, None, vertices, len(vertices), None, 0) != 0:
        for scale, opacity in ((1, 0.05), (0.72, 0.07), (0.42, 0.16), (0.18, 0.4)):
            pico2d.draw_circle(x, y, int(radius * scale), *color, a=int(alpha * opacity), filled=True)
