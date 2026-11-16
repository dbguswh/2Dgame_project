"""금속 보급 상자의 닫힘·중간·열림 스프라이트. 지급 판정과 독립적이다."""

import json
from pathlib import Path

import pico2d


ROOT = Path(__file__).resolve().parent / 'assets/images/items'
_image = None
_data = None


def clear_resources():
    global _image, _data
    _image = _data = None


def draw_supply_case(x, feet_y, progress):
    global _image, _data
    if _image is None:
        _data = json.loads((ROOT/'supply_case.json').read_text(encoding='utf-8'))
        _image = pico2d.load_image(str(ROOT/_data['image']))
    frame = _data['frames'][min(2, int(max(0, progress)*3))]
    left,top,right,bottom = frame['bounds']
    feet_x,feet_top = frame['feet']
    width,height = right-left,bottom-top
    scale = 58/_data['reference_width']
    _image.clip_draw(left,_data['source_size'][1]-bottom,width,height,
                     x+(left+width/2-feet_x)*scale,feet_y+(feet_top-top-height/2)*scale,
                     width*scale,height*scale)
