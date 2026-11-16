"""무기 획득과 구역 이동을 다른 화면 정보 없이 한 번에 전달한다."""

import pico2d
from effects import blended,glow
from enemy_art import draw_halo


def draw_weapon_acquired(font,heading):
    pico2d.draw_rectangle(0,0,959,539,7,13,23,filled=True)
    font.draw(94,437,'새 무기 획득',(223,189,119))
    heading.draw(92,383,'광륜',(255,232,179))
    pico2d.draw_line(94,344,864,344,113,101,73)
    with blended():
        glow(749,247,106,(255,194,95),alpha=60)
        draw_halo(749,247,size=156)
    for y,text in ((294,'A  광검과 광륜 전환'),(249,'W 유지  조준 / 놓으면 투척'),
                   (204,'방향키  방향과 위쪽 각도 조절'),(147,'던진 광륜은 돌아오며 뒤쪽 적도 공격한다.')):
        font.draw(94,y,text,(219,227,232) if y!=147 else (162,181,195))
    font.draw(94,79,'E 확인 후 장비 강화',(245,215,155))


def draw_stage_transition(game,font,heading):
    stage_id=game.stage.stage_id if game.transition_swapped else game.stage.next_stage_id
    hospital=stage_id=='hospital'
    pico2d.draw_rectangle(0,0,959,539,6,12,21,filled=True)
    font.draw(112,354,'다음 구역',(194,172,125))
    heading.draw(112,300,'운하 병원' if hospital else '중앙 변전소',(244,227,188))
    pico2d.draw_line(112,267,848,267,114,101,73)
    font.draw(112,217,'두 부품을 회수해 비상 전원을 복구하세요.' if hospital else
              '차단기와 승강기를 가동해 중앙 시설로 진입하세요.',(182,201,215))
