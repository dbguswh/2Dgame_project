"""운하 주택가의 지형과 필수 이동 경로."""

from dataclasses import dataclass

import pico2d

from lighting import LightRegion
from physics import Solid
from stage import GROUND_Y, Stage


@dataclass(frozen=True)
class EnemyPlacement:
    identity: str
    x: float
    feet_y: float
    bounds: tuple


class ResidentialStage(Stage):
    name = '운하 주택가'
    BRIDGE_TIME = 1.2

    def __init__(self):
        self.width = 2880
        self.start = (160, GROUND_Y)
        self.fixture_position = (2440, GROUND_Y)
        self.fixture_checkpoint = (2400, GROUND_Y)
        self.fixture_powered = False
        self.canal = (2496, 2688)
        self.exit_position = (2800, GROUND_Y)
        self.fuse_position = (1328, 208)
        self.fuse_checkpoint = (1456, GROUND_Y)
        self.light_regions = [LightRegion(0, GROUND_Y, self.width, 540)]
        self.solids = [
            Solid(0, 0, self.canal[0], GROUND_Y),
            Solid(self.canal[1], 0, self.width, GROUND_Y),
            Solid(288, GROUND_Y, 352, 128),
            Solid(896, GROUND_Y, 960, 128),
            Solid(1120, GROUND_Y, 1184, 128),
            Solid(1184, GROUND_Y, 1248, 160),
            Solid(1248, GROUND_Y, 1408, 192),
        ]
        self.enemy_placements = tuple(
            EnemyPlacement(f'residential-shade-{index}', x, GROUND_Y, bounds)
            for index, (x, bounds) in enumerate([
                (480, (352, 832)), (704, (352, 832)),
                (1664, (1568, 1888)), (1792, (1568, 1888)),
                (2080, (2016, 2304)), (2224, (2016, 2304)),
            ]))

    def draw(self, camera_x, screen_width, screen_height):
        background = (36, 40, 50) if self.fixture_powered else (19, 25, 38)
        pico2d.draw_rectangle(0, 0, screen_width - 1, screen_height - 1,
                              *background, filled=True)
        # 배경 건물은 충돌 지형과 구분한다. 세부 원화는 통행 경로 확정 후 적용한다.
        for index in range(16):
            x = index * 208 - camera_x * 0.35
            height = 200 + (index * 53) % 144
            pico2d.draw_rectangle(x, GROUND_Y, x + 168, height,
                                  27, 34, 48, filled=True)
            for floor in range(150, height - 16, 52):
                color = (170, 132, 74) if self.fixture_powered else (45, 54, 69)
                pico2d.draw_rectangle(x + 32, floor, x + 44, floor + 24,
                                      *color, filled=True)
        left, right = self.canal
        pico2d.draw_rectangle(left - camera_x, 0, right - camera_x, 44,
                              30, 62, 83, filled=True)
        for solid in self.solids:
            if solid.right < camera_x or solid.left > camera_x + screen_width:
                continue
            x = solid.left - camera_x
            color = (74, 65, 54) if solid.bottom == GROUND_Y else (51, 56, 65)
            pico2d.draw_rectangle(x, solid.bottom, solid.right - camera_x - 1,
                                  solid.top - 1, *color, filled=True)
            pico2d.draw_line(x, solid.top, solid.right - camera_x - 1, solid.top,
                              142, 148, 151)
        for lamp_x in (160, 816, 1488, 2384, 2768):
            self.draw_lamp(lamp_x - camera_x, lamp_x == 160 or self.fixture_powered)
        self.draw_fixture(camera_x)

    @staticmethod
    def draw_lamp(x, powered):
        pico2d.draw_rectangle(x - 2, GROUND_Y, x + 2, GROUND_Y + 160,
                              78, 86, 96, filled=True)
        color = (255, 216, 124) if powered else (73, 79, 90)
        pico2d.draw_rectangle(x - 10, GROUND_Y + 148, x + 10, GROUND_Y + 170,
                              *color, filled=True)
