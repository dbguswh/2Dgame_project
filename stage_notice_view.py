"""무기 획득과 구역 이동을 다른 화면 정보 없이 한 번에 전달한다."""

import pico2d
from effects import blended,glow
from enemy_art import draw_halo
from menu_ui import header,footer,body_font,TEXT,MUTED,GOLD
from controls_view import keycap,fonts as control_fonts


def draw_weapon_acquired(font,heading):
    pico2d.draw_rectangle(0,0,959,539,7,13,23,filled=True)
    header(heading,'새 무기 획득','광륜 · 돌아오는 궤적으로 후방을 공격하는 무기')
    heading.draw(94,370,'광륜',GOLD)
    with blended():
        glow(749,247,106,(255,194,95),alpha=60)
        draw_halo(749,247,size=156)
    small,key_font=control_fonts()
    keycap('A','광검과 광륜 전환',94,303,small,key_font)
    keycap('W','유지하여 조준 · 놓아서 투척',94,260,small,key_font)
    keycap('← →','방향',94,217,small,key_font)
    keycap('↑ ↓','각도 조절',312,217,small,key_font)
    body_font().draw(94,156,'투척당 배터리 10 · 복귀 후 1초 대기',GOLD)
    body_font().draw(94,125,'조준 취소는 배터리를 쓰지 않습니다.',MUTED)
    footer(((94,'E','확인 후 장비 강화'),))


def draw_stage_transition(game,font,heading):
    stage_id=game.stage.stage_id if game.transition_swapped else game.stage.next_stage_id
    hospital=stage_id=='hospital'
    pico2d.draw_rectangle(0,0,959,539,6,12,21,filled=True)
    body_font().draw(112,354,'다음 구역',(194,172,125))
    heading.draw(112,300,'운하 병원' if hospital else '중앙 변전소',(244,227,188))
    pico2d.draw_line(112,267,848,267,114,101,73)
    body_font().draw(112,217,'두 부품을 회수해 비상 전원을 복구하세요.' if hospital else
              '차단기와 승강기를 가동해 중앙 시설로 진입하세요.',(182,201,215))
