"""한 구간의 이동·전투·상태 복원을 갱신한다."""

from combat import overlaps
from halo import HALO_COOLDOWN


def restore_enemies(enemies, stage):
    for enemy in enemies:
        if stage.fixture_powered or stage.is_temporarily_lit(enemy.get_bb()):
            enemy.dissolve()
        else:
            enemy.reset()
    director = getattr(stage, 'respawns', None)
    if director is not None:
        director.reset(powered=stage.fixture_powered)
        for point in director.points:
            if not stage.fixture_powered and stage.is_temporarily_lit(point.get_bb()):
                point.state = 'WAITING'


def update_world(delta_time, player, enemies, stage, records=None):
    """이동, 적의 준비, 플레이어 타격, 살아 있는 적의 타격 순으로 판정한다."""
    stage.before_update(player)
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
        stage.interact(player)
    for enemy in enemies:
        if stage.fixture_powered or stage.is_temporarily_lit(enemy.get_bb()):
            enemy.dissolve()
    if records is not None:
        # Q·R 소비와 E 복구를 적의 타격보다 먼저 최신 기록에 반영한다.
        records.remember(player, stage)
    life_before = player.respawn_count
    for enemy in enemies:
        enemy.update(delta_time, player, stage, player.light)
    if player.halo is not None:
        ring=player.halo
        ring.update(delta_time,player,stage.solids)
        if not ring.active:
            player.halo_cooldown=max(player.halo_cooldown,HALO_COOLDOWN)
        candidates=ring.candidates([(e.identity,e.get_bb()) for e in enemies if e.alive],stage.solids)
        for enemy in enemies:
            if enemy.alive and enemy.identity in candidates:
                direction,point=candidates[enemy.identity]
                if enemy.receive_weapon(direction,point,'ring'):
                    ring.hits.add(enemy.identity)
                    player.notice,player.notice_time='광륜 명중',.8
    for bomb in player.bombs:
        bomb.update(delta_time, stage.solids)
        targets = bomb.consume_targets([(e.identity, e.get_bb()) for e in enemies if e.alive], stage.solids)
        for enemy in enemies:
            if enemy.alive and enemy.identity in targets:
                direction = 1 if enemy.x >= bomb.x else -1
                enemy.receive_bomb(direction, (enemy.x, max(enemy.feet_y + 8, min(bomb.y, enemy.feet_y + 80))))
        if targets:
            player.notice, player.notice_time = f'광탄 명중 · 침입자 {len(targets)}명', 1.2
    player.bombs[:] = [bomb for bomb in player.bombs if bomb.active]
    flash_target = player.consume_flash_target(
        [(enemy.identity, enemy.get_bb()) for enemy in enemies if enemy.alive])
    for enemy in enemies:
        if enemy.alive and enemy.identity == flash_target:
            point = (enemy.x, max(enemy.feet_y + 20, min(player.feet_y + 44, enemy.feet_y + 72)))
            enemy.receive_flash(player.face_dir, point)
            player.notice = '섬광 · 침입자 처치' if not enemy.alive else '섬광 명중 · 침입자 제압'
            player.notice_time = 1.0
    targets = player.get_attack_targets(
        [(enemy.identity, enemy.get_bb()) for enemy in enemies if enemy.alive]
    )
    for enemy in enemies:
        if enemy.alive and enemy.identity in targets:
            spin=player.attack_kind=='ground' and player.attack_stage==3
            heavy = player.attack_kind == 'ground' and player.attack_stage in (2,3)
            direction=(1 if enemy.x>=player.x else -1) if spin else player.face_dir
            attack, body = player.get_attack_box(), enemy.get_bb()
            point = ((max(attack[0], body[0]) + min(attack[2], body[2])) / 2,
                     (max(attack[1], body[1]) + min(attack[3], body[3])) / 2)
            style='spin' if spin else 'air' if player.attack_kind=='air' else 'rising' if heavy else 'horizontal'
            if not enemy.receive_weapon(direction,point,style,heavy):
                player.notice,player.notice_time='정면 방어 · 뒤쪽이나 공격 후 빈틈을 노리세요',1.0
                continue
            player.hit_pause.trigger(enemy.impact.hitstop)
            if heavy:
                enemy.apply_knockback(direction)
            player.notice = '회전 베기 명중' if spin else '침입자 처치' if not enemy.alive else '침입자 명중'
            player.notice_time = 1.0
    if hasattr(stage,'update_combat_seals'):
        stage.update_combat_seals(enemies)
        if records is not None:records.remember(player,stage)
    for enemy in enemies:
        enemy.launch_pending_shot()
        attack = enemy.consume_attack()
        if enemy.alive and overlaps(attack, player.get_bb()):
            enemy.mark_attack_contact()
            player.take_damage()
        for bolt in enemy.bolts:
            bolt.update(delta_time, stage.solids, player, player.light, fixed_light=stage.is_temporarily_lit)
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
    if hasattr(stage,'update_combat_seals'):stage.update_combat_seals(enemies)
    safe_position = stage.safe_position(player.motion)
    if safe_position is not None:
        player.last_safe_position = safe_position
    if records is not None:
        records.remember(player, stage)
    # 전투·사망 복원·E 복구를 모두 반영한 뒤 생성한다. 새 적은 다음 갱신부터 행동한다.
    director = getattr(stage, 'respawns', None)
    if director is not None:
        director.update(delta_time, player, enemies, powered=stage.fixture_powered,
                        previous_light=previous_light, previous_light_remaining=previous_light_remaining,
                        temporary_light=stage.is_temporarily_lit)
