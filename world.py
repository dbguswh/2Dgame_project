"""한 구간의 이동·전투·상태 복원을 갱신한다."""

from combat import overlaps


def update_world(delta_time, player, enemies, stage):
    """이동, 적의 준비, 플레이어 타격, 살아 있는 적의 타격 순으로 판정한다."""
    life_before = player.respawn_count
    player.update(delta_time, stage.width, stage.solids, stage.light_regions)
    if player.respawn_count != life_before:
        for enemy in enemies:
            enemy.reset()
    life_before = player.respawn_count
    for enemy in enemies:
        enemy.update(delta_time, player, stage, player.light)
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
