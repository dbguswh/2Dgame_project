"""투명 문틀과 재질이 있는 병원 설비. 충돌·조작 규칙과 분리된 그림."""
import json
from pathlib import Path
import pico2d
from effects import blended,glow

ROOT=Path(__file__).resolve().parent/'assets/images/environments'
_asset=None


def clear_resources():
    global _asset
    _asset=None


def draw_sprite(name,x,bottom,height,width=None):
    global _asset
    if _asset is None:
        data=json.loads((ROOT/'hospital_equipment.json').read_text(encoding='utf-8'))
        _asset=pico2d.load_image(str(ROOT/data['image'])),{f['name']:f for f in data['frames']}
    image,frames=_asset
    l,b,w,h=frames[name]['clip']
    width=height*w/h if width is None else width
    image.clip_draw(l,b,w,h,x,bottom+height/2,width,height)


def draw_door(door,camera_x,target_open):
    x,y=door.x-camera_x,door.feet_y
    top=y+door.height
    if not door.blocks_corridor:
        # 뒷벽 출구에만 얕은 실내 음영을 두며 통로 문에는 배경을 가리는 면을 넣지 않는다.
        with blended():
            pico2d.draw_rectangle(x-21,y+2,x+21,top-24,6,15,21,a=100,filled=True)
            if door.is_open:glow(x,y+67,44,(128,209,188),alpha=55,squash=1.8)
    panel_bottom=y+door.progress*door.height
    if not door.is_open:
        # 패널을 위로 이동시키고 문 안쪽으로 잘라 문틀/윗벽을 덮지 않는다.
        with blended((x-24,y,x+24,top-15)):
            draw_sprite('door_panel',x,panel_bottom,door.height,48)
    draw_sprite('door_frame',x,y,door.height+12,80)
    status=(127,214,174) if door.is_open and target_open else (231,188,103) if target_open else (194,93,86)
    with blended():
        pico2d.draw_line(x-10,top+1,x+10,top+1,*status,a=230)
        glow(x,top+1,10,status,alpha=55,squash=.5)
        if not door.is_open:
            pico2d.draw_line(x-20,y+112,x+20,y+112,*status,a=85)
    for side in (-31,29):
        pico2d.draw_rectangle(x+side,y,x+side+3,y+5,*status,filled=True)


def draw_terminal(stage,camera_x):
    x,y=stage.terminal_position[0]-camera_x,stage.terminal_position[1]
    draw_sprite('selector',x,y,82,56)
    for index,key in enumerate(('A','B')):
        color=(225,203,128) if stage.powered_circuit==key or stage.fixture_powered else (57,84,91)
        pico2d.draw_line(x-14+index*23,y+60,x-7+index*23,y+60,*color)
        pico2d.draw_line(x-14+index*23,y+57,x-7+index*23,y+57,*color)


def draw_repair_device(stage,camera_x):
    x,y=stage.fixture_position[0]-camera_x,stage.fixture_position[1]
    draw_sprite('repair',x,y,94,66)
    for index,key in enumerate(('A','B')):
        if not stage.parts[key]:continue
        sx=x-12+index*24
        color=(226,203,132) if key=='A' else (133,205,214)
        pico2d.draw_rectangle(sx-4,y+62,sx+4,y+75,*color,filled=True)
        pico2d.draw_line(sx-3,y+66,sx+3,y+66,49,65,69)
    if stage.fixture_powered:
        with blended():glow(x,y+42,15,(139,220,177),alpha=75)


def draw_switch(x,y,opened):
    # 벽 스위치는 바닥 보급함과 구분되는 작은 장치다.
    draw_sprite('manual_switch',x,y+50,38,24)
    color=(130,211,170) if opened else (220,160,96)
    pico2d.draw_line(x-3,y+80,x+3,y+80,*color)


def draw_trolley(solid,camera_x):
    # 바퀴는 바닥에, 상판은 실제 충돌 높이에 맞춘다.
    draw_sprite('trolley',(solid.left+solid.right)/2-camera_x,solid.bottom,
                (solid.top-solid.bottom)*1.20,solid.right-solid.left)


def draw_supply_dock(box,camera_x):
    x,y=box.x-camera_x,box.feet_y
    pico2d.draw_rectangle(x-34,y-3,x+34,y-1,28,37,43,filled=True)
    for side in (-36,29):
        pico2d.draw_line(x+side,y,x+side+7,y,149,139,108)
        pico2d.draw_line(x+side,y-3,x+side,y,92,105,108)
