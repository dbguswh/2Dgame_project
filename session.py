"""타이틀과 플레이 사이의 전환 및 한 실행의 진행을 관리한다."""

import pico2d

from enemy import Shade
from player import Player
from residential import ResidentialStage
from hospital import HospitalStage
from world import update_world, restore_enemies
from progress import ProgressRecords
from upgrades import ManagementVisit, CORE_UPGRADES, SUPPLY_OFFERS


class GameSession:
    PAUSE_ITEMS = ('계속하기', '스테이지 재시작', '타이틀로', '나가기')
    CLEAR_ITEMS = ('도시 지도', '주택가 다시하기', '타이틀로')

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
        self.management_visit = None
        self.completed_stage_ids = set()
        self.transition_elapsed = 0.0
        self.transition_swapped = False

    @property
    def running(self):
        return self.state != 'QUIT'

    def start_game(self):
        self.close_world()
        self.stage = self.stage_factory()
        self.player = Player(*self.stage.start)
        self.player.face_dir = getattr(self.stage, 'start_direction', 1)
        self.completed_stage_ids.clear()
        if self.stage.enemy_placements:
            self.enemies = [Shade(e.x, e.feet_y, identity=e.identity, combat_bounds=e.bounds,
                                  can_shoot=e.ranged)
                            for e in self.stage.enemy_placements]
        else:
            self.enemies = [Shade(*self.stage.enemy_spawn, combat_bounds=self.stage.combat_bounds)]
        self.records = ProgressRecords(self.player, self.stage)
        restore_enemies(self.enemies, self.stage)
        self.play_time = 0.0
        self.state = 'PLAY'

    def restart_stage(self):
        self.completed_stage_ids.discard(self.stage.stage_id)
        self.records.restore_entry(self.player, self.stage)
        restore_enemies(self.enemies, self.stage)
        self.player.clear_input()
        self.state = 'PLAY'
        self.selection = 0
        self.management_visit = None

    @property
    def can_depart(self):
        return (self.stage is not None and self.stage.completed
                and self.stage.stage_id == 'residential'
                and self.management_visit is not None and self.management_visit.completed)

    @property
    def clear_items(self):
        return ('도시 지도', f'{self.stage.name} 다시하기', '타이틀로')

    def depart(self):
        if self.state != 'MANAGEMENT' or not self.can_depart:
            return False
        self.state = 'TRANSITION'
        self.transition_elapsed = 0.0
        self.transition_swapped = False
        self.player.clear_input()
        return True

    def _enter_hospital(self):
        self.stage = HospitalStage()
        p = self.player
        p.x, p.feet_y = self.stage.start
        p.spawn_position = p.checkpoint_position = p.last_safe_position = self.stage.start
        p.health, p.battery = 3, p.max_battery
        p.light = None
        p.reset_actions_after_return(invulnerability=0)
        p.face_dir = self.stage.start_direction
        p.notice, p.notice_time = '운하 병원 · 중앙 단말기로 A/B 회로를 전환하세요', 3.5
        self.enemies = [Shade(e.x, e.feet_y, identity=e.identity, combat_bounds=e.bounds,
                              can_shoot=e.ranged) for e in self.stage.enemy_placements]
        restore_enemies(self.enemies, self.stage)
        self.records = ProgressRecords(p, self.stage)
        self.management_visit = None
        self.selection = 0

    def open_city_map(self):
        if (self.stage is None or not self.stage.completed
                or self.state not in ('STAGE_CLEAR', 'CITY_MAP', 'MANAGEMENT')):
            return False
        if self.management_visit is None:
            self.management_visit = ManagementVisit()
        self.state = 'CITY_MAP'
        self.selection = 0
        self.player.clear_input()
        return True

    def open_management(self):
        if self.state != 'CITY_MAP' or self.management_visit is None:
            return False
        self.state = 'MANAGEMENT'
        self.selection = len(SUPPLY_OFFERS) if self.management_visit.completed else 0
        self.player.clear_input()
        return True

    def return_to_title(self):
        self.close_world()
        self.state = 'TITLE'
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

        elif self.state == 'STAGE_CLEAR' and new_press:
            if event.key in (pico2d.SDLK_UP, pico2d.SDLK_DOWN):
                step = -1 if event.key == pico2d.SDLK_UP else 1
                self.selection = (self.selection + step) % len(self.CLEAR_ITEMS)
            elif event.key == pico2d.SDLK_ESCAPE:
                self.return_to_title()
            elif event.key == pico2d.SDLK_e:
                if self.selection == 0:
                    self.open_city_map()
                elif self.selection == 1:
                    self.restart_stage()
                else:
                    self.return_to_title()
        elif self.state == 'CITY_MAP' and new_press:
            if event.key == pico2d.SDLK_e:
                self.open_management()
            elif event.key == pico2d.SDLK_ESCAPE:
                self.state = 'STAGE_CLEAR'
                self.selection = 0
                self.player.clear_input()
        elif self.state == 'MANAGEMENT' and new_press:
            if event.key in (pico2d.SDLK_LEFT, pico2d.SDLK_RIGHT):
                step = -1 if event.key == pico2d.SDLK_LEFT else 1
                count = len(SUPPLY_OFFERS) + 1 + int(self.can_depart) if self.management_visit.completed else len(CORE_UPGRADES)
                self.selection = (self.selection + step) % count
            elif event.key == pico2d.SDLK_ESCAPE:
                self.open_city_map()
            elif event.key == pico2d.SDLK_e:
                if self.management_visit.completed:
                    if self.selection == len(SUPPLY_OFFERS):
                        self.open_city_map()
                    elif self.selection == len(SUPPLY_OFFERS) + 1 and self.can_depart:
                        self.depart()
                    elif self.management_visit.purchase_supply(self.player, self.selection):
                        self.records.remember(self.player, self.stage)
                elif self.management_visit.purchase(self.player, self.selection):
                    self.records.remember(self.player, self.stage)
                    # 구매 직후 E 유지로 보급품까지 연속 구매하지 않으며 지도 복귀를 기본 선택한다.
                    self.selection = len(SUPPLY_OFFERS)
        elif self.state == 'PLAY':
            if event.type == pico2d.SDL_KEYDOWN and not new_press:
                return
            if new_press and event.key == pico2d.SDLK_ESCAPE:
                self.state = 'PAUSED'
                self.selection = 0
                self.player.clear_input()
            elif new_press and event.key == pico2d.SDLK_F1:
                self.show_debug = not self.show_debug
            elif getattr(self.stage, 'controls_locked', False):
                self.player.clear_input()
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
        if self.state == 'TRANSITION':
            self.transition_elapsed = min(.7, self.transition_elapsed + max(0, delta_time))
            if self.transition_elapsed >= .35 and not self.transition_swapped:
                self._enter_hospital()
                self.transition_swapped = True
            if self.transition_elapsed >= .7:
                self.state = 'PLAY'
            return
        if self.state == 'PLAY':
            update_world(delta_time, self.player, self.enemies, self.stage, self.records)
            self.play_time += delta_time
            if self.stage.completed:
                self.completed_stage_ids.add(self.stage.stage_id)
                self.state = 'STAGE_CLEAR'
                self.selection = 0
                self.player.clear_input()

    def close_world(self):
        self.player = None
        self.enemies.clear()
        self.stage = None
        self.records = None
        self.management_visit = None
