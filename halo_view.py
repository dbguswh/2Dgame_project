"""손 위치를 따라 휴대한 광륜과 조준·실제 도달 경로를 보여준다."""

import pico2d
from halo import preview_path
from effects import blended,glow
from enemy_art import draw_halo


def carried_halo_pose(player):
    if (player.weapon!='ring' or player.is_attacking or player.light_cast>0
            or player.halo_aim is not None or player.bomb_aim is not None
            or player.halo is not None and player.halo.active):return None
    # 원본 동작의 빈손 위치를 발 기준으로 추적한다. 손이 원의 윗부분을 덮는다.
    state=player.animation_state
    if state=='run':
        dx,hand_y=((-25,48),(4,54),(6,57),(1,48),(3,57),(-21,50))[player.walk_frame]
    elif state=='walk':
        dx,hand_y=((-23,42),(-15,41),(-10,41),(-4,43),(0,42),(-2,42))[player.walk_frame]
    elif state.startswith('jump_'):
        dx,hand_y=((-26,51),(-29,39),(-28,50))[('jump_rise','jump_apex','jump_fall').index(state)]
    else:dx,hand_y=-24,42
    return player.x+dx*player.face_dir,player.feet_y+hand_y-10


def draw_carried_halo(player,camera_x):
    pose=carried_halo_pose(player)
    if pose is None:return
    x,y=pose
    # 회전/독립 흔들림 없이 잡고 있는 자세. 실제 비행과 구분한다.
    draw_halo(x-camera_x,y,size=27)


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
