"""주택가의 세 교전을 통로/보관함 개방 기록에 연결한다."""

from dataclasses import dataclass
import pico2d
from physics import Solid
from effects import blended,glow,segment


@dataclass
class CombatSeal:
    target: str
    barrier: Solid | None
    opened: bool=False
    elapsed: float=0

    def draw(self,camera_x):
        if self.barrier is None:return
        s=self.barrier;x=(s.left+s.right)/2-camera_x
        with blended():
            if not self.opened:
                pico2d.draw_rectangle(s.left-camera_x,s.bottom,s.right-camera_x,s.top,
                                      103,48,130,a=120,filled=True)
                for offset in (-6,6):segment((x+offset,s.bottom),(x+offset,s.top),(203,109,231),2)
                for y in range(int(s.bottom+12),int(s.top),30):
                    segment((x-6,y),(x+6,y+14),(167,90,202),2)
                glow(x,(s.bottom+s.top)/2,18,(169,83,215),alpha=55)
            elif self.elapsed<.5:
                alpha=round(190*(1-self.elapsed/.5))
                offset=self.elapsed*100
                pico2d.draw_line(x-offset,s.bottom,x-offset,s.top,231,195,123,a=alpha)
                pico2d.draw_line(x+offset,s.bottom,x+offset,s.top,231,195,123,a=alpha)


def draw_target_mark(enemy,camera_x):
    x,y=enemy.x-camera_x,enemy.feet_y+140
    with blended():
        for a,b in (((x,y+6),(x+5,y)),((x+5,y),(x,y-6)),((x,y-6),(x-5,y)),((x-5,y),(x,y+6))):
            segment(a,b,(246,206,132),2)
