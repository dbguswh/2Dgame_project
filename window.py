"""게임 좌표를 유지하면서 실제 창의 표시 크기를 조절한다."""

from ctypes import byref

import pico2d
from pico2d import pico2d as canvas
import sdl2


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 810
BACKGROUND_COLOR = (19, 25, 38)


def open_game_window():
    pico2d.open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT, sync=True)
    try:
        if not canvas.window or not canvas.renderer:
            raise RuntimeError("게임 창을 만들 수 없습니다.")
        if sdl2.SDL_RenderSetLogicalSize(
            canvas.renderer, SCREEN_WIDTH, SCREEN_HEIGHT
        ) != 0:
            raise RuntimeError("게임 화면의 표시 배율을 설정할 수 없습니다.")

        bounds = sdl2.SDL_Rect()
        display = sdl2.SDL_GetWindowDisplayIndex(canvas.window)
        has_bounds = sdl2.SDL_GetDisplayUsableBounds(display, byref(bounds)) == 0
        scale = 1.0
        if has_bounds:
            # 제목 표시줄과 작업 표시줄을 피해 작은 모니터에도 창을 맞춘다.
            scale = min(1.0, max(1, bounds.w - 64) / WINDOW_WIDTH,
                        max(1, bounds.h - 96) / WINDOW_HEIGHT)
        width, height = int(WINDOW_WIDTH * scale), int(WINDOW_HEIGHT * scale)
        sdl2.SDL_SetWindowResizable(canvas.window, sdl2.SDL_TRUE)
        sdl2.SDL_SetWindowMinimumSize(canvas.window, min(640, width), min(360, height))
        sdl2.SDL_SetWindowSize(canvas.window, width, height)
        if has_bounds:
            sdl2.SDL_SetWindowPosition(
                canvas.window, bounds.x + (bounds.w - width) // 2,
                bounds.y + (bounds.h - height) // 2,
            )
        pico2d.hide_lattice()
    except Exception:
        pico2d.close_canvas()
        raise


def clear_frame():
    # 창 비율이 바뀌어 생긴 여백까지 같은 배경색으로 지운다.
    sdl2.SDL_SetRenderDrawColor(canvas.renderer, *BACKGROUND_COLOR, 255)
    sdl2.SDL_RenderClear(canvas.renderer)
