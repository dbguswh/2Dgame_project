"""Warden의 이동과 대기·걷기 애니메이션을 관리한다."""

import json
from pathlib import Path

import pico2d

from physics import Motion, MOVE_SPEED, Solid


IMAGE_PATH = Path(__file__).resolve().parent / "assets/images/characters/player.png"
WALK_DATA_PATH = IMAGE_PATH.with_name("player_walk.json")
ACTION_DATA_PATH = IMAGE_PATH.with_name("player_actions.json")
ATTACK_DATA_PATH = IMAGE_PATH.with_name("player_attack.json")

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
ATTACK_FRAME_ENDS = (0.05, 0.10, 0.15, 0.20, 0.28, 0.36)
ATTACK_DURATION = ATTACK_FRAME_ENDS[-1]
ATTACK_RECOVERY = 0.15


class Player:
    def __init__(self, x, feet_y):
        # x는 양발의 가운데, feet_y는 지면에 닿는 발바닥 위치다.
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.image = pico2d.load_image(str(IMAGE_PATH))
        self.walk_data = json.loads(WALK_DATA_PATH.read_text(encoding="utf-8"))
        self.walk_image = pico2d.load_image(
            str(WALK_DATA_PATH.with_name(self.walk_data["image"]))
        )
        self.action_data = json.loads(ACTION_DATA_PATH.read_text(encoding="utf-8"))
        self.action_image = pico2d.load_image(
            str(ACTION_DATA_PATH.with_name(self.action_data["image"]))
        )
        self.attack_data = json.loads(ATTACK_DATA_PATH.read_text(encoding="utf-8"))
        self.attack_image = pico2d.load_image(
            str(ATTACK_DATA_PATH.with_name(self.attack_data["image"]))
        )
        self.pressed_keys = set()
        self.face_dir = 1
        self.is_moving = False
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.jump_requested = False
        self.spawn_position = (x, feet_y)
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
        self.solids = []

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
                              pico2d.SDLK_SPACE, pico2d.SDLK_w):
            return
        if event.type == pico2d.SDL_KEYDOWN:
            if event.key == pico2d.SDLK_SPACE and event.key not in self.pressed_keys:
                self.jump_requested = True
            elif event.key == pico2d.SDLK_w and event.key not in self.pressed_keys:
                self.attack_requested = True
            self.pressed_keys.add(event.key)
        elif event.type == pico2d.SDL_KEYUP:
            self.pressed_keys.discard(event.key)

    def clear_input(self):
        self.pressed_keys.clear()
        self.jump_requested = False
        self.attack_requested = False

    @property
    def is_attacking(self):
        return self.attack_elapsed is not None

    @property
    def attack_frame(self):
        if not self.is_attacking:
            return None
        # 짧은 준비, 빠른 타격, 조금 긴 회수로 베기의 힘과 흐름을 구분한다.
        for index, end in enumerate(ATTACK_FRAME_ENDS):
            if self.attack_elapsed < end:
                return index
        return len(ATTACK_FRAME_ENDS) - 1

    @property
    def animation_state(self):
        if self.is_attacking:
            return 'attack'
        if not self.motion.on_ground:
            if abs(self.motion.velocity_y) < 50:
                return 'jump_apex'
            return 'jump_rise' if self.motion.velocity_y > 0 else 'jump_fall'
        return 'walk' if self.is_moving else 'idle'

    def update(self, delta_time, area_width, solids=None):
        self.invulnerability = max(0.0, self.invulnerability - delta_time)
        self.notice_time = max(0.0, self.notice_time - delta_time)
        if solids is None:
            solids = [Solid(0, 0, area_width, 96)]
        self.solids = solids
        self.attack_cooldown = max(0.0, self.attack_cooldown - delta_time)
        if self.is_attacking:
            self.attack_elapsed += delta_time
            if self.attack_elapsed >= ATTACK_DURATION:
                self.attack_elapsed = None
                self.attack_cooldown = ATTACK_RECOVERY
        if (self.attack_requested and not self.is_attacking
                and self.attack_cooldown <= 0 and self.motion.on_ground):
            self.attack_elapsed = 0.0
            self.attack_id += 1
            self.attack_hits.clear()
        self.attack_requested = False
        if self.jump_requested and not self.is_attacking:
            self.motion.jump()
        self.jump_requested = False
        direction = int(pico2d.SDLK_RIGHT in self.pressed_keys) - int(
            pico2d.SDLK_LEFT in self.pressed_keys
        )
        if self.is_attacking:
            direction = 0
        previous_direction = self.face_dir
        if direction:
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
        )
        self.motion.step(delta_time, direction, solids, area_width, margin)
        if self.feet_y + BODY_HEIGHT < -32:
            self._return_after_fall()
            return

        distance = abs(self.x - previous_x)
        self.is_moving = distance > 0.000001 and self.motion.on_ground
        if self.is_moving:
            if self.face_dir != previous_direction:
                self.walk_distance = 0.0
            # 실제 이동 거리를 기준으로 재생해 화면 갱신 횟수에 영향을 받지 않는다.
            cycle = self.walk_data["cycle_distance"]
            self.walk_distance = (self.walk_distance + distance) % cycle
            self.walk_frame = int(
                self.walk_distance / cycle * len(self.walk_data["frames"])
            )
        else:
            # 키를 놓거나 양쪽 키·화면 끝 때문에 멈추면 원래 대기 자세로 돌아간다.
            self.walk_distance = 0.0
            self.walk_frame = 0

    def draw(self, camera_x=0):
        if self.invulnerability > 0 and int(self.invulnerability * 12) % 2:
            return
        state = self.animation_state
        if state == 'attack':
            frame = self.attack_data['frames'][self.attack_frame]
            image = self.attack_image
            left, bottom, width, height = frame['rect']
            feet_x, feet_y = frame['feet']
            scale = DRAW_HEIGHT / self.attack_data['reference_height']
        elif state.startswith('jump_'):
            phase = ('jump_rise', 'jump_apex', 'jump_fall').index(state)
            index = self.action_data['jump'][phase]
            frame = self.action_data['frames'][index]
            image = self.action_image
            left, bottom, width, height = frame["rect"]
            feet_x, feet_y = frame["feet"]
            scale = DRAW_HEIGHT / self.action_data["reference_height"]
        elif self.is_moving:
            frame = self.walk_data["frames"][self.walk_frame]
            image = self.walk_image
            left, bottom, width, height = frame["rect"]
            feet_x, feet_y = frame["feet"]
            scale = DRAW_HEIGHT / self.walk_data["reference_height"]
        else:
            image = self.image
            left, bottom = SOURCE_LEFT, SOURCE_BOTTOM
            width, height = SOURCE_WIDTH, SOURCE_HEIGHT
            feet_x, feet_y = SOURCE_FEET_X, 0
            scale = DRAW_HEIGHT / SOURCE_HEIGHT

        center_offset = (width / 2 - feet_x) * scale
        image.clip_composite_draw(
            left, bottom, width, height,
            0, "h" if self.face_dir < 0 else "",
            self.x - camera_x + center_offset * self.face_dir,
            self.feet_y + (height / 2 - feet_y) * scale,
            width * scale, height * scale,
        )

    def get_bb(self):
        """이미지와 별도로 실제 지형 충돌에 사용하는 몸통 영역이다."""
        return self.motion.get_bb()

    def get_attack_box(self):
        """타격 프레임에서만 전방 1타일의 범위를 반환한다. 벽 뒤는 잘라낸다."""
        if not self.is_attacking or not 0.1 <= self.attack_elapsed < 0.2:
            return None
        bottom, top = self.feet_y + 12, self.feet_y + 64
        if self.face_dir > 0:
            left, right = self.x + BODY_WIDTH / 2, self.x + BODY_WIDTH / 2 + 32
            for solid in self.solids:
                if bottom < solid.top and top > solid.bottom and left <= solid.left < right:
                    right = solid.left
        else:
            left, right = self.x - BODY_WIDTH / 2 - 32, self.x - BODY_WIDTH / 2
            for solid in self.solids:
                if bottom < solid.top and top > solid.bottom and left < solid.right <= right:
                    left = solid.right
        return (left, bottom, right, top) if right > left else None

    def get_attack_target(self, targets):
        """(대상 ID, 피격 영역) 목록 중 가까운 한 명을 공격당 한 번만 선택한다."""
        attack = self.get_attack_box()
        if attack is None or self.attack_hits:
            return None
        left, bottom, right, top = attack
        candidates = [(identity, box) for identity, box in targets
                      if box[0] < right and box[2] > left
                      and box[1] < top and box[3] > bottom]
        if not candidates:
            return None
        identity, _ = min(candidates, key=lambda item: abs((item[1][0] + item[1][2]) / 2 - self.x))
        self.attack_hits.add(identity)
        return identity

    def _return_after_fall(self):
        self.health -= 1
        if self.health <= 0:
            self.health = 3
            self.last_safe_position = self.spawn_position
            self.notice = "체력 소진: 시작 지점으로 복귀"
        else:
            self.notice = "낙하 피해 -1: 마지막 안전 발판으로 복귀"
        self.x, self.feet_y = self.last_safe_position
        self.motion.velocity_y = 0
        self.motion.on_ground = True
        self.invulnerability = 1.0
        self.notice_time = 2.0
        self.clear_input()
        self.is_moving = False
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.attack_elapsed = None
        self.attack_cooldown = 0.0

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
