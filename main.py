"""Blackout: 게임 창과 플레이어의 기본 출력을 시작한다."""

import pico2d
from time import perf_counter
from pathlib import Path

from player import Player
from enemy import Shade
from combat import overlaps
from physics import camera_offset
from stage import Stage
from window import (
    SCREEN_WIDTH, SCREEN_HEIGHT, clear_frame, has_input_focus, open_game_window,
)


def main():
    open_game_window()
    player = None
    font = None
    enemies = []
    enemy = None
    try:
        stage = Stage()
        player = Player(x=stage.start[0], feet_y=stage.start[1])
        enemies = [Shade(*stage.enemy_spawn, combat_bounds=stage.combat_bounds)]
        font = pico2d.load_font(
            str(Path(pico2d.__file__).parent / 'data' / 'ConsolaMalgun.ttf'), 18,
        )
        running = True
        show_debug = False
        previous_time = perf_counter()

        while running:
            now = perf_counter()
            # 창 이동·중단 뒤 한 프레임에 멀리 이동하는 현상을 방지한다.
            delta_time = min(now - previous_time, 0.05)
            previous_time = now
            for event in pico2d.get_events():
                if event.type == pico2d.SDL_QUIT:
                    running = False
                elif event.type == pico2d.SDL_KEYDOWN:
                    if event.key == pico2d.SDLK_ESCAPE:
                        running = False
                    elif event.key == pico2d.SDLK_F1:
                        show_debug = not show_debug
                player.handle_event(event)

            if not running:
                break

            if not has_input_focus():
                player.clear_input()
            life_before = player.respawn_count
            player.update(delta_time, stage.width, stage.solids)
            if player.respawn_count != life_before:
                for enemy in enemies:
                    enemy.reset()
            life_before = player.respawn_count
            for enemy in enemies:
                enemy.update(delta_time, player, stage)
            target = player.get_attack_target(
                [(enemy.identity, enemy.get_bb()) for enemy in enemies if enemy.alive]
            )
            for enemy in enemies:
                if enemy.alive and enemy.identity == target:
                    enemy.take_damage()
                    player.notice = 'Shade 처치' if not enemy.alive else 'Shade 명중'
                    player.notice_time = 1.0
            for enemy in enemies:
                attack = enemy.consume_attack()
                if enemy.alive and overlaps(attack, player.get_bb()):
                    player.take_damage()
                if player.respawn_count != life_before:
                    for reset_enemy in enemies:
                        reset_enemy.reset()
                    break
            safe_position = stage.safe_position(player.motion)
            if safe_position is not None:
                player.last_safe_position = safe_position
            camera_x = camera_offset(player.x, stage.width, SCREEN_WIDTH)
            clear_frame()
            stage.draw(camera_x, SCREEN_WIDTH, SCREEN_HEIGHT)
            for enemy in enemies:
                enemy.draw(camera_x)
            player.draw(camera_x)
            if show_debug:
                stage.draw_debug(camera_x)
                player.draw_debug(camera_x)
                for enemy in enemies:
                    enemy.draw_debug(camera_x)
            font.draw(20, SCREEN_HEIGHT - 28, f'체력 {player.health} / 3', (235, 240, 245))
            font.draw(20, 24, '방향키 이동    Space 점프    W 베기    F1 판정 표시    Esc 종료',
                      (210, 219, 230))
            if player.notice_time > 0:
                font.draw(20, SCREEN_HEIGHT - 58, player.notice, (255, 195, 110))
            pico2d.update_canvas()
            pico2d.delay(0.001)
    finally:
        # 렌더러를 닫기 전에 캐릭터의 이미지 자원을 해제한다.
        player = None
        font = None
        enemy = None
        reset_enemy = None
        enemies.clear()
        pico2d.close_canvas()


if __name__ == "__main__":
    main()
