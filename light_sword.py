"""광검의 초기 사거리와 벽·발판으로 제한한 근접 판정."""

from combat import front_box


SWORD_REACH = 80
AIR_SWORD_DROP = 32


def sword_box(x, feet_y, direction, air, solids, rising=False):
    bottom = feet_y - AIR_SWORD_DROP if air else feet_y + 12
    top = feet_y + 48 if air else feet_y + (112 if rising else 80)
    box = front_box(x, direction, 12, 12 + SWORD_REACH, bottom, top, solids)
    if box is None:
        return None
    left, bottom, right, top = box
    if air:
        for solid in solids:
            if left < solid.right and right > solid.left and bottom < solid.top <= feet_y:
                bottom = solid.top
    else:
        for solid in solids:
            if left < solid.right and right > solid.left and feet_y + 12 <= solid.bottom < top:
                top = solid.bottom
    return (left, bottom, right, top) if top > bottom else None
