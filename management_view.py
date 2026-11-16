"""도시 지도와 관리소의 코어 강화·선택 보급 구매 화면."""

from math import cos, sin, pi

import pico2d

from effects import blended, glow, polygon, segment
from item_art import draw_item
from upgrades import CORE_UPGRADES, FOCUS, SPREAD, SUPPLY_OFFERS
from inventory import STACK_LIMIT
from menu_ui import header,footer,panel,body_font,TEXT,MUTED,GOLD,GREEN,RED,EDGE


def draw_background(game):
    camera_x = max(0, game.stage.width - 960)
    game.stage.draw(camera_x, 960, 540)
    with blended():
        pico2d.draw_rectangle(0, 0, 959, 539, 7, 13, 23, a=232, filled=True)



def upgrade_names(player):
    return ' · '.join(u.name for u in CORE_UPGRADES if u.key in player.core_upgrades) or '없음'


def draw_city_map(game,font,heading):
    draw_background(game)
    p=game.player;body=body_font()
    header(heading,'도시 지도',f'{game.stage.name} 복구 완료',p.fragments)
    done=game.completed_stage_ids
    for left,right,lit in ((165,480,'residential' in done),(480,795,'hospital' in done)):
        segment((left,317),(right,317),GOLD if lit else EDGE,width=2)
    for x,stage_id,label in ((165,'residential','주택가'),(480,'hospital','병원'),(795,'substation','변전소')):
        completed=stage_id in done;next_stage=stage_id==game.stage.next_stage_id
        color=GREEN if completed else GOLD if next_stage else EDGE
        with blended():
            if completed or next_stage:glow(x,317,35,color,alpha=55)
        pico2d.draw_circle(x,317,22,*color)
        pico2d.draw_circle(x,317,17,11,20,31,filled=True)
        if completed:
            segment((x-9,317),(x-2,310),color,3)
            segment((x-2,310),(x+10,324),color,3)
        else:pico2d.draw_circle(x,317,4,*color,filled=True)
        heading.draw(x-(39 if label=='주택가' or label=='변전소' else 26),255,label,TEXT if completed or next_stage else MUTED)
        body.draw(x-32,219,'복구 완료' if completed else '다음 구역' if next_stage else '진입 대기',color)
    pico2d.draw_line(52,178,908,178,*EDGE)
    body.draw(52,139,f'현재 강화  {upgrade_names(p)}',TEXT)
    body.draw(52,109,'보급품과 남은 조각은 다음 구역으로 이월됩니다.',MUTED)
    for slot,amount in enumerate(p.inventory.counts):
        x=624+slot*76
        draw_item(slot,x,132,28)
        body.draw(x+22,132,str(amount),TEXT)
    footer(((52,'E','관리소'),(300,'ESC','완료 화면')))


def draw_upgrade_icon(index, x, y):
    with blended():
        glow(x, y, 37, (195, 175, 114), alpha=65)
        if index == 0:
            for offset in (-17, 7):
                pico2d.draw_rectangle(x+offset, y-20, x+offset+11, y+20, 88, 119, 126, filled=True)
                pico2d.draw_rectangle(x+offset, y-20, x+offset+11, y+20, 173, 207, 207)
                for dy in (-12, -3, 6):
                    pico2d.draw_rectangle(x+offset+3, y+dy, x+offset+8, y+dy+5, 224, 217, 151, filled=True)
        elif index == 1:
            polygon(((x-25, y-17), (x+28, y), (x-25, y+17)), (222, 206, 155), alpha=48)
            segment((x-25, y), (x+28, y), (248, 227, 174), 3)
            pico2d.draw_circle(x-17, y, 13, 185, 173, 129)
            pico2d.draw_circle(x-17, y, 7, 249, 229, 168, filled=True)
        else:
            for radius, alpha in ((13, 235), (23, 170), (33, 100)):
                pico2d.draw_circle(x, y, radius, 248, 219, 147, a=alpha)
            glow(x, y, 12, (255, 231, 170), alpha=200)
            for i in range(6):
                angle=i*pi/3
                segment((x+cos(angle)*14,y+sin(angle)*14),
                        (x+cos(angle)*33,y+sin(angle)*33), (186, 169, 123), 1)


