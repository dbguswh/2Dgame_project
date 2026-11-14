"""애니메이션이 완전히 끝난 뒤 통과할 수 있는 병원 전동문."""

from dataclasses import dataclass
from physics import Solid


@dataclass
class PowerDoor:
    identity: str
    x: float
    feet_y: float = 96
    progress: float = 0
    duration: float = .55
    height: float = 344
    blocks_corridor: bool = True

    @property
    def is_open(self):
        return self.progress >= 1 - 1e-8

    @property
    def solid(self):
        return Solid(self.x - 24, self.feet_y, self.x + 24, self.feet_y+self.height)

    def update(self, delta_time, target_open):
        direction = 1 if target_open else -1
        self.progress = max(0, min(1, self.progress + direction * max(0, delta_time) / self.duration))
