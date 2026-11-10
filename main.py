"""Blackout 실행과 단일 게임 루프."""

from time import perf_counter

import pico2d

from screens import draw_session
from session import GameSession
from window import has_input_focus, open_game_window
from world import update_world
from effects import clear_resources
from ui_text import UIFont


def main():
    open_game_window()
    game = GameSession()
    font = menu_font = title_font = None
    try:
        font = UIFont(18)
        menu_font = UIFont(26)
        title_font = UIFont(64)
        previous_time = perf_counter()
        while game.running:
            now = perf_counter()
            delta_time = min(now - previous_time, 0.05)
            previous_time = now
            for event in pico2d.get_events():
                game.handle_event(event)
            if not game.running:
                break
            game.update(delta_time, focused=has_input_focus())
            draw_session(game, font, menu_font, title_font)
            pico2d.update_canvas()
            pico2d.delay(0.001)
    finally:
        game.close_world()
        for loaded_font in (font, menu_font, title_font):
            if loaded_font is not None:
                loaded_font.close()
        font = menu_font = title_font = None
        clear_resources()
        pico2d.close_canvas()


if __name__ == '__main__':
    main()
