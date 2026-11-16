"""도시 지도와 관리소의 코어 강화·선택 보급 구매 화면."""

from math import cos, sin, pi

import pico2d

from effects import blended, glow, polygon, segment
from item_art import draw_item
from upgrades import CORE_UPGRADES, FOCUS, SPREAD, SUPPLY_OFFERS
from inventory import STACK_LIMIT


def draw_background(game):
    camera_x = max(0, game.stage.width - 960)
    game.stage.draw(camera_x, 960, 540)
    with blended():
        pico2d.draw_rectangle(0, 0, 959, 539, 7, 13, 23, a=232, filled=True)
    segment((52, 430), (908, 430), (109, 99, 74), width=1)


def upgrade_names(player):
    return ' · '.join(u.name for u in CORE_UPGRADES if u.key in player.core_upgrades) or '없음'


def draw_city_map(game, font, heading):
    draw_background(game)
    heading.draw(52, 488, '도시 지도', (242, 225, 191))
    font.draw(52, 450, f'{game.stage.name} 복구 완료 · 다음 목적지: {game.stage.destination_name}', (178, 194, 209))
    with blended():
        for y in range(163, 211, 6):
            pico2d.draw_line(55, y, 902, y, 41, 77, 96, a=95)
    segment((153, 305), (478, 305), (191, 160, 99), width=3)
    segment((478, 305), (802, 305), (61, 76, 90), width=2)
    done = game.completed_stage_ids
    hospital_done = 'hospital' in done
    for x, color, completed in ((153, (233, 195, 117), 'residential' in done),
                                (478, (135, 209, 226), hospital_done),
                                (802, (93, 105, 119), False)):
        with blended():
            glow(x, 305, 43 if completed else 30, color, alpha=95 if completed else 40)
        pico2d.draw_circle(x, 305, 24, *color)
        pico2d.draw_circle(x, 305, 18, 18, 29, 41, filled=True)
        if completed:
            segment((x-10, 305), (x-3, 298), color, 3)
            segment((x-3, 298), (x+11, 314), color, 3)
        else:
            pico2d.draw_circle(x, 305, 5, *color, filled=True)
    heading.draw(108, 251, '주택가', (235, 219, 185))
    heading.draw(447, 251, '병원', (180, 219, 232))
    heading.draw(756, 251, '변전소', (134, 149, 166))
    font.draw(112, 220, '복구 완료', (199, 194, 161))
    font.draw(428, 220, '복구 완료' if hospital_done else '다음 목적지', (150, 199, 216))
    font.draw(749, 220, '다음 목적지' if hospital_done else '병원 복구 후', (112, 129, 146))
    font.draw(52, 135, f'보유 전력 조각  {game.player.fragments}', (242, 213, 149))
    font.draw(52, 105, f'현재 강화: {upgrade_names(game.player)}', (182, 198, 209))
    for slot, amount in enumerate(game.player.inventory.counts):
        x = 572 + slot * 84
        draw_item(slot, x, 119, 26)
        font.draw(x + 19, 119, str(amount), (213, 225, 231))
    visit = game.management_visit
    action = '관리소에서 강화·보급 확인' if visit.completed else '관리소에서 장비 강화'
    font.draw(52, 54, f'E {action}     Esc 완료 화면', (218, 208, 178))


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
    p, visit = game.player, game.management_visit
    heading.draw(52, 488, '관리소', (242, 225, 191))
    heading.draw(748, 488, f'전력 조각 {p.fragments}', (242, 211, 142))
    font.draw(52, 450, f'현재 강화: {upgrade_names(p)}', (185, 202, 215))
    if p.ring_unlocked:font.draw(52,423,'광륜 해금 완료 · A 무기 전환 · W 투척 · ↑+W 위쪽 투척',(233,204,143))
    if visit.completed:
        draw_supply_shop(game, font, heading)
        return
    descriptions = (('Q·R 에너지 저장', '용량을 늘린다.'),
                    ('먼 거리의 적을', '먼저 제압한다.'),
                    ('더 넓은 공간을', '빛으로 보호한다.'))
    for index, upgrade in enumerate(CORE_UPGRADES):
        x = 52 + index * 288
        selected = index == game.selection
        owned = upgrade.key in p.core_upgrades
        edge = (141, 207, 171) if owned else (240, 205, 131) if selected else (66, 83, 99)
        pico2d.draw_rectangle(x, 183, x+270, 410, 18, 29, 42, filled=True)
        pico2d.draw_rectangle(x, 183, x+270, 410, *edge)
        if selected:
            pico2d.draw_rectangle(x+1, 406, x+269, 410, *edge, filled=True)
        title_color = edge if selected or owned else (185, 201, 214) if not visit.completed else (93, 108, 122)
        heading.draw(x+24, 381, upgrade.name, title_color)
        draw_upgrade_icon(index, x+216, 368)
        font.draw(x+24, 329, upgrade.before, (171, 189, 206))
        heading.draw(x+24, 294, upgrade.after, (241, 226, 188))
        font.draw(x+24, 250, descriptions[index][0], (184, 200, 215))
        font.draw(x+24, 226, descriptions[index][1], (184, 200, 215))
        label = '적용 완료' if owned else '이번 방문 선택 완료' if visit.completed else '비용: 전력 조각 2개'
        label_color = edge if owned else (206, 194, 154) if not visit.completed else (93, 108, 122)
        font.draw(x+24, 200, label, label_color)
    font.draw(52, 145, visit.notice, (240, 210, 146))
    q_bonus = '+25%' if FOCUS in p.core_upgrades else '기본'
    r_bonus = '+25%' if SPREAD in p.core_upgrades else '기본'
    font.draw(52, 111, f'배터리 {p.battery}/{p.max_battery}   Q 사거리 {q_bonus}   R 범위 {r_bonus}',
              (167, 193, 211))
    font.draw(52, 58, '← / → 강화 선택     E 구매     Esc 도시 지도', (218, 208, 178))