def draw_management(game, font, heading):
    draw_background(game)
    p,visit=game.player,game.management_visit
    header(heading,'관리소',f'현재 강화  {upgrade_names(p)}',p.fragments)
    if visit.completed:
        draw_supply_shop(game,font,heading)
        return
    body=body_font()
    body.draw(52,393,'코어 강화 선택',TEXT)
    body.draw(676,393,'이번 방문에서 1개 선택',MUTED)
    descriptions=('광륜 · 섬광 · 투광기',
                  '멀리 있는 적 제압','더 넓은 공간 확보')
    for index,upgrade in enumerate(CORE_UPGRADES):
        x=52+index*288;selected=index==game.selection;owned=upgrade.key in p.core_upgrades
        panel(x,176,x+270,367,selected)
        body.draw(x+20,341,upgrade.name,GOLD if selected else TEXT)
        draw_upgrade_icon(index,x+220,320)
        body.draw(x+20,302,upgrade.before,MUTED)
        heading.draw(x+20,269,upgrade.after,GOLD)
        body.draw(x+20,228,descriptions[index],MUTED)
        label='적용 완료' if owned else '전력 조각 2개'
        body.draw(x+20,194,label,GREEN if owned else GOLD)
    body.draw(52,136,visit.notice,GOLD)
    body.draw(52,106,f'배터리 {p.battery}/{p.max_battery}   구매 시 현재 잔량은 유지됩니다.',MUTED)
    footer(((52,'← →','강화 선택'),(300,'E','구매'),(548,'ESC','도시 지도')))


def draw_supply_shop(game, font, heading):
    p,visit=game.player,game.management_visit
    body=body_font()
    body.draw(52,392,'선택 보급',TEXT)
    body.draw(415,392,'종류별 최대 2개',MUTED)
    body.draw(628,392,'다음 행동',TEXT)
    for index,offer in enumerate(SUPPLY_OFFERS):
        y=318-index*106;selected=game.selection==index
        panel(52,y-45,584,y+45,selected)
        draw_item(offer.slot,94,y,46)
        body.draw(136,y+23,offer.name,GOLD if selected else TEXT)
        body.draw(390,y+23,f'보유 {p.inventory.counts[offer.slot]}/{STACK_LIMIT}',MUTED)
        body.draw(496,y+23,f'{offer.cost} 조각',GOLD)
        body.draw(136,y-3,'체력 1칸 회복' if index==0 else '범위 피해 · 공격 취소',MUTED)
        reason=visit.supply_blocked_reason(p,index)
        label='보유 한도 도달' if p.inventory.counts[offer.slot]>=STACK_LIMIT else '전력 조각 부족' if reason else '구매 가능'
        body.draw(136,y-27,label,RED if reason else GREEN)
    # 구매와 이동을 별도 열로 구분하되 기존 선택 순서 0/1/2/3은 유지한다.
    panel(628,273,908,363,game.selection==2)
    body.draw(650,341,'도시 지도',GOLD if game.selection==2 else TEXT)
    body.draw(650,310,'현재 진행과 보급품 유지',MUTED)
    body.draw(650,288,'지도로 돌아가기',MUTED)
    panel(628,167,908,257,game.selection==3 and game.can_depart)
    if game.can_depart:
        body.draw(650,235,f'{game.stage.destination_name} 출발',GOLD if game.selection==3 else TEXT)
        body.draw(650,204,'체력 · 배터리 회복',MUTED)
        body.draw(650,182,'강화 · 소모품 이월',MUTED)
    else:
        body.draw(650,227,'다음 구역 준비 중',MUTED)
        body.draw(650,195,'도시 지도에서 진행 확인',MUTED)
    body.draw(52,133,visit.notice,GOLD)
    body.draw(52,105,f'체력 {p.health}/3   배터리 {p.battery}/{p.max_battery}   보급품 구매는 선택입니다.',MUTED)
    action='1개 구매' if game.selection<2 else '지도 보기' if game.selection==2 else '출발'
    footer(((52,'← →','항목 선택'),(300,'E',action),(548,'ESC','도시 지도')))
