"""속도·보호막의 독립 수명과 한 번 차단 규칙."""

from dataclasses import dataclass

from inventory import SPEED, SHIELD


SPEED_DURATION = 5.0
SPEED_MULTIPLIER = 1.3
SHIELD_DURATION = 6.0
SHIELD_BREAK_TIME = 0.35


@dataclass
class ItemEffects:
    speed_remaining: float = 0.0
    shield_remaining: float = 0.0
    shield_flash: float = 0.0
    shield_activation: float = 0.0
    clock: float = 0.0

    @property
    def speed_multiplier(self):
        return SPEED_MULTIPLIER if self.speed_remaining > 0 else 1.0

    def activate(self, slot):
        if slot == SPEED and self.speed_remaining <= 0:
            self.speed_remaining = SPEED_DURATION
            return True
        if slot == SHIELD and self.shield_remaining <= 0:
            self.shield_remaining = SHIELD_DURATION
            self.shield_activation = .25
            return True
        return False

    def update(self, delta_time):
        dt = max(0.0, delta_time)
        covered = min(dt, self.speed_remaining)
        self.clock += dt
        self.speed_remaining = max(0.0, self.speed_remaining - dt)
        self.shield_remaining = max(0.0, self.shield_remaining - dt)
        self.shield_flash = max(0.0, self.shield_flash - dt)
        self.shield_activation = max(0.0, self.shield_activation - dt)
        # 만료를 걸치는 한 프레임도 활성 시간만큼의 수평 이동을 허용한다.
        return 1 + (SPEED_MULTIPLIER - 1) * covered / dt if dt else self.speed_multiplier

    def absorb_attack(self):
        if self.shield_remaining <= 0:
            return False
        self.shield_remaining = 0.0
        self.shield_activation = 0.0
        self.shield_flash = SHIELD_BREAK_TIME
        return True

    def clear(self):
        self.speed_remaining = self.shield_remaining = 0.0
        self.shield_flash = self.shield_activation = self.clock = 0.0
