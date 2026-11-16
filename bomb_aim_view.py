"""광탄 조준 궤적·착지 범위·충전 게이지. 월드의 밝기나 판정은 바꾸지 않는다."""

from math import atan2, cos, pi, sin

import pico2d

from effects import blended, glow
from inventory import LIGHT_BOMB
from item_art import draw_item
from light_bomb import BLAST_RADIUS, blocked_segment, predict_throw


def draw_bomb_aim(player, solids, font, camera_x, screen_width, screen_height):
    aim = player.bomb_aim
    if aim is None:
        return
    points, impact = predict_throw(player.x, player.feet_y + 44, aim.direction,
                                   aim.charge, aim.angle, solids)
    gold = (255, 216, 131)
    with blended():
        for index, (px, py) in enumerate(points[1:]):
            x = px - camera_x
            if -4 <= x <= screen_width + 4 and 64 <= py < screen_height - 112:
                pico2d.draw_circle(round(x), round(py), 2, *gold,
                                  a=255 if index % 3 == 0 else 185, filled=True)
        if len(points) > 3:
            px, py = points[3]
            angle = atan2(py - points[2][1], px - points[2][0])
            for offset in (-.55, .55):
                pico2d.draw_line(px-camera_x, py, px-camera_x-9*cos(angle+offset),
                                  py-9*sin(angle+offset), *gold, a=240)
        if impact is not None:
            x, y = impact[0] - camera_x, impact[1]
            nearby = [s for s in solids if s.left < impact[0]+BLAST_RADIUS
                      and s.right > impact[0]-BLAST_RADIUS and s.bottom < y+BLAST_RADIUS
                      and s.top > y-BLAST_RADIUS]
            # 벽·바닥 뒤에는 실제 피해가 전달되지 않으므로 범위선도 잘라 표시한다.
            for index in range(64):
                first = (impact[0]+BLAST_RADIUS*cos(index*pi/32), y+BLAST_RADIUS*sin(index*pi/32))
                second = (impact[0]+BLAST_RADIUS*cos((index+1)*pi/32), y+BLAST_RADIUS*sin((index+1)*pi/32))
                if not blocked_segment(impact, first, nearby) and not blocked_segment(impact, second, nearby):
                    pico2d.draw_line(first[0]-camera_x, first[1], second[0]-camera_x, second[1], *gold, a=185)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                pico2d.draw_line(x+dx*6, y+dy*6, x+dx*13, y+dy*13, *gold, a=245)
            pico2d.draw_circle(round(x), round(y), 4, *gold, a=240)
        hand_x = player.x-camera_x+aim.direction*20
        glow(hand_x, player.feet_y+53, 12, gold, alpha=75+65*aim.charge)
        draw_item(LIGHT_BOMB, hand_x, player.feet_y+53, 18)

        # 높은 발판에서는 머리 위 HUD와 겹치지 않게 발 아래로 옮긴다.
        center = max(88, min(screen_width-88, player.x-camera_x))
        y = player.feet_y + 110
        if y + 48 > screen_height - 112:
            y = max(112, player.feet_y-65)
        pico2d.draw_rectangle(center-82, y-4, center+82, y+46, 10, 18, 27, a=235, filled=True)
        pico2d.draw_rectangle(center-82, y-4, center+82, y+46, 131, 112, 73, a=210)
        pico2d.draw_rectangle(center-70, y+5, center+70, y+12, 49, 56, 63, filled=True)
        if aim.charge > 0:
            pico2d.draw_rectangle(center-70, y+5, center-70+140*aim.charge, y+12,
                                  *gold, filled=True)
        if aim.charge >= 1:
            pico2d.draw_line(center-70, y+15, center+70, y+15, 255, 243, 201)
    font.draw(center-68, y+31, f'광탄 {round(aim.charge*100):3d}%  {round(aim.angle):2d}도', gold)
