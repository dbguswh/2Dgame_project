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

    @classmethod
    def capture(cls, player, stage):
        return cls(player.health, player.battery, player.max_battery,
                   (player.x, player.feet_y), tuple(player.checkpoint_position),
                   stage.fixture_powered, stage.fuse_state, stage.bridge_elapsed, stage.completed)


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
        player.checkpoint_position = snapshot.checkpoint
        stage.fixture_powered = snapshot.fixture_powered
        stage.fuse_state = snapshot.fuse_state
        stage.bridge_elapsed = snapshot.bridge_elapsed
        stage.completed = snapshot.completed
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
        player.face_dir = 1
        player.light = None
        player.reset_actions_after_return(invulnerability=0.0)
        player.notice = '구간을 처음부터 다시 시작합니다'
        player.notice_time = 1.5
        self.latest = replace(self.entry)
