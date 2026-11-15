"""양쪽 층 호출과 탑승자의 상대 위치를 보존하는 2개 층 승강기."""

from dataclasses import dataclass, field
from physics import Solid


@dataclass
class Elevator:
    x: float = 1792
    lower_y: float = 96
    upper_y: float = 352
    duration: float = 1.5
    width: float = 128
    y: float = 96
    target_y: float = 96
    origin_y: float = 96
    elapsed: float = 0
    rider: object = field(default=None, repr=False, compare=False)
    rider_offset: float = 0

    @property
    def moving(self):
        return abs(self.y-self.target_y) > 1e-6

    @property
    def solid(self):
        return Solid(self.x-self.width/2, self.y-16, self.x+self.width/2, self.y, True)

    def on_platform(self, player):
        return (player.motion.on_ground and abs(player.feet_y-self.y) <= .01
                and abs(player.x-self.x) <= self.width/2-player.motion.width/2-4)

    def call(self, level):
        if self.moving or level not in (self.lower_y, self.upper_y) or abs(self.y-level) < 1e-6:
            return False
        self.origin_y, self.target_y, self.elapsed = self.y, level, 0
        return True

    def attach(self, player):
        self.rider, self.rider_offset = player, player.x-self.x
        player.clear_input()
        player.motion.velocity_y = 0
        player.is_moving = False

    def board(self, player):
        if self.moving or not self.on_platform(player):
            return False
        target = self.upper_y if abs(self.y-self.lower_y) < .01 else self.lower_y
        if not self.call(target):
            return False
        self.attach(player)
        return True

    def update(self, delta_time):
        if not self.moving:
            return
        self.elapsed = min(self.duration, self.elapsed+max(0, delta_time))
        t = self.elapsed/self.duration
        t = t*t*(3-2*t)
        self.y = self.origin_y+(self.target_y-self.origin_y)*t
        if self.rider is not None:
            p = self.rider
            p.x, p.feet_y = self.x+self.rider_offset, self.y
            p.motion.velocity_y, p.motion.on_ground = 0, True
            p.clear_input()
        if not self.moving:
            self.y = self.target_y
            self.rider = None

    def reset_lower(self):
        if self.rider is not None:
            self.rider.clear_input()
        self.y = self.target_y = self.origin_y = self.lower_y
        self.elapsed = 0
        self.rider = None

    def snapshot(self):
        return self.y, self.target_y, self.origin_y, self.elapsed

    def restore(self, state):
        self.y, self.target_y, self.origin_y, self.elapsed = state
        self.rider = None
