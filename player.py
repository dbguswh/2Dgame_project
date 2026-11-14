"""Warden의 이동과 대기·걷기 애니메이션을 관리한다."""

import json
from math import cos, sin
from pathlib import Path

import pico2d

from physics import Motion, MOVE_SPEED, RUN_SPEED, Solid
from combat import front_box, overlaps
from combat_feedback import HitPause
from inventory import Inventory, ITEM_NAMES, MEDKIT, SPEED, LIGHT_BOMB, SHIELD
from item_effects import ItemEffects
from light_bomb import LightBomb
from flash import FLASH_COST, FLASH_RANGE, FLASH_COOLDOWN, FLASH_FRAME_ENDS, FlashPulse
from lighting import (LIGHT_COST, LIGHT_CAST_TIME, DEPLOY_DATA, LightRegion,
                      PortableLight, find_region, constrain_region, load_deploy_image)


IMAGE_PATH = Path(__file__).resolve().parent / "assets/images/characters/player.png"
WALK_DATA_PATH = IMAGE_PATH.with_name("player_walk.json")
RUN_DATA_PATH = IMAGE_PATH.with_name("player_run.json")
ACTION_DATA_PATH = IMAGE_PATH.with_name("player_actions.json")
ATTACK_DATA_PATH = IMAGE_PATH.with_name("player_attack.json")
SECOND_ATTACK_DATA_PATH = IMAGE_PATH.with_name("player_attack_second.json")
AIR_ATTACK_DATA_PATH = IMAGE_PATH.with_name("player_attack_air.json")
FLASH_DATA_PATH = IMAGE_PATH.with_name("player_flash.json")

# 확정 이미지(1312×1199)의 캐릭터 영역. 원본 파일을 수정하지 않고 잘라 그린다.
# 좌표는 pico2d의 왼쪽 아래 기준이며 희미한 여백을 제외한 범위다.
SOURCE_LEFT = 330
SOURCE_BOTTOM = 39
SOURCE_WIDTH = 766
SOURCE_HEIGHT = 1134
SOURCE_FEET_X = 660 - SOURCE_LEFT

DRAW_HEIGHT = 96
BODY_WIDTH = 24
BODY_HEIGHT = 92  # 후드가 천장 안으로 깊이 들어가지 않도록 실제 키에 맞춘 초기값.
ATTACK_FRAME_ENDS = (0.07, 0.10, 0.135, 0.20, 0.27, 0.36)
ATTACK_DURATION = ATTACK_FRAME_ENDS[-1]
ATTACK_RECOVERY = 0.15
SECOND_ATTACK_FRAME_ENDS = (0.08, 0.12, 0.155, 0.24, 0.34, 0.44)
COMBO_WINDOW = 0.4
COMBO_RECOVERY = 0.5
AIR_ATTACK_FRAME_ENDS = (0.07, 0.10, 0.135, 0.22, 0.28, 0.34)


