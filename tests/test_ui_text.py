import ctypes
import os
import unittest
from unittest.mock import patch

import pico2d
from pico2d import pico2d as canvas
import sdl2
from sdl2 import sdlttf

from ui_text import UIFont


class UITextRenderTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_RENDER_DRIVER='software')
        environment.start()
        self.addCleanup(environment.stop)
        pico2d.open_canvas(960, 540, sync=False)
        sdl2.SDL_RenderSetLogicalSize(canvas.renderer, 960, 540)
        self.font = UIFont(18)

    def tearDown(self):
        self.font.close()
        pico2d.close_canvas()

    def render_sample(self):
        sdl2.SDL_SetRenderDrawColor(canvas.renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderClear(canvas.renderer)
        self.font.draw(20, 400, '주택가 전력 복구 123', (255, 255, 255))
        width, height = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_GetRendererOutputSize(canvas.renderer, ctypes.byref(width), ctypes.byref(height))
        pixels = (ctypes.c_uint8 * (width.value * height.value * 4))()
        self.assertEqual(sdl2.SDL_RenderReadPixels(canvas.renderer, None, sdl2.SDL_PIXELFORMAT_RGBA32,
                                                 pixels, width.value * 4), 0)
        visible = [i // 4 for i in range(0, len(pixels), 4) if pixels[i] > 30]
        self.assertTrue(visible, '실제 출력 화면에 글자가 그려져야 함')
        columns = [i % width.value for i in visible]
        shades = {pixels[i] for i in range(0, len(pixels), 4) if 0 < pixels[i] < 255}
        return max(columns) - min(columns) + 1, shades

    def test_korean_glyphs_render_with_antialiased_edges_at_enlarged_size(self):
        sdl2.SDL_SetWindowSize(canvas.window, 1440, 810)
        _, shades = self.render_sample()
        for character in '주택가전력복구':
            self.assertNotEqual(sdlttf.TTF_GlyphIsProvided(self.font._font, ord(character)), 0)
        self.assertGreater(len(shades), 8)

    def test_resize_with_letterboxing_preserves_logical_text_width(self):
        native_width, _ = self.render_sample()
        sdl2.SDL_SetWindowSize(canvas.window, 1440, 900)
        enlarged_width, _ = self.render_sample()
        self.assertAlmostEqual(enlarged_width / 1.5, native_width, delta=6)


if __name__ == '__main__':
    unittest.main()
