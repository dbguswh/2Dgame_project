"""화면 상태에 맞춰 메뉴와 플레이 화면을 그린다."""

from math import ceil

import pico2d

from effects import blended
from physics import camera_offset
from window import SCREEN_WIDTH, SCREEN_HEIGHT, clear_frame
from visibility import draw_darkness, draw_navigation, enemy_is_visible
from item_art import draw_item
from inventory import ITEM_NAMES, LIGHT_BOMB
from bomb_aim_view import draw_bomb_aim
from buff_visuals import draw_buffs, draw_buff_timers
from management_view import draw_city_map, draw_management
from sword_visuals import draw_sword_stroke
from title_view import draw_title


def draw_choices(font, items, selection, start_y=270):
    for index, text in enumerate(items):
        color = (255, 218, 134) if index == selection else (164, 175, 192)
        if index == selection:
            font.draw(370, start_y - index * 44, '>', color)
        font.draw(410, start_y - index * 44, text, color)


def draw_game(game, font):
    player, stage = game.player, game.stage
    camera_x = camera_offset(player.x, stage.width, SCREEN_WIDTH)
    shake = sum(enemy.impact.shake_x for enemy in game.enemies if enemy.impact is not None)
    camera_x = max(0, min(stage.width - SCREEN_WIDTH, camera_x + max(-3, min(3, shake))))
    stage.draw(camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    director = getattr(stage, 'respawns', None)
    if director is not None:
        director.draw_floor(camera_x, SCREEN_WIDTH)
    if player.light is not None:
        player.light.draw(camera_x)
    for enemy in game.enemies:
        enemy.draw(camera_x, signals=False)
    player.draw(camera_x)
    draw_darkness(stage, player, camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    draw_navigation(stage, player, camera_x, SCREEN_WIDTH)
    stage.draw_labels(font, camera_x)
    player.draw_flash(camera_x)
    player.draw_recovery(camera_x)
    draw_sword_stroke(player,camera_x)
    draw_buffs(player, camera_x)
    for bomb in player.bombs:
        bomb.draw(camera_x)
    for enemy in game.enemies:
        enemy.draw_signals(camera_x, show_health=enemy_is_visible(stage, player, enemy))
        enemy.draw_effects(camera_x)
    if director is not None:
        director.draw_signals(camera_x, font, SCREEN_WIDTH)
    draw_bomb_aim(player, stage.solids, font, camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    if game.show_debug:
        stage.draw_debug(camera_x)
        player.draw_debug(camera_x)
        for enemy in game.enemies:
            enemy.draw_debug(camera_x)
    with blended():
        for y in range(SCREEN_HEIGHT - 112, SCREEN_HEIGHT, 4):
            alpha = min(210, (y - SCREEN_HEIGHT + 112) * 3)
            pico2d.draw_rectangle(0, y, SCREEN_WIDTH - 1, y + 3,
                                  9, 14, 23, a=alpha, filled=True)
        pico2d.draw_rectangle(0, 0, SCREEN_WIDTH - 1, 64, 9, 14, 23, a=190, filled=True)
    hp_color = (160, 239, 183) if player.heal_effect > 0 else (235, 240, 245)
    font.draw(20, SCREEN_HEIGHT - 28, f'체력 {player.health} / 3', hp_color)
    battery_color = (255, 215, 126) if player.battery >= 50 else (238, 145, 118)
    font.draw(170, SCREEN_HEIGHT - 28,
              f'배터리 {player.battery} / {player.max_battery}', battery_color)
    if player.light is not None:
        seconds = ceil(player.light.remaining * 10) / 10
        font.draw(440, SCREEN_HEIGHT - 28, f'조명 {seconds:.1f}초', (255, 221, 146))
    minutes, seconds = divmod(int(game.play_time), 60)
    font.draw(840, SCREEN_HEIGHT - 28, f'{minutes:02}:{seconds:02}', (164, 175, 192))
    font.draw(20, SCREEN_HEIGHT - 58, stage.objective, (188, 200, 212))
    if stage.fuse_state != 'ABSENT' or stage.stage_id in ('hospital','substation'):
        font.draw(840, SCREEN_HEIGHT - 58, f'조각 {player.fragments}', (170, 197, 211))
    if hasattr(stage, 'hud_status'):
        font.draw(635, SCREEN_HEIGHT - 28, stage.hud_status, (255, 223, 137))
    elif stage.fuse_state != 'ABSENT':
        label = {'WORLD': '미획득', 'CARRIED': '보유', 'INSTALLED': '설치 완료'}[stage.fuse_state]
        font.draw(635, SCREEN_HEIGHT - 28, f'퓨즈 {label}', (255, 223, 137))
    prompt = stage.interaction_prompt(player)
    if prompt is not None:
        x, y, label = prompt
        prompt_x = max(20, min(SCREEN_WIDTH - 220, x - camera_x - 55))
        font.draw(prompt_x, min(y + 132, 430), label, (255, 223, 137))
    controls = ('←/→ 방향  ↑/↓ 각도  F 놓아 투척' if player.bomb_aim is not None
                else '방향키 이동  Shift 달리기  Space 점프  W 광검')
    font.draw(20, 44, controls,
              (210, 219, 230))
    item_controls = ('충전 1초 · 다른 행동이나 슬롯 선택으로 취소' if player.bomb_aim is not None
                     else 'Q 섬광  R 투광기  E 조작  1~4 선택  F 사용  Esc 메뉴')
    font.draw(20, 18, item_controls, (177, 191, 207))
    for slot, label in enumerate(('치료제', '속도', '광탄', '보호막')):
        x = 616 + slot * 82
        selected = player.inventory.selected == slot
        pico2d.draw_rectangle(x, 6, x + 78, 60, 27, 33, 39, filled=True)
        pico2d.draw_rectangle(x, 6, x + 78, 60, *( (244, 206, 119) if selected else (68, 77, 88)))
        font.draw(x + 5, 46, f'{slot + 1} {label}', (235, 223, 192))
        draw_item(slot, x + 23, 22, 28)
        font.draw(x + 43, 22, f'{player.inventory.counts[slot]}/2', (220, 228, 228))
    selected_name = ITEM_NAMES[player.inventory.selected]
    item_hint = 'F 유지 / 놓아 투척' if player.inventory.selected == LIGHT_BOMB else 'F 사용'
    font.draw(616, 78, f'선택: {selected_name} · {item_hint}', (241, 211, 150))
    with blended():
        draw_buff_timers(font, player.item_effects)
    if player.notice_time > 0:
        font.draw(20, SCREEN_HEIGHT - 84, player.notice, (255, 195, 110))


def draw_session(game, font, menu_font, title_font):
    clear_frame()
    if game.state == 'TITLE':
        draw_title(game,font,menu_font,title_font,SCREEN_WIDTH,SCREEN_HEIGHT)
    elif game.state == 'CITY_MAP':
        draw_city_map(game, font, menu_font)
    elif game.state == 'MANAGEMENT':
        draw_management(game, font, menu_font)
    elif game.state in ('PLAY', 'PAUSED', 'STAGE_CLEAR', 'TRANSITION'):
        draw_game(game, font)
        if game.state == 'TRANSITION':
            alpha = int(255 * max(0, 1-abs(game.transition_elapsed-.35)/.35))
            with blended():
                pico2d.draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 5, 11, 18, a=alpha, filled=True)
        elif game.state == 'PAUSED':
            pico2d.draw_rectangle(250, 90, 710, 440, 15, 21, 32, filled=True)
            pico2d.draw_rectangle(250, 90, 710, 440, 120, 108, 83)
            menu_font.draw(410, 405, '일시정지', (242, 225, 191))
            draw_choices(menu_font, game.PAUSE_ITEMS, game.selection, start_y=320)
            if game.PAUSE_ITEMS[game.selection] == '스테이지 재시작':
                font.draw(290, 150, '구간의 진행과 자원을 모두 되돌립니다', (220, 180, 125))
            font.draw(345, 115, 'E 확인    Esc 계속하기', (164, 175, 192))
        elif game.state == 'STAGE_CLEAR':
            with blended():
                pico2d.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1,
                                      6, 11, 20, a=165, filled=True)
            pico2d.draw_rectangle(220, 140, 740, 420, 15, 21, 32, filled=True)
            pico2d.draw_rectangle(220, 140, 740, 420, 120, 108, 83)
            menu_font.draw(350, 377, f'{game.stage.name} 복구 완료', (242, 225, 191))
            draw_choices(menu_font, game.clear_items, game.selection, start_y=290)
            font.draw(330, 157, '위/아래 선택    E 확인', (164, 175, 192))
