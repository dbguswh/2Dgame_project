"""칼날 궤적과 같은 판정 영역에 남는 짧은 금빛 참격."""

from math import cos, sin, pi

import pico2d

from effects import blended, glow, polygon
from light_sword import SWORD_REACH, sword_box


def stroke_state(player):
    if not player.is_attacking or player.attack_kind not in ('ground', 'air', 'upper'):
        return None
    air = player.attack_kind == 'air'
    rising = not air and player.attack_stage == 2
    start, end, linger = (.1, .22, .06) if air else (.12, .24, .10) if rising else (.1, .2, .08)
    elapsed = player.attack_elapsed
    if elapsed < start or elapsed >= end + linger:
        return None
    progress = min(1, (elapsed-start)/(end-start))
    opacity = max(0, 1-(max(0, elapsed-end)/linger))
    bounds = (player.get_attack_box() if player.attack_kind=='upper'
              else sword_box(player.x, player.feet_y, player.face_dir, air, player.solids, rising))
    return bounds, air, rising, progress, opacity


def draw_sword_stroke(player, camera_x=0):
    state = stroke_state(player)
    if state is None or state[0] is None:
        return
    bounds, air, rising, progress, opacity = state
    left, bottom, right, top = bounds
    x = player.x-camera_x+player.face_dir*12
    y = player.feet_y+(40 if air else 44 if rising else 45)
    angle = (-65*progress) if air else (-23+80*progress) if rising else (22-44*progress)
    angle_start, angle_end = (angle,angle+28) if air else (angle-25,angle) if rising else (angle,angle+22)
    minimum,maximum=(-65,0) if air else (-23,57) if rising else (-22,22)
    angle_start,angle_end=max(minimum,angle_start),min(maximum,angle_end)
    radius = SWORD_REACH
    if player.attack_kind=='upper':
        y=player.feet_y+44
        radius=112
        angle=20+75*progress
        angle_start,angle_end=angle-24,angle
    with blended((left-camera_x,bottom,right-camera_x,top)):
        for index in range(32):
            t0,t1=index/32,(index+1)/32
            a=(angle_start+(angle_end-angle_start)*t0)*pi/180
            b=(angle_start+(angle_end-angle_start)*t1)*pi/180
            taper=sin(pi*(t0+t1)/2)**.65
            for width,alpha,color in ((14,82,(244,175,65)),(7,160,(255,215,133)),(2,230,(255,246,208))):
                outer=radius
                inner_a=radius-width*sin(pi*t0)**.65
                inner_b=radius-width*sin(pi*t1)**.65
                pts=((x+player.face_dir*cos(a)*inner_a,y+sin(a)*inner_a),
                     (x+player.face_dir*cos(a)*outer,y+sin(a)*outer),
                     (x+player.face_dir*cos(b)*outer,y+sin(b)*outer),
                     (x+player.face_dir*cos(b)*inner_b,y+sin(b)*inner_b))
                polygon(pts,color,alpha*opacity*(.3+.7*taper))
        tip=angle*pi/180
        glow(x+player.face_dir*cos(tip)*(radius-4),y+sin(tip)*(radius-4),
             13 if rising else 10,(255,222,148),alpha=140*opacity)
