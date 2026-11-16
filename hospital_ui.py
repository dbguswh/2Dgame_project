"""병원 배전 상태·다음 행동을 장소와 가까운 안내로 표시한다."""
import pico2d
from controls_view import fonts


def circuit_status(stage,key):
    if stage.fixture_powered:return '전체 복구 완료'
    if stage.returned[key]:return '부품 확보 · 중앙 귀환 완료'
    if stage.parts[key]:return '부품 확보 · 정전 구간 귀환 중'
    return '공급 중 · 방 안은 어두움' if stage.powered_circuit==key else '공급 대기 · 중앙 E로 선택'


def draw_labels(stage,font,camera_x):
    small,_=fonts()
    if stage.in_hub and stage.record_time<=0:
        center=1472-camera_x
        pico2d.draw_rectangle(center-238,302,center+238,416,13,24,32,filled=True)
        pico2d.draw_line(center-238,416,center+238,416,110,136,137)
        font.draw(center-220,394,'비상 배전 · 두 부품을 모아 중앙에 설치',(223,216,179))
        for key,y in (('A',365),('B',339)):
            color=(237,207,133) if stage.powered_circuit==key else (167,195,203)
            small.draw(center-218,y,key+'  '+circuit_status(stage,key),color)
        small.draw(center-218,315,'회로 선택 → 방 교전 → 부품 E 분리 → 귀환',(162,180,192))
    # 목적지 명패. 가까운 E 안내와 겹치지 않는 위치에만 표시한다.
    for wx,y,text,w in ((760,286,'A 창고',86),(1408,244,'회로 선택',102),
                         (1536,278,'부품 설치',102),(2576,268,'B 정비실',102)):
        x=wx-camera_x
        if 18+w/2<=x<=942-w/2:
            pico2d.draw_rectangle(x-w/2,y-13,x+w/2,y+13,13,24,32,filled=True)
            small.draw(x-w/2+10,y,text,(185,206,204))
    for key,(wx,y) in stage.part_positions.items():
        x=wx-camera_x
        if not stage.parts[key] and 100<x<860:
            name='A 전력 퓨즈' if key=='A' else 'B 전원 모듈'
            small.draw(x-45,y+53,name,(234,216,160))
    pending=stage.returning_key
    if pending:
        warnings=[p.warning_duration-p.warning_elapsed for p in stage.corridor_points(pending) if p.state=='WARNING']
        if warnings:
            from math import ceil
            seconds=max(.1,ceil(min(warnings)*10-1e-9)/10)
            small.draw(24,406,f'{pending} 복도 침입자 · 출현 {seconds:.1f}초 전',(224,151,177))
    if stage.record_time>0:
        font.draw(24,390,'시설 기록: 그림자 핵이 중앙 전력망을 잠식하고 있다.',(231,215,159))
        small.draw(24,362,'다음 임무: 변전소의 두 차단기로 봉쇄 설비 가동',(196,207,211))
