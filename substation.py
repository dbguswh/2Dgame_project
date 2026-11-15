"""하부·상부 차단기, 호출식 승강기와 독립 충전 전원의 중앙 변전소."""

from combat import overlaps
from stage import Stage, EnemyPlacement
from physics import Solid
from lighting import LightRegion
from supplies import SupplyBox
from inventory import MEDKIT, LIGHT_BOMB, SHIELD, ITEM_NAMES
from respawn import RespawnDirector
from elevator import Elevator
from power_doors import PowerDoor


class SubstationStage(Stage):
    name = '중앙 변전소'
    stage_id = 'substation'
    start_direction = 1

    def __init__(self):
        super().__init__()
        self.width = 3840
        self.start = (160,96)
        self.breakers = [False,False]
        self.breaker_positions = ((1568,96),(2816,352))
        self.charger_position = (240,96)
        self.call_positions = ((1664,96),(1936,352))
        self.checkpoints = ((1648,96),(1936,352))
        self.lift = Elevator()
        self.core_gate = PowerDoor('substation-core',2912)
        self.visual_time = 0
        self.power_restore_elapsed = 0
        self.upper_gallery = Solid(1856,332,2880,352,True)
        self.base_solids = [Solid(0,0,self.width,96),self.upper_gallery,
                            Solid(896,96,960,128),Solid(3200,96,3264,128),
                            Solid(2480,352,2544,400)]
        self.light_regions = [LightRegion(0,96,1536,332),LightRegion(1536,96,2032,540),
                              LightRegion(2032,96,2880,332),LightRegion(2032,352,2880,540),
                              LightRegion(2880,96,3840,540)]
        self.supply_boxes = (SupplyBox('substation-medkit',992,96,item=MEDKIT),
                             SupplyBox('substation-bomb',1376,96,item=LIGHT_BOMB),
                             SupplyBox('substation-shield',2032,352,item=SHIELD))
        self.enemy_placements = tuple(EnemyPlacement(f'substation-shade-{i}',x,y,bounds,ranged)
            for i,(x,y,bounds,ranged) in enumerate((
                (560,96,(448,864),False),(784,96,(448,864),True),
                (1120,96,(1008,1488),False),(1280,96,(1008,1488),True),(1432,96,(1008,1488),False),
                (2112,352,(2064,2464),False),(2368,352,(2064,2464),True),(2640,352,(2560,2736),False),
                (3328,96,(3280,3776),False),(3616,96,(3280,3776),True))))
        self.respawns = RespawnDirector(self.enemy_placements)
        self.scene = None
        self.update(0)

    @property
    def controls_locked(self):
        return self.lift.moving and self.lift.rider is not None

    @property
    def both_breakers(self):
        return all(self.breakers)

    @property
    def local_light_regions(self):
        return (LightRegion(0,96,384,540),LightRegion(1536,96,2032,540),
                LightRegion(2752,352,2880,540))

    @property
    def fixed_light_regions(self):
        return (LightRegion(0,96,self.width,540),) if self.fixture_powered else self.local_light_regions

    def is_temporarily_lit(self, box):
        return any(overlaps(box,(r.left,r.bottom,r.right,r.top)) for r in self.fixed_light_regions)

    def before_update(self, player):
        # 호출 중인 차에 뒤늦게 착지한 경우도 실제 바닥과 함께 운반한다.
        if self.lift.moving and self.lift.rider is None and self.lift.on_platform(player):
            self.lift.attach(player)

    def update(self, delta_time):
        dt = max(0,delta_time)
        self.visual_time += dt
        self.lift.update(dt)
        self.core_gate.update(dt,self.both_breakers)
        if self.fixture_powered:
            self.power_restore_elapsed = min(1.2,self.power_restore_elapsed+dt)
        self.solids = [*self.base_solids,self.lift.solid]
        if not self.core_gate.is_open:
            self.solids.append(self.core_gate.solid)
        for box in self.supply_boxes:
            box.update(dt)

    def collect_pickups(self, player):
        for box in self.supply_boxes:
            x,y = box.pickup_position
            if box.pickup_ready and overlaps(player.get_bb(),(x-8,y-9,x+8,y+10)) and player.add_item(box.item):
                box.claimed = True

    def _target(self, player):
        if (self.controls_locked or not player.motion.on_ground
                or player.is_attacking or player.light_cast > 0):
            return None
        if self.lift.on_platform(player):
            return 'ride',(self.lift.x,self.lift.y),None
        targets = [('charger',self.charger_position,None)]
        targets += [('breaker',pos,i) for i,pos in enumerate(self.breaker_positions) if not self.breakers[i]]
        targets += [('call',pos,i) for i,pos in enumerate(self.call_positions)]
        targets += [('supply',(b.x,b.feet_y),b) for b in self.supply_boxes if not b.opened]
        candidates = [t for t in targets if abs(player.x-t[1][0])<=48 and abs(player.feet_y-t[1][1])<=8]
        return min(candidates,key=lambda t:abs(player.x-t[1][0]),default=None)

    def interact(self, player):
        target = self._target(player)
        if target is None:
            return False
        kind,_,obj = target
        if kind == 'charger':
            player.battery = player.max_battery
            player.notice = '독립 비상 전원 · 배터리 충전 완료'
        elif kind == 'breaker':
            if obj == 1 and not self.breakers[0]:
                player.notice = '하부 1번 차단기를 먼저 작동하세요'
            else:
                self.breakers[obj] = True
                player.checkpoint_position = self.checkpoints[obj]
                player.notice = '1번 차단기 작동 · 승강기 전원 공급' if obj == 0 else '2번 차단기 작동 · 봉쇄 설비 전원 공급'
        elif kind in ('ride','call'):
            if not self.breakers[0]:
                player.notice = '하부 1번 차단기로 승강기 전원을 공급하세요'
            elif self.lift.moving:
                player.notice = '승강기가 이동하고 있습니다'
            elif kind == 'ride':
                self.lift.board(player)
                player.notice = '승강기 이동 중 · 도착 후 내리세요'
            elif self.lift.call(self.call_positions[obj][1]):
                player.notice = '승강기 호출 · 도착 후 플랫폼 위에서 E'
            else:
                player.notice = '승강기 도착 · 플랫폼 위에서 E로 탑승 이동'
        elif kind == 'supply' and obj.open():
            player.notice = f'{ITEM_NAMES[obj.item]} 보급함 개봉 · 아이템을 회수하세요'
        player.notice_time = 2.2
        self.update(0)
        return True

    def interaction_prompt(self, player):
        if self.controls_locked:
            return self.lift.x,self.lift.y,'승강기 이동 중'
        target = self._target(player)
        if target is None:
            return None
        kind,pos,obj = target
        if kind == 'supply':
            text = f'E: {ITEM_NAMES[obj.item]} 보급함'
        elif kind == 'breaker':
            text = f'E: {obj+1}번 차단기 작동'
        elif kind in ('ride','call'):
            text = ('1번 차단기 전원 필요' if not self.breakers[0] else '승강기 이동 중' if self.lift.moving
                    else 'E: 반대 층으로 이동' if kind == 'ride' else 'E: 승강기 호출')
        else:
            text = 'E: 배터리 충전'
        return *pos,text

    @property
    def objective(self):
        if not self.breakers[0]:
            return '중앙 변전소 · 하부 1번 차단기를 작동하세요'
        if not self.breakers[1]:
            return '중앙 변전소 · 승강기로 올라가 2번 차단기를 작동하세요'
        return '중앙 변전소 · 차단기 2개 복구 완료'

    @property
    def hud_status(self):
        return f'차단기 {sum(self.breakers)}/2'

    def capture_state(self):
        return tuple(self.breakers),self.lift.snapshot(),self.core_gate.progress,self.power_restore_elapsed

    def restore_state(self, state):
        if state:
            breakers,lift,self.core_gate.progress,self.power_restore_elapsed = state
            self.breakers = list(breakers)
            self.lift.restore(lift)

    def restore_after_death(self):
        self.lift.reset_lower()
        self.core_gate.progress = 1 if self.both_breakers else 0
        self.update(0)

    def draw(self, camera_x, screen_width, screen_height):
        if self.scene is None:
            from substation_scene import SubstationScene
            self.scene = SubstationScene()
        self.scene.draw(self,camera_x,screen_width,screen_height)

    def draw_labels(self, font, camera_x):
        for x,y,text in ((190,214,'독립 충전 전원'),(1500,235,'1번 차단기'),
                         (2080,308,'상부 전기실'),(2720,308,'2번 차단기')):
            if -160 < x-camera_x < 960:
                font.draw(x-camera_x,y,text,(181,196,198))
