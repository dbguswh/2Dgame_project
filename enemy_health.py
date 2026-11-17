"""종류별 최대 체력 비율을 보여주는 연속 게이지. 숫자와 칸 경계는 표시하지 않는다."""

import pico2d
from effects import blended


def draw_health(enemy,camera_x=0,offset=114,color=(192,100,215),width=44):
    if not enemy.alive:return
    x,y=enemy.x-camera_x,enemy.feet_y+offset
    left=x-width/2
    ratio=max(0,min(1,enemy.health/enemy.max_health))
    pico2d.draw_rectangle(left-2,y-2,left+width+2,y+6,11,16,25,filled=True)
    pico2d.draw_rectangle(left-1,y-1,left+width+1,y+5,84,77,94)
    pico2d.draw_rectangle(left,y,left+width,y+4,42,29,51,filled=True)
    if ratio>0:
        pico2d.draw_rectangle(left,y,left+width*ratio,y+4,*color,filled=True)
        pico2d.draw_line(left,y+3,left+width*ratio,y+3,
                           *tuple(min(255,c+40) for c in color))
    previous=min(1,enemy.health_before_hit/enemy.max_health)
    if previous>ratio and enemy.hurt_time>0:
        with blended():
            pico2d.draw_rectangle(left+width*ratio,y,left+width*previous,y+4,
                                  255,225,187,a=int(210*enemy.hurt_time/enemy.hurt_duration),filled=True)
