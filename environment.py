"""운하 도시의 원경·중경·충돌 지형에 맞춘 전경을 그린다."""

from math import floor, sin
from pathlib import Path

import pico2d

from effects import blended, glow
from stage import GROUND_Y


FACADE_PATH = Path(__file__).resolve().parent / 'assets/images/environments/residential_facades.png'


class ResidentialScene:
    def __init__(self):
        self.facades = None

    def draw(self, stage, camera_x, width, height):
        if self.facades is None:
            self.facades = pico2d.load_image(str(FACADE_PATH))
        restored = stage.fixture_powered
        # 하늘과 먼 지붕은 중경 건물보다 느리게 이동한다.
        for y in range(0, height, 8):
            ratio = y / height
            lift = 4 if restored else 0
            color = (int(22 - 13 * ratio) + lift, int(31 - 15 * ratio) + lift,
                     int(46 - 15 * ratio) + lift)
            pico2d.draw_rectangle(0, y, width - 1, y + 7, *color, filled=True)
        with blended():
            glow(836 - camera_x * 0.04, 404, 76, (105, 126, 162), alpha=20)
        pico2d.draw_circle(836 - camera_x * 0.04, 404, 17,
                           r=112, g=132, b=161, filled=True)
        for index in range(16):
            x = index * 152 - camera_x * 0.18 - 40
            top = 240 + (index * 47) % 126
            pico2d.draw_rectangle(x, GROUND_Y, x + 112, top, 17, 25, 40, filled=True)
            pico2d.draw_line(x - 5, top, x + 56, top + 24, 29, 39, 55)
            pico2d.draw_line(x + 56, top + 24, x + 117, top, 29, 39, 55)
        # 원화의 종횡비를 유지한다. 스크롤 끝에서도 파사드의 빈 가장자리가 드러나지 않는다.
        draw_width = 1536
        draw_height = draw_width * self.facades.h / self.facades.w
        self.facades.opacify(0.96 if restored else 0.83)
        self.facades.draw(draw_width / 2 - camera_x * 0.3,
                          GROUND_Y + draw_height / 2, draw_width, draw_height)
        self.facades.opacify(1)
        self.draw_water(stage, camera_x)
        for solid in stage.solids:
            if solid == stage.bridge_solid:
                continue
            if solid.right < camera_x or solid.left > camera_x + width:
                continue
            if solid.bottom == GROUND_Y:
                self.draw_crate(solid, camera_x)
            else:
                self.draw_stone(solid, camera_x, width)
        self.draw_street_details(stage, camera_x, width)
        for lamp_x in (160, 816, 1488, 2384, 2768):
            if -100 < lamp_x - camera_x < width + 100:
                self.draw_lamp(lamp_x - camera_x, lamp_x == 160 or restored)

    @staticmethod
    def draw_stone(solid, camera_x, width):
        left, right = solid.left - camera_x, solid.right - camera_x
        pico2d.draw_rectangle(left, solid.bottom, right - 1, solid.top - 1,
                              30, 35, 43, filled=True)
        for row, y in enumerate(range(int(solid.bottom), int(solid.top - 8), 24)):
            offset = 22 if row % 2 else 0
            start = max(solid.left, floor((camera_x - offset) / 44) * 44 + offset)
            for x in range(int(start), int(min(solid.right, camera_x + width + 44)), 44):
                end = min(x + 41, solid.right - 2)
                shade = (int(x) * 7 + row * 13) % 13
                pico2d.draw_rectangle(x - camera_x + 2, y + 2, end - camera_x, y + 21,
                                      46 + shade, 48 + shade, 56 + shade, filled=True)
                pico2d.draw_line(x - camera_x + 3, y + 21, end - camera_x, y + 21,
                                  65 + shade, 66 + shade, 71 + shade)
        for x in range(int(max(solid.left, floor(camera_x / 32) * 32)),
                       int(min(solid.right, camera_x + width + 32)), 32):
            right_x = min(x + 30, solid.right - 1) - camera_x
            pico2d.draw_rectangle(x - camera_x, solid.top - 8, right_x, solid.top - 1,
                                  91, 91, 94, filled=True)
            pico2d.draw_line(x - camera_x, solid.top, right_x, solid.top, 163, 157, 142)

    @staticmethod
    def draw_crate(solid, camera_x):
        x, right = solid.left - camera_x, solid.right - camera_x
        pico2d.draw_rectangle(x, solid.bottom, right - 1, solid.top - 1,
                              65, 48, 35, filled=True)
        for plank_x in range(int(solid.left + 3), int(solid.right), 16):
            pico2d.draw_line(plank_x - camera_x, solid.bottom + 3,
                              plank_x - camera_x, solid.top - 4, 99, 73, 47)
        for y in (solid.bottom + 4, solid.top - 7):
            pico2d.draw_rectangle(x, y, right - 1, y + 4, 120, 92, 60, filled=True)
        pico2d.draw_line(x + 4, solid.bottom + 8, right - 5, solid.top - 9, 143, 110, 70)
        pico2d.draw_line(x + 4, solid.bottom + 9, right - 5, solid.top - 8, 143, 110, 70)
        pico2d.draw_line(x, solid.top, right - 1, solid.top, 194, 165, 116)
        for bolt_x in (x + 5, right - 6):
            for bolt_y in (solid.bottom + 6, solid.top - 5):
                pico2d.draw_rectangle(bolt_x, bolt_y, bolt_x + 2, bolt_y + 2,
                                      163, 164, 153, filled=True)

    @staticmethod
    def draw_street_details(stage, camera_x, width):
        # 배경과 별개인 현장 표식으로 실제 이동 구역을 식별한다.
        for left, right in ((24, 240), (1008, 1096), (2704, 2872)):
            if right < camera_x or left > camera_x + width:
                continue
            for x in range(left, right, 24):
                pico2d.draw_line(x - camera_x, GROUND_Y, x - camera_x, GROUND_Y + 42,
                                  62, 74, 83)
            pico2d.draw_line(left - camera_x, GROUND_Y + 43,
                              right - camera_x, GROUND_Y + 43, 91, 100, 104)
        for x in (120, 1292, 2776):
            sx = x - camera_x
            pico2d.draw_rectangle(sx, GROUND_Y + 172, sx + 96, GROUND_Y + 205,
                                  38, 43, 47, filled=True)
            pico2d.draw_rectangle(sx, GROUND_Y + 172, sx + 96, GROUND_Y + 205, 117, 105, 78)
        # 정비소의 전선은 제어함으로 이어지는 흐름을 암시한다.
        for left, right in ((1120, 1408), (2024, 2440)):
            for x in range(left, right, 16):
                y = GROUND_Y + 148 - 14 * sin((x - left) / (right - left) * 3.14159)
                pico2d.draw_line(x - camera_x, y, x + 16 - camera_x, y - 1, 67, 62, 56)

    @staticmethod
    def draw_lamp(x, powered):
        y = GROUND_Y
        if powered:
            with blended():
                glow(x, y + 88, 100, alpha=26, squash=1.05)
                glow(x, y + 2, 72, alpha=58, squash=0.16)
                glow(x, y + 166, 34, alpha=92)
        pico2d.draw_rectangle(x - 5, y, x + 5, y + 7, 73, 78, 84, filled=True)
        pico2d.draw_rectangle(x - 2, y + 7, x + 2, y + 154, 74, 82, 87, filled=True)
        pico2d.draw_line(x - 3, y + 12, x - 3, y + 150, 107, 112, 109)
        color = (247, 202, 119) if powered else (56, 63, 73)
        pico2d.draw_rectangle(x - 8, y + 154, x + 8, y + 174, *color, filled=True)
        for side in (-9, 8):
            pico2d.draw_rectangle(x + side, y + 152, x + side + 2, y + 176,
                                  89, 94, 91, filled=True)
        pico2d.draw_rectangle(x - 12, y + 176, x + 12, y + 179, 92, 97, 95, filled=True)
        pico2d.draw_line(x - 12, y + 179, x, y + 186, 119, 120, 109)
        pico2d.draw_line(x, y + 186, x + 12, y + 179, 119, 120, 109)

    @staticmethod
    def draw_water(stage, camera_x):
        left, right = stage.canal
        pico2d.draw_rectangle(left - camera_x, 0, right - camera_x, 44,
                              15, 38, 56, filled=True)
        for index in range(14):
            y = 3 + index * 3
            offset = int(sin(stage.visual_time * 0.8 + index) * 9)
            x = left + (index * 47) % 145 + offset
            color = (130, 105, 65) if stage.fixture_powered and index % 3 == 0 else (37, 67, 85)
            pico2d.draw_line(max(left, x) - camera_x, y,
                              min(right, x + 25) - camera_x, y, *color)
