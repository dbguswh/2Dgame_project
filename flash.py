"""섬광 공격의 초기 수치와 즉시 발사되는 짧은 빛 표현."""

from dataclasses import dataclass

import pico2d

from effects import blended, glow, light_beam


FLASH_COST = 20
FLASH_RANGE = 160
FLASH_COOLDOWN = 0.8
FLASH_STUN = 1.2
FLASH_KNOCKBACK = 48
FLASH_FRAME_ENDS = (0.04, 0.08, 0.12, 0.19, 0.26, 0.32)


@dataclass
class FlashPulse:
    x: float
    feet_y: float
    direction: int
    box: tuple | None
    age: float = 0.0

    @property
    def active(self):
        return self.age < 0.18

    def update(self, delta_time):
        self.age += delta_time

    def draw(self, camera_x=0):
        if not self.active:
            return
        x, y = self.x - camera_x + self.direction * 38, self.feet_y + 54
        strength = max(0.0, 1 - self.age / 0.18)
        if self.box is not None:
            left, bottom, right, top = self.box
            end = (right if self.direction > 0 else left) - camera_x
            with blended((left - camera_x, bottom, right - camera_x, top)):
                light_beam((x, y), (end, bottom), (end, top), alpha=225 * strength)
                for offset in (-2, 0, 2):
                    pico2d.draw_line(x, y + offset, end, y + offset,
                                      255, 239, 184, a=int(175 * strength))
                glow(x, y, 22, (255, 224, 155), alpha=210 * strength)
                # 유효 거리의 끝도 읽혀 짧은 근접 베기와 구분되게 한다.
                glow(end,y,8,(255,239,190),alpha=130*strength)
        with blended():
            glow(x, y, 12, (255, 245, 211), alpha=220 * strength)
