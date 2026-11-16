"""선택 경로에서 전력 조각 하나를 즉시 회수하는 벽면 보급고."""

from dataclasses import dataclass


@dataclass
class FragmentCache:
    identity: str
    x: float
    feet_y: float
    opened: bool = False
    opening_elapsed: float = 0.0

    def open(self):
        if self.opened:
            return False
        self.opened = True
        return True

    def update(self, delta_time):
        if self.opened:
            self.opening_elapsed = min(.3, self.opening_elapsed + max(0, delta_time))

    def snapshot(self):
        return self.identity, self.opened, self.opening_elapsed

    def restore(self, state):
        _, self.opened, self.opening_elapsed = state

    def draw(self, camera_x=0):
        import pico2d
        from effects import segment, blended, glow, polygon
        x, y = self.x - camera_x, self.feet_y
        progress = min(1, self.opening_elapsed / .3)
        brass, steel = (163,133,77), (75,89,99)
        # 벽면 고정 프레임·배선·보강 모서리. 실제 충돌체와 지급 시점은 유지한다.
        segment((x+30,y+67),(x+37,y+67),(37,48,57),width=4)
        segment((x+37,y+67),(x+37,y+11),(37,48,57),width=4)
        polygon(((x-31,y+4),(x-31,y+72),(x-23,y+80),(x+23,y+80),
                 (x+31,y+72),(x+31,y+4)),(24,33,42))
        pico2d.draw_rectangle(x-26,y+6,x+26,y+74,*steel,filled=True)
        pico2d.draw_rectangle(x-22,y+10,x+22,y+68,11,19,26,filled=True)
        for xx in (-29,23):
            for yy in (8,65):
                pico2d.draw_rectangle(x+xx,y+yy,x+xx+6,y+yy+10,*brass,filled=True)
                pico2d.draw_rectangle(x+xx+2,y+yy+3,x+xx+4,y+yy+5,40,45,44,filled=True)
        for xx in (-13,0,13):
            pico2d.draw_rectangle(x+xx-4,y+20,x+xx+4,y+54,35,47,55,filled=True)
            pico2d.draw_line(x+xx-3,y+51,x+xx+3,y+51,91,105,110)
        # 두 장의 잠금문이 양옆으로 물러나며 회수 후 빈 슬롯을 드러낸다.
        width = 21*(1-progress)
        for side in (-1,1):
            left,right = ((x-22,x-22+width) if side<0 else (x+22-width,x+22))
            if width > .1:
                pico2d.draw_rectangle(left,y+11,right,y+67,48,61,70,filled=True)
                pico2d.draw_line(left,y+67,right,y+67,123,135,136)
                pico2d.draw_line(left,y+13,right,y+13,27,36,42)
                if width > 4:
                    for yy in (18,21,57,60):
                        pico2d.draw_line(left+2,y+yy,right-2,y+yy,72,85,93)
        if progress < 1:
            with blended():
                alpha = round(255*(1-progress))
                emblem = ((x,y+56),(x+13,y+49),(x+13,y+32),
                          (x,y+24),(x-13,y+32),(x-13,y+49))
                polygon(emblem,(25,33,38),alpha=alpha)
                for a,b in zip(emblem,emblem[1:]+emblem[:1]):
                    pico2d.draw_line(*a,*b,*brass,a=alpha)
                points=((x+4,y+51),(x-5,y+39),(x+3,y+39),(x-3,y+29))
                for a,b in zip(points,points[1:]):
                    pico2d.draw_line(*a,*b,255,215,131,a=alpha)
                glow(x,y+40,25,(240,192,92),alpha=45*(1-progress))
        pico2d.draw_rectangle(x-13,y+73,x+13,y+77,17,25,31,filled=True)
        for dx in (-8,0,8):
            color=(238,194,106) if not self.opened else (60,75,78)
            pico2d.draw_rectangle(x+dx-2,y+74,x+dx+2,y+76,*color,filled=True)
        pico2d.draw_rectangle(x-29,y,x+29,y+5,43,53,60,filled=True)
