"""신규 침입자와 광륜의 원본 투명 PNG를 공유해 그린다."""

import json
from pathlib import Path
import pico2d

ROOT=Path(__file__).resolve().parent/'assets/images'
_assets={}


def clear_resources():
    _assets.clear()


def load(name):
    if name not in _assets:
        folder=ROOT/('items' if name=='halo' else 'characters')
        data=json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
        _assets[name]=(pico2d.load_image(str(folder/data['image'])),data)
    return _assets[name]


def draw_halo(x,y,angle=0,size=36):
    image,data=load('halo')
    l,t,r,b=data['bounds'];w,h=r-l,b-t;s=size/max(w,h)
    image.clip_composite_draw(l,data['source_size'][1]-b,w,h,angle,'',x,y,w*s,h*s)


def draw_enemy(enemy,kind,frame,camera_x=0):
    image,data=load(kind);f=data['frames'][frame]
    l,t,r,b=f['bounds'];ax,ay=f['anchor'];s=(94 if kind=='wraith' else 116)/data['reference_height']
    opacity=max(0,1-enemy.state_time/.8) if not enemy.alive else 1
    image.opacify(opacity)
    x=enemy.x-camera_x; y=enemy.feet_y+(24 if kind=='wraith' else 0)
    offset=(l+(r-l)/2-ax)*s
    image.clip_composite_draw(l,data['source_size'][1]-b,r-l,b-t,0,
                              'h' if enemy.face_dir>0 else '',x-offset if enemy.face_dir>0 else x+offset,
                              y+(ay-t-(b-t)/2)*s,(r-l)*s,(b-t)*s)
    image.opacify(1)
