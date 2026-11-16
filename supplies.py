"""한 번만 개봉하고 미수령 소모품을 남기는 보급함."""

from dataclasses import dataclass
from inventory import MEDKIT, SPEED, LIGHT_BOMB, SHIELD
from item_art import draw_item


OPEN_TIME = 0.3
SUPPLY_COLORS = ((175, 126, 111), (125, 177, 117), (196, 162, 93), (115, 175, 191))


@dataclass
class SupplyBox:
    identity: str
    x: float
    feet_y: float
    opened: bool = False
    claimed: bool = False
    opening_elapsed: float = 0.0
    item: int = MEDKIT

    @property
    def pickup_ready(self):
        return self.opened and not self.claimed and self.opening_elapsed >= OPEN_TIME

    @property
    def pickup_position(self):
        return self.x + 16, self.feet_y + 14

    def open(self):
        if self.opened:
            return False
        self.opened = True
        return True

    def update(self, delta_time):
        if self.opened:
            self.opening_elapsed = min(OPEN_TIME, self.opening_elapsed + max(0, delta_time))

    def snapshot(self):
        return self.identity, self.opened, self.claimed, self.opening_elapsed

    def restore(self, state):
        _, self.opened, self.claimed, self.opening_elapsed = state

    def draw(self, camera_x=0):
        import pico2d
        from effects import blended, glow
        from supply_art import draw_supply_case
        x, y = self.x - camera_x, self.feet_y
        progress = min(1, self.opening_elapsed / OPEN_TIME)
        draw_supply_case(x,y,progress)
        # 같은 상자를 쓰되 전면 표식으로 내용물 종류를 구분한다.
        marker_x,marker_y=x-2,y+10
        if self.item == MEDKIT:
            pico2d.draw_rectangle(marker_x-1,marker_y-4,marker_x+1,marker_y+4,190,79,69,filled=True)
            pico2d.draw_rectangle(marker_x-4,marker_y-1,marker_x+4,marker_y+1,190,79,69,filled=True)
        elif self.item == LIGHT_BOMB:
            pico2d.draw_circle(round(marker_x),round(marker_y),4,206,160,71,filled=True)
            pico2d.draw_circle(round(marker_x),round(marker_y),2,255,237,179,filled=True)
        else:
            draw_item(self.item,marker_x,marker_y,12)
        if not self.opened:
            with blended():
                glow(x,y+22,23,SUPPLY_COLORS[self.item],alpha=35)
        if self.pickup_ready:
            px, py = self.pickup_position
            with blended():
                color = (132, 219, 244) if self.item == SHIELD else (175, 222, 162)
                glow(px - camera_x, py, 19, color, alpha=75)
            draw_item(self.item, px - camera_x, py, 27 if self.item in (SPEED,SHIELD) else 22)


def draw_medkit_icon(x, y, size=18):
    draw_item(MEDKIT, x, y, size)


def draw_battery_pack(x, y):
    import pico2d
    pico2d.draw_rectangle(x - 9, y - 10, x + 9, y + 10, 63, 82, 97, filled=True)
    pico2d.draw_rectangle(x - 9, y - 10, x + 9, y + 10, 134, 159, 170)
    pico2d.draw_rectangle(x - 4, y + 10, x + 4, y + 13, 164, 170, 165, filled=True)
    for bar_y in (y - 6, y - 1, y + 4):
        pico2d.draw_rectangle(x - 5, bar_y, x + 5, bar_y + 2, 137, 195, 203, filled=True)
