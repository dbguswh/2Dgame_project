"""Warden의 이동과 대기·걷기 애니메이션을 관리한다."""

import json
from pathlib import Path

import pico2d

from physics import Motion, MOVE_SPEED, Solid


IMAGE_PATH = Path(__file__).resolve().parent / "assets/images/characters/player.png"
WALK_DATA_PATH = IMAGE_PATH.with_name("player_walk.json")

# 확정 이미지(1312×1199)의 캐릭터 영역. 원본 파일을 수정하지 않고 잘라 그린다.
# 좌표는 pico2d의 왼쪽 아래 기준이며 희미한 여백을 제외한 범위다.
SOURCE_LEFT = 330
SOURCE_BOTTOM = 39
SOURCE_WIDTH = 766
SOURCE_HEIGHT = 1134
SOURCE_FEET_X = 660 - SOURCE_LEFT

DRAW_HEIGHT = 96
BODY_WIDTH = 24
BODY_HEIGHT = 80


class Player:
    def __init__(self, x, feet_y):
        # x는 양발의 가운데, feet_y는 지면에 닿는 발바닥 위치다.
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.image = pico2d.load_image(str(IMAGE_PATH))
        self.walk_data = json.loads(WALK_DATA_PATH.read_text(encoding="utf-8"))
        self.walk_image = pico2d.load_image(
            str(WALK_DATA_PATH.with_name(self.walk_data["image"]))
        )
        self.pressed_keys = set()
        self.face_dir = 1
        self.is_moving = False
        self.walk_distance = 0.0
        self.walk_frame = 0
        self.jump_requested = False

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
        if event.key not in (pico2d.SDLK_LEFT, pico2d.SDLK_RIGHT, pico2d.SDLK_SPACE):
            return
        if event.type == pico2d.SDL_KEYDOWN:
            if event.key == pico2d.SDLK_SPACE and event.key not in self.pressed_keys:
                self.jump_requested = True
            self.pressed_keys.add(event.key)
        elif event.type == pico2d.SDL_KEYUP:
            self.pressed_keys.discard(event.key)

    def clear_input(self):
        self.pressed_keys.clear()
        self.jump_requested = False

    def update(self, delta_time, area_width, solids=None):
        if solids is None:
            solids = [Solid(0, 0, area_width, 96)]
        if self.jump_requested:
            self.motion.jump()
        self.jump_requested = False
        direction = int(pico2d.SDLK_RIGHT in self.pressed_keys) - int(
            pico2d.SDLK_LEFT in self.pressed_keys
        )
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
        )
        self.motion.step(delta_time, direction, solids, area_width, margin)

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

    def draw(self):
        if self.is_moving:
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
            self.x + center_offset * self.face_dir,
            self.feet_y + (height / 2 - feet_y) * scale,
            width * scale, height * scale,
        )

    def get_bb(self):
        """이미지와 별도로 실제 지형 충돌에 사용하는 몸통 영역이다."""
        return self.motion.get_bb()

    def draw_debug(self):
        pico2d.draw_rectangle(*self.get_bb(), r=112, g=220, b=148)
        pico2d.draw_line(
            self.x - 5, self.feet_y, self.x + 5, self.feet_y,
            r=255, g=196, b=80,
        )
        pico2d.draw_line(
            self.x, self.feet_y - 5, self.x, self.feet_y + 5,
            r=255, g=196, b=80,
        )
