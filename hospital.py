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
        self.width = 2880
        self.start = (1432, GROUND_Y)
        self.fixture_position = (1488, GROUND_Y)
        self.fixture_checkpoint = self.start
        self.terminal_position = (1376, GROUND_Y)
        self.exit_position = (1664, GROUND_Y)
        self.circuit = 'A'
        self.parts = {'A': False, 'B': False}
        self.returned = {'A': False, 'B': False}
        self.room_cleared = {'A': False, 'B': False}
        self.room_guards = {'A': 'hospital-shade-0', 'B': 'hospital-shade-6'}
        self.return_open = {'A': False, 'B': False}
        self.return_checkpoints = {'A': (912,96), 'B': (2128,96)}
        self.blackout_remaining = 0.0
        self.part_positions = {'A': (192, 304), 'B': (2752, 112)}
        self.latch_positions = {'A': (880,96), 'B': (2112,96)}
        self.doors = {'A': PowerDoor('hospital-a', 948, progress=1),
                      'B': PowerDoor('hospital-b', 2036),
                      'exit': PowerDoor('hospital-exit', 1664, height=176, blocks_corridor=False)}
        self.power_restore_elapsed = 0.0
        self.record_time = 0.0
        self.visual_time = 0.0
        self.supply_boxes = (SupplyBox('hospital-a-return-medkit', 1072, 96, item=MEDKIT),
                             SupplyBox('hospital-b-return-bomb', 2672, 96, item=LIGHT_BOMB),
                             SupplyBox('hospital-hub-shield', 1568, 96, item=SHIELD))
        self.fragment_cache = FragmentCache('hospital-upper-cache', 704, 336)
        self.battery_pack_position = (1328, 112)
        self.ascent_ledges = (Solid(768, 128, 896, 144, True), Solid(640, 176, 736, 192, True),
                              Solid(512, 224, 608, 240, True))
        self.archive_gallery = Solid(128, 268, 480, 288, True)
        self.cache_gallery = Solid(512, 316, 752, 336, True)
        self.cover_solids = (Solid(1824,96,1888,144), Solid(2240,96,2304,144), Solid(2544,96,2608,144))
        self.base_solids = [Solid(0, 0, self.width, 96), *self.ascent_ledges,
                            self.archive_gallery, self.cache_gallery,
                            Solid(1120, 96, 1184, 144), *self.cover_solids]
        self.light_regions = [LightRegion(0, 96, 960, 540), LightRegion(960, 96, 1344, 540),
                              LightRegion(1344, 96, 1664, 540), LightRegion(1664, 96, 2048, 540),
                              LightRegion(2048, 96, 2880, 540)]
        self.enemy_placements = tuple(EnemyPlacement(f'hospital-shade-{i}', x, y, bounds, ranged,
                                                     'wraith' if i in (3,7) else 'shade')
            for i, (x, y, bounds, ranged) in enumerate((
                (336, 288, (128, 480), False), (624, 336, (512, 752), True),
                (1040, 96, (992, 1312), False), (1216, 96, (992, 1312), True),
                (1744, 96, (1696, 2016), False), (1952, 96, (1696, 2016), True),
                (2384, 96, (2304, 2816), False), (2688, 96, (2304, 2816), True))))
        self.respawns = RespawnDirector(self.enemy_placements)
        self.in_hub = True
        self.scene = None
        self.update(0)

    def before_update(self,player):
        self.in_hub=1312<=player.x<=1696

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
        pending = self.returning_key
        if (pending is not None and player.motion.on_ground and abs(player.feet_y-96)<=8
                and 1352<=player.x<=1656):
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

    def update_combat_seals(self,enemies):
        actors={e.identity:e for e in enemies}
        for key,identity in self.room_guards.items():
            actor=actors.get(identity)
            if actor is not None and not actor.alive and actor.death_by_hit:self.room_cleared[key]=True

    def draw_combat_targets(self,enemies,camera_x):
        from combat_seals import draw_target_mark
        targets={identity for key,identity in self.room_guards.items() if not self.room_cleared[key]}
        for enemy in enemies:
            if enemy.alive and enemy.identity in targets:draw_target_mark(enemy,camera_x)

    def detach_part(self,key,player):
        if self.parts[key]:return False
        if not self.room_cleared[key]:
            player.notice,player.notice_time='금색 표식 침입자를 처치해 부품 잠금을 해제하세요',2
            return False
        if self.powered_circuit!=key:
            player.notice,player.notice_time=f'중앙에서 {key} 회로를 선택하세요',2
            return False
        self.parts[key]=True
        self.returned[key]=False
        self.return_open[key]=False
        self.blackout_remaining=1.2
        player.checkpoint_position=self.return_checkpoints[key]
        self.respawns.arm_warning([p.identity for p in self.corridor_points(key)],4)
        name='전력 퓨즈' if key=='A' else '전원 모듈'
        player.notice,player.notice_time=f'{name} 회수 · {key} 복도 정전! 안쪽 스위치 E로 문을 여세요',3.5
        self.update(0)
        return True

    def apply_rewards(self, player):
        if self.fixture_powered and not self.reward_claimed:
            player.fragments += 2
            self.reward_claimed = True

    def _target(self, player):
        if not player.motion.on_ground or player.is_attacking or player.light_cast > 0:
            return None
        targets = [('exit', self.exit_position, None)]
        targets += [('part',(x,y-16),key) for key,(x,y) in self.part_positions.items() if not self.parts[key]]
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
        if kind == 'part':
            return self.detach_part(obj,player)
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
            elif not all(self.returned.values()):
                player.notice='부품을 가지고 중앙까지 귀환하세요'
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
        if kind == 'part':
            label=(f'E: {"전력 퓨즈" if obj=="A" else "전원 모듈"} 분리 · 복도 정전'
                   if self.room_cleared[obj] else '금색 표식 침입자 처치 필요')
        elif kind == 'supply':
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
            direction='오른쪽' if pending=='A' else '왼쪽'
            return (f'{pending} 정전 · {direction} 방 입구 스위치 E로 문을 여세요' if not self.return_open[pending]
                    else f'{pending} 귀환 · {direction} 어두운 복도를 지나 중앙으로 돌아가세요')
        if self.part_count == 2:
            return '운하 병원 · 중앙에서 두 부품을 함께 설치하세요'
        if self.parts[self.circuit]:
            other = 'B' if self.circuit == 'A' else 'A'
            return f'운하 병원 · 중앙 단말기에서 {other} 회로로 전환하세요'
        key=self.circuit
        destination='왼쪽 A 창고' if key=='A' else '오른쪽 B 정비실'
        if not self.room_cleared[key]:return f'{destination} · 금색 표식 침입자를 처치하세요'
        return f'{destination} · 부품 앞 E로 분리하세요 (회수 시 복도 정전)'

    def capture_state(self):
        return (self.circuit, tuple(self.parts.values()), tuple(self.return_open.values()),
                tuple(d.progress for d in self.doors.values()), self.power_restore_elapsed, self.record_time,
                tuple(self.returned.values()),self.blackout_remaining,tuple(self.room_cleared.values()))

    def restore_state(self, state):
        if not state:
            return
        (self.circuit, parts, latches, doors, self.power_restore_elapsed, self.record_time,
         returned,self.blackout_remaining,cleared) = state
        self.room_cleared=dict(zip(('A','B'),cleared))
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
        from hospital_ui import draw_labels
        draw_labels(self,font,camera_x)

    def draw_foreground(self,player,camera_x):
        # 상자 앞면만 발보다 앞에 그려 상자를 뚫고 서 있는 듯한 겹침을 줄인다.
        from effects import blended
        for box in self.supply_boxes:
            if abs(player.x-box.x)>44 or abs(player.feet_y-box.feet_y)>8:continue
            x,y=box.x-camera_x,box.feet_y
            with blended((x-40,y,x+40,y+24)):box.draw(camera_x)
