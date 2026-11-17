"""플레이 화면 하단의 정렬된 키 안내와 무기 사용 상태."""

from math import ceil
import pico2d
from ui_text import UIFont
from halo import HALO_COST

_small=None
_key_font=None


def clear_resources():
    global _small,_key_font
    for font in (_small,_key_font):
        if font is not None:font.close()
    _small=_key_font=None


def fonts():
    global _small,_key_font
    if _small is None:_small=UIFont(14)
    if _key_font is None:_key_font=UIFont(12)
    return _small,_key_font


def weapon_status(player):
    if player.bomb_aim is not None:return '광탄 조준 중',(227,207,150)
    if player.weapon!='ring':return 'W 3연격 · ↑ W 올려 베기',(159,178,193)
    if player.halo is not None and player.halo.active:
        return '비행 중 · 복귀 후 1초 대기',(220,189,123)
    if player.halo_cooldown>0:
        return f'재사용 {ceil(player.halo_cooldown*10)/10:.1f}초',(222,181,127)
    if player.battery<HALO_COST:return '배터리 부족 · 10 필요',(237,144,126)
    if player.halo_aim is not None:return '조준 중 · 놓으면 배터리 -10',(227,207,150)
    return '사용 가능 · 배터리 10',(151,209,184)


def keycap(key,label,x,y,small,key_font,width=50):
    pico2d.draw_rectangle(x,y-11,x+width,y+11,28,38,48,filled=True)
    pico2d.draw_rectangle(x,y-11,x+width,y+11,76,91,105)
    # 고정 폭 키 이름을 가운데 배치한다. 라벨 시작점도 모든 열에서 같다.
    key_font.draw(x+max(5,(width-len(key)*7)/2),y,key,(225,233,240))
    small.draw(x+60,y,label,(191,205,216))


def draw_controls(player,font):
    small,key_font=fonts()
    pico2d.draw_line(20,67,586,67,43,57,69)
    pico2d.draw_line(605,12,605,84,43,57,69)
    font.draw(20,82,'광륜' if player.weapon=='ring' else '광검',(239,219,176))
    status,color=weapon_status(player)
    small.draw(88,82,status,color)
    if player.ring_unlocked:keycap('A','무기 전환',446,82,small,key_font)
    aiming=player.halo_aim is not None or player.bomb_aim is not None
    if aiming:
        row1=(('← →','방향'),('↑ ↓','각도'),('W' if player.halo_aim is not None else 'F','놓아 투척'),('SPACE','취소·점프'))
    else:
        row1=(('← →','이동'),('SHIFT','달리기'),('SPACE','점프'),('E','상호작용'))
    row2=(('W','조준·투척' if player.weapon=='ring' else '광검 공격'),('Q','섬광 20'),('R','투광기 50'),('ESC','메뉴'))
    for y,row in ((49,row1),(20,row2)):
        for x,(key,label) in zip((20,162,304,446),row):keycap(key,label,x,y,small,key_font)
