"""변전소 배경과 실제 충돌 위치에 맞춘 레일·차단기·승강기."""

import json
from pathlib import Path
from math import sin
import pico2d
from effects import blended,glow,segment
from hospital_scene import HospitalScene
from supplies import SUPPLY_COLORS


DATA_PATH = Path(__file__).resolve().parent/'assets/images/environments/substation_interiors.json'


class SubstationScene:
    def __init__(self):
        self.data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
        self.image = pico2d.load_image(str(DATA_PATH.with_name(self.data['image'])))

    def draw(self, stage, camera_x, width, height):
        pico2d.draw_rectangle(0,0,width,height,12,20,32,filled=True)
        for i,key in enumerate(('entry','machine','upper','containment')):
            x = i*960-camera_x
            if x+960 >= 0 and x <= width:
                self.image.clip_draw(*self.data['frames'][key],x+480,336,960,480)
        HospitalScene.draw_floor(camera_x,width)
        self.draw_lift(stage,camera_x)
        HospitalScene.draw_gallery(stage.upper_gallery,camera_x)
        for solid in stage.base_solids[2:]:
            if solid.left <= camera_x+width and solid.right >= camera_x:
                HospitalScene.draw_trolley(solid,camera_x)
        for i,pos in enumerate(stage.breaker_positions):
            self.draw_breaker(pos[0]-camera_x,pos[1],stage.breakers[i])
        self.draw_charger(stage.charger_position[0]-camera_x,96,stage.visual_time)
        HospitalScene.draw_door(stage.core_gate,camera_x,stage.both_breakers)
        for box in stage.supply_boxes:
            if -48 < box.x-camera_x < width+48:
                HospitalScene.draw_wall_panel(box.x-camera_x,box.feet_y,SUPPLY_COLORS[box.item])
                box.draw(camera_x)
        for x in range(144,stage.width,256):
            if -40 < x-camera_x < width+40:
                lit = stage.fixture_powered or x < 384 or 1536 <= x <= 2032
                HospitalScene.draw_wall_lamp(x-camera_x,458,lit)

    @staticmethod
    def draw_breaker(x,y,powered):
        color=(221,214,145) if powered else (172,103,89)
        pico2d.draw_rectangle(x-24,y,x+24,y+81,34,48,59,filled=True)
        pico2d.draw_rectangle(x-24,y,x+24,y+81,110,130,135)
        pico2d.draw_rectangle(x-17,y+40,x+17,y+70,19,30,40,filled=True)
        pico2d.draw_circle(x+11,y+60,4,*color,filled=True)
        segment((x-4,y+45),(x-4,y+64 if powered else y+48),(195,190,158),5)
        for yy in (10,16,22):
            segment((x-15,y+yy),(x+15,y+yy),(77,99,112),2)
        if powered:
            with blended():
                glow(x,y+56,23,color,alpha=70)

    @staticmethod
    def draw_charger(x,y,time):
        pico2d.draw_rectangle(x-27,y,x+27,y+78,36,57,65,filled=True)
        pico2d.draw_rectangle(x-27,y,x+27,y+78,113,154,157)
        pico2d.draw_rectangle(x-17,y+30,x+17,y+67,13,37,47,filled=True)
        for i in range(4):
            color=(138,214,205) if i < 3+sin(time*3) else (54,100,109)
            pico2d.draw_rectangle(x-11,y+36+i*7,x+11,y+40+i*7,*color,filled=True)
        segment((x+25,y+31),(x+36,y+14),(109,155,164),3)
        segment((x+36,y+14),(x+18,y+8),(109,155,164),3)

    @staticmethod
    def draw_lift(stage,camera_x):
        lift=stage.lift
        x,y=lift.x-camera_x,lift.y
        for dx in (-67,63):
            pico2d.draw_rectangle(x+dx,80,x+dx+4,516,75,96,112,filled=True)
            segment((x+dx+1,80),(x+dx+1,516),(136,156,161),1)
        for yy in range(112,516,40):
            for dx in (-68,64):
                pico2d.draw_rectangle(x+dx,yy,x+dx+6,yy+8,37,56,71,filled=True)
        for dx in (-26,26):
            segment((x+dx,y+120),(x+dx,516),(127,139,138),2)
        for dx in (-54,50):
            pico2d.draw_rectangle(x+dx,y,x+dx+4,y+116,68,90,102,filled=True)
        pico2d.draw_rectangle(x-56,y+113,x+56,y+121,72,92,100,filled=True)
        pico2d.draw_rectangle(x-64,y-16,x+64,y,54,76,90,filled=True)
        pico2d.draw_rectangle(x-64,y-5,x+64,y,177,170,124,filled=True)
        for dx in range(-58,60,16):
            segment((x+dx,y-14),(x+dx+9,y-6),(125,123,91),3)
        color=(239,211,132) if stage.breakers[0] else (113,85,78)
        pico2d.draw_rectangle(x-35,y+115,x+35,y+118,*color,filled=True)
        # 양쪽 호출 패널은 승강기와 독립된 정지 발판에 고정한다.
        for wx,wy in stage.call_positions:
            sx=wx-camera_x
            pico2d.draw_rectangle(sx-8,wy,sx+8,wy+40,43,64,77,filled=True)
            pico2d.draw_circle(sx,wy+29,4,*color,filled=True)
            segment((sx-5,wy+13),(sx+5,wy+13),(144,167,172),2)
