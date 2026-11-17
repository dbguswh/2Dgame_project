"""전력 복구 설비의 재질·상태·송전 연출. 시야와 전투 조명 판정은 만들지 않는다."""

import json
from math import cos, sin, pi
from pathlib import Path

import pico2d
from effects import blended, glow, segment


ROOT = Path(__file__).resolve().parent / 'assets/images/environments'
_asset = None
_fuse = None
AMBER = (244, 191, 99)
READY = (132, 215, 231)
POWERED = (150, 232, 179)


def clear_resources():
    global _asset,_fuse
    _asset = None
    _fuse = None


def sprite(name, x, bottom, height):
    global _asset
    if _asset is None:
        data = json.loads((ROOT / 'residential_power.json').read_text(encoding='utf-8'))
        _asset = (pico2d.load_image(str(ROOT / data['image'])),
                  {f['name']: f['clip'] for f in data['frames']})
    image, frames = _asset
    l, b, w, h = frames[name]
    image.clip_draw(l, b, w, h, x, bottom + height / 2, height * w / h, height)


def status(stage):
    return POWERED if stage.fixture_powered else READY if stage.fuse_state == 'CARRIED' else AMBER


def bolt(x, y, color, scale=1):
    points = ((3,-8),(-3,-1),(1,-1),(-3,8),(4,0),(0,0))
    for a,b in zip(points,points[1:]):
        segment((x+a[0]*scale,y+a[1]*scale),(x+b[0]*scale,y+b[1]*scale),color,2)


def draw_switchgear(stage, camera_x):
    wx, y = stage.fixture_position
    x = wx - camera_x + 16
    if not -100 < x < 1060:return
    # 장치 받침은 기존 옥상에 고정한 짧은 돌출 보이며 통행 충돌체가 아니다.
    segment((x-67,y-3),(x+67,y-3),(44,57,62),7)
    segment((x-67,y),(x+67,y),(158,142,97),2)
    for dx in (-55,55):
        segment((x+dx,y-3),(x+dx/2,y-18),(64,79,84),4)
    sprite('switchgear',x,y,130)
    color = status(stage)
    # 원형 계기의 눈금·바늘·퓨즈는 이미지의 실제 빈 홈에 맞춘다.
    cx,cy=x,y+85
    for i in range(9):
        angle=(.8+i*.175)*pi
        segment((cx+cos(angle)*19,cy+sin(angle)*19),
                (cx+cos(angle)*22,cy+sin(angle)*22),(128,129,106),1)
    amount = min(1,stage.reveal_light_elapsed/.8) if stage.fixture_powered else 0
    angle=(1.22-.75*amount)*pi
    segment((cx,cy),(cx+cos(angle)*16,cy+sin(angle)*16),color,2)
    pico2d.draw_circle(cx,cy,3,*color,filled=True)
    if stage.fuse_state == 'INSTALLED':
        draw_fuse(x,y+49,POWERED)
    else:
        pico2d.draw_rectangle(x-4,y+33,x+4,y+61,20,28,30,filled=True)
        for sy in (y+34,y+59):pico2d.draw_line(x-4,sy,x+4,sy,171,145,91)
    for sy in (y+52,y+61):
        pico2d.draw_circle(x-23,sy,2,*color,filled=True)


def draw_fuse(x,y,color=READY):
    draw_fuse_art(x,y,26)


def draw_fuse_art(x,y,height=46,opacity=1):
    global _fuse
    if _fuse is None:
        root=ROOT.parent/'items'
        data=json.loads((root/'restoration_fuse.json').read_text(encoding='utf-8'))
        _fuse=pico2d.load_image(str(root/data['image'])),data['clip']
    image,(l,b,w,h)=_fuse
    image.opacify(opacity)
    try:image.clip_draw(l,b,w,h,x,y,height*w/h,height)
    finally:image.opacify(1)


def draw_workshop(stage,camera_x):
    bx,by=stage.return_battery_position
    fx,fy=stage.fuse_position
    if -100 < bx-camera_x < 1060:
        sprite('battery_rack',bx-camera_x,by-16,70)
    x=fx-camera_x
    if not -100 < x < 1060:return
    sprite('fuse_cabinet',x,fy-16,64)


