"""수납된 무기는 숨기고 조준 중 전개와 실제 도달 경로를 보여준다."""

import pico2d
from halo import preview_path
from effects import blended,glow
from enemy_art import draw_halo


def draw_halo_aim(player,stage,font,camera_x):
    aim=player.halo_aim
    if aim is None:return
    x,y=player.halo_origin
    points=preview_path(x,y,aim.direction,aim.angle,stage.solids)
    end_x,end_y=points[-1]
    with blended():
        for i in range(0,len(points)-1,4):
            a,b=points[i],points[min(i+2,len(points)-1)]
            pico2d.draw_line(a[0]-camera_x,a[1],b[0]-camera_x,b[1],250,218,146,a=185)
        pico2d.draw_circle(end_x-camera_x,end_y,9,255,222,147,a=205)
        glow(x-camera_x,y,22,(255,210,120),alpha=90)
        draw_halo(x-camera_x,y,size=30)
    label_x=max(18,min(655,x-camera_x-45))
    label_y=y+72 if y+112<430 else y-60
    pico2d.draw_rectangle(label_x-8,label_y-16,label_x+220,label_y+16,8,14,22,filled=True)
    font.draw(label_x,label_y,f'각도 {aim.angle:.0f}°   상승 {max(0,end_y-y):.0f}px',(255,222,150))
