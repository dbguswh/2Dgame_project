"""화면 표시 배율에 맞춰 한글을 렌더링하고 문자열 텍스처를 재사용한다."""

from collections import OrderedDict
from ctypes import byref, c_int
from math import ceil
import os
from pathlib import Path

import pico2d
from pico2d import pico2d as canvas
import sdl2
from sdl2 import sdlttf

from window import SCREEN_WIDTH, SCREEN_HEIGHT


def font_path():
    windows_font = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/malgun.ttf'
    if windows_font.is_file():
        return windows_font
    return Path(pico2d.__file__).parent / 'data/ConsolaMalgun.ttf'


class UIFont:
    CACHE_LIMIT = 256

    def __init__(self, size):
        self.size = size
        self.path = font_path()
        self._font = None
        self._renderer = None
        self._scale = None
        self._cache = OrderedDict()

    @staticmethod
    def display_scale():
        width, height = c_int(), c_int()
        if sdl2.SDL_GetRendererOutputSize(canvas.renderer, byref(width), byref(height)) != 0:
            raise RuntimeError('글자 표시 크기를 확인할 수 없습니다')
        if width.value <= 0 or height.value <= 0:
            return 1.0
        return min(width.value / SCREEN_WIDTH, height.value / SCREEN_HEIGHT)

    def _prepare(self):
        actual_scale = self.display_scale()
        # 작은 창에서는 원래 글자 해상도를 유지하고, 확대 시에는 상위 0.5배 단위로 준비한다.
        scale = max(1.0, ceil(actual_scale * 2) / 2)
        if self._font is not None and self._renderer is canvas.renderer and scale == self._scale:
            return actual_scale
        self.close()
        self._font = sdlttf.TTF_OpenFont(str(self.path).encode('utf-8'), round(self.size * scale))
        if not self._font:
            raise RuntimeError(f'글꼴을 열 수 없습니다: {self.path.name}')
        self._scale = scale
        self._renderer = canvas.renderer
        sdlttf.TTF_SetFontHinting(self._font, sdlttf.TTF_HINTING_NORMAL)
        return actual_scale

    def _text(self, text, color):
        key = (text, tuple(color))
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        surface = sdlttf.TTF_RenderUTF8_Blended(self._font, text.encode('utf-8'), sdl2.SDL_Color(*color, 255))
        if not surface:
            raise RuntimeError('문자열을 그릴 수 없습니다')
        try:
            width, height = surface.contents.w, surface.contents.h
            texture = sdl2.SDL_CreateTextureFromSurface(canvas.renderer, surface)
        finally:
            sdl2.SDL_FreeSurface(surface)
        if not texture:
            raise RuntimeError('글자 텍스처를 생성할 수 없습니다')
        sdl2.SDL_SetTextureBlendMode(texture, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetTextureScaleMode(texture, sdl2.SDL_ScaleModeLinear)
        self._cache[key] = (texture, width / self._scale, height / self._scale)
        if len(self._cache) > self.CACHE_LIMIT:
            _, (old_texture, _, _) = self._cache.popitem(last=False)
            sdl2.SDL_DestroyTexture(old_texture)
        return self._cache[key]

    def draw(self, x, y, text, color=(0, 0, 0)):
        if not text:
            return
        scale = self._prepare()
        texture, width, height = self._text(text, color)
        # 글자 왼쪽과 위쪽을 실제 픽셀 격자에 맞춰 반 픽셀 위치에서 번지는 현상을 줄인다.
        left = round(x * scale) / scale
        top = round((SCREEN_HEIGHT - 1 - y - height / 2) * scale) / scale
        rect = sdl2.SDL_FRect(left, top, width, height)
        sdl2.SDL_RenderCopyF(canvas.renderer, texture, None, byref(rect))

    def close(self):
        if self._renderer is canvas.renderer:
            for texture, _, _ in self._cache.values():
                sdl2.SDL_DestroyTexture(texture)
        self._cache.clear()
        if self._font:
            sdlttf.TTF_CloseFont(self._font)
        self._font = None
        self._renderer = None
        self._scale = None
