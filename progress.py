"""실행 중 스테이지 진입 기록과 최신 진행 기록을 별도로 보관한다."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ProgressSnapshot:
    health: int
    battery: int
    max_battery: int
    position: tuple
    checkpoint: tuple
    fixture_powered: bool
    fuse_state: str
    bridge_elapsed: float
    completed: bool
    fragments: int
    reward_claimed: bool
    battery_pack_collected: bool
    fixture_seen: bool = False
    medkits: int = 0
    return_battery_collected: bool = False
    supply_states: tuple = ()
    inventory_counts: tuple = (0, 0, 0, 0)
    core_upgrades: tuple = ()
    fragment_cache_state: tuple = ()
    stage_state: tuple = ()
    ring_unlocked: bool = False
    weapon: str = 'sword'

    @classmethod
    def capture(cls, player, stage):
        cache = getattr(stage, 'fragment_cache', None)
        return cls(player.health, player.battery, player.max_battery,
                   (player.x, player.feet_y), tuple(player.checkpoint_position),
                   stage.fixture_powered, stage.fuse_state, stage.bridge_elapsed, stage.completed,
                   player.fragments, stage.reward_claimed, stage.battery_pack_collected,
                   getattr(stage, 'fixture_seen', False), player.medkits,
                   getattr(stage, 'return_battery_collected', False),
                   tuple(box.snapshot() for box in getattr(stage, 'supply_boxes', ())),
                   player.inventory.snapshot(), tuple(sorted(player.core_upgrades)),
                   cache.snapshot() if cache is not None else (), stage.capture_state(),player.ring_unlocked,player.weapon)


class ProgressRecords:
    def __init__(self, player, stage):
        self.entry = ProgressSnapshot.capture(player, stage)
        self.latest = replace(self.entry)

    def remember(self, player, stage):
        self.latest = ProgressSnapshot.capture(player, stage)

    @staticmethod
    def _apply_progress(snapshot, player, stage):
        player.battery = snapshot.battery
        player.max_battery = snapshot.max_battery
        player.core_upgrades = set(snapshot.core_upgrades)
        player.ring_unlocked=snapshot.ring_unlocked
        player.weapon=snapshot.weapon
        player.checkpoint_position = snapshot.checkpoint
        stage.fixture_powered = snapshot.fixture_powered
        stage.fuse_state = snapshot.fuse_state
        stage.bridge_elapsed = snapshot.bridge_elapsed
        if hasattr(stage,'reveal_light_elapsed'):stage.reveal_light_elapsed=snapshot.bridge_elapsed
        stage.completed = snapshot.completed
        player.fragments = snapshot.fragments
        stage.reward_claimed = snapshot.reward_claimed
        stage.battery_pack_collected = snapshot.battery_pack_collected
        if hasattr(stage, 'fixture_seen'):
            stage.fixture_seen = snapshot.fixture_seen
        player.inventory.restore(snapshot.inventory_counts)
        player.medkits = snapshot.medkits
        if hasattr(stage, 'return_battery_collected'):
            stage.return_battery_collected = snapshot.return_battery_collected
        states = {state[0]: state for state in snapshot.supply_states}
        for box in getattr(stage, 'supply_boxes', ()):
            if box.identity in states:
                box.restore(states[box.identity])
        cache = getattr(stage, 'fragment_cache', None)
        if cache is not None and snapshot.fragment_cache_state:
            cache.restore(snapshot.fragment_cache_state)
        stage.restore_state(snapshot.stage_state)
        stage.update(0)

    def restore_after_death(self, player, stage):
        self._apply_progress(self.latest, player, stage)
        stage.restore_after_death()
        player.health = 3
        player.x, player.feet_y = self.latest.checkpoint
        player.last_safe_position = self.latest.checkpoint
        player.light = None
        player.reset_actions_after_return(invulnerability=1.0)
        player.notice = '안전 지점에서 다시 시작합니다'
        player.notice_time = 2.0
        self.remember(player, stage)

    def restore_entry(self, player, stage):
        self._apply_progress(self.entry, player, stage)
        player.health = self.entry.health
        player.x, player.feet_y = self.entry.position
        player.last_safe_position = self.entry.position
        player.face_dir = getattr(stage, 'start_direction', 1)
        player.light = None
        player.reset_actions_after_return(invulnerability=0.0)
        player.notice = '구간을 처음부터 다시 시작합니다'
        player.notice_time = 1.5
        self.latest = replace(self.entry)
