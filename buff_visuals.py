"""속도 발광·몸을 감싸는 보호막과 차단 파편. 판정용 빛은 만들지 않는다."""

from math import ceil, cos, pi, sin

import pico2d

from effects import blended, glow, polygon
from inventory import SPEED, SHIELD
from item_art import draw_item
from item_effects import SPEED_DURATION, SHIELD_DURATION, SHIELD_BREAK_TIME


def draw_buffs(player, camera_x=0):
    effects = player.item_effects
    x, y = player.x - camera_x, player.feet_y
    with blended():
        if effects.speed_remaining > 0 and player.is_moving:
            strength = min(1, effects.speed_remaining / .3)
            glow(x, y + 5, 22, (116, 226, 153), alpha=80 * strength)
            for index in range(4):
                age = (effects.clock * 4 + index / 4) % 1
                tail = x - player.face_dir * (10 + age * 36)
                height = y + 4 + index % 2 * 5 + age * 8
                pico2d.draw_line(tail, height, tail + player.face_dir * (8 + age * 10), height + 1,
                                  158, 243, 181, a=int(210 * (1 - age) * strength))
        if effects.shield_remaining > 0:
            strength = min(1, effects.shield_remaining / .5)
            pulse = .85 + .15 * sin(effects.clock * 8)
            points = [(x, y - 5), (x + 34, y + 15), (x + 37, y + 75),
                      (x, y + 107), (x - 37, y + 75), (x - 34, y + 15)]
            polygon(points, (70, 174, 211), alpha=round(17 * strength))
            for index, first in enumerate(points):
                second = points[(index + 1) % len(points)]
                pico2d.draw_line(*first, *second, 132, 228, 249, a=round(205 * pulse * strength))
                glow(*first, 5, (135, 228, 249), alpha=110 * strength)
            for side in (-1, 1):
                for height in (30, 54, 78):
                    bx, by = x + side * 25, y + height
                    pico2d.draw_line(bx, by - 6, bx + side * 6, by - 2,
                                      91, 208, 236, a=round(75 * strength))
                    pico2d.draw_line(bx + side * 6, by - 2, bx + side * 6, by + 5,
                                      91, 208, 236, a=round(75 * strength))
            if effects.shield_activation > 0:
                progress = 1 - effects.shield_activation / .25
                for index in range(28):
                    angle = index * 2 * pi / 28
                    next_angle = (index + 1) * 2 * pi / 28
                    rx, ry = 29 + progress * 15, 47 + progress * 13
                    pico2d.draw_line(x + cos(angle) * rx, y + 47 + sin(angle) * ry,
                                      x + cos(next_angle) * rx, y + 47 + sin(next_angle) * ry,
                                      183, 244, 255, a=round(190 * (1 - progress)))
        if effects.shield_flash > 0:
            progress = 1 - effects.shield_flash / SHIELD_BREAK_TIME
            alpha = round(240 * (1 - progress))
            glow(x, y + 46, 48 * (1 - progress), (148, 233, 255), alpha=alpha)
            for index in range(12):
                angle = index * 2 * pi / 12
                radius = 18 + progress * 34
                px, py = x + cos(angle) * radius, y + 46 + sin(angle) * radius * 1.25
                pico2d.draw_line(px, py, px + cos(angle) * 8, py + sin(angle) * 8,
                                  190, 244, 255, a=alpha)


def draw_buff_timers(font, effects):
    for slot, remaining, duration, label, x, color in (
        (SPEED, effects.speed_remaining, SPEED_DURATION, '속도', 690, (139, 233, 166)),
        (SHIELD, effects.shield_remaining, SHIELD_DURATION, '보호막', 690, (144, 225, 247)),
    ):
        if remaining <= 0:
            continue
        y=112 if slot==SPEED else 142
        pico2d.draw_rectangle(x - 5, y-14, x + 248, y+12, 13, 23, 30, a=220, filled=True)
        draw_item(slot, x + 8, y, 21)
        seconds = max(.1, ceil((remaining - 1e-9) * 10) / 10)
        font.draw(x + 25, y, f'{label} {seconds:.1f}초', color)
        pico2d.draw_rectangle(x + 155, y-4, x + 238, y+1, 48, 60, 69, filled=True)
        pico2d.draw_rectangle(x + 155, y-4, x + 155 + 83 * remaining / duration, y+1, *color, filled=True)
