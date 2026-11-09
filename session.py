"""타이틀과 플레이 사이의 전환 및 한 실행의 진행을 관리한다."""

import pico2d

from enemy import Shade
from player import Player
from stage import Stage
from world import update_world


class GameSession:
    def __init__(self):
        self.state = 'TITLE'
        self.selection = 0
        self.pressed_keys = set()
        self.player = None
        self.stage = None
        self.enemies = []
        self.show_debug = False
        self.play_time = 0.0

    @property
    def running(self):
        return self.state != 'QUIT'

    def start_game(self):
        self.close_world()
        self.stage = Stage()
        self.player = Player(*self.stage.start)
        self.enemies = [Shade(*self.stage.enemy_spawn, combat_bounds=self.stage.combat_bounds)]
        self.play_time = 0.0
        self.state = 'PLAY'

    def clear_input(self):
        self.pressed_keys.clear()
        if self.player is not None:
            self.player.clear_input()

    def handle_event(self, event):
        if event.type == pico2d.SDL_QUIT:
            self.state = 'QUIT'
            return
        if event.type not in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
            return
        new_press = event.type == pico2d.SDL_KEYDOWN and event.key not in self.pressed_keys
        if event.type == pico2d.SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
        else:
            self.pressed_keys.discard(event.key)
        if self.state == 'TITLE':
            if not new_press:
                return
            if event.key in (pico2d.SDLK_UP, pico2d.SDLK_DOWN):
                self.selection = 1 - self.selection
            elif event.key == pico2d.SDLK_ESCAPE:
                self.state = 'QUIT'
            elif event.key == pico2d.SDLK_e:
                if self.selection == 0:
                    self.start_game()
                else:
                    self.state = 'QUIT'
        elif self.state == 'PLAY':
            if event.type == pico2d.SDL_KEYDOWN and not new_press:
                return
            if new_press and event.key == pico2d.SDLK_ESCAPE:
                self.state = 'QUIT'
            elif new_press and event.key == pico2d.SDLK_F1:
                self.show_debug = not self.show_debug
            else:
                self.player.handle_event(event)

    def update(self, delta_time, focused=True):
        if not focused:
            self.clear_input()
            return
        if self.state == 'PLAY':
            update_world(delta_time, self.player, self.enemies, self.stage)
            self.play_time += delta_time

    def close_world(self):
        self.player = None
        self.enemies.clear()
        self.stage = None
