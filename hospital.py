"""중앙 배전, A 상부 탐색, B 차폐물 교전으로 구성한 운하 병원."""

from combat import overlaps
from physics import Solid
from stage import Stage, GROUND_Y, EnemyPlacement
from lighting import LightRegion
from power_doors import PowerDoor
from supplies import SupplyBox
from fragment_cache import FragmentCache
from inventory import MEDKIT, LIGHT_BOMB, SHIELD, ITEM_NAMES
from respawn import RespawnDirector


class HospitalStage(Stage):
    name = '운하 병원'
    stage_id = 'hospital'
    next_stage_id = 'substation'
    destination_name = '중앙 변전소'
    start_direction = -1

    def __init__(self):
        super().__init__()
        self.width = 3840
        self.start = (1920, GROUND_Y)
        self.fixture_position = (1984, GROUND_Y)
        self.fixture_checkpoint = self.start
        self.terminal_position = (1856, GROUND_Y)
        self.exit_position = (2112, GROUND_Y)
        self.circuit = 'A'
        self.parts = {'A': False, 'B': False}
        self.returned = {'A': False, 'B': False}
        self.return_open = {'A': False, 'B': False}
        self.return_checkpoints = {'A': (912,96), 'B': (2992,96)}
        self.blackout_remaining = 0.0
        self.part_positions = {'A': (192, 304), 'B': (3712, 112)}
        self.latch_positions = {'A': (904,96), 'B': (2960,96)}
        self.doors = {'A': PowerDoor('hospital-a', 948, progress=1),
                      'B': PowerDoor('hospital-b', 2892),
                      'exit': PowerDoor('hospital-exit', 2112, height=176, blocks_corridor=False)}
        self.power_restore_elapsed = 0.0
        self.record_time = 0.0
        self.visual_time = 0.0
        self.supply_boxes = (SupplyBox('hospital-a-return-medkit', 1000, 96, item=MEDKIT),
                             SupplyBox('hospital-b-return-bomb', 3632, 96, item=LIGHT_BOMB),
                             SupplyBox('hospital-hub-shield', 2048, 96, item=SHIELD))
        self.fragment_cache = FragmentCache('hospital-upper-cache', 704, 336)
        self.battery_pack_position = (1760, 112)
        self.ascent_ledges = (Solid(768, 128, 896, 144, True), Solid(640, 176, 736, 192, True),
                              Solid(512, 224, 608, 240, True))
        self.archive_gallery = Solid(128, 268, 480, 288, True)
        self.cache_gallery = Solid(512, 316, 752, 336, True)
        self.cover_solids = (Solid(2528,96,2592,144), Solid(3104,96,3168,144), Solid(3424,96,3488,144))
        self.base_solids = [Solid(0, 0, self.width, 96), *self.ascent_ledges,
                            self.archive_gallery, self.cache_gallery,
                            Solid(1280, 96, 1344, 128), *self.cover_solids]
        self.light_regions = [LightRegion(0, 96, 960, 540), LightRegion(960, 96, 1664, 540),
                              LightRegion(1664, 96, 2176, 540), LightRegion(2176, 96, 2880, 540),
                              LightRegion(2880, 96, 3840, 540)]
        self.enemy_placements = tuple(EnemyPlacement(f'hospital-shade-{i}', x, y, bounds, ranged,
                                                     'wraith' if i in (3,7) else 'shade')
            for i, (x, y, bounds, ranged) in enumerate((
                (336, 288, (128, 480), False), (624, 336, (512, 752), True),
                (1120, 96, (1008, 1600), False), (1472, 96, (1008, 1600), True),
                (2352, 96, (2304, 2816), False), (2688, 96, (2304, 2816), True),
                (3264, 96, (3168, 3776), False), (3616, 96, (3168, 3776), True))))
        self.respawns = RespawnDirector(self.enemy_placements)
        self.scene = None
        self.update(0)

    @property
    def local_light_regions(self):
        if self.powered_circuit is None:
            return (self.light_regions[2],)
        corridor = self.light_regions[1 if self.powered_circuit == 'A' else 3]
        return self.light_regions[2], corridor

    @property
    def powered_circuit(self):
        return None if self.parts[self.circuit] else self.circuit

    @property
    def returning_key(self):
        return next((k for k in ('A','B') if self.parts[k] and not self.returned[k]),None)

    def door_should_open(self, key):
        return self.fixture_powered or key != 'exit' and (self.powered_circuit == key or self.return_open[key])

    def corridor_points(self, key):
        return self.respawns.points[2:4] if key == 'A' else self.respawns.points[4:6]

    def supply_lock_reason(self, box):
        if box.item == MEDKIT and not self.parts['A']:
            return 'A 전력 퓨즈 분리 후 치료제 개봉 가능'
        if box.item == LIGHT_BOMB and not self.parts['B']:
            return 'B 모듈 분리 후 광탄 개봉 가능'
        if box.item == SHIELD and self.part_count == 0:
            return '부품을 하나 회수하면 중앙 보호막 보급함을 사용할 수 있습니다'
        return ''

    @property
    def fixed_light_regions(self):
        if self.fixture_powered:
            return (LightRegion(0, 96, self.width, 540),)
        return self.local_light_regions

    def is_temporarily_lit(self, box):
        return any(overlaps(box, (r.left, r.bottom, r.right, r.top)) for r in self.fixed_light_regions)

    @property
    def part_count(self):
        return sum(self.parts.values())

    @property
    def hud_status(self):
        if self.fixture_powered:
            return '병원 복구 완료'
        label = f'{self.powered_circuit} 공급' if self.powered_circuit else '임시 전원 차단'
        return f'{label} · {self.part_count}/2'

    def update(self, delta_time):
        dt = max(0, delta_time)
        self.visual_time += dt
        self.record_time = max(0, self.record_time - dt)
        self.blackout_remaining = max(0,self.blackout_remaining-dt)
        if self.fixture_powered:
            self.power_restore_elapsed = min(1.2, self.power_restore_elapsed + dt)
        for key, door in self.doors.items():
            door.update(dt,self.door_should_open(key))
        self.solids = self.base_solids + [d.solid for d in self.doors.values() if d.blocks_corridor and not d.is_open]
        for box in self.supply_boxes:
            box.update(dt)
        self.fragment_cache.update(dt)

    def collect_pickups(self, player):
        for key, (x, y) in self.part_positions.items():
            if not self.parts[key] and overlaps(player.get_bb(), (x-9, y-12, x+9, y+12)):
                self.parts[key] = True
                self.returned[key] = False
                self.return_open[key] = False
                self.blackout_remaining = 1.2
                player.checkpoint_position = self.return_checkpoints[key]
                self.respawns.arm_warning([p.identity for p in self.corridor_points(key)],4)
                name = '전력 퓨즈' if key == 'A' else '전원 제어 모듈'
                player.notice = f'{name} 분리 · {key} 정전! 안쪽 스위치로 문을 여세요'
                player.notice_time = 3.5
        pending = self.returning_key
        if (pending is not None and player.motion.on_ground and abs(player.feet_y-96)<=8
                and 1680<=player.x<=2160):
            self.returned[pending] = True
            player.checkpoint_position = self.start
            player.notice,player.notice_time = '중앙 복귀 완료 · 회로 전환 또는 부품 설치',2.2
        for box in self.supply_boxes:
            x, y = box.pickup_position
            if box.pickup_ready and overlaps(player.get_bb(), (x-8, y-9, x+8, y+10)) and player.add_item(box.item):
                box.claimed = True
        x, y = self.battery_pack_position
        if not self.battery_pack_collected and player.battery < player.max_battery and overlaps(
                player.get_bb(), (x-10, y-12, x+10, y+12)):
            amount = min(50, player.max_battery-player.battery)
            player.battery += amount
            self.battery_pack_collected = True
            player.notice, player.notice_time = f'비상 배터리 +{amount}', 1.8

    def apply_rewards(self, player):
        if self.fixture_powered and not self.reward_claimed:
            player.fragments += 2
            self.reward_claimed = True

    def _target(self, player):
        if not player.motion.on_ground or player.is_attacking or player.light_cast > 0:
            return None
        targets = [('exit', self.exit_position, None)]
        if not self.fixture_powered:
            targets += [('terminal', self.terminal_position, None), ('repair', self.fixture_position, None)]
        targets += [('latch', pos, key) for key, pos in self.latch_positions.items() if not self.return_open[key]]
        targets += [('supply', (b.x, b.feet_y), b) for b in self.supply_boxes if not b.opened]
        if not self.fragment_cache.opened:
            targets.append(('cache', (self.fragment_cache.x, self.fragment_cache.feet_y), self.fragment_cache))
        candidates = [t for t in targets if abs(player.x-t[1][0]) <= 48 and abs(player.feet_y-t[1][1]) <= 8]
        return min(candidates, key=lambda t: abs(player.x-t[1][0]), default=None)

    def interact(self, player):
        target = self._target(player)
        if target is None:
            return False
        kind, _, obj = target
        if kind == 'terminal':
            if self.part_count == 2:
                player.notice = '두 부품 확보 · 오른쪽 전원 장치에 함께 설치하세요'
            else:
                self.circuit = 'B' if self.circuit == 'A' else 'A'
                player.notice = (f'{self.circuit} 회로 공급 · 부품 분리 시 이 복도도 꺼집니다'
                                 if self.powered_circuit else f'{self.circuit} 부품 분리 상태 · 임시 전원 공급 불가')
        elif kind == 'repair':
            if self.part_count < 2:
                missing = '전력 퓨즈' if not self.parts['A'] else '전원 제어 모듈'
                player.notice = f'{missing} 필요 · 두 부품을 모아 함께 설치하세요'
            else:
                self.fixture_powered = True
                self.power_restore_elapsed = 0
                self.record_time = 6
                self.apply_rewards(player)
                player.notice = '중앙 기록: 그림자 핵이 전력망 잠식 · 변전소로 이동'
        elif kind == 'latch':
            if not self.parts[obj]:
                player.notice = f'{obj} 부품을 회수한 뒤 수동 개방할 수 있습니다'
            else:
                self.return_open[obj] = True
                player.notice = f'{obj} 문 수동 개방 · 어두워진 복도를 지나 중앙으로 복귀하세요'
        elif kind == 'cache':
            if obj.open():
                player.fragments += 1
            player.notice = '상부 선택 보급고 · 전력 조각 +1'
        elif kind == 'supply':
            reason = self.supply_lock_reason(obj)
            if reason:
                player.notice = reason
            elif obj.open():
                player.notice = f'{ITEM_NAMES[obj.item]} 보급함 개봉 · 아이템을 회수하세요'
        elif kind == 'exit':
            if self.fixture_powered and self.doors['exit'].is_open:
                self.completed = True
                player.clear_input()
            else:
                player.notice = '두 부품으로 병원 전력을 복구하고 문이 열릴 때까지 기다리세요'
        player.notice_time = 3 if self.fixture_powered else 2
        self.update(0)
        return True

    def interaction_prompt(self, player):
        target = self._target(player)
        if target is None:
            return None
        kind, position, obj = target
        labels = {'terminal': f'E: {"B" if self.circuit == "A" else "A"} 회로 선택' if self.part_count < 2 else '오른쪽 전원 장치에 두 부품 설치',
                  'repair': 'E: 두 부품 설치' if self.part_count == 2 else '전력 퓨즈·전원 모듈 필요',
                  'latch': 'E: 문 수동 개방' if kind == 'latch' and self.parts[obj] else '부품 회수 후 수동 개방', 'cache': 'E: 선택 보급고 · 조각 +1',
                  'exit': 'E: 정비 통로로 이동' if self.fixture_powered and self.doors['exit'].is_open else '병원 전력 복구 필요'}
        if kind == 'supply':
            label = self.supply_lock_reason(obj) or f'E: {ITEM_NAMES[obj.item]} 보급함'
        else:
            label = labels[kind]
        return *position, label

    @property
    def objective(self):
        if self.completed:
            return '운하 병원 · 복구 완료'
        if self.fixture_powered:
            return '운하 병원 · 중앙 정비 통로로 이동하세요'
        pending = self.returning_key
        if pending:
            return (f'{pending} 정전 · 안쪽 스위치로 문을 수동 개방하세요' if not self.return_open[pending]
                    else f'{pending} 정전 · 어두운 복도를 지나 중앙으로 복귀하세요')
        if self.part_count == 2:
            return '운하 병원 · 중앙에서 두 부품을 함께 설치하세요'
        if self.parts[self.circuit]:
            other = 'B' if self.circuit == 'A' else 'A'
            return f'운하 병원 · 중앙 단말기에서 {other} 회로로 전환하세요'
        return ('운하 병원 · A 창고 위층의 전력 퓨즈를 회수하세요' if self.circuit == 'A'
                else '운하 병원 · B 정비실의 전원 모듈을 회수하세요')

    def capture_state(self):
        return (self.circuit, tuple(self.parts.values()), tuple(self.return_open.values()),
                tuple(d.progress for d in self.doors.values()), self.power_restore_elapsed, self.record_time,
                tuple(self.returned.values()),self.blackout_remaining)

    def restore_state(self, state):
        if not state:
            return
        (self.circuit, parts, latches, doors, self.power_restore_elapsed, self.record_time,
         returned,self.blackout_remaining) = state
        self.parts = dict(zip(('A', 'B'), parts))
        self.return_open = dict(zip(('A', 'B'), latches))
        self.returned = dict(zip(('A','B'),returned))
        for door, progress in zip(self.doors.values(), doors):
            door.progress = progress

    def restore_after_death(self):
        if self.fixture_powered:
            self.power_restore_elapsed = 1.2
        for key, door in self.doors.items():
            door.progress = 1 if self.door_should_open(key) else 0
        self.blackout_remaining = 0
        self.update(0)

    def draw(self, camera_x, screen_width, screen_height):
        if self.scene is None:
            from hospital_scene import HospitalScene
            self.scene = HospitalScene()
        self.scene.draw(self, camera_x, screen_width, screen_height)

    def draw_labels(self, font, camera_x):
        for x, y, text in ((96, 216, 'A · 약품 창고'), (1788, 266, '회로 전환'),
                            (1928, 266, '비상 전원'), (3480, 256, 'B · 정비실'),
                            (650, 306, '상부 보급고')):
            if -180 < x-camera_x < 960:
                font.draw(x-camera_x, y, text, (170, 196, 196))
        if not self.battery_pack_collected:
            font.draw(1710-camera_x, 70, '비상 배터리 +50', (142, 198, 206))
        for key, (x, y) in self.part_positions.items():
            if not self.parts[key] and -60 < x-camera_x < 960:
                font.draw(x-camera_x-42, y+36, '전력 퓨즈' if key == 'A' else '전원 모듈', (223, 206, 151))
                font.draw(x-camera_x-66, y+60, '분리하면 회로 차단', (196,149,117))
        pending = self.returning_key
        if pending:
            warnings = [p.warning_duration-p.warning_elapsed for p in self.corridor_points(pending) if p.state == 'WARNING']
            if warnings:
                from math import ceil
                remaining = max(.1,ceil(min(warnings)*10-1e-9)/10)
                font.draw(36,408,f'{pending} 복도 침입자 · 출현 {remaining:.1f}초 전',(224,151,177))
        if self.record_time > 0:
            font.draw(36, 384, '시설 기록: 그림자 핵이 중앙 전력망을 잠식하고 있다.', (231, 215, 159))
            font.draw(36, 359, '다음 임무: 변전소 차단기 2개로 봉쇄 설비를 가동한다.', (196, 207, 211))
