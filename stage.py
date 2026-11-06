"""1주차 이동·충돌을 확인할 두 화면 길이의 구간."""

import pico2d

from physics import EPSILON, Solid


TILE_SIZE = 32
GROUND_Y = TILE_SIZE * 3


class Stage:
    def __init__(self):
        self.width = 1920
        self.start = (160, GROUND_Y)
        self.enemy_spawn = (440, GROUND_Y)
        self.combat_bounds = (288, 768)
        self.solids = [
            Solid(0, 0, 960, GROUND_Y),
            Solid(1024, 0, self.width, GROUND_Y),
            Solid(192, 224, 288, 240),
            Solid(320, 96, 384, 128),
            Solid(704, 96, 768, 128),
            Solid(768, 96, 832, 160),
            Solid(832, 96, 896, 192),
            Solid(896, 160, 960, 208),
            Solid(1248, 96, 1312, 128),
            Solid(1312, 96, 1376, 160),
            Solid(1376, 96, 1440, 192),
        ]

    def safe_position(self, motion):
        if not motion.on_ground:
            return None
        margin = motion.width / 2 + 8
        for solid in self.solids:
            if abs(motion.feet_y - solid.top) < EPSILON:
                if solid.left + margin <= motion.x <= solid.right - margin:
                    return motion.x, motion.feet_y
        return None

    def draw(self, camera_x, screen_width, screen_height):
        pico2d.draw_rectangle(0, 0, screen_width - 1, screen_height - 1,
                              19, 25, 38, filled=True)
        # 물이 있는 빈칸은 통과 가능한 바닥을 그리지 않는다.
        pico2d.draw_rectangle(960 - camera_x, 0, 1024 - camera_x, 44,
                              31, 65, 89, filled=True)
        for solid in self.solids:
            if solid.right < camera_x or solid.left > camera_x + screen_width:
                continue
            left, right = solid.left - camera_x, solid.right - camera_x
            pico2d.draw_rectangle(left, solid.bottom, right - 1, solid.top - 1,
                                  51, 56, 65, filled=True)
            pico2d.draw_line(left, solid.top, right - 1, solid.top, 137, 148, 159)

    def draw_debug(self, camera_x):
        for solid in self.solids:
            pico2d.draw_rectangle(solid.left - camera_x, solid.bottom,
                                  solid.right - camera_x, solid.top,
                                  r=109, g=153, b=207)
