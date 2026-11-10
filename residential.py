"""운하 주택가의 지형과 필수 이동 경로."""

from dataclasses import dataclass

import pico2d

from lighting import LightRegion
from combat import overlaps
from physics import Solid
from stage import GROUND_Y, Stage
from environment import ResidentialScene


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
        super().__init__()
        self.width = 2880
        self.start = (160, GROUND_Y)
        self.fixture_position = (2440, GROUND_Y)
        self.fixture_checkpoint = (2400, GROUND_Y)
        self.fixture_powered = False
        self.canal = (2496, 2688)
        self.bridge_solid = Solid(self.canal[0], GROUND_Y - 16, self.canal[1], GROUND_Y)
        self.exit_position = (2800, GROUND_Y)
        self.fuse_position = (1328, 208)
        self.fuse_checkpoint = (1456, GROUND_Y)
        self.fuse_state = 'WORLD'
        self.scene = ResidentialScene()
        self.visual_time = 0.0
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

    def collect_pickups(self, player):
        x, y = self.fuse_position
        if self.fuse_state == 'WORLD' and overlaps(player.get_bb(), (x - 10, y - 12, x + 10, y + 12)):
            self.fuse_state = 'CARRIED'
            player.checkpoint_position = self.fuse_checkpoint
            player.notice = '퓨즈 획득 · 오른쪽 제어함에 설치하세요'
            player.notice_time = 2.5

    def activate_fixture(self, player):
        if self.fixture_powered or not self.can_interact(player):
            return False
        if self.fuse_state != 'CARRIED':
            player.notice = '퓨즈가 필요합니다 · 정비 선반을 찾아보세요'
            player.notice_time = 2.0
            return False
        self.fuse_state = 'INSTALLED'
        self.fixture_powered = True
        self.bridge_elapsed = 0.0
        return True

    @property
    def bridge_ready(self):
        return self.fixture_powered and self.bridge_elapsed >= self.BRIDGE_TIME

    def update(self, delta_time):
        self.visual_time += max(0, delta_time)
        if self.fixture_powered:
            self.bridge_elapsed = min(self.BRIDGE_TIME, self.bridge_elapsed + max(0, delta_time))
        self.sync_bridge()

    def sync_bridge(self):
        if self.bridge_ready and self.bridge_solid not in self.solids:
            self.solids.append(self.bridge_solid)
        elif not self.bridge_ready and self.bridge_solid in self.solids:
            self.solids.remove(self.bridge_solid)

    def restore_after_death(self):
        if self.fixture_powered:
            self.bridge_elapsed = self.BRIDGE_TIME
        self.sync_bridge()

    @property
    def objective(self):
        if self.fixture_powered:
            if not self.bridge_ready:
                return '운하 주택가 · 다리 전개 중'
            return '운하 주택가 · 다리를 건너 출구로 이동하세요'
        if self.fuse_state == 'CARRIED':
            return '운하 주택가 · 오른쪽 제어함에 퓨즈를 설치하세요'
        return '운하 주택가 · 정비 선반의 퓨즈를 찾으세요'

    def interaction_prompt(self, player):
        if self.can_interact(player):
            label = ('복구 완료' if self.fixture_powered else
                     'E: 퓨즈 설치' if self.fuse_state == 'CARRIED' else '퓨즈 필요')
            return (*self.fixture_position, label)
        return None

    def draw(self, camera_x, screen_width, screen_height):
        self.scene.draw(self, camera_x, screen_width, screen_height)
        self.draw_fixture(camera_x)
        self.draw_bridge(camera_x)
        if self.fuse_state == 'WORLD':
            from effects import blended, glow
            x, y = self.fuse_position
            x -= camera_x
            with blended():
                glow(x, y, 25, alpha=65)
            pico2d.draw_rectangle(x - 5, y - 12, x + 5, y + 12, 107, 143, 151, filled=True)
            for cap_y in (y - 12, y + 8):
                pico2d.draw_rectangle(x - 7, cap_y, x + 7, cap_y + 4,
                                      199, 173, 115, filled=True)
            pico2d.draw_line(x, y - 6, x, y + 6, 245, 218, 146)

    def draw_labels(self, font, camera_x):
        for x, label in ((133, '대피소'), (1305, '정비소'), (2782, '병원')):
            font.draw(x - camera_x, GROUND_Y + 188, label, (192, 178, 146))
        x, y = 2854 - camera_x, GROUND_Y + 188
        pico2d.draw_line(x - 12, y, x, y, 192, 178, 146)
        pico2d.draw_line(x - 5, y + 5, x, y, 192, 178, 146)
        pico2d.draw_line(x - 5, y - 5, x, y, 192, 178, 146)

    def draw_bridge(self, camera_x):
        from math import cos, sin, pi
        left, right = self.canal
        # 펼쳐지는 두 반쪽은 기동 중 장식이다. 바닥 판정은 전개 완료 시 한 번에 추가한다.
        fraction = self.bridge_elapsed / self.BRIDGE_TIME if self.fixture_powered else 0
        angle = (1 - fraction) * pi / 2
        length = (right - left) / 2
        for hinge, direction in ((left, 1), (right, -1)):
            x = hinge - camera_x
            tip_x = x + direction * length * cos(angle)
            tip_y = GROUND_Y + length * sin(angle)
            for offset in range(8):
                pico2d.draw_line(x, GROUND_Y - offset, tip_x, tip_y - offset, 151, 128, 86)
        if self.bridge_ready:
            pico2d.draw_line(left - camera_x, GROUND_Y + 28,
                              right - camera_x, GROUND_Y + 28, 133, 138, 139)
            for post in range(left, right + 1, 32):
                pico2d.draw_line(post - camera_x, GROUND_Y,
                                  post - camera_x, GROUND_Y + 28, 133, 138, 139)

