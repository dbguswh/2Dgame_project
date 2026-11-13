"""한 구간의 이동·전투·상태 복원을 갱신한다."""

from combat import overlaps


def restore_enemies(enemies, stage):
    for enemy in enemies:
        if stage.fixture_powered:
            enemy.dissolve()
        else:
            enemy.reset()


def update_world(delta_time, player, enemies, stage, records=None):
    """이동, 적의 준비, 플레이어 타격, 살아 있는 적의 타격 순으로 판정한다."""
    stage.update(delta_time)
    life_before = player.respawn_count
    player.update(delta_time, stage.width, stage.solids, stage.light_regions)
    if player.respawn_count != life_before:
        if records is not None:
            records.remember(player, stage)
            records.restore_after_death(player, stage)
        else:
            stage.restore_after_death()
        restore_enemies(enemies, stage)
    stage.collect_pickups(player)
    stage.apply_rewards(player)
    interaction_requested = player.interaction_requested
    player.interaction_requested = False
    if interaction_requested:
        if stage.activate_exit(player):
            player.clear_input()
        elif stage.activate_fixture(player):
            player.checkpoint_position = stage.fixture_checkpoint
            player.notice = '구역 조명 복구 · 안전 지점 확보'
            player.notice_time = 2.2
    if stage.fixture_powered:
        for enemy in enemies:
            enemy.dissolve()
    if records is not None:
        # R 소비와 E 복구를 적의 타격보다 먼저 최신 기록에 반영한다.
        records.remember(player, stage)
    life_before = player.respawn_count
    for enemy in enemies:
        enemy.update(delta_time, player, stage, player.light)
    target = player.get_attack_target(
        [(enemy.identity, enemy.get_bb()) for enemy in enemies if enemy.alive]
    )
    for enemy in enemies:
        if enemy.alive and enemy.identity == target:
            enemy.take_damage()
            if player.attack_kind == 'ground' and player.attack_stage == 2:
                enemy.apply_knockback(player.face_dir)
            player.notice = 'Shade 처치' if not enemy.alive else 'Shade 명중'
            player.notice_time = 1.0
    for enemy in enemies:
        attack = enemy.consume_attack()
        if enemy.alive and overlaps(attack, player.get_bb()):
            player.take_damage()
        if player.respawn_count != life_before:
            if records is not None:
                records.restore_after_death(player, stage)
            else:
                stage.restore_after_death()
            restore_enemies(enemies, stage)
            break
    safe_position = stage.safe_position(player.motion)
    if safe_position is not None:
        player.last_safe_position = safe_position
    if records is not None:
        records.remember(player, stage)
