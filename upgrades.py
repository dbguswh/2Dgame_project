"""복구 후 관리소 방문당 서로 다른 코어 강화 한 개를 구매한다."""

from dataclasses import dataclass
from inventory import MEDKIT, LIGHT_BOMB, ITEM_NAMES, STACK_LIMIT


UPGRADE_COST = 2
CAPACITY, FOCUS, SPREAD = 'capacity', 'focus', 'spread'


@dataclass(frozen=True)
class CoreUpgrade:
    key: str
    name: str
    before: str
    after: str
    description: str


CORE_UPGRADES = (
    CoreUpgrade(CAPACITY, '축전', '배터리 최대치 100', '140', 'Q·R을 위한 저장 용량 증가'),
    CoreUpgrade(FOCUS, '집광', 'Q 사거리', '+25%', '멀리 있는 적을 먼저 제압'),
    CoreUpgrade(SPREAD, '확산', 'R 조명 범위', '+25%', '더 넓은 이동·방어 공간 확보'),
)
UPGRADE_KEYS = frozenset(upgrade.key for upgrade in CORE_UPGRADES)


@dataclass(frozen=True)
class SupplyOffer:
    slot: int
    description: str
    cost: int = 1

    @property
    def name(self):
        return ITEM_NAMES[self.slot]


SUPPLY_OFFERS = (SupplyOffer(MEDKIT, '사용하면 체력 1칸 회복'),
                 SupplyOffer(LIGHT_BOMB, '여러 적에게 피해 1·공격 취소'))


class ManagementVisit:
    def __init__(self):
        self.chosen_upgrade = None
        self.notice = '전력 조각 2개로 코어 강화를 하나 선택하세요'

    @property
    def completed(self):
        return self.chosen_upgrade is not None

    def blocked_reason(self, player, selection):
        if selection not in range(len(CORE_UPGRADES)):
            return '선택할 수 없는 강화입니다'
        if self.completed:
            return '이번 방문의 강화를 완료했습니다'
        if CORE_UPGRADES[selection].key in player.core_upgrades:
            return '이미 적용한 강화입니다'
        if player.fragments < UPGRADE_COST:
            return '전력 조각이 부족합니다'
        return ''

    def purchase(self, player, selection):
        reason = self.blocked_reason(player, selection)
        if reason:
            self.notice = reason
            return False
        upgrade = CORE_UPGRADES[selection]
        if not player.apply_core_upgrade(upgrade.key):
            self.notice = '이미 적용한 강화입니다'
            return False
        player.fragments -= UPGRADE_COST
        self.chosen_upgrade = upgrade.key
        self.notice = f'{upgrade.name} 강화 완료 · 전력 조각 -2'
        return True

    def supply_blocked_reason(self, player, selection):
        if selection not in range(len(SUPPLY_OFFERS)):
            return '선택할 수 없는 보급품입니다'
        if not self.completed:
            return '코어 강화를 먼저 완료하세요'
        offer = SUPPLY_OFFERS[selection]
        if player.inventory.counts[offer.slot] >= STACK_LIMIT:
            return f'{offer.name} 보유 한도 {STACK_LIMIT}개에 도달했습니다'
        if player.fragments < offer.cost:
            return '전력 조각이 부족합니다'
        return ''

    def purchase_supply(self, player, selection):
        reason = self.supply_blocked_reason(player, selection)
        if reason:
            self.notice = reason
            return False
        offer = SUPPLY_OFFERS[selection]
        if not player.inventory.add(offer.slot):
            self.notice = '보유 수량을 확인하세요'
            return False
        player.fragments -= offer.cost
        self.notice = f'{offer.name} +1 · 전력 조각 -{offer.cost}'
        return True
