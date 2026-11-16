"""도시 배경과 실제 플레이어 이미지를 사용하는 메인 메뉴."""

from math import cos, sin
import os
from pathlib import Path

import pico2d

from effects import blended, glow
from ui_text import font_path


ROOT = Path(__file__).resolve().parent / 'assets/images'
_background = None
_player = None


def title_font_path():
    for name in ('bahnschrift.ttf', 'arialbd.ttf'):
        candidate = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / name
        if candidate.is_file():
            return candidate
    return font_path()


def clear_resources():
    global _background, _player
    _background = _player = None


def draw_title(game, font, menu_font, title_font, width, height):
    global _background, _player
    if _background is None:
        _background = pico2d.load_image(str(ROOT/'environments/title_city.png'))
        _player = pico2d.load_image(str(ROOT/'characters/player.png'))
    clock = game.title_time
    scale = max((width+12)/_background.w, (height+12)/_background.h)
    _background.draw(width/2+3*sin(clock*.08), height/2,
                     _background.w*scale, _background.h*scale)
    with blended():
        # 텍스트 뒤는 어둡게, 오른쪽 도시와 주인공은 그대로 읽히게 한다.
        for x in range(0, 656, 8):
            alpha = round(215*max(0, 1-x/656)**.65)
            pico2d.draw_rectangle(x,0,x+7,height,5,10,18,a=alpha,filled=True)
        for y in range(0,144,4):
            pico2d.draw_rectangle(0,y,width,y+3,5,10,18,a=round(185*(1-y/144)),filled=True)
        pulse = 1+.035*sin(clock*2.1)
        glow(669,177,87,(255,184,83),alpha=77*pulse)
        glow(733,59,103,(242,178,86),alpha=50,squash=.18)

    # 플레이에 사용 중인 확정 캐릭터를 그대로 확대한다.
    hero_scale = (258+sin(clock*1.8)*.8)/1134
    dx = (766/2-330)*hero_scale
    _player.clip_composite_draw(330,39,766,1134,0,'h',
                                740-dx,58+1134*hero_scale/2,766*hero_scale,1134*hero_scale)
    with blended():
        for index in range(10):
            phase=(clock*.035+index*.117)%1
            px=635+index*19+sin(clock*.25+index)*13
            py=75+phase*250
            glow(px,py,1.8,(244,204,140),alpha=45*sin(phase*3.14159))

    gold = (232,194,119)
    font.draw(80,440,'MAIN MENU',(166,155,132))
    title_font.draw(76,366,'BLACKOUT',(244,237,217))
    pico2d.draw_line(80,312,446,312,85,82,73)
    pico2d.draw_line(80,312,150,312,*gold)
    for index,label in enumerate(('게임 시작','게임 종료')):
        y=241-index*57
        selected=game.selection==index
        if selected:
            with blended():
                pico2d.draw_rectangle(77,y-24,442,y+24,104,82,47,a=52,filled=True)
            pico2d.draw_rectangle(77,y-17,80,y+17,*gold,filled=True)
        font.draw(94,y,f'0{index+1}',gold if selected else (88,100,112))
        menu_font.draw(138,y,label,(245,229,191) if selected else (135,147,159))
        pico2d.draw_line(94,y-28,442,y-28,57,64,70)
        if selected:
            font.draw(405,y,'E',gold)
    font.draw(80,77,'↑/↓ 선택    E 확인    Esc 종료',(165,177,188))
    pico2d.draw_line(80,43,width-80,43,51,62,71)
