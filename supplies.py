"""한 번만 개봉하고 미수령 치료제를 남기는 보급함."""

from dataclasses import dataclass


OPEN_TIME = 0.3


@dataclass
class SupplyBox:
    identity: str
    x: float
    feet_y: float
    opened: bool = False
    claimed: bool = False
    opening_elapsed: float = 0.0

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
