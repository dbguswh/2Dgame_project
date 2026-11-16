"""복구 직후 다리로 이동하고 전개를 보여준 뒤 돌아오는 짧은 카메라 연출."""

from dataclasses import dataclass
from physics import camera_offset


def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)


@dataclass
class BridgeReveal:
    origin: float
    destination: float
    elapsed: float = 0.0
    active: bool = True

    @classmethod
    def start(cls,player,stage):
        return cls(camera_offset(player.x,stage.width,960),
                   camera_offset(sum(stage.canal)/2,stage.width,960))

    @property
    def camera_x(self):
        if self.elapsed<.6:t=smooth(self.elapsed/.6)
        elif self.elapsed<3:t=1
        else:t=1-smooth((self.elapsed-3)/.6)
        return self.origin+(self.destination-self.origin)*t

    def update(self,dt,stage):
        self.elapsed=min(3.6,self.elapsed+max(0,dt))
        stage.reveal_light_elapsed=self.elapsed
        stage.visual_time+=max(0,dt)
        stage.bridge_elapsed=max(0,min(stage.BRIDGE_TIME,self.elapsed-.6))
        stage.sync_bridge()
        if self.elapsed>=3.6-1e-9:self.active=False

    def skip(self,stage):
        self.update(3.6,stage)

    def draw(self,font,width,height):
        import pico2d
        pico2d.draw_rectangle(0,0,width-1,45,5,9,14,filled=True)
        pico2d.draw_rectangle(0,height-46,width-1,height-1,5,9,14,filled=True)
        label='교량으로 전력 공급' if self.elapsed<.6 else '교량 잠금 해제 · 전개' if self.elapsed<3 else '교량 복구 완료'
        font.draw(width/2-112,height-24,label,(245,220,164))
        font.draw(width/2-100,22,'Space 건너뛰기 · Esc 일시정지',(179,190,199))
