"""타이틀과 플레이 사이의 전환 및 한 실행의 진행을 관리한다."""

import pico2d

from enemy import Shade
from player import Player
from residential import ResidentialStage
from world import update_world, restore_enemies
from progress import ProgressRecords


class GameSession:
    PAUSE_ITEMS = ('계속하기', '스테이지 재시작', '타이틀로', '나가기')

    def __init__(self, stage_factory=ResidentialStage):
        self.stage_factory = stage_factory
        self.state = 'TITLE'
        self.selection = 0
        self.pressed_keys = set()
        self.player = None
        self.stage = None
        self.enemies = []
        self.show_debug = False
        self.play_time = 0.0
        self.records = None

    @property
    def running(self):
        return self.state != 'QUIT'

    def start_game(self):
        self.close_world()
        self.stage = self.stage_factory()
        self.player = Player(*self.stage.start)
        if self.stage.enemy_placements:
            self.enemies = [Shade(e.x, e.feet_y, identity=e.identity, combat_bounds=e.bounds)
                            for e in self.stage.enemy_placements]
        else:
            self.enemies = [Shade(*self.stage.enemy_spawn, combat_bounds=self.stage.combat_bounds)]
        self.records = ProgressRecords(self.player, self.stage)
        self.play_time = 0.0
        self.state = 'PLAY'

    def restart_stage(self):
        self.records.restore_entry(self.player, self.stage)
        restore_enemies(self.enemies, self.stage)
        self.player.clear_input()
        self.state = 'PLAY'
        self.selection = 0

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
                self.state = 'PAUSED'
                self.selection = 0
                self.player.clear_input()
            elif new_press and event.key == pico2d.SDLK_F1:
                self.show_debug = not self.show_debug
            else:
                self.player.handle_event(event)
        elif self.state == 'PAUSED' and new_press:
            if event.key == pico2d.SDLK_ESCAPE:
                self.state = 'PLAY'
                self.player.clear_input()
            elif event.key in (pico2d.SDLK_UP, pico2d.SDLK_DOWN):
                step = -1 if event.key == pico2d.SDLK_UP else 1
                self.selection = (self.selection + step) % len(self.PAUSE_ITEMS)
            elif event.key == pico2d.SDLK_e:
                if self.selection == 0:
                    self.state = 'PLAY'
                    self.player.clear_input()
                elif self.selection == 1:
                    self.restart_stage()
                elif self.selection == 2:
                    self.close_world()
                    self.state = 'TITLE'
                    self.selection = 0
                else:
                    self.state = 'QUIT'

    def update(self, delta_time, focused=True):
        if not focused:
            self.clear_input()
            return
        if self.state == 'PLAY':
            update_world(delta_time, self.player, self.enemies, self.stage, self.records)
            self.play_time += delta_time

    def close_world(self):
        self.player = None
        self.enemies.clear()
        self.stage = None
        self.records = None
