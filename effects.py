"""월드 조명에 사용하는 부드러운 SDL 그라데이션. 범위 판정과 독립적이다."""

from contextlib import contextmanager
from ctypes import byref, c_int, c_uint8
from math import ceil, floor, sqrt

import pico2d
from pico2d import pico2d as canvas
import sdl2


_glow_texture = None
_glow_renderer = None


def clear_resources():
    global _glow_texture, _glow_renderer
    from visibility import clear_resources as clear_darkness
    clear_darkness()
    if _glow_texture is not None and _glow_renderer is canvas.renderer:
        sdl2.SDL_DestroyTexture(_glow_texture)
    _glow_texture = None
    _glow_renderer = None


def _radial_texture():
    """광원마다 같은 흰색 알파 커널을 색·크기만 바꿔 재사용한다."""
    global _glow_texture, _glow_renderer
    if _glow_texture is not None and _glow_renderer is canvas.renderer:
        return _glow_texture
    size = 128
    pixels = (c_uint8 * (size * size * 4))()
    stops = ((0, 1), (0.18, 0.9), (0.42, 0.62), (0.72, 0.2), (1, 0))
    for y in range(size):
        for x in range(size):
            distance = sqrt(((x + 0.5) / (size / 2) - 1) ** 2
                            + ((y + 0.5) / (size / 2) - 1) ** 2)
            opacity = 0
            for (inner, a), (outer, b) in zip(stops, stops[1:]):
                if inner <= distance <= outer:
                    opacity = a + (b - a) * (distance - inner) / (outer - inner)
                    break
            index = (y * size + x) * 4
            pixels[index:index + 4] = (255, 255, 255, int(255 * opacity))
    texture = sdl2.SDL_CreateTexture(canvas.renderer, sdl2.SDL_PIXELFORMAT_RGBA32,
                                    sdl2.SDL_TEXTUREACCESS_STATIC, size, size)
    if not texture:
        raise RuntimeError('조명 텍스처를 생성할 수 없습니다')
    if sdl2.SDL_UpdateTexture(texture, None, pixels, size * 4) != 0:
        sdl2.SDL_DestroyTexture(texture)
        raise RuntimeError('조명 텍스처를 업로드할 수 없습니다')
    sdl2.SDL_SetTextureBlendMode(texture, sdl2.SDL_BLENDMODE_BLEND)
    sdl2.SDL_SetTextureScaleMode(texture, sdl2.SDL_ScaleModeLinear)
    _glow_texture, _glow_renderer = texture, canvas.renderer
    return texture


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
    texture = _radial_texture()
    sdl2.SDL_SetTextureColorMod(texture, *color)
    sdl2.SDL_SetTextureAlphaMod(texture, max(0, min(255, int(alpha))))
    target = sdl2.SDL_FRect(x - radius, pico2d.get_canvas_height() - 1 - y - radius * squash,
                           radius * 2, radius * 2 * squash)
    sdl2.SDL_RenderCopyF(canvas.renderer, texture, None, byref(target))


def light_beam(origin, first, second, alpha=48):
    """광원에서 밝고 끝으로 갈수록 투명해지는 작은 반사광 삼각형이다."""
    vertices = (sdl2.SDL_Vertex * 3)()
    for index, (x, y) in enumerate((origin, first, second)):
        vertices[index].position = sdl2.SDL_FPoint(x, pico2d.get_canvas_height() - 1 - y)
        vertices[index].color = sdl2.SDL_Color(255, 221, 151,
                                               max(0, min(255, int(alpha))) if index == 0 else 0)
        vertices[index].tex_coord = sdl2.SDL_FPoint(0, 0)
    sdl2.SDL_RenderGeometry(canvas.renderer, None, vertices, 3, None, 0)


def polygon(points, color):
    """작은 볼록 금속 면을 삼각형 묶음으로 그린다."""
    vertices = (sdl2.SDL_Vertex * len(points))()
    for index, (x, y) in enumerate(points):
        vertices[index].position = sdl2.SDL_FPoint(x, pico2d.get_canvas_height() - 1 - y)
        vertices[index].color = sdl2.SDL_Color(*color, 255)
        vertices[index].tex_coord = sdl2.SDL_FPoint(0, 0)
    triangles = [value for index in range(1, len(points) - 1) for value in (0, index, index + 1)]
    indices = (c_int * len(triangles))(*triangles)
    sdl2.SDL_RenderGeometry(canvas.renderer, None, vertices, len(points), indices, len(triangles))


def segment(first, second, color, width=2):
    """카메라 배율에서도 두께가 유지되는 금속 보·난간 선분이다."""
    ax, ay = first
    bx, by = second
    length = sqrt((bx - ax) ** 2 + (by - ay) ** 2)
    if length <= 0:
        return
    nx, ny = -(by - ay) / length * width / 2, (bx - ax) / length * width / 2
    polygon(((ax + nx, ay + ny), (bx + nx, by + ny),
             (bx - nx, by - ny), (ax - nx, ay - ny)), color)