class Player:
    def __init__(self, x, feet_y):
        # x는 양발의 가운데, feet_y는 지면에 닿는 발바닥 위치다.
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.image = pico2d.load_image(str(IMAGE_PATH))
        self.walk_data = json.loads(WALK_DATA_PATH.read_text(encoding="utf-8"))
        self.walk_image = pico2d.load_image(
            str(WALK_DATA_PATH.with_name(self.walk_data["image"]))
        )
        self.run_data = json.loads(RUN_DATA_PATH.read_text(encoding='utf-8'))
        self.run_image = pico2d.load_image(str(RUN_DATA_PATH.with_name(self.run_data['image'])))
        self.action_data = json.loads(ACTION_DATA_PATH.read_text(encoding="utf-8"))
        self.action_image = pico2d.load_image(
            str(ACTION_DATA_PATH.with_name(self.action_data["image"]))
        )
        self.attack_data = json.loads(ATTACK_DATA_PATH.read_text(encoding="utf-8"))
        self.attack_image = pico2d.load_image(
            str(ATTACK_DATA_PATH.with_name(self.attack_data["image"]))
        )
        self.second_attack_data = json.loads(SECOND_ATTACK_DATA_PATH.read_text(encoding='utf-8'))
        self.second_attack_image = pico2d.load_image(
            str(SECOND_ATTACK_DATA_PATH.with_name(self.second_attack_data['image']))
        )
        self.air_attack_data = json.loads(AIR_ATTACK_DATA_PATH.read_text(encoding='utf-8'))
        self.air_attack_image = pico2d.load_image(
            str(AIR_ATTACK_DATA_PATH.with_name(self.air_attack_data['image']))
        )
        self.light_deploy_image = load_deploy_image()
        self.flash_data = json.loads(FLASH_DATA_PATH.read_text(encoding='utf-8'))
        self.flash_image = pico2d.load_image(str(FLASH_DATA_PATH.with_name(self.flash_data['image'])))
        self.pressed_keys = set()
        self.face_dir = 1
        self.is_moving = False
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.jump_requested = False
        self.spawn_position = (x, feet_y)
        self.checkpoint_position = self.spawn_position
        self.last_safe_position = self.spawn_position
        self.health = 3
        self.invulnerability = 0.0
        self.notice = ""
        self.notice_time = 0.0
        self.attack_requested = False
        self.attack_elapsed = None
        self.attack_cooldown = 0.0
        self.attack_id = 0
        self.attack_hits = set()
        self.attack_stage = 1
        self.attack_kind = 'ground'
        self.air_attack_used = False
        self.hit_pause = HitPause()
        self.combo_window = 0.0
        self.combo_queued = False
        self.combo_direction = self.face_dir
        self.solids = []
        self.respawn_count = 0
        self.max_battery = 100
        self.battery = self.max_battery
        self.light = None
        self.light_requested = False
        self.light_cast = 0.0
        self.interaction_requested = False
        self.fragments = 0
        self.flash_requested = False
        self.flash_pending = False
        self.flash_cooldown = 0.0
        self.flash_effect = None
        self.inventory = Inventory()
        self.item_effects = ItemEffects()
        self.bombs = []
        self.requested_item = None
        self.use_medkit_requested = False
        self.heal_effect = 0.0

    @property
    def x(self):
        return self.motion.x

    @x.setter
    def x(self, value):
        self.motion.x = value

    @property
    def feet_y(self):
        return self.motion.feet_y

    @feet_y.setter
    def feet_y(self, value):
        self.motion.feet_y = value

    def handle_event(self, event):
        if event.key not in (pico2d.SDLK_LEFT, pico2d.SDLK_RIGHT,
                              pico2d.SDLK_SPACE, pico2d.SDLK_q, pico2d.SDLK_w, pico2d.SDLK_r, pico2d.SDLK_e,
                              pico2d.SDLK_1, pico2d.SDLK_2, pico2d.SDLK_3, pico2d.SDLK_4, pico2d.SDLK_f,
                              pico2d.SDLK_LSHIFT, pico2d.SDLK_RSHIFT):
            return
        if event.type == pico2d.SDL_KEYDOWN:
            if event.key == pico2d.SDLK_SPACE and event.key not in self.pressed_keys:
                self.jump_requested = True
            elif event.key == pico2d.SDLK_w and event.key not in self.pressed_keys:
                self.attack_requested = True
            elif event.key == pico2d.SDLK_q and event.key not in self.pressed_keys:
                self.flash_requested = True
            elif event.key == pico2d.SDLK_r and event.key not in self.pressed_keys:
                self.light_requested = True
            elif event.key == pico2d.SDLK_e and event.key not in self.pressed_keys:
                self.interaction_requested = True
            elif event.key == pico2d.SDLK_f and event.key not in self.pressed_keys:
                self.use_medkit_requested = True
                self.requested_item = self.inventory.selected
            elif pico2d.SDLK_1 <= event.key <= pico2d.SDLK_4 and event.key not in self.pressed_keys:
                self.inventory.select(event.key - pico2d.SDLK_1)
                self.notice, self.notice_time = f'{ITEM_NAMES[self.inventory.selected]} 선택 · F로 사용', 1.0
            self.pressed_keys.add(event.key)
        elif event.type == pico2d.SDL_KEYUP:
            self.pressed_keys.discard(event.key)

    def clear_input(self):
        self.pressed_keys.clear()
        self.jump_requested = False
        self.attack_requested = False
        self.flash_requested = False
        self.light_requested = False
        self.interaction_requested = False
        self.use_medkit_requested = False
        self.requested_item = None

    @property
    def medkits(self):
        return self.inventory.counts[MEDKIT]

    @medkits.setter
    def medkits(self, value):
        self.inventory.counts[MEDKIT] = value

    def add_item(self, slot):
        if not self.inventory.add(slot):
            return False
        self.notice, self.notice_time = f'{ITEM_NAMES[slot]} +1 · {slot + 1} 선택 후 F 사용', 1.5
        return True

    def add_medkit(self):
        return self.add_item(MEDKIT)

    def use_selected_item(self, slot):
        if slot == MEDKIT:
            return self.use_medkit()
        if slot in (SPEED, SHIELD):
            if self.inventory.counts[slot] <= 0:
                self.notice, self.notice_time = f'보유한 {ITEM_NAMES[slot]}이 없습니다', 1.0
                return False
            if not self.item_effects.activate(slot):
                self.notice, self.notice_time = f'{ITEM_NAMES[slot]} 효과가 남아 있습니다', 1.0
                return False
            self.inventory.consume(slot)
            effect = '이동 속도 +30% · 5초' if slot == SPEED else '적 공격 1회 차단 · 6초'
            self.notice, self.notice_time = f'{ITEM_NAMES[slot]} 사용 · {effect}', 1.3
            return True
        if slot != LIGHT_BOMB:
            self.notice, self.notice_time = '아직 사용할 수 없는 장비입니다', 1.0
            return False
        if self.is_attacking or self.light_cast > 0:
            self.notice, self.notice_time = '현재 동작을 마친 뒤 투척하세요', 1.0
            return False
        if not self.inventory.consume(LIGHT_BOMB):
            self.notice, self.notice_time = '보유한 광탄이 없습니다', 1.0
            return False
        self.bombs.append(LightBomb(self.x, self.feet_y + 44, self.face_dir))
        self.attack_kind = 'bomb'
        self.attack_elapsed = 0.0
        self.combo_queued = False
        self.combo_window = 0.0
        self.notice, self.notice_time = '광탄 투척', 1.0
        return True

    def use_medkit(self):
        if self.medkits <= 0:
            self.notice, self.notice_time = '보유한 치료제가 없습니다', 1.0
            return False
        if self.health >= 3 or self.health <= 0:
            self.notice, self.notice_time = '체력이 가득 차 있습니다', 1.0
            return False
        self.medkits -= 1
        self.health += 1
        self.heal_effect = 0.55
        self.notice, self.notice_time = '치료제 사용 · 체력 +1', 1.2
        return True

    @property
    def is_attacking(self):
        return self.attack_elapsed is not None

    @property
    def run_held(self):
        return bool(self.pressed_keys.intersection((pico2d.SDLK_LSHIFT, pico2d.SDLK_RSHIFT)))

    @property
    def is_running(self):
        return self.is_moving and self.run_held and not self.is_attacking and self.light_cast <= 0

    @property
    def attack_frame(self):
        if not self.is_attacking:
            return None
        # 짧은 준비, 빠른 타격, 조금 긴 회수로 베기의 힘과 흐름을 구분한다.
        ends = self._attack_frame_ends()
        for index, end in enumerate(ends):
            if self.attack_elapsed < end:
                return index
        return len(ends) - 1

    def _attack_frame_ends(self):
        if self.attack_kind in ('flash', 'bomb'):
            return FLASH_FRAME_ENDS
        if self.attack_kind == 'air':
            return AIR_ATTACK_FRAME_ENDS
        return SECOND_ATTACK_FRAME_ENDS if self.attack_stage == 2 else ATTACK_FRAME_ENDS

    @property
    def attack_lean(self):
        """발 기준으로 준비 때 뒤로, 타격 때 앞으로 힘을 싣는 시각 회전이다."""
        if not self.is_attacking or self.attack_kind in ('flash', 'bomb'):
            return 0.0
        ends = self._attack_frame_ends()
        angles = (0.035, 0.07, -0.07, -0.045, -0.015, 0.0)
        frame = self.attack_frame
        start = ends[frame - 1] if frame else 0
        previous = angles[frame - 1] if frame else 0
        fraction = max(0.0, min(1.0, (self.attack_elapsed - start) / (ends[frame] - start)))
        return (previous + (angles[frame] - previous) * fraction) * self.face_dir

    def _begin_air_attack(self):
        self._begin_attack(1)
        self.attack_kind = 'air'
        self.air_attack_used = True
        self.combo_window = 0.0

    def _begin_attack(self, stage, elapsed=0.0):
        self.attack_kind = 'ground'
        self.attack_stage = stage
        self.attack_elapsed = elapsed
        self.attack_id += 1
        self.attack_hits.clear()
        self.attack_cooldown = 0.0
        self.combo_queued = False
        if stage == 1:
            self.combo_window = COMBO_WINDOW
            self.combo_direction = self.face_dir
        else:
            self.combo_window = 0.0
            self.face_dir = self.combo_direction

    def _advance_attack(self, delta_time):
        self.attack_cooldown = max(0.0, self.attack_cooldown - delta_time)
        self.combo_window = max(0.0, self.combo_window - delta_time)
        if not self.is_attacking:
            return
        self.attack_elapsed += delta_time
        duration = self._attack_frame_ends()[-1]
        if self.attack_elapsed < duration:
            return
        if self.attack_kind == 'ground' and self.attack_stage == 1 and self.combo_queued and self.motion.on_ground:
            self._begin_attack(2, self.attack_elapsed - duration)
        else:
            self.attack_elapsed = None
            self.combo_queued = False
            if self.attack_kind in ('air', 'flash', 'bomb'):
                self.attack_cooldown = 0.0
            else:
                self.attack_cooldown = COMBO_RECOVERY if self.attack_stage == 2 else ATTACK_RECOVERY

    def _request_attack(self, combo_open):
        if not self.attack_requested or self.light_cast > 0:
            return
        if self.is_attacking and self.attack_kind == 'bomb':
            return
        if not self.motion.on_ground:
            if not self.air_attack_used and not self.is_attacking and self.attack_cooldown <= 0:
                self._begin_air_attack()
            return
        if self.attack_stage == 1 and combo_open:
            if self.is_attacking:
                self.combo_queued = True
            else:
                self._begin_attack(2)
        elif not self.is_attacking and self.attack_cooldown <= 0:
            self._begin_attack(1)

    @property
    def animation_state(self):
        if self.is_attacking:
            if self.attack_kind in ('flash', 'bomb'):
                return 'flash'
            return 'air_attack' if self.attack_kind == 'air' else 'attack'
        if not self.motion.on_ground:
            if abs(self.motion.velocity_y) < 50:
                return 'jump_apex'
            return 'jump_rise' if self.motion.velocity_y > 0 else 'jump_fall'
        if self.light_cast > 0:
            return 'light_cast'
        return 'run' if self.is_running else 'walk' if self.is_moving else 'idle'

    def _install_light(self, regions):
        if self.is_attacking or self.light_cast > 0:
            return False
        if not self.motion.on_ground:
            self.notice, self.notice_time = '바닥에 착지한 뒤 조명을 설치하세요', 1.0
            return False
        if self.battery < LIGHT_COST:
            self.notice, self.notice_time = '배터리 부족: 조명 설치에는 50이 필요합니다', 1.2
            return False
        x, y = self.x, self.feet_y + 24
        region = find_region(regions, x, y)
        if region is None:
            self.notice, self.notice_time = '이 위치에는 조명을 설치할 수 없습니다', 1.2
            return False
        region = constrain_region(region, x, y, self.solids)
        self.light = PortableLight(x, y, region, art=self.light_deploy_image)
        self.battery -= LIGHT_COST
        self.light_cast = LIGHT_CAST_TIME
        self.attack_requested = False
        self.combo_window = 0.0
        self.combo_queued = False
        self.jump_requested = False
        self.notice, self.notice_time = '투광기 전개 · 주변 제압 · 12초 점등', 1.1
        return True

    def _cast_flash(self):
        if self.is_attacking or self.light_cast > 0 or self.flash_cooldown > 0:
            return False
        if self.battery < FLASH_COST:
            self.notice, self.notice_time = '배터리 부족: 섬광 공격에는 20이 필요합니다', 1.0
            return False
        self.battery -= FLASH_COST
        self._begin_attack(1)
        self.attack_kind = 'flash'
        self.combo_window = 0.0
        self.flash_cooldown = FLASH_COOLDOWN
        self.flash_pending = True
        box = front_box(self.x, self.face_dir, BODY_WIDTH / 2, BODY_WIDTH / 2 + FLASH_RANGE,
                        self.feet_y + 10, self.feet_y + 72, self.solids)
        self.flash_effect = FlashPulse(self.x, self.feet_y, self.face_dir, box)
        self.jump_requested = False
        self.notice, self.notice_time = '섬광 공격 · 배터리 -20', 0.7
        return True

    def consume_flash_target(self, targets):
        if not self.flash_pending:
            return None
        self.flash_pending = False
        box = self.flash_effect.box if self.flash_effect is not None else None
        candidates = [(identity, body) for identity, body in targets if overlaps(box, body)]
        if not candidates:
            return None
        return min(candidates, key=lambda target: abs((target[1][0] + target[1][2]) / 2 - self.x))[0]

    def update(self, delta_time, area_width, solids=None, light_regions=None):
        speed_factor = self.item_effects.update(delta_time)
        self.heal_effect = max(0.0, self.heal_effect - delta_time)
        self.invulnerability = max(0.0, self.invulnerability - delta_time)
        self.notice_time = max(0.0, self.notice_time - delta_time)
        self.light_cast = max(0.0, self.light_cast - delta_time)
        self.flash_cooldown = max(0.0, self.flash_cooldown - delta_time)
        if self.flash_effect is not None:
            self.flash_effect.update(delta_time)
            if not self.flash_effect.active:
                self.flash_effect = None
        if self.light is not None:
            self.light.update(delta_time)
            if not self.light.active:
                self.light = None
        was_frozen = self.hit_pause.remaining > 0
        delta_time = self.hit_pause.consume(delta_time)
        if was_frozen and delta_time <= 0:
            return
        if solids is None:
            solids = [Solid(0, 0, area_width, 96)]
        self.solids = solids
        combo_open = self.combo_window > 0
        self._advance_attack(delta_time)
        higher_priority_action = self.light_requested or self.flash_requested
        if self.light_requested:
            regions = light_regions if light_regions is not None else [LightRegion(0, 96, area_width, 540)]
            self._install_light(regions)
            self.flash_requested = False
            self.attack_requested = False
        elif self.flash_requested:
            self._cast_flash()
            self.attack_requested = False
        self.light_requested = False
        self.flash_requested = False
        if self.use_medkit_requested:
            slot = self.requested_item if self.requested_item is not None else self.inventory.selected
            if slot != LIGHT_BOMB or not higher_priority_action:
                self.use_selected_item(slot)
            self.use_medkit_requested = False
            self.requested_item = None
        self._request_attack(combo_open)
        self.attack_requested = False
        if self.jump_requested and not self.is_attacking and self.light_cast <= 0:
            self.motion.jump()
        self.jump_requested = False
        direction = int(pico2d.SDLK_RIGHT in self.pressed_keys) - int(
            pico2d.SDLK_LEFT in self.pressed_keys
        )
        if (self.is_attacking and (self.attack_kind == 'ground'
                                  or (self.attack_kind in ('flash', 'bomb') and self.motion.on_ground))) or self.light_cast > 0:
            direction = 0
        previous_direction = self.face_dir
        if direction and not self.is_attacking:
            self.face_dir = direction
        previous_x = self.x

        # 두 방향 모두에서 전체 그림이 화면 안에 남도록 초기 경계를 제한한다.
        scale = DRAW_HEIGHT / SOURCE_HEIGHT
        margin = max(
            max(SOURCE_FEET_X, SOURCE_WIDTH - SOURCE_FEET_X) * scale,
            self.walk_data["visible_half_width"] * DRAW_HEIGHT
            / self.walk_data["reference_height"],
            self.attack_data["visible_half_width"] * DRAW_HEIGHT
            / self.attack_data["reference_height"],
            self.air_attack_data["visible_half_width"] * DRAW_HEIGHT
            / self.air_attack_data["reference_height"],
        )
        speed = (RUN_SPEED if self.run_held else MOVE_SPEED) * max(speed_factor, self.item_effects.speed_multiplier)
        self.motion.step(delta_time, direction, solids, area_width, margin, speed=speed)
        if self.motion.on_ground:
            self.air_attack_used = False
            if self.attack_kind == 'air':
                # 착지는 공중 동작을 끝낸다. 입력을 예약하지 않고 새 W로 지상 공격한다.
                self.attack_elapsed = None
                self.attack_kind = 'ground'
                self.attack_stage = 1
                self.attack_cooldown = 0.0
                self.combo_window = 0.0
                self.combo_queued = False
        if self.feet_y + BODY_HEIGHT < -32:
            self._return_after_fall()
            return

        distance = abs(self.x - previous_x)
        self.is_moving = distance > 0.000001 and self.motion.on_ground
        if self.is_moving:
            if self.face_dir != previous_direction:
                self.walk_distance = 0.0
            # 실제 이동 거리를 기준으로 재생해 화면 갱신 횟수에 영향을 받지 않는다.
            data = self.run_data if self.is_running else self.walk_data
            cycle = data["cycle_distance"]
            self.walk_distance = (self.walk_distance + distance) % cycle
            self.walk_frame = int(
                self.walk_distance / cycle * len(data["frames"])
            )
        else:
            # 키를 놓거나 양쪽 키·화면 끝 때문에 멈추면 원래 대기 자세로 돌아간다.
            self.walk_distance = 0.0
            self.walk_frame = 0

    def draw(self, camera_x=0):
        if self.invulnerability > 0 and int(self.invulnerability * 12) % 2:
            return
        state = self.animation_state
        if state in ('attack', 'air_attack', 'flash'):
            if state == 'flash':
                data, image = self.flash_data, self.flash_image
            elif state == 'air_attack':
                data, image = self.air_attack_data, self.air_attack_image
            elif self.attack_stage == 2:
                data, image = self.second_attack_data, self.second_attack_image
            else:
                data, image = self.attack_data, self.attack_image
            frame = data['frames'][self.attack_frame]
            left, bottom, width, height = frame['rect']
            feet_x, feet_y = frame['feet']
            scale = DRAW_HEIGHT / data['reference_height']
        elif state.startswith('jump_'):
            phase = ('jump_rise', 'jump_apex', 'jump_fall').index(state)
            index = self.action_data['jump'][phase]
            frame = self.action_data['frames'][index]
            image = self.action_image
            left, bottom, width, height = frame["rect"]
            feet_x, feet_y = frame["feet"]
            scale = DRAW_HEIGHT / self.action_data["reference_height"]
        elif state == 'light_cast':
            elapsed = LIGHT_CAST_TIME - self.light_cast
            phase = min(2, int(elapsed / (LIGHT_CAST_TIME / 3)))
            frame = DEPLOY_DATA['frames'][DEPLOY_DATA['cast'][phase]]
            image = self.light_deploy_image
            left, bottom, width, height = frame['rect']
            feet_x, feet_y = frame['feet']
            scale = DRAW_HEIGHT / DEPLOY_DATA['player_reference_height']
        elif self.is_moving:
            data = self.run_data if self.is_running else self.walk_data
            frame = data["frames"][self.walk_frame]
            image = self.run_image if self.is_running else self.walk_image
            left, bottom, width, height = frame["rect"]
            feet_x, feet_y = frame["feet"]
            scale = DRAW_HEIGHT / data["reference_height"]
        else:
            image = self.image
            left, bottom = SOURCE_LEFT, SOURCE_BOTTOM
            width, height = SOURCE_WIDTH, SOURCE_HEIGHT
            feet_x, feet_y = SOURCE_FEET_X, 0
            scale = DRAW_HEIGHT / SOURCE_HEIGHT

        center_offset = (width / 2 - feet_x) * scale
        angle = self.attack_lean
        dx, dy = center_offset * self.face_dir, (height / 2 - feet_y) * scale
        # 셀 중심이 아니라 발을 회전축으로 삼아 기울어져도 바닥이 흔들리지 않는다.
        image.clip_composite_draw(
            left, bottom, width, height,
            angle, "h" if self.face_dir < 0 else "",
            self.x - camera_x + dx * cos(angle) - dy * sin(angle),
            self.feet_y + dx * sin(angle) + dy * cos(angle),
            width * scale, height * scale,
        )

    def get_bb(self):
        """이미지와 별도로 실제 지형 충돌에 사용하는 몸통 영역이다."""
        return self.motion.get_bb()

    def get_attack_box(self):
        """타격 프레임의 전방 1타일. 공중은 아래쪽이며 벽·발판 뒤는 제외한다."""
        if self.attack_kind in ('flash', 'bomb'):
            return None
        if self.attack_kind == 'air':
            if not self.is_attacking or not 0.10 <= self.attack_elapsed < 0.22:
                return None
            attack = front_box(
                self.x, self.face_dir, BODY_WIDTH / 2, BODY_WIDTH / 2 + 32,
                self.feet_y - 16, self.feet_y + 48, self.solids,
            )
            if attack is None:
                return None
            left, bottom, right, top = attack
            for solid in self.solids:
                if left < solid.right and right > solid.left and bottom < solid.top <= self.feet_y:
                    bottom = solid.top
            return (left, bottom, right, top) if top > bottom else None
        start, end = (0.12, 0.24) if self.attack_stage == 2 else (0.1, 0.2)
        if not self.is_attacking or not start <= self.attack_elapsed < end:
            return None
        return front_box(self.x, self.face_dir, BODY_WIDTH / 2, BODY_WIDTH / 2 + 32,
                         self.feet_y + 12, self.feet_y + 64, self.solids)

    def get_attack_target(self, targets):
        """(대상 ID, 피격 영역) 목록 중 가까운 한 명을 공격당 한 번만 선택한다."""
        attack = self.get_attack_box()
        if attack is None or self.attack_hits:
            return None
        candidates = [(identity, box) for identity, box in targets
                      if overlaps(attack, box)]
        if not candidates:
            return None
        identity, _ = min(candidates, key=lambda item: abs((item[1][0] + item[1][2]) / 2 - self.x))
        self.attack_hits.add(identity)
        return identity

    def _return_after_fall(self):
        self.health -= 1
        if self.health <= 0:
            self._respawn()
            return
        self.notice = "낙하 피해 -1: 마지막 안전 발판으로 복귀"
        self.x, self.feet_y = self.last_safe_position
        self.reset_actions_after_return(clear_consumable_effects=False)
        self.notice_time = 2.0

    def take_damage(self):
        if self.invulnerability > 0 or self.health <= 0:
            return False
        if self.item_effects.absorb_attack():
            self.invulnerability = 1.0
            self.notice, self.notice_time = '보호막 차단 · 체력 유지', .9
            return False
        self.health -= 1
        self.hit_pause.reset()
        self.attack_elapsed = None
        self.attack_requested = False
        self.flash_pending = False
        self.flash_requested = False
        self.combo_window = 0.0
        self.combo_queued = False
        self.jump_requested = False
        if self.health <= 0:
            self._respawn()
        else:
            self.invulnerability = 1.0
            self.notice = '공격 피해 -1'
            self.notice_time = 0.7
        return True

    def _respawn(self):
        self.health = 3
        self.last_safe_position = self.checkpoint_position
        self.x, self.feet_y = self.checkpoint_position
        self.respawn_count += 1
        self.notice = '체력 소진: 안전 지점으로 복귀'
        self.notice_time = 2.0
        self.light = None
        self.reset_actions_after_return()

    def reset_actions_after_return(self, invulnerability=1.0, clear_consumable_effects=True):
        self.hit_pause.reset()
        self.motion.velocity_y = 0
        self.motion.on_ground = True
        self.invulnerability = invulnerability
        self.clear_input()
        self.is_moving = False
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.attack_elapsed = None
        self.attack_cooldown = 0.0
        self.attack_hits.clear()
        self.attack_stage = 1
        self.attack_kind = 'ground'
        self.air_attack_used = False
        self.combo_window = 0.0
        self.combo_queued = False
        self.combo_direction = self.face_dir
        self.light_cast = 0.0
        self.flash_pending = False
        self.flash_cooldown = 0.0
        self.flash_effect = None
        self.heal_effect = 0.0
        self.bombs.clear()
        if clear_consumable_effects:
            self.item_effects.clear()

    def draw_flash(self, camera_x=0):
        if self.flash_effect is not None:
            self.flash_effect.draw(camera_x)

    def draw_recovery(self, camera_x=0):
        if self.heal_effect <= 0:
            return
        from effects import blended, glow
        strength = self.heal_effect / 0.55
        age = 1 - strength
        x = self.x - camera_x
        with blended():
            glow(x, self.feet_y + 44, 32, (133, 220, 161), alpha=85 * strength)
            for index, dx in enumerate((-15, 0, 15)):
                y = self.feet_y + 53 + age * 30 + index * 6
                alpha = int(220 * strength)
                pico2d.draw_rectangle(x + dx - 1, y - 5, x + dx + 1, y + 5,
                                      158, 238, 179, a=alpha, filled=True)
                pico2d.draw_rectangle(x + dx - 5, y - 1, x + dx + 5, y + 1,
                                      158, 238, 179, a=alpha, filled=True)

    def draw_debug(self, camera_x=0):
        left, bottom, right, top = self.get_bb()
        pico2d.draw_rectangle(left - camera_x, bottom, right - camera_x, top,
                              r=112, g=220, b=148)
        pico2d.draw_line(
            self.x - camera_x - 5, self.feet_y, self.x - camera_x + 5, self.feet_y,
            r=255, g=196, b=80,
        )
        pico2d.draw_line(
            self.x - camera_x, self.feet_y - 5, self.x - camera_x, self.feet_y + 5,
            r=255, g=196, b=80,
        )
        attack = self.get_attack_box()
        if attack is not None:
            left, bottom, right, top = attack
            pico2d.draw_rectangle(left - camera_x, bottom, right - camera_x, top,
                                  r=255, g=111, b=92)
