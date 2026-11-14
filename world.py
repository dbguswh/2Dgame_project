"""한 구간의 이동·전투·상태 복원을 갱신한다."""

from combat import overlaps


def restore_enemies(enemies, stage):
    for enemy in enemies:
        if stage.fixture_powered:
            enemy.dissolve()
        else:
            enemy.reset()
    director = getattr(stage, 'respawns', None)
    if director is not None:
        director.reset(powered=stage.fixture_powered)


def update_world(delta_time, player, enemies, stage, records=None):
    """이동, 적의 준비, 플레이어 타격, 살아 있는 적의 타격 순으로 판정한다."""
    stage.update(delta_time)
    previous_light = player.light
    previous_light_remaining = previous_light.remaining if previous_light is not None else 0.0
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
        else:
            supply_action = getattr(stage, 'activate_supply', None)
            if supply_action is not None:
                supply_action(player)
    if stage.fixture_powered:
        for enemy in enemies:
            enemy.dissolve()
    if records is not None:
        # Q·R 소비와 E 복구를 적의 타격보다 먼저 최신 기록에 반영한다.
        records.remember(player, stage)
    life_before = player.respawn_count
    for enemy in enemies:
        enemy.update(delta_time, player, stage, player.light)
    for bomb in player.bombs:
        bomb.update(delta_time, stage.solids)
        targets = bomb.consume_targets([(e.identity, e.get_bb()) for e in enemies if e.alive], stage.solids)
        for enemy in enemies:
            if enemy.alive and enemy.identity in targets:
                direction = 1 if enemy.x >= bomb.x else -1
                enemy.receive_bomb(direction, (enemy.x, max(enemy.feet_y + 8, min(bomb.y, enemy.feet_y + 80))))
        if targets:
            player.notice, player.notice_time = f'광탄 명중 · Shade {len(targets)}명', 1.2
    player.bombs[:] = [bomb for bomb in player.bombs if bomb.active]
    flash_target = player.consume_flash_target(
        [(enemy.identity, enemy.get_bb()) for enemy in enemies if enemy.alive])
    for enemy in enemies:
        if enemy.alive and enemy.identity == flash_target:
            point = (enemy.x, max(enemy.feet_y + 20, min(player.feet_y + 44, enemy.feet_y + 72)))
            enemy.receive_flash(player.face_dir, point)
            player.notice = '섬광 · Shade 처치' if not enemy.alive else '섬광 명중 · Shade 제압'
            player.notice_time = 1.0
    target = player.get_attack_target(
        [(enemy.identity, enemy.get_bb()) for enemy in enemies if enemy.alive]
    )
    for enemy in enemies:
        if enemy.alive and enemy.identity == target:
            heavy = player.attack_kind == 'ground' and player.attack_stage == 2
            attack, body = player.get_attack_box(), enemy.get_bb()
            point = ((max(attack[0], body[0]) + min(attack[2], body[2])) / 2,
                     (max(attack[1], body[1]) + min(attack[3], body[3])) / 2)
            style='air' if player.attack_kind=='air' else 'rising' if heavy else 'horizontal'
            enemy.take_damage(direction=player.face_dir, heavy=heavy, point=point, sword_style=style)
            player.hit_pause.trigger(enemy.impact.hitstop)
            if heavy:
                enemy.apply_knockback(player.face_dir)
            player.notice = 'Shade 처치' if not enemy.alive else 'Shade 명중'
            player.notice_time = 1.0
    for enemy in enemies:
        enemy.launch_pending_shot()
        attack = enemy.consume_attack()
        if enemy.alive and overlaps(attack, player.get_bb()):
            player.take_damage()
        for bolt in enemy.bolts:
            bolt.update(delta_time, stage.solids, player, player.light)
            if bolt.consume_hit():
                player.take_damage()
        enemy.bolts[:] = [bolt for bolt in enemy.bolts if bolt.active or bolt.fade > 0]
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
    # 전투·사망 복원·E 복구를 모두 반영한 뒤 생성한다. 새 적은 다음 갱신부터 행동한다.
    director = getattr(stage, 'respawns', None)
    if director is not None:
        director.update(delta_time, player, enemies, powered=stage.fixture_powered,
                        previous_light=previous_light, previous_light_remaining=previous_light_remaining)
