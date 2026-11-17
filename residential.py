"""운하 주택가의 지형과 필수 이동 경로."""

import pico2d

from lighting import LightRegion
from combat import overlaps
from physics import Solid
from stage import GROUND_Y, Stage, EnemyPlacement
from environment import ResidentialScene
from respawn import RespawnDirector
from supplies import SupplyBox, draw_battery_pack
from fragment_cache import FragmentCache
from inventory import ITEM_NAMES, LIGHT_BOMB, SPEED, SHIELD
from combat_seals import CombatSeal


class ResidentialStage(Stage):
    name = '운하 주택가'
    stage_id = 'residential'
    next_stage_id = 'hospital'
    destination_name = '운하 병원'
    BRIDGE_TIME = 2.4
    UPPER_FLOOR_Y = 288
    WORKSHOP_Y = 304
    BRIDGE_Y = 224

    def __init__(self):
        super().__init__()
        self.width = 2880
        self.start = (160, GROUND_Y)
        self.fixture_position = (1184, self.UPPER_FLOOR_Y)
        self.fixture_checkpoint = self.fixture_position
        self.fixture_seen = False
        self.bridge_approach_position = (2304, self.BRIDGE_Y)
        self.fixture_powered = False
        self.canal = (2368, 2752)
        self.bridge_solid = Solid(self.canal[0], self.BRIDGE_Y - 16, self.canal[1], self.BRIDGE_Y)
        self.bridge_gate = Solid(self.canal[0] - 12, self.BRIDGE_Y,
                                 self.canal[0] + 4, self.BRIDGE_Y + 80)
        self.exit_position = (2800, self.BRIDGE_Y)
        self.fuse_position = (2240, self.WORKSHOP_Y + 16)
        self.battery_pack_position = (1760, self.UPPER_FLOOR_Y + 16)
        self.return_battery_position = (2104, self.WORKSHOP_Y + 16)
        self.return_battery_collected = False
        self.supply_boxes = (SupplyBox('ascent-medkit', 832, 144),
                             SupplyBox('workshop-medkit', 1648, GROUND_Y),
                             SupplyBox('rooftop-light-bomb', 1408, self.UPPER_FLOOR_Y, item=LIGHT_BOMB),
                             SupplyBox('lower-detour-speed', 1456, 144, item=SPEED),
                             SupplyBox('connector-shield', 1848, 256, item=SHIELD))
        self.fragment_cache = FragmentCache('lower-power-cache', 2264, 144)
        self.fuse_checkpoint = (2240, self.WORKSHOP_Y)
        self.fuse_state = 'WORLD'
        self.scene = ResidentialScene()
        self.visual_time = 0.0
        self.reveal_light_elapsed = 0.0
        self.light_regions = [LightRegion(0, GROUND_Y, self.width, 540)]
        self.stair_solids = ()
        # 얇은 상승 발판은 아래·옆에서 통과하고 내려올 때 윗면에 착지한다.
        # 발판 사이로 떨어져도 지상에서 왼쪽 첫 발판으로 돌아갈 수 있다.
        self.approach_ledges = (Solid(768, 128, 896, 144, one_way=True),
                                Solid(896, 176, 992, 192, one_way=True),
                                Solid(1024, 224, 1120, 240, one_way=True))
        self.upper_walkways = (Solid(1152, 268, 1808, self.UPPER_FLOOR_Y, one_way=True),
                               Solid(1872, self.WORKSHOP_Y - 20, 2272, self.WORKSHOP_Y))
        self.workshop_ledges = (Solid(1808, 240, 1904, 256, one_way=True),)
        self.supply_ledges = (Solid(1376, 128, 1520, 144, one_way=True),)
        # 아래 골목에서 옥상/정비실 연결로로 다시 올라가는 동쪽 계단식 발판.
        self.lower_walkways = (Solid(1664,128,1744,144,one_way=True),
                               Solid(1736,176,1816,192,one_way=True),
                               Solid(1792,224,1856,240,one_way=True))
        self.bridge_approaches = (Solid(2208, 204, 2368, self.BRIDGE_Y, one_way=True),
                                  Solid(2752, 204, 2880, self.BRIDGE_Y, one_way=True))
        self.return_ledges = (Solid(2224, 128, 2312, 144, one_way=True),
                              Solid(2304, 176, 2352, 192, one_way=True),
                              Solid(2768, 128, 2816, 144, one_way=True),
                              Solid(2832, 176, 2880, 192, one_way=True))
        self.solids = [
            Solid(0, 0, self.canal[0], GROUND_Y),
            Solid(self.canal[1], 0, self.width, GROUND_Y),
            Solid(384, GROUND_Y, 448, 128),
            *self.approach_ledges,
            *self.upper_walkways,
            *self.workshop_ledges,
            *self.supply_ledges,
            *self.lower_walkways,
            *self.bridge_approaches,
            *self.return_ledges,
        ]
        self.enemy_placements = tuple(
            EnemyPlacement(f'residential-shade-{index}', x, y, bounds, ranged,kind)
            for index, (x, y, bounds, ranged,kind) in enumerate([
                (560, GROUND_Y, (448, 752), False,'shade'), (704, GROUND_Y, (448, 752), True,'shade'),
                (1328, self.UPPER_FLOOR_Y, (1280, 1712), False,'shade'),
                (1040, GROUND_Y, (960, 1280), False,'shade'),
                (1600, self.UPPER_FLOOR_Y, (1280, 1712), False,'wraith'),
                (1904, self.WORKSHOP_Y, (1872, 2064), False,'shade'),
                (1168, GROUND_Y, (960, 1280), True,'shade'),
                (2032, self.WORKSHOP_Y, (1872, 2064), True,'shade'),
            ]))
        self.respawns = RespawnDirector(self.enemy_placements)
        self.combat_seals=[CombatSeal('residential-shade-0',Solid(748,96,756,320)),
                           CombatSeal('residential-shade-2',Solid(1804,96,1812,416)),
                           CombatSeal('residential-shade-7',None)]
        self.sync_combat_seals()
        # 정비실이 전부 점등되면 연결 발판을 거쳐 옥상으로 후퇴할 수 있다.
        # 처음부터 순찰 범위를 넓히지 않고 빛 탈출이 막힌 개체에만 적용한다.
        self.light_retreat_bounds = {
            e.identity: (1280, 2064) for e in self.enemy_placements
            if e.feet_y == self.WORKSHOP_Y
        }

    def sync_combat_seals(self):
        for seal in self.combat_seals:
            if seal.barrier is None:continue
            if seal.opened and seal.barrier in self.solids:self.solids.remove(seal.barrier)
            elif not seal.opened and seal.barrier not in self.solids:self.solids.append(seal.barrier)

    def update_combat_seals(self,enemies):
        actors={e.identity:e for e in enemies}
        for seal in self.combat_seals:
            actor=actors.get(seal.target)
            if not seal.opened and actor is not None and not actor.alive and actor.death_by_hit:
                seal.opened=True;seal.elapsed=0
        self.sync_combat_seals()

    def capture_state(self):
        return tuple(s.opened for s in self.combat_seals)

    def restore_state(self,state):
        if len(state)==len(self.combat_seals):
            for seal,opened in zip(self.combat_seals,state):seal.opened=opened;seal.elapsed=.5 if opened else 0
        self.sync_combat_seals()

    def draw_combat_targets(self,enemies,camera_x):
        from combat_seals import draw_target_mark
        targets={s.target for s in self.combat_seals if not s.opened}
        for e in enemies:
            if e.alive and e.identity in targets:draw_target_mark(e,camera_x)

    @property
    def fuse_unlocked(self):
        return all(seal.opened for seal in self.combat_seals)

    def collect_pickups(self, player):
        for box in self.supply_boxes:
            x, y = box.pickup_position
            if (box.pickup_ready and overlaps(player.get_bb(), (x - 8, y - 9, x + 8, y + 10))
                    and player.add_item(box.item)):
                box.claimed = True
        if (player.motion.on_ground and abs(player.x - self.fixture_position[0]) <= 96
                and abs(player.feet_y - self.fixture_position[1]) <= 8):
            self.fixture_seen = True
        x, y = self.fuse_position
        if self.fuse_unlocked and self.fuse_state == 'WORLD' and overlaps(player.get_bb(), (x - 10, y - 12, x + 10, y + 12)):
            self.fuse_state = 'CARRIED'
            player.checkpoint_position = self.fuse_checkpoint
            player.notice = '퓨즈 획득 · 왼쪽 중앙 제어함으로 돌아가세요'
            player.notice_time = 2.5
        for position, flag in ((self.battery_pack_position, 'battery_pack_collected'),
                               (self.return_battery_position, 'return_battery_collected')):
            x, y = position
            if (not getattr(self, flag) and player.battery < player.max_battery
                    and overlaps(player.get_bb(), (x - 10, y - 12, x + 10, y + 12))):
                amount = min(50, player.max_battery - player.battery)
                player.battery += amount
                setattr(self, flag, True)
                player.notice = f'배터리 팩 획득 · 배터리 +{amount}'
                player.notice_time = 1.8

    def nearby_supply(self, player):
        if not player.motion.on_ground or player.is_attacking or player.light_cast > 0:
            return None
        return next((box for box in sorted((*self.supply_boxes, self.fragment_cache),
                                          key=lambda b: abs(player.x - b.x))
                     if not box.opened and abs(player.x - box.x) <= 48
                     and abs(player.feet_y - box.feet_y) <= 8), None)

    def can_interact(self, player):
        if not super().can_interact(player):
            return False
        # 제어함과 옥상 보급함의 범위가 겹쳐도 안내한 가까운 대상만 조작한다.
        box = self.nearby_supply(player)
        return box is None or abs(player.x - self.fixture_position[0]) <= abs(player.x - box.x)

    def activate_supply(self, player):
        box = self.nearby_supply(player)
        if box is None or self.can_interact(player):
            return False
        if box.open():
            if box is self.fragment_cache:
                player.fragments += 1
                player.notice, player.notice_time = '선택 보급고 · 전력 조각 +1', 1.8
            else:
                player.notice, player.notice_time = f'{ITEM_NAMES[box.item]} 보급함 개봉 · 앞의 아이템을 회수하세요', 1.4
            return True
        player.notice, player.notice_time = '이미 개봉한 보급함입니다', 1.0
        return False

    def activate_fixture(self, player):
        if self.fixture_powered or not self.can_interact(player):
            return False
        if self.fuse_state != 'CARRIED':
            self.fixture_seen = True
            player.notice = '퓨즈가 필요합니다 · 오른쪽 정비실에서 회수해 돌아오세요'
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
        for seal in self.combat_seals:
            if self.fixture_powered:seal.opened=True
            if seal.opened:seal.elapsed=min(.5,seal.elapsed+max(0,delta_time))
        self.sync_combat_seals()
        for box in self.supply_boxes:
            box.update(delta_time)
        self.fragment_cache.update(delta_time)
        if self.fixture_powered:
            self.bridge_elapsed = min(self.BRIDGE_TIME, self.bridge_elapsed + max(0, delta_time))
            self.reveal_light_elapsed += max(0,delta_time)
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
            return '운하 주택가 · 왼쪽 중앙 제어함으로 돌아가 퓨즈를 설치하세요'
        if not self.combat_seals[0].opened:return '운하 주택가 · 표식 침입자를 처치해 입구 봉쇄를 해제하세요'
        if self.fixture_seen and not self.combat_seals[1].opened:return '운하 주택가 · 옥상 표식 침입자를 처치해 연결로를 여세요'
        if self.combat_seals[1].opened and not self.combat_seals[2].opened:return '운하 주택가 · 정비실 표식 침입자를 처치해 퓨즈를 확보하세요'
        if self.fixture_seen:
            return '운하 주택가 · 오른쪽 정비실에서 퓨즈를 회수하세요'
        return '운하 주택가 · 발판을 올라 중앙 제어함을 찾으세요'

    def interaction_prompt(self, player):
        if (self.fuse_state=='WORLD' and not self.fuse_unlocked
                and abs(player.x-self.fuse_position[0])<60 and abs(player.feet_y-self.WORKSHOP_Y)<10):
            return (*self.fuse_position,'표식 침입자 처치 후 개방')
        if self.near_exit(player):
            return (*self.exit_position, 'E: 출구 이동' if self.bridge_ready else '다리 복구 필요')
        if self.can_interact(player):
            label = ('복구 완료' if self.fixture_powered else
                     'E: 전력 복구 · 퓨즈 설치' if self.fuse_state == 'CARRIED' else '퓨즈 필요')
            return (*self.fixture_position, label)
        box = self.nearby_supply(player)
        if box is not None and not box.opened:
            if box is self.fragment_cache:
                return box.x, box.feet_y, 'E: 선택 보급고 · 조각 +1'
            return box.x, box.feet_y, f'E: {ITEM_NAMES[box.item]} 보급함 열기'
        return None

    def draw(self, camera_x, screen_width, screen_height):
        self.scene.draw(self, camera_x, screen_width, screen_height)
        for box in self.supply_boxes:
            box.draw(camera_x)
        self.fragment_cache.draw(camera_x)
        self.draw_fixture(camera_x)
        self.draw_bridge(camera_x)
        for seal in self.combat_seals:seal.draw(camera_x)
        x, y = self.exit_position
        x -= camera_x
        color = (162, 146, 102) if self.bridge_ready else (74, 84, 94)
        pico2d.draw_rectangle(x - 19, y, x + 19, y + 100, 17, 25, 35, filled=True)
        for side in (-21, 18):
            pico2d.draw_rectangle(x + side, y, x + side + 3, y + 102, *color, filled=True)
        pico2d.draw_rectangle(x - 22, y + 101, x + 22, y + 105, *color, filled=True)
        for position, collected in ((self.battery_pack_position, self.battery_pack_collected),
                                     (self.return_battery_position, self.return_battery_collected)):
            if not collected:
                draw_battery_pack(position[0] - camera_x, position[1])

    def draw_labels(self, font, camera_x):
        from controls_view import fonts
        small,_=fonts()
        # 목적지 이름만 고정 폭 명패로 표시한다. 보급/이동 화살표는 HUD와 중복하지 않는다.
        for wx,y,label,w in ((160,284,'대피소',72),
                              (2112,408,'정비실',78),(2800,364,'병원',64)):
            x=wx-camera_x
            if not 18+w/2 <= x <= 942-w/2:continue
            pico2d.draw_rectangle(x-w/2,y-13,x+w/2,y+13,13,22,31,filled=True)
            pico2d.draw_line(x-w/2,y-13,x+w/2,y-13,105,115,119)
            small.draw(x-w/2+10,y,label,(202,201,183))
        from power_objectives import draw_labels
        draw_labels(self,camera_x)

    def draw_bridge(self, camera_x):
        from bridge_visuals import draw_bridge
        draw_bridge(self, camera_x)

    def draw_fixture(self, camera_x):
        from power_objectives import draw_switchgear
        draw_switchgear(self,camera_x)

    def draw_objective_signals(self, player, camera_x):
        from power_objectives import draw_signals
        draw_signals(self,player,camera_x)
