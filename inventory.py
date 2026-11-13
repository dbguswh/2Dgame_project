"""종류별 두 개까지 보관하는 고정 네 칸 인벤토리."""

from dataclasses import dataclass, field


ITEM_NAMES = ('치료제', '속도 촉진제', '광탄', '보호막 팩')
MEDKIT, SPEED, LIGHT_BOMB, SHIELD = range(4)
STACK_LIMIT = 2


@dataclass
class Inventory:
    counts: list = field(default_factory=lambda: [0, 0, 0, 0])
    selected: int = MEDKIT

    def select(self, slot):
        if slot not in range(4):
            return False
        self.selected = slot
        return True

    def add(self, slot):
        if slot not in range(4) or self.counts[slot] >= STACK_LIMIT:
            return False
        self.counts[slot] += 1
        return True

    def consume(self, slot):
        if slot not in range(4) or self.counts[slot] <= 0:
            return False
        self.counts[slot] -= 1
        return True

    def snapshot(self):
        return tuple(self.counts)

    def restore(self, counts):
        if len(counts) != 4 or any(type(n) is not int or not 0 <= n <= STACK_LIMIT for n in counts):
            raise ValueError('아이템 수량은 네 종류 각각 0~2개여야 합니다')
        self.counts[:] = counts
