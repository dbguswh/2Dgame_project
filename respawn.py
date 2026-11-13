"""초기 적과 같은 개체를 생성 지점에 연결해 어둠 속에서 보충한다."""

from dataclasses import dataclass
from math import ceil, hypot


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
    appear_remaining: float = 0.0

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
            point.appear_remaining = 0.0

    def update(self, delta_time, player, enemies, powered=False,
               previous_light=None, previous_light_remaining=0.0):
        dt = max(0.0, delta_time)
        self.visual_time += dt
        self.actors = {enemy.identity: enemy for enemy in enemies}
        for point in self.points:
            point.appear_remaining = max(0.0, point.appear_remaining - dt)
            if powered:
                point.state = 'SEALED'
                point.warning_elapsed = 0.0
                point.appear_remaining = 0.0
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
                point.appear_remaining = 0.0
                continue
            lit = player.light is not None and player.light.illuminates(point.get_bb())
            covered_time = (min(dt, previous_light_remaining)
                            if previous_light is not None and not previous_light.active
                            and previous_light.covers(point.get_bb()) else 0.0)
            dark_time = max(0.0, dt - covered_time)
            near = hypot(player.x - point.x, player.feet_y - point.feet_y) < SAFE_DISTANCE
            if point.state == 'WARNING':
                if lit or near or covered_time > 0:
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
                        point.appear_remaining = 0.35
            elif not lit:
                point.remaining = max(0.0, point.remaining - dark_time)
                if point.remaining <= 0.000000001:
                    point.remaining = 0.0
                    if not near:
                        point.state = 'WARNING'
                        point.warning_elapsed = 0.0

    def draw_floor(self, camera_x, screen_width=960):
        import pico2d
        from effects import blended, glow
        with blended():
            for point in self.points:
                x, y = point.x - camera_x, point.feet_y + 2
                if not -50 <= x <= screen_width + 50:
                    continue
                color = (119, 108, 79) if point.state == 'SEALED' else (94, 64, 116)
                glow(x, y, 19, color, alpha=45, squash=0.14)
                for a, b in (((-16, 0), (-6, 3)), ((-6, 3), (2, -1)), ((2, -1), (16, 2))):
                    pico2d.draw_line(x + a[0], y + a[1], x + b[0], y + b[1], *color, a=140)

    def draw_signals(self, camera_x, font, screen_width=960):
        import pico2d
        from math import sin
        from effects import blended, glow
        for point in self.points:
            x, y = point.x - camera_x, point.feet_y
            if not -100 <= x <= screen_width + 100:
                continue
            if point.appear_remaining > 0:
                with blended():
                    glow(x, y + 28, 38, (170, 86, 224), alpha=100 * point.appear_remaining / 0.35)
            if point.state != 'WARNING':
                continue
            progress = point.warning_elapsed / WARNING_DURATION
            with blended():
                glow(x, y + 3, 22 + progress * 14, (155, 72, 213), alpha=180, squash=0.20)
                glow(x, y + 35, 25 + progress * 14, (109, 55, 163), alpha=70 + progress * 60)
                for index in range(7):
                    phase = (self.visual_time * 0.85 + index / 7) % 1
                    sx = x + sin(index * 2.4 + self.visual_time * 3) * (17 - phase * 9)
                    sy = y + 6 + phase * (50 + progress * 45)
                    pico2d.draw_line(sx, sy, sx + sin(index) * 3, sy + 6,
                                      192, 110, 232, a=int(220 * (1 - phase)))
            enemy = self.actors.get(point.identity)
            if enemy is not None:
                data = enemy.motion_data
                frame = data['frames'][data['walk'][0]]
                left, bottom, width, height = frame['rect']
                feet_x, feet_y = frame['feet']
                scale = 104 / data['reference_height']
                enemy.image.opacify(0.12 + progress * 0.38)
                try:
                    enemy.image.clip_composite_draw(left, bottom, width, height, 0, '',
                        x + (width / 2 - feet_x) * scale, y + (height / 2 - feet_y) * scale,
                        width * scale, height * scale)
                finally:
                    enemy.image.opacify(1.0)
            pico2d.draw_rectangle(x - 18, y + 112, x + 18, y + 115, 52, 31, 66, filled=True)
            pico2d.draw_rectangle(x - 18, y + 112, x - 18 + 36 * progress, y + 115,
                                  193, 113, 232, filled=True)
            seconds = max(0.1, ceil((WARNING_DURATION - point.warning_elapsed) * 10 - 0.000000001) / 10)
            font.draw(x - 50, y + 124, f'출현 {seconds:.1f}초 전', (210, 155, 235))

