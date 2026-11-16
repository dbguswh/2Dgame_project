"""광검을 손으로 쥔 이동·대기·점프 자세. 판정과 분리된 공유 이미지."""

import json
from pathlib import Path
import pico2d

ROOT=Path(__file__).resolve().parent/'assets/images/characters'
_assets={}


def clear_resources():
    _assets.clear()


def carried_frame(player,state):
    if player.weapon!='sword' or state not in ('idle','walk','run','jump_rise','jump_apex','jump_fall'):
        return None
    kind='jump' if state.startswith('jump_') else 'run' if state=='run' else 'walk'
    if kind not in _assets:
        data=json.loads((ROOT/f'player_sword_{kind}.json').read_text(encoding='utf-8'))
        _assets[kind]=(data,pico2d.load_image(str(ROOT/data['image'])))
    data,image=_assets[kind]
    index=('jump_rise','jump_apex','jump_fall').index(state) if kind=='jump' else player.walk_frame if state!='idle' else 0
    return data,image,data['frames'][index]
