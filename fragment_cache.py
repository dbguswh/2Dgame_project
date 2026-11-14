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
        from effects import segment, blended, glow
        x, y = self.x - camera_x, self.feet_y
        metal = (167, 148, 102)
        pico2d.draw_rectangle(x - 27, y, x + 27, y + 73, 30, 39, 47, filled=True)
        pico2d.draw_rectangle(x - 27, y, x + 27, y + 73, 78, 91, 98)
        pico2d.draw_rectangle(x - 21, y + 6, x + 21, y + 64, 15, 25, 32, filled=True)
        progress = self.opening_elapsed / .3
        # 앞문이 접히며 내부 수납칸을 드러낸다. 개봉·지급 기록은 E 입력 순간 확정한다.
        edge = x + 21 - 38 * progress
        pico2d.draw_rectangle(x - 21, y + 6, edge, y + 64, 48, 61, 65, filled=True)
        pico2d.draw_rectangle(x - 21, y + 6, edge, y + 64, *metal)
        for yy in (20, 43):
            pico2d.draw_line(x - 16, y + yy, x + 16, y + yy, 83, 96, 97)
        if not self.opened:
            points = ((x + 3, y + 54), (x - 7, y + 36), (x + 3, y + 36), (x - 3, y + 20))
            for a, b in zip(points, points[1:]):
                segment(a, b, (239, 204, 125), width=3)
            with blended():
                glow(x, y + 39, 24, (226, 190, 105), alpha=45)
        color = (219, 188, 115) if not self.opened else (67, 77, 79)
        pico2d.draw_rectangle(x - 16, y + 68, x - 7, y + 70, *color, filled=True)
