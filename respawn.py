"""초기 적과 같은 개체를 생성 지점에 연결해 어둠 속에서 보충한다."""

from dataclasses import dataclass
from math import hypot


RESPAWN_DELAY = 9.0
WARNING_DURATION = 1.0
SAFE_DISTANCE = 128


@dataclass
class SpawnPoint:
    identity: object
    x: float
    feet_y: float
    state: str = 'OCCUPIED'
    remaining: float = RESPAWN_DELAY
    warning_elapsed: float = 0.0
    generation: int = 0

    def get_bb(self):
        return self.x - 24, self.feet_y, self.x + 24, self.feet_y + 88


class RespawnDirector:
    def __init__(self, placements):
        self.points = [SpawnPoint(p.identity, p.x, p.feet_y) for p in placements]
        self.visual_time = 0.0
        self.actors = {}

    def reset(self, powered=False):
        self.visual_time = 0.0
        for point in self.points:
            point.state = 'SEALED' if powered else 'OCCUPIED'
            point.remaining = RESPAWN_DELAY
            point.warning_elapsed = 0.0
            point.generation = 0

    def update(self, delta_time, player, enemies, powered=False):
        dt = max(0.0, delta_time)
        self.visual_time += dt
        self.actors = {enemy.identity: enemy for enemy in enemies}
        for point in self.points:
            if powered:
                point.state = 'SEALED'
                point.warning_elapsed = 0.0
                continue
            if point.state == 'SEALED':
                continue
            enemy = self.actors.get(point.identity)
            if enemy is None:
                continue
            if enemy.alive:
                point.state = 'OCCUPIED'
                point.remaining = RESPAWN_DELAY
                point.warning_elapsed = 0.0
                continue
            if point.state == 'OCCUPIED':
                point.state = 'WAITING'
                point.remaining = RESPAWN_DELAY
                point.warning_elapsed = 0.0
                # 처치가 일어난 갱신의 시간을 대기에서 미리 빼지 않는다.
                continue
            lit = player.light is not None and player.light.illuminates(point.get_bb())
            near = hypot(player.x - point.x, player.feet_y - point.feet_y) < SAFE_DISTANCE
            if point.state == 'WARNING':
                if lit or near:
                    point.state = 'WAITING'
                    point.warning_elapsed = 0.0
                else:
                    point.warning_elapsed = min(WARNING_DURATION, point.warning_elapsed + dt)
                    if point.warning_elapsed >= WARNING_DURATION - 0.000000001:
                        enemy.reset()
                        point.state = 'OCCUPIED'
                        point.remaining = RESPAWN_DELAY
                        point.warning_elapsed = 0.0
                        point.generation += 1
            elif not lit:
                point.remaining = max(0.0, point.remaining - dt)
                if point.remaining <= 0.000000001:
                    point.remaining = 0.0
                    if not near:
                        point.state = 'WARNING'
                        point.warning_elapsed = 0.0

