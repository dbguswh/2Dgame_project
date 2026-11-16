"""지형에 막히면 돌아오며 한 적을 투척당 한 번만 타격하는 광륜."""

from dataclasses import dataclass, field
from math import cos, sin, hypot, radians

from combat import overlaps
from light_bomb import blocked_segment


OUT_TIME = .45
OUT_SPEED = 480
RETURN_SPEED = 560
MAX_TIME = 3.0
RADIUS = 14
MAX_FLIGHT_Y = 508
HALO_COST = 10
HALO_COOLDOWN = 1.0


@dataclass
class HaloAim:
    direction: int
    angle: float = 0.0

    def update(self, dt, direction=0, elevation=0):
        if direction:self.direction=direction
        self.angle=max(0,min(75,self.angle+elevation*90*max(0,dt)))


@dataclass
class Halo:
    x: float
    y: float
    direction: int
    upward: bool = False
    age: float = 0.0
    phase: str = 'OUT'
    active: bool = True
    hits: set = field(default_factory=set)
    segments: list = field(default_factory=list)
    trail: list = field(default_factory=list)
    angle: float | None = None

    def update(self, dt, player, solids):
        self.segments.clear()
        remaining = max(0, dt)
        while remaining > 1e-9 and self.active:
            step = min(remaining, 1/120)
            self.age += step
            if self.age >= MAX_TIME:
                self.active = False
                break
            if self.phase == 'OUT' and self.age-step >= OUT_TIME-1e-9:
                self.phase = 'RETURN'
            if self.phase == 'OUT':
                angle = radians(self.angle if self.angle is not None else 45 if self.upward else 0)
                dx,dy = self.direction*cos(angle)*OUT_SPEED*step, sin(angle)*OUT_SPEED*step
            else:
                vx,vy = player.x-self.x, player.feet_y+44-self.y
                length = hypot(vx,vy)
                if length <= RETURN_SPEED*step+12:
                    self.active = False
                    break
                dx,dy = vx/length*RETURN_SPEED*step,vy/length*RETURN_SPEED*step
            start,end = (self.x,self.y),(self.x+dx,self.y+dy)
            if blocked_segment(start,end,solids) or not 16 <= end[1] <= MAX_FLIGHT_Y:
                if self.phase == 'OUT':
                    self.phase='RETURN'
                else:
                    self.active=False
                    break
            else:
                self.x,self.y=end
                self.segments.append((start,end))
            remaining -= step
        self.trail.append((self.x,self.y))
        self.trail[:]=self.trail[-8:]

    def candidates(self, targets, solids):
        result={}
        for identity,body in targets:
            if identity in self.hits:
                continue
            for first,last in self.segments:
                sweep=(min(first[0],last[0])-RADIUS,min(first[1],last[1])-RADIUS,
                       max(first[0],last[0])+RADIUS,max(first[1],last[1])+RADIUS)
                point=(max(body[0],min(last[0],body[2])),max(body[1],min(last[1],body[3])))
                if overlaps(sweep,body) and not blocked_segment(last,point,solids):
                    direction=1 if last[0]>=first[0] else -1
                    result[identity]=(direction,point)
                    break
        return result

    def draw(self,camera_x=0):
        from math import sin
        import pico2d
        from effects import blended,glow
        from enemy_art import draw_halo
        with blended():
            for index,(x,y) in enumerate(self.trail):
                glow(x-camera_x,y,5+index*.6,(255,204,106),alpha=15+index*12)
            glow(self.x-camera_x,self.y,23,(255,216,133),alpha=100)
            draw_halo(self.x-camera_x,self.y,self.age*16,size=42)


def preview_path(x,y,direction,angle,solids):
    """실탄과 같은 작은 이동 단계로 전진 경로만 반환한다."""
    from types import SimpleNamespace
    h=Halo(x,y,direction,angle=angle)
    owner=SimpleNamespace(x=x,feet_y=y-44)
    points=[(x,y)]
    for _ in range(54):
        h.update(1/120,owner,solids)
        if h.segments:points.append((h.x,h.y))
        if h.phase!='OUT' or not h.active:break
    return points