def draw_network(stage,camera_x,signals=False):
    x,y=stage.fixture_position
    trunk=250
    if signals and not stage.fixture_powered:return
    if not signals:
        for dy in (-3,3):
            segment((x+16-camera_x,y),(x+16-camera_x,trunk+dy),(35,46,52),5)
            segment((x+16-camera_x,trunk+dy),(2336-camera_x,trunk+dy),(42,52,58),5)
            segment((x+16-camera_x,trunk+dy),(2336-camera_x,trunk+dy),(105,91,65),1)
        for wx in range(1232,2337,96):
            segment((wx-camera_x,trunk-7),(wx-camera_x,trunk+7),(99,109,111),3)
        segment((2336-camera_x,trunk),(2336-camera_x,224),(63,73,75),6)
        segment((2336-camera_x,224),(2368-camera_x,224),(105,91,65),4)
        return
    # 송전선만 빛난다. 주변을 밝히거나 침입자의 행동을 취소하지 않는다.
    with blended():
        pico2d.draw_line(x+16-camera_x,trunk,2336-camera_x,trunk,239,199,112,a=155)
        pico2d.draw_line(2336-camera_x,trunk,2336-camera_x,224,*POWERED,a=180)
        pico2d.draw_line(2336-camera_x,224,2368-camera_x,224,*POWERED,a=180)
        for offset in range(0,1136,112):
            wx=x+16+(offset+stage.visual_time*148)%1136
            if -20 < wx-camera_x < 980:
                glow(wx-camera_x,trunk,9,AMBER,alpha=65,squash=.32)
                pico2d.draw_line(wx-camera_x-6,trunk,wx-camera_x+4,trunk,255,231,169,a=240)


def draw_signals(stage,player,camera_x):
    wx,y=stage.fixture_position
    x=wx-camera_x+16
    color=status(stage)
    if -100<x<1060:
        with blended():
            glow(x,y+119,26,color,alpha=75+int(15*sin(stage.visual_time*3)))
            glow(x,y+85,22,color,alpha=23)
            pico2d.draw_rectangle(x-3,y+120,x+3,y+126,*color,a=245,filled=True)
            # 세로 안내등은 목적물 바로 위에만 보이며 HUD까지 뻗지 않는다.
            for dx in (-47,47):
                pico2d.draw_line(x+dx,y+17,x+dx,y+103,*color,a=75)
            if stage.fixture_powered and stage.reveal_light_elapsed<1.1:
                t=stage.reveal_light_elapsed/1.1
                for r in (int(28+t*90),int(16+t*72)):
                    pico2d.draw_circle(x,y+71,r,*POWERED,a=int(130*(1-t)))
        bolt(x,y+85,color,.75)
    fx,fy=stage.fuse_position
    if stage.fuse_state=='WORLD' and -60<fx-camera_x<1020:
        color=READY if stage.fuse_unlocked else AMBER
        with blended():
            glow(fx-camera_x,fy+24,34,color,alpha=90 if stage.fuse_unlocked else 35)
        draw_fuse_art(fx-camera_x,fy+24,46,1 if stage.fuse_unlocked else .55)
        if not stage.fuse_unlocked:
            for sy in (fy+10,fy+36):
                segment((fx-camera_x-16,sy),(fx-camera_x+16,sy),(139,143,135),3)
            pico2d.draw_rectangle(fx-camera_x-4,fy+20,fx-camera_x+4,fy+28,*AMBER,filled=True)
        else:
            with blended():
                for side in (-1,1):
                    sx=fx-camera_x+side*(24+2*sin(stage.visual_time*3))
                    pico2d.draw_line(sx,fy+22,sx-side*5,fy+27,*READY,a=210)
                    pico2d.draw_line(sx,fy+22,sx-side*5,fy+17,*READY,a=210)
    bx,by=stage.return_battery_position
    if not stage.return_battery_collected and -60<bx-camera_x<1020:
        with blended():glow(bx-camera_x+27,by+33,12,READY,alpha=38)
    draw_network(stage,camera_x,signals=True)


def draw_labels(stage,camera_x):
    from controls_view import fonts
    small,tiny=fonts()
    x=stage.fixture_position[0]-camera_x+16
    color=status(stage)
    if 94<x<866:
        pico2d.draw_rectangle(x-89,204,x+89,247,11,22,29,filled=True)
        pico2d.draw_line(x-89,247,x+89,247,*color)
        bolt(x-72,228,color,.7)
        small.draw(x-57,234,'중앙 제어함',(224,221,202))
        label=('교량 전력 공급 완료' if stage.fixture_powered else
               'E 전력 복구 · 퓨즈 설치' if stage.fuse_state=='CARRIED' else '퓨즈를 확보해 전력 복구')
        tiny.draw(x-75,216,label,color)
    x=stage.fuse_position[0]-camera_x
    if stage.fuse_state=='WORLD' and -20<x<770:
        color=READY if stage.fuse_unlocked else AMBER
        pico2d.draw_rectangle(x+28,368,x+178,410,12,24,30,filled=True)
        pico2d.draw_line(x+13,384,x+28,392,*color)
        small.draw(x+40,398,'복구 퓨즈',color)
        label='계단 정상에서 회수' if stage.fuse_unlocked else '표식 침입자 처치 필요'
        tiny.draw(x+40,380,label,(187,202,207))
