"""병원 벽면 아틀라스와 실제 지형에 맞춘 의료 설비·전동문."""

import json
from pathlib import Path
import pico2d
from effects import blended, glow, segment
from supplies import draw_battery_pack, SUPPLY_COLORS


DATA_PATH = Path(__file__).resolve().parent / 'assets/images/environments/hospital_interiors.json'


class HospitalScene:
    def __init__(self):
        self.data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
        self.image = pico2d.load_image(str(DATA_PATH.with_name(self.data['image'])))

    def draw(self, stage, camera_x, width, height):
        pico2d.draw_rectangle(0, 0, width, height, 12, 23, 32, filled=True)
        for index, key in enumerate(('archive', 'atrium', 'ward', 'maintenance')):
            x = index * 960-camera_x
            if x+960 < 0 or x > width:
                continue
            self.image.clip_draw(*self.data['frames'][key], x+480, 336, 960, 480)
        if camera_x < 2400 and camera_x+width > 1440:
            self.image.clip_draw(*self.data['frames']['atrium'], 1920-camera_x, 336, 960, 480)
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
                lit = stage.fixture_powered or 1664 <= x <= 2176 or (
                    stage.circuit == 'A' and 960 <= x <= 1664 or stage.circuit == 'B' and 2176 <= x <= 2880)
                self.draw_wall_lamp(x-camera_x, 390, lit)
        for box in stage.supply_boxes:
            if -48 < box.x-camera_x < width+48:
                self.draw_wall_panel(box.x-camera_x, box.feet_y, SUPPLY_COLORS[box.item])
                box.draw(camera_x)
        stage.fragment_cache.draw(camera_x)
        for key, door in stage.doors.items():
            if -48 < door.x-camera_x < width+48:
                self.draw_door(door, camera_x, stage.fixture_powered or key != 'exit' and (stage.circuit == key or stage.return_open[key]))
        self.draw_terminal(stage, camera_x)
        self.draw_repair_device(stage, camera_x)
        for key, position in stage.latch_positions.items():
            x, y = position[0]-camera_x, position[1]
            self.draw_wall_panel(x, y, (116, 182, 160) if stage.return_open[key] else (161, 123, 88))
            pico2d.draw_rectangle(x-7, y+26, x+7, y+44, 31, 46, 52, filled=True)
            segment((x-4, y+33), (x+5, y+37), (213, 188, 126), width=3)
        for key, (wx, y) in stage.part_positions.items():
            if not stage.parts[key]:
                self.draw_part(key, wx-camera_x, y)
        if not stage.battery_pack_collected:
            draw_battery_pack(stage.battery_pack_position[0]-camera_x, stage.battery_pack_position[1])

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
    def draw_trolley(solid, camera_x):
        a, b, y, bottom = solid.left-camera_x, solid.right-camera_x, solid.top, solid.bottom
        pico2d.draw_rectangle(a, bottom+5, b, y-5, 53, 76, 82, filled=True)
        pico2d.draw_rectangle(a-1, y-6, b+1, y, 166, 178, 164, filled=True)
        pico2d.draw_rectangle(a+5, bottom+13, b-5, y-12, 32, 51, 58, filled=True)
        for x in (a+9, b-9):
            pico2d.draw_circle(x, bottom+4, 4, 116, 132, 135, filled=True)
        segment((a+8, bottom+24), (b-8, bottom+24), (96, 121, 123), 2)

    @staticmethod
    def draw_wall_lamp(x, y, lit):
        pico2d.draw_rectangle(x-21, y-4, x+21, y+5, 58, 76, 84, filled=True)
        color = (210, 222, 185) if lit else (64, 79, 88)
        pico2d.draw_rectangle(x-16, y-2, x+16, y+2, *color, filled=True)
        if lit:
            with blended():
                glow(x, y, 52, (201, 224, 171), alpha=45, squash=.45)

    @staticmethod
    def draw_wall_panel(x, y, accent):
        pico2d.draw_rectangle(x-25, y+2, x+25, y+61, 33, 49, 57, filled=True)
        pico2d.draw_rectangle(x-25, y+2, x+25, y+61, 90, 115, 120)
        pico2d.draw_rectangle(x-15, y+54, x-4, y+56, *accent, filled=True)

    @staticmethod
    def draw_door(door, camera_x, lit):
        x, y = door.x-camera_x, door.feet_y
        pico2d.draw_rectangle(x-22, y, x+22, 440, 19, 31, 39, filled=True)
        for offset in (-23, 18):
            pico2d.draw_rectangle(x+offset, y, x+offset+5, 443, 92, 117, 122, filled=True)
        bottom = y+(440-y)*door.progress
        if bottom < 440:
            pico2d.draw_rectangle(x-12, bottom, x+12, 440, 62, 83, 88, filled=True)
            for yy in range(int(bottom)+5, 441, 16):
                pico2d.draw_line(x-10, yy, x+10, yy, 109, 132, 129)
        color = (224, 216, 142) if lit else (162, 89, 88)
        pico2d.draw_rectangle(x-20, 441, x+20, 448, *color, filled=True)
        pico2d.draw_rectangle(x-7, y+112, x+7, y+116, *color, filled=True)

    @staticmethod
    def draw_terminal(stage, camera_x):
        x, y = stage.terminal_position[0]-camera_x, stage.terminal_position[1]
        HospitalScene.draw_wall_panel(x, y, (181, 202, 138))
        pico2d.draw_rectangle(x-18, y+29, x+18, y+53, 12, 30, 36, filled=True)
        for index, key in enumerate(('A', 'B')):
            color = (238, 210, 127) if stage.circuit == key or stage.fixture_powered else (57, 81, 89)
            pico2d.draw_rectangle(x-13+index*16, y+34, x-3+index*16, y+47, *color, filled=True)
        segment((x-5, y+9), (x+8, y+18), (193, 180, 132), 3)

    @staticmethod
    def draw_repair_device(stage, camera_x):
        x, y = stage.fixture_position[0]-camera_x, stage.fixture_position[1]
        pico2d.draw_rectangle(x-25, y, x+25, y+83, 38, 60, 66, filled=True)
        pico2d.draw_rectangle(x-25, y, x+25, y+83, 142, 160, 143)
        for index, key in enumerate(('A', 'B')):
            color = (229, 209, 139) if stage.parts[key] else (56, 80, 84)
            pico2d.draw_rectangle(x-17+index*19, y+12, x-4+index*19, y+34, *color, filled=True)
        pico2d.draw_rectangle(x-17, y+47, x+17, y+70, 16, 34, 39, filled=True)
        color = (194, 226, 179) if stage.fixture_powered else (184, 139, 89)
        for yy in (53, 59, 65):
            pico2d.draw_line(x-12, y+yy, x+11, y+yy, *color)

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
