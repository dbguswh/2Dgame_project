"""병원 벽면 아틀라스와 실제 지형에 맞춘 의료 설비·전동문."""

import json
from pathlib import Path
import pico2d
from effects import blended, glow, segment
from supplies import draw_battery_pack
import hospital_equipment as equipment


DATA_PATH = Path(__file__).resolve().parent / 'assets/images/environments/hospital_interiors.json'


class HospitalScene:
    def __init__(self):
        self.data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
        self.image = pico2d.load_image(str(DATA_PATH.with_name(self.data['image'])))

    def draw(self, stage, camera_x, width, height):
        pico2d.draw_rectangle(0, 0, width, height, 12, 23, 32, filled=True)
        for index, key in enumerate(('archive', 'atrium', 'maintenance')):
            x = index * 960-camera_x
            if x+960 < 0 or x > width:
                continue
            self.image.clip_draw(*self.data['frames'][key], x+480, 336, 960, 480)
        for region in stage.fixed_light_regions:
            a, b = max(0, region.left-camera_x), min(width, region.right-camera_x)
            if a < b:
                with blended():
                    pico2d.draw_rectangle(a, 98, b, 444, 129, 172, 168, a=20, filled=True)
        self.draw_floor(camera_x, width)
        for solid in stage.base_solids[1:]:
            if solid.right < camera_x or solid.left > camera_x+width:
                continue
            if solid in stage.cover_solids:
                self.draw_trolley(solid, camera_x)
            elif solid.one_way:
                self.draw_gallery(solid, camera_x)
            else:
                self.draw_trolley(solid, camera_x)
        # 천장 전선과 벽면 조명은 회로 A/B를 따라 켜진다.
        for x in range(160, stage.width, 256):
            if -40 <= x-camera_x <= width+40:
                lit = stage.is_temporarily_lit((x-1,96,x+1,100))
                self.draw_wall_lamp(x-camera_x, 390, lit)
        for key, door in stage.doors.items():
            if -60 < door.x-camera_x < width+60:
                equipment.draw_door(door,camera_x,stage.door_should_open(key))
        equipment.draw_terminal(stage,camera_x)
        equipment.draw_repair_device(stage,camera_x)
        for key, (wx,y) in stage.latch_positions.items():
            equipment.draw_switch(wx-camera_x,y,stage.return_open[key])
        for key, (wx, y) in stage.part_positions.items():
            x = wx-camera_x
            pico2d.draw_rectangle(x-23,y-16,x+23,y+29,31,50,58,filled=True)
            pico2d.draw_rectangle(x-23,y-16,x+23,y+29,116,138,140)
            pico2d.draw_rectangle(x-11,y-12,x+11,y+15,13,28,38,filled=True)
            connected = not stage.parts[key]
            color = (209,200,128) if connected else (166,92,82)
            pico2d.draw_rectangle(x-17,y+21,x+17,y+24,*color,filled=True)
            if not connected and stage.circuit == key and stage.blackout_remaining > 0:
                with blended():
                    glow(x,y+8,42,(203,91,73),alpha=110*stage.blackout_remaining/1.2)
            for dx in (-16,16):
                segment((x+dx,y-16),(x+dx,y-28),(92,126,132),2)
            if not stage.parts[key]:
                self.draw_part(key,x,y)
                if not stage.room_cleared[key]:
                    for dx in (-16,0,16):
                        segment((x+dx,y-14),(x+dx,y+18),(148,92,174),2)
        if not stage.battery_pack_collected:
            draw_battery_pack(stage.battery_pack_position[0]-camera_x, stage.battery_pack_position[1])
        for box in stage.supply_boxes:
            if -60 < box.x-camera_x < width+60:
                equipment.draw_supply_dock(box,camera_x)
                box.draw(camera_x)
        stage.fragment_cache.draw(camera_x)

    @staticmethod
    def draw_floor(camera_x, width):
        pico2d.draw_rectangle(0, 0, width, 96, 29, 40, 47, filled=True)
        for x in range(int(camera_x//48)*48, int(camera_x+width)+48, 48):
            sx = x-camera_x
            pico2d.draw_rectangle(sx+1, 73, sx+46, 95, 101, 117, 116, filled=True)
            pico2d.draw_line(sx+2, 95, sx+46, 95, 170, 184, 173)
            for y in (12, 40):
                pico2d.draw_rectangle(sx+2, y, sx+46, y+25, 42, 56, 65, filled=True)
        segment((0, 70), (width, 70), (69, 93, 100), 2)

    @staticmethod
    def draw_gallery(solid, camera_x):
        a, b, y = solid.left-camera_x, solid.right-camera_x, solid.top
        pico2d.draw_rectangle(a, solid.bottom, b, y, 47, 67, 74, filled=True)
        pico2d.draw_rectangle(a, y-6, b, y, 139, 153, 143, filled=True)
        segment((a, y+30), (b, y+30), (110, 141, 144), 2)
        for x in range(int(solid.left+8), int(solid.right), 48):
            sx = x-camera_x
            segment((sx, y), (sx, y+30), (83, 113, 121), 2)
            segment((sx, solid.bottom), (sx+22, solid.bottom-24), (74, 97, 104), 3)
        for x in (a+3, b-3):
            pico2d.draw_rectangle(x, y-5, x+2, y-1, 217, 190, 119, filled=True)

    @staticmethod
    def draw_trolley(solid,camera_x):
        equipment.draw_trolley(solid,camera_x)

    @staticmethod
    def draw_wall_lamp(x, y, lit):
        pico2d.draw_rectangle(x-21, y-4, x+21, y+5, 58, 76, 84, filled=True)
        color = (210, 222, 185) if lit else (64, 79, 88)
        pico2d.draw_rectangle(x-16, y-2, x+16, y+2, *color, filled=True)
        if lit:
            with blended():
                glow(x, y, 52, (201, 224, 171), alpha=45, squash=.45)

    @staticmethod
    def draw_part(key, x, y):
        with blended():
            glow(x, y, 25, (223, 190, 105) if key == 'A' else (111, 196, 215), alpha=65)
        if key == 'A':
            pico2d.draw_rectangle(x-5, y-12, x+5, y+12, 125, 166, 168, filled=True)
            for yy in (-12, 8):
                pico2d.draw_rectangle(x-7, y+yy, x+7, y+yy+4, 221, 196, 127, filled=True)
        else:
            pico2d.draw_rectangle(x-10, y-11, x+10, y+11, 74, 119, 128, filled=True)
            pico2d.draw_rectangle(x-10, y-11, x+10, y+11, 170, 210, 206)
            for yy in (-5, 1, 7):
                pico2d.draw_line(x-6, y+yy, x+6, y+yy, 209, 231, 192)