def draw_supply_shop(game, font, heading):
    p, visit = game.player, game.management_visit
    count = 4 if game.can_depart else 3
    stride = 216 if game.can_depart else 288
    card_width = stride-18
    def card(index, title):
        x = 52 + index * stride
        selected = game.selection == index
        edge = (240, 205, 131) if selected else (66, 83, 99)
        pico2d.draw_rectangle(x, 183, x+card_width, 410, 18, 29, 42, filled=True)
        pico2d.draw_rectangle(x, 183, x+card_width, 410, *edge)
        if selected:
            pico2d.draw_rectangle(x+1, 406, x+card_width-1, 410, *edge, filled=True)
        heading.draw(x+18, 381, title, edge if selected else (204, 215, 222))
        return x

    for index, offer in enumerate(SUPPLY_OFFERS):
        x = card(index, offer.name)
        reason = visit.supply_blocked_reason(p, index)
        draw_item(offer.slot, x+card_width-32, 349, 38)
        amount = p.inventory.counts[offer.slot]
        font.draw(x + 24, 329, f'보유 {amount} / {STACK_LIMIT}', (171, 189, 206))
        heading.draw(x + 24, 294, f'조각 {offer.cost}개', (241, 226, 188))
        description = (('체력 1칸 회복', '소모품으로 보관') if index == 0 else ('범위 피해 1', '적의 공격 취소')) if count == 4 else offer.description
        for row, text in enumerate(description):
            font.draw(x + 24, 250 - row * 24, text, (184, 200, 215))
        label = ('보유 한도 도달' if amount >= STACK_LIMIT else '전력 조각 부족') if reason else 'E: 1개 구매'
        font.draw(x + 24, 200, label, (153, 160, 165) if reason else (159, 214, 177))
    x = card(2, '도시 지도')
    font.draw(x + 24, 329, '보급품 구매는 선택', (171, 189, 206))
    heading.draw(x + 24, 294, '돌아가기', (241, 226, 188))
    font.draw(x + 24, 250, '남은 조각과 소모품을', (184, 200, 215))
    font.draw(x + 24, 226, '그대로 유지한다.', (184, 200, 215))
    font.draw(x + 24, 200, 'E: 지도 확인', (159, 214, 177))
    if game.can_depart:
        destination = '병원' if game.stage.next_stage_id == 'hospital' else '변전소'
        x = card(3, f'{destination} 출발')
        font.draw(x+18, 329, '다음 스테이지', (171, 189, 206))
        heading.draw(x+18, 294, game.stage.destination_name, (241, 226, 188))
        font.draw(x+18, 250, '체력·배터리 회복', (184, 200, 215))
        font.draw(x+18, 226, '장비·소모품 이월', (184, 200, 215))
        font.draw(x+18, 200, f'E: {destination} 이동', (159, 214, 177))
    font.draw(52, 145, visit.notice, (240, 210, 146))
    font.draw(52, 111, f'체력 {p.health}/3   배터리 {p.battery}/{p.max_battery}   구매 시 보유 수량만 증가',
              (167, 193, 211))
    font.draw(52, 58, '← / → 선택     E 구매·이동     Esc 도시 지도', (218, 208, 178))
