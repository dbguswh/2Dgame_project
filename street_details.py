"""충돌 지형 뒤에 놓이는 운하 도시의 배관·셔터·배선 장식."""

import json
from pathlib import Path
import pico2d

ROOT=Path(__file__).resolve().parent/'assets/images/environments'
_asset=None
# 이름, 월드 중심 x, 아래 y, 높이. 장식에는 충돌/상호작용 판정이 없다.
PLACEMENTS=((0,320,100,156),(5,680,102,122),(1,1008,98,112),
            (3,1440,100,160),(2,1552,312,104),(0,1792,100,132),
            (4,1960,360,92),(5,2296,100,138),(2,2784,100,96))


def clear_resources():
    global _asset
    _asset=None


def draw_details(camera_x,width):
    global _asset
    if _asset is None:
        data=json.loads((ROOT/'street_details.json').read_text(encoding='utf-8'))
        _asset=data,pico2d.load_image(str(ROOT/data['image']))
    data,image=_asset
    image.opacify(.72)
    try:
        for index,wx,bottom,height in PLACEMENTS:
            left,top,w,h=data['frames'][index]['clip']
            draw_width=height*w/h
            x=wx-camera_x
            if x+draw_width/2<0 or x-draw_width/2>width:continue
            image.clip_draw(left,top,w,h,x,bottom+height/2,draw_width,height)
    finally:image.opacify(1)
