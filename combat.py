"""플레이어와 적이 함께 사용하는 근접 공격의 기하 판정."""


def overlaps(first, second):
    if first is None or second is None:
        return False
    return (first[0] < second[2] and first[2] > second[0]
            and first[1] < second[3] and first[3] > second[1])


def front_box(x, direction, start, end, bottom, top, solids):
    if direction > 0:
        left, right = x + start, x + end
        for solid in solids:
            if bottom < solid.top and top > solid.bottom and left <= solid.left < right:
                right = solid.left
    else:
        left, right = x - end, x - start
        for solid in solids:
            if bottom < solid.top and top > solid.bottom and left < solid.right <= right:
                left = solid.right
    return (left, bottom, right, top) if right > left else None
