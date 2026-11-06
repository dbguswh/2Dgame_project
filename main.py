"""Blackout: 게임 창과 플레이어의 기본 출력을 시작한다."""

import pico2d

from player import Player


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
TILE_SIZE = 32
GROUND_Y = TILE_SIZE * 3


def draw_ground():
    """이동과 충돌 구현에 사용할 임시 바닥을 표시한다."""
    pico2d.draw_rectangle(
        0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1,
        19, 25, 38, filled=True,
    )
    pico2d.draw_rectangle(
        0, 0, SCREEN_WIDTH - 1, GROUND_Y - 1,
        51, 56, 65, filled=True,
    )
    pico2d.draw_line(0, GROUND_Y, SCREEN_WIDTH - 1, GROUND_Y, 137, 148, 159)


def main():
    pico2d.open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT, sync=True)
    player = None
    try:
        pico2d.hide_lattice()
        player = Player(x=TILE_SIZE * 5, feet_y=GROUND_Y)
        running = True
        show_debug = False

        while running:
            for event in pico2d.get_events():
                if event.type == pico2d.SDL_QUIT:
                    running = False
                elif event.type == pico2d.SDL_KEYDOWN:
                    if event.key == pico2d.SDLK_ESCAPE:
                        running = False
                    elif event.key == pico2d.SDLK_F1:
                        show_debug = not show_debug

            if not running:
                break

            pico2d.clear_canvas()
            draw_ground()
            player.draw()
            if show_debug:
                player.draw_debug()
            pico2d.update_canvas()
            pico2d.delay(0.001)
    finally:
        # 렌더러를 닫기 전에 캐릭터의 이미지 자원을 해제한다.
        player = None
        pico2d.close_canvas()


if __name__ == "__main__":
    main()
