"""Warden의 정지 이미지와 발 기준 좌표를 관리한다."""

from pathlib import Path

import pico2d


IMAGE_PATH = Path(__file__).resolve().parent / "assets/images/characters/player.png"

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
MOVE_SPEED = 128  # 초당 4타일. 표시 창의 배율과 무관한 게임 좌표 기준이다.


class Player:
    def __init__(self, x, feet_y):
        # x는 양발의 가운데, feet_y는 지면에 닿는 발바닥 위치다.
        self.x = x
        self.feet_y = feet_y
        self.image = pico2d.load_image(str(IMAGE_PATH))
        self.pressed_keys = set()
        self.face_dir = 1

    def handle_event(self, event):
        if event.key not in (pico2d.SDLK_LEFT, pico2d.SDLK_RIGHT):
            return
        if event.type == pico2d.SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
        elif event.type == pico2d.SDL_KEYUP:
            self.pressed_keys.discard(event.key)

    def clear_input(self):
        self.pressed_keys.clear()

    def update(self, delta_time, area_width):
        direction = int(pico2d.SDLK_RIGHT in self.pressed_keys) - int(
            pico2d.SDLK_LEFT in self.pressed_keys
        )
        if direction:
            self.face_dir = direction
        self.x += direction * MOVE_SPEED * delta_time

        # 두 방향 모두에서 전체 그림이 화면 안에 남도록 초기 경계를 제한한다.
        scale = DRAW_HEIGHT / SOURCE_HEIGHT
        margin = max(SOURCE_FEET_X, SOURCE_WIDTH - SOURCE_FEET_X) * scale
        self.x = max(margin, min(area_width - margin, self.x))

    def draw(self):
        scale = DRAW_HEIGHT / SOURCE_HEIGHT
        center_offset = (SOURCE_WIDTH / 2 - SOURCE_FEET_X) * scale
        self.image.clip_composite_draw(
            SOURCE_LEFT, SOURCE_BOTTOM, SOURCE_WIDTH, SOURCE_HEIGHT,
            0, "h" if self.face_dir < 0 else "",
            self.x + center_offset * self.face_dir, self.feet_y + DRAW_HEIGHT / 2,
            SOURCE_WIDTH * scale, DRAW_HEIGHT,
        )

    def get_bb(self):
        """다음 이동 단계에서 사용할 몸통 충돌 영역의 초기 크기다."""
        return (
            self.x - BODY_WIDTH / 2, self.feet_y,
            self.x + BODY_WIDTH / 2, self.feet_y + BODY_HEIGHT,
        )

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
