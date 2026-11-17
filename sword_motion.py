"""곡예 마무리의 실제 도약·짧은 전진. 표시 좌표로 몸통을 속이지 않는다."""

from dataclasses import dataclass
from math import sqrt
from physics import GRAVITY

TAKEOFF=.16
TRAVEL_END=.48
HOP_HEIGHT=36
TRAVEL=24


def ease(t):
    t=max(0,min(1,t))
    return t*t*(3-2*t)


@dataclass
class AcrobatStep:
    floor_y:float
    direction:int
    launched:bool=False
    travel:float=0

    def advance(self,motion,elapsed,dt,solids):
        if elapsed<TAKEOFF:return 0.0
        if not self.launched:
            self.launched=True
            # 같은 바닥의 실제 지지 면 안에서만 짧게 전진한다. 끝에서는 제자리 도약한다.
            destination=motion.x+self.direction*TRAVEL
            if any(abs(s.top-self.floor_y)<.01 and
                   s.left+motion.width/2<=min(motion.x,destination) and
                   max(motion.x,destination)<=s.right-motion.width/2 for s in solids):
                self.travel=TRAVEL
            if motion.on_ground:
                motion.velocity_y=sqrt(2*GRAVITY*HOP_HEIGHT)
                motion.on_ground=False
        duration=TRAVEL_END-TAKEOFF
        return self.direction*self.travel*(ease((elapsed-TAKEOFF)/duration)-
                                          ease((elapsed-dt-TAKEOFF)/duration))
