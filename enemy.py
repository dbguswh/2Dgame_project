"""Shade의 위치·이미지와 전투 상태를 관리한다."""

from pathlib import Path

import pico2d

from physics import Motion


IMAGE_PATH = Path(__file__).resolve().parent / 'assets/images/characters/shade.png'
DRAW_HEIGHT = 104
BODY_WIDTH = 36
BODY_HEIGHT = 88


class Shade:
    def __init__(self, x, feet_y, identity=0):
        self.identity = identity
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.image = pico2d.load_image(str(IMAGE_PATH))
        self.face_dir = -1
        self.health = 2

    @property
    def x(self):
        return self.motion.x

    @property
    def feet_y(self):
        return self.motion.feet_y

    @property
    def alive(self):
        return self.health > 0

    def get_bb(self):
        return self.motion.get_bb()

    def draw(self, camera_x=0):
        scale = DRAW_HEIGHT / 1101
        # 기본 이미지는 왼쪽을 본다. 긴 팔을 제외하고 양발 기준으로 정렬한다.
        self.image.clip_composite_draw(
            103, 12, 1265, 1101, 0, 'h' if self.face_dir > 0 else '',
            self.x - camera_x + (1265 / 2 - 803) * scale * -self.face_dir,
            self.feet_y + DRAW_HEIGHT / 2, 1265 * scale, DRAW_HEIGHT,
        )
        for index in range(2):
            left = self.x - camera_x - 12 + index * 13
            color = (202, 91, 214) if index < self.health else (69, 57, 78)
            pico2d.draw_rectangle(left, self.feet_y + 112, left + 10,
                                  self.feet_y + 116, *color, filled=True)

    def draw_debug(self, camera_x=0):
        left, bottom, right, top = self.get_bb()
        pico2d.draw_rectangle(left - camera_x, bottom, right - camera_x, top,
                              r=195, g=119, b=230)
