"""맵·투척체·인벤토리가 공유하는 원본 PNG 아이템 스프라이트."""

import json
from pathlib import Path

from inventory import MEDKIT, LIGHT_BOMB


ROOT = Path(__file__).resolve().parent / 'assets/images/items'
ASSETS = {MEDKIT: 'medkit', LIGHT_BOMB: 'light_bomb'}
_images = {}


def clear_resources():
    _images.clear()


def draw_item(slot, x, y, size=28):
    import pico2d
    name = ASSETS.get(slot)
    if name is None:
        return
    if slot not in _images:
        data = json.loads((ROOT / (name + '.json')).read_text(encoding='utf-8'))
        _images[slot] = (pico2d.load_image(str(ROOT / data['image'])), data)
    image, data = _images[slot]
    left, top, right, bottom = data['bounds']
    width, height = right - left, bottom - top
    scale = size / max(width, height)
    image.clip_draw(left, data['source_size'][1] - bottom, width, height,
                    x, y, width * scale, height * scale)
