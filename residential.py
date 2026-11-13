"""운하 주택가의 지형과 필수 이동 경로."""

from dataclasses import dataclass

import pico2d

from lighting import LightRegion
from combat import overlaps
from physics import Solid
from stage import GROUND_Y, Stage
from environment import ResidentialScene
from respawn import RespawnDirector


@dataclass(frozen=True)
class EnemyPlacement:
    identity: str
    x: float
    feet_y: float
    bounds: tuple
    ranged: bool = False


class ResidentialStage(Stage):
    name = '운하 주택가'
    BRIDGE_TIME = 2.4
    UPPER_FLOOR_Y = 288
    BRIDGE_Y = 224

    def __init__(self):
        super().__init__()
        self.width = 2880
        self.start = (160, GROUND_Y)
        self.fixture_position = (2336, self.BRIDGE_Y)
        self.fixture_checkpoint = (2304, self.BRIDGE_Y)
        self.fixture_powered = False
        self.canal = (2368, 2752)
        self.bridge_solid = Solid(self.canal[0], self.BRIDGE_Y - 16, self.canal[1], self.BRIDGE_Y)
        self.bridge_gate = Solid(self.canal[0] - 12, self.BRIDGE_Y,
                                 self.canal[0] + 4, self.BRIDGE_Y + 80)
        self.exit_position = (2800, self.BRIDGE_Y)
        self.fuse_position = (1760, self.UPPER_FLOOR_Y + 16)
        self.battery_pack_position = (2160, 208)
        self.fuse_checkpoint = (1760, self.UPPER_FLOOR_Y)
        self.fuse_state = 'WORLD'
        self.scene = ResidentialScene()
        self.visual_time = 0.0
        self.light_regions = [LightRegion(0, GROUND_Y, self.width, 540)]
        self.stair_solids = ()
        # 얇은 상승 발판은 아래·옆에서 통과하고 내려올 때 윗면에 착지한다.
        # 발판 사이로 떨어져도 지상에서 왼쪽 첫 발판으로 돌아갈 수 있다.
        self.approach_ledges = (Solid(768, 128, 864, 144, one_way=True),
                                Solid(896, 176, 992, 192, one_way=True),
                                Solid(1024, 224, 1120, 240, one_way=True))
        self.upper_walkways = (Solid(1152, 268, 1808, self.UPPER_FLOOR_Y),)
        self.lower_walkways = (Solid(1872, 172, 2208, 192),)
        self.bridge_approaches = (Solid(2208, 204, 2368, self.BRIDGE_Y, one_way=True),
                                  Solid(2752, 204, 2880, self.BRIDGE_Y, one_way=True))
        self.return_ledges = (Solid(2240, 128, 2288, 144, one_way=True),
                              Solid(2304, 176, 2352, 192, one_way=True),
                              Solid(2768, 128, 2816, 144, one_way=True),
                              Solid(2832, 176, 2880, 192, one_way=True))
        self.solids = [
            Solid(0, 0, self.canal[0], GROUND_Y),
            Solid(self.canal[1], 0, self.width, GROUND_Y),
            Solid(288, GROUND_Y, 352, 128),
            *self.approach_ledges,
            *self.upper_walkways,
            *self.lower_walkways,
            *self.bridge_approaches,
            *self.return_ledges,
        ]
        self.enemy_placements = tuple(
            EnemyPlacement(f'residential-shade-{index}', x, y, bounds, ranged)
            for index, (x, y, bounds, ranged) in enumerate([
                (480, GROUND_Y, (352, 752), False), (640, GROUND_Y, (352, 752), True),
                (1248, self.UPPER_FLOOR_Y, (1152, 1632), False),
                (1392, self.UPPER_FLOOR_Y, (1152, 1632), False),
                (1520, self.UPPER_FLOOR_Y, (1152, 1632), True),
                (1952, 192, (1872, 2208), False), (2048, 192, (1872, 2208), False),
                (2144, 192, (1872, 2208), True),
            ]))
        self.respawns = RespawnDirector(self.enemy_placements)

    def collect_pickups(self, player):
        x, y = self.fuse_position
        if self.fuse_state == 'WORLD' and overlaps(player.get_bb(), (x - 10, y - 12, x + 10, y + 12)):
            self.fuse_state = 'CARRIED'
            player.checkpoint_position = self.fuse_checkpoint
            player.notice = '퓨즈 획득 · 오른쪽 제어함에 설치하세요'
            player.notice_time = 2.5
        x, y = self.battery_pack_position
        if (not self.battery_pack_collected and player.battery < player.max_battery
                and overlaps(player.get_bb(), (x - 10, y - 12, x + 10, y + 12))):
            amount = min(50, player.max_battery - player.battery)
            player.battery += amount
            self.battery_pack_collected = True
            player.notice = f'배터리 팩 획득 · 배터리 +{amount}'
            player.notice_time = 1.8

    def activate_fixture(self, player):
        if self.fixture_powered or not self.can_interact(player):
            return False
        if self.fuse_state != 'CARRIED':
            player.notice = '퓨즈가 필요합니다 · 위층 적 구간 뒤 정비 선반을 찾아보세요'
            player.notice_time = 2.0
            return False
        self.fuse_state = 'INSTALLED'
        self.fixture_powered = True
        self.bridge_elapsed = 0.0
        return True

    def apply_rewards(self, player):
        if self.bridge_ready and not self.reward_claimed:
            player.fragments += 2
            self.reward_claimed = True
            player.notice = '다리 복구 완료 · 전력 조각 2개 획득'
            player.notice_time = 2.4

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
        deploying = self.fixture_powered and not self.bridge_ready
        if deploying and self.bridge_gate not in self.solids:
            self.solids.append(self.bridge_gate)
        elif not deploying and self.bridge_gate in self.solids:
            self.solids.remove(self.bridge_gate)

    def restore_after_death(self):
        if self.fixture_powered:
            self.bridge_elapsed = self.BRIDGE_TIME
        self.sync_bridge()

    def near_exit(self, player):
        x, y = self.exit_position
        return (player.motion.on_ground and abs(player.x - x) <= 40
                and abs(player.feet_y - y) <= 8
                and not player.is_attacking and player.light_cast <= 0)

    def activate_exit(self, player):
        if self.completed or not self.near_exit(player):
            return False
        if not self.bridge_ready:
            player.notice = '주택가 전력을 복구하고 다리를 펼쳐야 합니다'
            player.notice_time = 2
            return False
        self.completed = True
        return True

    @property
    def objective(self):
        if self.completed:
            return '운하 주택가 · 복구 완료'
        if self.fixture_powered:
            if not self.bridge_ready:
                if self.bridge_elapsed < 0.25:
                    return '운하 주택가 · 교량 잠금 해제 중'
                if self.bridge_elapsed > self.BRIDGE_TIME - 0.35:
                    return '운하 주택가 · 교량 결합 중'
                return '운하 주택가 · 대형 교량 전개 중'
            return '운하 주택가 · 다리를 건너 출구로 이동하세요'
        if self.fuse_state == 'CARRIED':
            return '운하 주택가 · 위층 교량 제어함에 퓨즈를 설치하세요'
        return '운하 주택가 · 발판을 올라 위층 적 구간 뒤의 퓨즈를 찾으세요'

    def interaction_prompt(self, player):
        if self.near_exit(player):
            return (*self.exit_position, 'E: 출구 이동' if self.bridge_ready else '다리 복구 필요')
        if self.can_interact(player):
            label = ('복구 완료' if self.fixture_powered else
                     'E: 퓨즈 설치' if self.fuse_state == 'CARRIED' else '퓨즈 필요')
            return (*self.fixture_position, label)
        return None

    def draw(self, camera_x, screen_width, screen_height):
        self.scene.draw(self, camera_x, screen_width, screen_height)
        self.draw_fixture(camera_x)
        self.draw_bridge(camera_x)
        x, y = self.exit_position
        x -= camera_x
        color = (162, 146, 102) if self.bridge_ready else (74, 84, 94)
        pico2d.draw_rectangle(x - 19, y, x + 19, y + 100, 17, 25, 35, filled=True)
        for side in (-21, 18):
            pico2d.draw_rectangle(x + side, y, x + side + 3, y + 102, *color, filled=True)
        pico2d.draw_rectangle(x - 22, y + 101, x + 22, y + 105, *color, filled=True)
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
        if not self.battery_pack_collected:
            x, y = self.battery_pack_position
            x -= camera_x
            pico2d.draw_rectangle(x - 9, y - 10, x + 9, y + 10, 63, 82, 97, filled=True)
            pico2d.draw_rectangle(x - 9, y - 10, x + 9, y + 10, 134, 159, 170)
            pico2d.draw_rectangle(x - 4, y + 10, x + 4, y + 13, 164, 170, 165, filled=True)
            for bar_y in (y - 6, y - 1, y + 4):
                pico2d.draw_rectangle(x - 5, bar_y, x + 5, bar_y + 2,
                                      137, 195, 203, filled=True)

    def draw_labels(self, font, camera_x):
        for x, y, label in ((133, GROUND_Y + 188, '대피소'),
                            (1500, 411, '정비 선반 · 퓨즈'),
                            (1880, 345, '하강 발판 · 배터리'),
                            (2782, self.BRIDGE_Y + 140, '병원')):
            font.draw(x - camera_x, y, label, (192, 178, 146))
        x, y = 2854 - camera_x, self.BRIDGE_Y + 140
        pico2d.draw_line(x - 12, y, x, y, 192, 178, 146)
        pico2d.draw_line(x - 5, y + 5, x, y, 192, 178, 146)
        pico2d.draw_line(x - 5, y - 5, x, y, 192, 178, 146)
        if not self.battery_pack_collected:
            x, y = self.battery_pack_position
            font.draw(x - camera_x - 40, y + 39, '배터리 +50', (157, 197, 208))

    def draw_bridge(self, camera_x):
        from bridge_visuals import draw_bridge
        draw_bridge(self, camera_x)

