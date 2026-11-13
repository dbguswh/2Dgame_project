"""주택가의 대형 양엽식 금속 다리. 충돌은 스테이지가 전개 완료 때 추가한다."""

from math import cos, sin, pi

import pico2d

from effects import blended, glow, polygon, segment
from stage import GROUND_Y


def bridge_angle(elapsed, duration):
    progress = max(0.0, min(1.0, (elapsed - 0.25) / (duration - 0.60)))
    eased = progress * progress * (3 - 2 * progress)
    return (1 - eased) * pi / 2


def draw_bridge(stage, camera_x):
    left, right = stage.canal
    half = (right - left) / 2
    elapsed = stage.bridge_elapsed if stage.fixture_powered else 0
    angle = bridge_angle(elapsed, stage.BRIDGE_TIME)
    c, s = cos(angle), sin(angle)
    powered, ready = stage.fixture_powered, stage.bridge_ready
    for hinge, direction in ((left, 1), (right, -1)):
        shore_x = hinge - camera_x
        # 물가의 돌 교각과 고정 기계실이 다리의 무게를 받친다.
        outer = shore_x - direction * 46
        pier_left, pier_right = sorted((outer, shore_x + direction * 8))
        pico2d.draw_rectangle(pier_left, 8, pier_right, GROUND_Y - 1, 49, 57, 66, filled=True)
        for y in range(10, GROUND_Y - 8, 22):
            pico2d.draw_line(pier_left, y, pier_right, y, 25, 34, 43)
        pico2d.draw_rectangle(pier_left - 3, GROUND_Y - 8, pier_right + 3,
                              GROUND_Y - 1, 125, 126, 116, filled=True)

        def point(distance, height):
            return (shore_x + direction * (distance * c - height * s),
                    GROUND_Y + distance * s + height * c)

        def line(a, b, color, thickness=1):
            ax, ay = point(*a)
            bx, by = point(*b)
            segment((ax, ay), (bx, by), color, width=max(1.5, thickness))

        # 두께 있는 철제 상판과 아래쪽 삼각 보강재.
        polygon([point(0, 0), point(half, 0), point(half, -13), point(0, -13)], (62, 77, 89))
        polygon([point(0, 0), point(half, 0), point(half, -4), point(0, -4)], (180, 171, 140))
        line((0, -29), (half, -29), (79, 96, 108), 4)
        for distance in range(0, int(half), 48):
            end = min(distance + 48, half)
            line((distance, -12), (end, -29), (112, 125, 127), 3)
            line((distance, -29), (end, -12), (112, 125, 127), 3)
            line((distance, -12), (distance, -29), (52, 66, 80), 2)
            for bolt_height in (-9, -25):
                bx, by = point(distance + 5, bolt_height)
                pico2d.draw_circle(bx, by, 2, 193, 162, 99, filled=True)
        for distance in range(8, int(half), 16):
            line((distance, 0), (distance, -4), (72, 83, 88))
        # 난간은 상판과 함께 회전하며 완성 후에도 길 전체에 남는다.
        for distance in range(0, int(half) + 1, 48):
            line((distance, 0), (distance, 34), (115, 127, 129), 3)
        line((0, 34), (half, 34), (174, 178, 165), 3)
        line((0, 15), (half, 15), (91, 107, 116), 2)
        for distance in range(0, 28, 7):
            line((distance, -1), (distance + 5, -4), (233, 179, 72), 2)
        # 외부 와이어와 힌지 모터를 연결해 전개 방향을 읽을 수 있게 한다.
        mast_x = shore_x - direction * 30
        pico2d.draw_rectangle(mast_x - 3, GROUND_Y, mast_x + 3,
                              GROUND_Y + 76, 72, 87, 98, filled=True)
        tip_x, tip_y = point(half * 0.72, 3)
        previous = (mast_x, GROUND_Y + 76)
        for index in range(1, 13):
            t = index / 12
            next_point = (mast_x + (tip_x - mast_x) * t,
                          GROUND_Y + 76 + (tip_y - GROUND_Y - 76) * t - sin(pi * t) * 8)
            pico2d.draw_line(*previous, *next_point, 124, 133, 128)
            previous = next_point
        pico2d.draw_circle(shore_x, GROUND_Y + 2, 12, 33, 46, 59, filled=True)
        pico2d.draw_circle(shore_x, GROUND_Y + 2, 9, 140, 124, 83)
        rotation = angle * direction + elapsed * 0.5
        for index in range(6):
            theta = rotation + index * pi / 3
            bx, by = shore_x + cos(theta) * 7, GROUND_Y + 2 + sin(theta) * 7
            pico2d.draw_circle(bx, by, 2, 196, 171, 117, filled=True)
        color = (171, 226, 181) if ready else (255, 191, 90) if powered else (58, 70, 81)
        pico2d.draw_rectangle(mast_x - 5, GROUND_Y + 74, mast_x + 5,
                              GROUND_Y + 86, *color, filled=True)
        if powered:
            with blended():
                glow(mast_x, GROUND_Y + 80, 18, color, alpha=60)
                if elapsed < 0.25:
                    glow(shore_x, GROUND_Y + 4, 18, alpha=100 * (1 - elapsed / 0.25))
    if powered and elapsed > stage.BRIDGE_TIME - 0.35:
        center = (left + right) / 2 - camera_x
        strength = max(0.0, 1 - abs(elapsed - (stage.BRIDGE_TIME - 0.15)) / 0.2)
        with blended():
            glow(center, GROUND_Y, 24, (255, 225, 151), alpha=100 * strength)
    if powered and not ready:
        x = left - 5 - camera_x
        pico2d.draw_rectangle(x - 6, GROUND_Y, x + 6, GROUND_Y + 80,
                              73, 82, 88, filled=True)
        for y in range(GROUND_Y + 3, GROUND_Y + 78, 10):
            pico2d.draw_line(x - 5, y, x + 5, y + 5, 236, 176, 66)
