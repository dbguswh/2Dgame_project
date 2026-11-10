"""1주차 이동·충돌을 확인할 두 화면 길이의 구간."""

import pico2d

from physics import EPSILON, Solid
from lighting import LightRegion


TILE_SIZE = 32
GROUND_Y = TILE_SIZE * 3


class Stage:
    def __init__(self):
        self.width = 1920
        self.start = (160, GROUND_Y)
        self.enemy_spawn = (440, GROUND_Y)
        self.combat_bounds = (288, 768)
        self.enemy_placements = ()
        self.fixture_position = (640, GROUND_Y)
        self.fixture_checkpoint = (608, GROUND_Y)
        self.fixture_powered = False
        self.fuse_state = 'ABSENT'
        self.light_regions = [LightRegion(0, GROUND_Y, self.width, 540)]
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

    def collect_pickups(self, player):
        """각 스테이지의 접촉 획득을 처리한다."""

    @property
    def objective(self):
        return '구역 조명 복구 완료' if self.fixture_powered else '목표: 조명 제어함을 찾아 복구하세요'

    def interaction_prompt(self, player):
        if self.can_interact(player):
            label = '복구 완료' if self.fixture_powered else 'E: 조명 복구'
            return (*self.fixture_position, label)
        return None

    def can_interact(self, player):
        x, y = self.fixture_position
        return (player.motion.on_ground and abs(player.x - x) <= 48
                and abs(player.feet_y - y) <= 8
                and not player.is_attacking and player.light_cast <= 0)

    def activate_fixture(self, player):
        if self.fixture_powered or not self.can_interact(player):
            return False
        self.fixture_powered = True
        return True

    def draw(self, camera_x, screen_width, screen_height):
        background = (31, 35, 45) if self.fixture_powered else (19, 25, 38)
        pico2d.draw_rectangle(0, 0, screen_width - 1, screen_height - 1,
                              *background, filled=True)
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
        self.draw_fixture(camera_x)

    def draw_fixture(self, camera_x):
        x, y = self.fixture_position
        x -= camera_x
        pico2d.draw_rectangle(x - 3, y, x + 3, y + 15, 86, 92, 102, filled=True)
        pico2d.draw_rectangle(x - 12, y + 12, x + 12, y + 42, 52, 61, 75, filled=True)
        pico2d.draw_rectangle(x - 12, y + 12, x + 12, y + 42, 151, 158, 166)
        color = (255, 223, 137) if self.fixture_powered else (143, 84, 68)
        pico2d.draw_circle(x, y + 31, 4, r=color[0], g=color[1], b=color[2], filled=True)
        pico2d.draw_line(x - 6, y + 20, x + 6, y + 20, *color)

    def draw_debug(self, camera_x):
        for solid in self.solids:
            pico2d.draw_rectangle(solid.left - camera_x, solid.bottom,
                                  solid.right - camera_x, solid.top,
                                  r=109, g=153, b=207)
