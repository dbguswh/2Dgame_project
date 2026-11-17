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
from halo_view import draw_halo_aim
from stage_notice_view import draw_weapon_acquired,draw_stage_transition
from controls_view import draw_controls,fonts as control_fonts
from menu_ui import choice_overlay


def draw_choices(font, items, selection, start_y=270):
    for index, text in enumerate(items):
        color = (255, 218, 134) if index == selection else (164, 175, 192)
        if index == selection:
            font.draw(370, start_y - index * 44, '>', color)
        font.draw(410, start_y - index * 44, text, color)


def draw_game(game, font, show_hud=True):
    player, stage = game.player, game.stage
    camera_x = camera_offset(player.x, stage.width, SCREEN_WIDTH)
    shake = sum(enemy.impact.shake_x for enemy in game.enemies if enemy.impact is not None)
    camera_x = max(0, min(stage.width - SCREEN_WIDTH, camera_x + max(-3, min(3, shake))))
    reveal=game.bridge_reveal
    if reveal is not None and reveal.active:camera_x=reveal.camera_x
    stage.draw(camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    director = getattr(stage, 'respawns', None)
    if director is not None:
        director.draw_floor(camera_x, SCREEN_WIDTH)
    if player.light is not None:
        player.light.draw(camera_x)
    for enemy in game.enemies:
        enemy.draw(camera_x, signals=False)
    player.draw(camera_x)
    if hasattr(stage,'draw_foreground'):stage.draw_foreground(player,camera_x)
    draw_darkness(stage, player, camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    draw_navigation(stage, player, camera_x, SCREEN_WIDTH)
    if hasattr(stage,'draw_objective_signals'):stage.draw_objective_signals(player,camera_x)
    stage.draw_labels(font, camera_x)
    player.draw_flash(camera_x)
    player.draw_recovery(camera_x)
    draw_sword_stroke(player,camera_x)
    draw_buffs(player, camera_x)
    for bomb in player.bombs:
        bomb.draw(camera_x)
    if player.halo is not None and player.halo.active:player.halo.draw(camera_x)
    for enemy in game.enemies:
        enemy.draw_signals(camera_x, show_health=enemy_is_visible(stage, player, enemy))
        enemy.draw_effects(camera_x)
    if hasattr(stage,'draw_combat_targets'):stage.draw_combat_targets(game.enemies,camera_x)
    if director is not None:
        director.draw_signals(camera_x, font, SCREEN_WIDTH)
    draw_bomb_aim(player, stage.solids, font, camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    draw_halo_aim(player,stage,font,camera_x)
    if reveal is not None and reveal.active:
        reveal.draw(font,SCREEN_WIDTH,SCREEN_HEIGHT)
        return
    if game.show_debug:
        stage.draw_debug(camera_x)
        player.draw_debug(camera_x)
        for enemy in game.enemies:
            enemy.draw_debug(camera_x)
    if not show_hud:return
    with blended():
        for y in range(SCREEN_HEIGHT - 112, SCREEN_HEIGHT, 4):
            alpha = min(210, (y - SCREEN_HEIGHT + 112) * 3)
            pico2d.draw_rectangle(0, y, SCREEN_WIDTH - 1, y + 3,
                                  9, 14, 23, a=alpha, filled=True)
        pico2d.draw_rectangle(0, 0, SCREEN_WIDTH - 1, 96, 9, 16, 25, a=240, filled=True)
        pico2d.draw_line(0,96,SCREEN_WIDTH-1,96,57,72,83,a=210)
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
        if stage.stage_id=='residential' and stage.fuse_state=='CARRIED':
            from power_objectives import draw_fuse_art
            draw_fuse_art(621,SCREEN_HEIGHT-28,22)
        label = {'WORLD': '미획득', 'CARRIED': '보유', 'INSTALLED': '설치 완료'}[stage.fuse_state]
        font.draw(635, SCREEN_HEIGHT - 28, f'퓨즈 {label}', (255, 223, 137))
    prompt = stage.interaction_prompt(player)
    if prompt is not None:
        x, y, label = prompt
        prompt_x = max(20, min(SCREEN_WIDTH - 220, x - camera_x - 55))
        font.draw(prompt_x, min(y + 132, 430), label, (255, 223, 137))
    draw_controls(player,font)
    small,_=control_fonts()
    for slot, label in enumerate(('치료제', '속도', '광탄', '보호막')):
        x = 616 + slot * 82
        selected = player.inventory.selected == slot
        pico2d.draw_rectangle(x, 6, x + 78, 60, 27, 33, 39, filled=True)
        pico2d.draw_rectangle(x, 6, x + 78, 60, *( (244, 206, 119) if selected else (68, 77, 88)))
        small.draw(x + 5, 47, f'{slot + 1} {label}', (235, 223, 192))
        draw_item(slot, x + 23, 22, 28)
        small.draw(x + 43, 22, f'{player.inventory.counts[slot]}/2', (220, 228, 228))
    selected_name = ITEM_NAMES[player.inventory.selected]
    small.draw(616, 81, f'1~4 선택   F {"유지·놓아 투척" if player.inventory.selected==LIGHT_BOMB else "사용"}  ·  {selected_name}', (213, 199, 165))
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
        if game.weapon_tip_open:draw_weapon_acquired(font,menu_font)
        else:draw_management(game, font, menu_font)
    elif game.state=='TRANSITION':
        draw_stage_transition(game,font,menu_font)
    elif game.state in ('PLAY', 'PAUSED', 'STAGE_CLEAR', 'TRANSITION'):
        draw_game(game, font, show_hud=game.state=='PLAY')
        if game.state == 'PAUSED':
            warning='구간 진행과 자원을 초기화합니다.' if game.selection==1 else ''
            choice_overlay(menu_font,'일시정지',game.PAUSE_ITEMS,game.selection,
                           '플레이 시간과 모든 효과가 멈춰 있습니다.',warning)
        elif game.state == 'STAGE_CLEAR':
            choice_overlay(menu_font,f'{game.stage.name} 복구 완료',game.clear_items,
                           game.selection,'지도·관리소에서 다음 구역을 준비하세요.',escape_label='타이틀')
