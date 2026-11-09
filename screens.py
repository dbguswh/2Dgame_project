"""화면 상태에 맞춰 메뉴와 플레이 화면을 그린다."""

from math import ceil

import pico2d

from physics import camera_offset
from window import SCREEN_WIDTH, SCREEN_HEIGHT, clear_frame


def draw_choices(font, items, selection, start_y=270):
    for index, text in enumerate(items):
        color = (255, 218, 134) if index == selection else (164, 175, 192)
        if index == selection:
            font.draw(370, start_y - index * 44, '>', color)
        font.draw(410, start_y - index * 44, text, color)


def draw_game(game, font):
    player, stage = game.player, game.stage
    camera_x = camera_offset(player.x, stage.width, SCREEN_WIDTH)
    stage.draw(camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
    if player.light is not None:
        player.light.draw(camera_x)
    for enemy in game.enemies:
        enemy.draw(camera_x)
    player.draw(camera_x)
    if game.show_debug:
        stage.draw_debug(camera_x)
        player.draw_debug(camera_x)
        for enemy in game.enemies:
            enemy.draw_debug(camera_x)
    font.draw(20, SCREEN_HEIGHT - 28, f'체력 {player.health} / 3', (235, 240, 245))
    battery_color = (255, 215, 126) if player.battery >= 50 else (238, 145, 118)
    font.draw(170, SCREEN_HEIGHT - 28,
              f'배터리 {player.battery} / {player.max_battery}', battery_color)
    if player.light is not None:
        seconds = ceil(player.light.remaining * 10) / 10
        font.draw(440, SCREEN_HEIGHT - 28, f'조명 {seconds:.1f}초', (255, 221, 146))
    minutes, seconds = divmod(int(game.play_time), 60)
    font.draw(840, SCREEN_HEIGHT - 28, f'{minutes:02}:{seconds:02}', (164, 175, 192))
    objective = '구역 조명 복구 완료' if stage.fixture_powered else '목표: 조명 제어함을 찾아 복구하세요'
    font.draw(20, SCREEN_HEIGHT - 58, objective, (188, 200, 212))
    if stage.can_interact(player):
        prompt = '복구 완료' if stage.fixture_powered else 'E: 조명 복구'
        x, y = stage.fixture_position
        font.draw(x - camera_x - 55, y + 132, prompt, (255, 223, 137))
    font.draw(20, 24, '방향키 이동  Space 점프  W 베기  R 조명(50)  E 설비  F1 판정  Esc 메뉴',
              (210, 219, 230))
    if player.notice_time > 0:
        font.draw(20, SCREEN_HEIGHT - 84, player.notice, (255, 195, 110))


def draw_session(game, font, menu_font, title_font):
    clear_frame()
    if game.state == 'TITLE':
        title_font.draw(350, 365, 'Blackout', (242, 225, 191))
        draw_choices(menu_font, ('시작', '나가기'), game.selection)
        font.draw(320, 105, '위/아래 선택    E 확인    Esc 종료', (164, 175, 192))
    elif game.state in ('PLAY', 'PAUSED'):
        draw_game(game, font)
        if game.state == 'PAUSED':
            pico2d.draw_rectangle(250, 90, 710, 440, 15, 21, 32, filled=True)
            pico2d.draw_rectangle(250, 90, 710, 440, 120, 108, 83)
            menu_font.draw(410, 405, '일시정지', (242, 225, 191))
            draw_choices(menu_font, game.PAUSE_ITEMS, game.selection, start_y=320)
            if game.PAUSE_ITEMS[game.selection] == '스테이지 재시작':
                font.draw(290, 150, '구간의 진행과 자원을 모두 되돌립니다', (220, 180, 125))
            font.draw(345, 115, 'E 확인    Esc 계속하기', (164, 175, 192))
