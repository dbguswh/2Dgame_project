"""Shade의 위치·이미지와 전투 상태를 관리한다."""

from pathlib import Path
import json

import pico2d

from physics import EPSILON, Motion
from combat import front_box, overlaps
from combat_feedback import HitPause, Impact
from projectiles import ShadowBolt
from flash import FLASH_STUN, FLASH_KNOCKBACK


IMAGE_PATH = Path(__file__).resolve().parent / 'assets/images/characters/shade.png'
MOTION_DATA_PATH = IMAGE_PATH.with_name('shade_motion.json')
REACTION_DATA_PATH = IMAGE_PATH.with_name('shade_reactions.json')
RANGED_DATA_PATH = IMAGE_PATH.with_name('shade_ranged.json')
DRAW_HEIGHT = 104
BODY_WIDTH = 48
BODY_HEIGHT = 88
WINDUP_TIME = 0.7
STRIKE_TIME = 0.18
RECOVER_TIME = 1.0 - STRIKE_TIME
DEATH_TIME = 0.8
LIGHT_STATES = ('RETREAT', 'LIGHT_WAIT', 'DARK_PATROL')
RANGED_WINDUP = 0.65
RANGED_RELEASE = 0.24
RANGED_COOLDOWN = 1.8


class Shade:
    def __init__(self, x, feet_y, identity=0, combat_bounds=(288, 544), can_shoot=False):
        self.identity = identity
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.motion_data = json.loads(MOTION_DATA_PATH.read_text(encoding='utf-8'))
        self.image = pico2d.load_image(str(MOTION_DATA_PATH.with_name(self.motion_data['image'])))
        self.reaction_data = json.loads(REACTION_DATA_PATH.read_text(encoding='utf-8'))
        self.reaction_image = pico2d.load_image(
            str(REACTION_DATA_PATH.with_name(self.reaction_data['image'])))
        self.face_dir = -1
        self.health = 2
        self.spawn_position = (x, feet_y)
        self.combat_bounds = combat_bounds
        self.patrol_bounds = (combat_bounds[0] + BODY_WIDTH / 2 + 4,
                              combat_bounds[1] - BODY_WIDTH / 2 - 4)
        self.state = 'PATROL'
        self.is_moving = False
        self.walk_distance = 0.0
        self.solids = []
        self.state_time = 0.0
        self.attack_event = None
        self.hurt_time = 0.0
        self.death_pose = 0
        self.retreat_light = None
        self.retreat_direction = 0
        self.active_light = None
        self.knockback_remaining = 0.0
        self.knockback_direction = 1
        self.hit_pause = HitPause()
        self.impact = None
        self.hurt_duration = 0.22
        self.hit_direction = 1
        self.reaction_heavy = False
        self.death_by_hit = False
        self.retreat_retry = 0.0
        self.can_shoot = can_shoot
        self.shot_cooldown = 0.0
        self.shot_target = None
        self.shot_event = None
        self.bolts = []
        self.ranged_data = None
        self.ranged_image = None
        self.stun_remaining = 0.0
        if can_shoot:
            self.ranged_data = json.loads(RANGED_DATA_PATH.read_text(encoding='utf-8'))
            self.ranged_image = pico2d.load_image(str(RANGED_DATA_PATH.with_name(self.ranged_data['image'])))

    @property
    def x(self):
        return self.motion.x

    @property
    def feet_y(self):
        return self.motion.feet_y

    @property
    def alive(self):
        return self.health > 0

    @property
    def animation_frame(self):
        if self.state in ('DYING', 'DEAD'):
            return self.death_pose
        if self.state in ('WINDUP', 'RANGED_WINDUP'):
            return self.motion_data['windup']
        if self.state in ('STRIKE', 'RANGED_RELEASE'):
            return self.motion_data['strike']
        if self.state == 'STUNNED':
            return self.motion_data['walk'][3]
        if self.state == 'LIGHT_WAIT':
            return self.motion_data['walk'][3]
        if self.is_moving:
            phase = int(self.walk_distance / self.motion_data['cycle_distance'] * 4) % 4
            return self.motion_data['walk'][phase]
        return self.motion_data['walk'][0]

    def get_bb(self):
        return self.motion.get_bb()

    @property
    def reaction_frame(self):
        if self.state == 'DYING' and self.death_by_hit:
            phase = 0 if self.state_time < 0.10 else 1 if self.state_time < 0.28 else 2
            return self.reaction_data['defeat'][phase]
        # 실제 타격이 시작되면 피격 자세보다 적의 공격 자세를 우선해 위험을 보여준다.
        if self.alive and self.hurt_time > 0 and self.state not in ('STRIKE', 'RANGED_RELEASE'):
            elapsed = self.hurt_duration - self.hurt_time
            phase = (1 if elapsed < 0.13 else 2) if self.reaction_heavy else (
                0 if elapsed < 0.06 else 1 if elapsed < 0.13 else 2)
            return self.reaction_data['hurt'][phase]
        return None

    def can_see(self, player):
        if not self.combat_bounds[0] <= player.x <= self.combat_bounds[1]:
            return False
        if abs(player.x - self.x) > (384 if self.can_shoot else 192) or abs(player.feet_y - self.feet_y) > 48:
            return False
        line_y = min(self.feet_y + BODY_HEIGHT / 2, player.feet_y + 46)
        left, right = sorted((self.x, player.x))
        return not any(s.left < right and s.right > left and s.bottom < line_y < s.top
                       for s in self.solids)

    def _reach_box(self):
        # 몸이 겹쳐도 앞쪽 팔의 타격에는 맞는다. 몸 접촉 자체로는 피해를 주지 않는다.
        return front_box(self.x, self.face_dir, -4, BODY_WIDTH / 2 + 32,
                         self.feet_y + 10, self.feet_y + 58, self.solids)

    def _enter(self, state):
        self.state = state
        self.state_time = 0.0
        self.is_moving = False

    def get_attack_box(self):
        return self._reach_box() if self.state == 'STRIKE' else None

    def consume_attack(self):
        attack = self.attack_event
        self.attack_event = None
        return attack

    def clear_projectiles(self):
        self.bolts.clear()
        self.shot_event = None

    def launch_pending_shot(self):
        if self.alive and self.shot_event is not None:
            self.bolts.append(ShadowBolt.aimed(*self.shot_event))
        self.shot_event = None

    def take_damage(self, direction=None, heavy=False, point=None):
        if not self.alive:
            return False
        pose = self.animation_frame
        self.health -= 1
        self.hurt_duration = 0.26 if heavy else 0.22
        self.hurt_time = self.hurt_duration
        self.hit_direction = direction if direction is not None else -self.face_dir
        self.reaction_heavy = heavy
        self.death_by_hit = not self.alive
        if direction is not None:
            self.impact = Impact(*(point or (self.x, self.feet_y + 44)),
                                 direction, heavy=heavy, lethal=not self.alive)
            self.hit_pause.trigger(self.impact.hitstop)
        if not self.alive:
            self.death_pose = pose
            self.attack_event = None
            self.shot_event = None
            self._enter('DYING')
        return True

    def receive_flash(self, direction, point=None):
        if not self.take_damage(direction=direction, heavy=True, point=point):
            return False
        self.attack_event = None
        self.shot_event = None
        self.shot_target = None
        self.hit_pause.reset()
        self.apply_knockback(direction, FLASH_KNOCKBACK)
        if self.alive:
            self.stun_remaining = FLASH_STUN
            self._enter('STUNNED')
        return True

    def reset(self):
        self.stun_remaining = 0.0
        self.clear_projectiles()
        self.shot_cooldown = 0.0
        self.shot_target = None
        self.hit_pause.reset()
        self.impact = None
        self.motion.x, self.motion.feet_y = self.spawn_position
        self.motion.velocity_y = 0
        self.motion.on_ground = True
        self.health = 2
        self.face_dir = -1
        self.walk_distance = 0.0
        self.attack_event = None
        self.hurt_time = 0.0
        self.reaction_heavy = False
        self.death_by_hit = False
        self.retreat_retry = 0.0
        self.death_pose = 0
        self.retreat_light = None
        self.retreat_direction = 0
        self.active_light = None
        self.knockback_remaining = 0.0
        self.knockback_direction = 1
        self._enter('PATROL')

    def dissolve(self):
        self.clear_projectiles()
        self.stun_remaining = 0.0
        if not self.alive:
            return False
        self.death_pose = self.animation_frame
        self.hit_pause.reset()
        self.impact = None
        self.death_by_hit = False
        self.hurt_time = 0.0
        self.health = 0
        self.attack_event = None
        self.knockback_remaining = 0.0
        self._enter('DYING')
        return True

    def apply_knockback(self, direction, distance=32):
        self.knockback_direction = 1 if direction > 0 else -1
        self.knockback_remaining = distance

    def _update_knockback(self, delta_time):
        if self.knockback_remaining <= EPSILON:
            return False
        distance = min(self.knockback_remaining, 240 * delta_time)
        moved = 0.0
        while distance > EPSILON:
            step = min(2, distance)
            next_x = self.x + step * self.knockback_direction
            if not self._can_move_to(next_x, self.knockback_direction):
                self.knockback_remaining = 0.0
                break
            self.motion.x = next_x
            self.knockback_remaining = max(0.0, self.knockback_remaining - step)
            moved += step
            distance -= step
        self.is_moving = False
        return moved > 0

    def _can_move_to(self, x, direction):
        if not (self.combat_bounds[0] + BODY_WIDTH / 2 <= x
                <= self.combat_bounds[1] - BODY_WIDTH / 2):
            return False
        box = (x - BODY_WIDTH / 2, self.feet_y, x + BODY_WIDTH / 2, self.feet_y + BODY_HEIGHT)
        if any(overlaps(box, (s.left, s.bottom, s.right, s.top)) for s in self.solids):
            return False
        probe = x + direction * (BODY_WIDTH / 2 + 2)
        return any(s.left <= probe <= s.right and abs(s.top - self.feet_y) < EPSILON
                   for s in self.solids)

    def _choose_retreat_direction(self, light):
        candidates = []
        for direction in (-1, 1):
            for distance in range(4, int(self.combat_bounds[1] - self.combat_bounds[0]) + 4, 4):
                x = self.x + direction * distance
                if not self._can_move_to(x, direction):
                    break
                box = (x - BODY_WIDTH / 2, self.feet_y,
                       x + BODY_WIDTH / 2, self.feet_y + BODY_HEIGHT)
                if not light.illuminates(box):
                    candidates.append((distance, direction))
                    break
        if candidates:
            return min(candidates, key=lambda item: item[0])[1]
        return 1 if self.x >= light.x else -1

    def _update_light_response(self, delta_time, player, stage, light):
        if light is None or not light.active:
            self.retreat_light = None
            if self.state in LIGHT_STATES:
                self._enter('CHASE')
            return False
        # 새 조명을 설치하면 이전 조명에서 기다리던 상태를 그대로 옮기지 않는다.
        if light is not self.retreat_light and self.state in LIGHT_STATES:
            self._enter('CHASE')
            self.retreat_retry = 0.0
        if light.illuminates(self.get_bb()):
            if light is not self.retreat_light or self.state not in ('RETREAT', 'LIGHT_WAIT'):
                self.retreat_light = light
                self.retreat_direction = self._choose_retreat_direction(light)
                self._enter('RETREAT')
            elif self.state == 'LIGHT_WAIT' and self.retreat_retry <= 0:
                # 밝은 곳의 대기는 탈출 성공이 아니다. 밀림·지형 변화 후에도 다시 후퇴한다.
                self.retreat_direction = self._choose_retreat_direction(light)
                self._enter('RETREAT')
            self.attack_event = None
            if self.state == 'RETREAT':
                self.face_dir = -self.retreat_direction
                if delta_time <= 0:
                    return True
                moved = self._move(delta_time, self.retreat_direction, 80, stage)
                if not moved:
                    self._enter('LIGHT_WAIT')
                    self.retreat_retry = 0.15
                elif not light.illuminates(self.get_bb()):
                    self._enter('DARK_PATROL')
                    self.face_dir = self.retreat_direction
                    self.is_moving = True
            return True
        sees_player = self.can_see(player)
        path_is_lit = light.illuminates((min(self.x, player.x) - BODY_WIDTH / 2,
                                        self.feet_y,
                                        max(self.x, player.x) + BODY_WIDTH / 2,
                                        self.feet_y + BODY_HEIGHT))
        safe_target = sees_player and not light.illuminates(player.get_bb()) and not path_is_lit
        dark_patrol = self.state in LIGHT_STATES and light is self.retreat_light
        if not safe_target and (dark_patrol or (sees_player and path_is_lit)):
            if self.state != 'DARK_PATROL':
                self._enter('DARK_PATROL')
                self.face_dir = 1 if self.x >= light.x else -1
            self.retreat_light = light
            self.attack_event = None
            self._patrol(delta_time, stage)
            return True
        if self.state in LIGHT_STATES:
            self._enter('CHASE')
        return False

    def _light_blocks_move(self, next_x):
        light = self.active_light
        if light is None or not light.active or self.state == 'RETREAT':
            return False
        box = (next_x - BODY_WIDTH / 2, self.feet_y,
               next_x + BODY_WIDTH / 2, self.feet_y + BODY_HEIGHT)
        return light.illuminates(box)

    def _move(self, delta_time, direction, speed, stage):
        old_x = self.x
        next_x = self.x + direction * speed * delta_time
        if direction and self._light_blocks_move(next_x):
            return False
        if direction and not self._can_move_to(next_x, direction):
            direction = 0
        self.motion.step(delta_time, direction, self.solids, stage.width,
                         edge_margin=BODY_WIDTH / 2, speed=speed)
        distance = abs(self.x - old_x)
        self.is_moving = distance > EPSILON
        self.walk_distance += distance
        return self.is_moving

    def _patrol(self, delta_time, stage):
        if self.x <= self.patrol_bounds[0]:
            self.face_dir = 1
        elif self.x >= self.patrol_bounds[1]:
            self.face_dir = -1
        if delta_time <= 0:
            self.is_moving = False
            return
        if not self._move(delta_time, self.face_dir, 48, stage):
            self.face_dir *= -1
            # 경계에서 한 프레임씩 멈추지 않고 같은 프레임에 반대 방향으로 걸음을 잇는다.
            self._move(delta_time, self.face_dir, 48, stage)

    def update(self, delta_time, player, stage, light=None):
        self.solids = stage.solids
        self.active_light = light
        self.attack_event = None
        self.shot_event = None
        was_stunned = self.stun_remaining > 0
        self.stun_remaining = max(0.0, self.stun_remaining - delta_time)
        self.retreat_retry = max(0.0, self.retreat_retry - delta_time)
        if self.impact is not None:
            self.impact.update(delta_time)
            if not self.impact.active:
                self.impact = None
        if self.alive and not was_stunned and light is not None and light.illuminates(self.get_bb()):
            # 조명은 짧은 피격 정지보다 우선한다. 공격을 접고 즉시 빛에서 이탈한다.
            self.hit_pause.reset()
            self.knockback_remaining = 0.0
        was_frozen = self.hit_pause.remaining > 0
        delta_time = self.hit_pause.consume(delta_time)
        if was_frozen and delta_time <= 0:
            return
        self.state_time += delta_time
        self.shot_cooldown = max(0.0, self.shot_cooldown - delta_time)
        self.hurt_time = max(0.0, self.hurt_time - delta_time)
        pushed = self._update_knockback(delta_time)
        if not self.alive:
            self.is_moving = False
            if self.state != 'DEAD' and self.state_time >= DEATH_TIME:
                self._enter('DEAD')
            return
        if was_stunned:
            self.attack_event = None
            self.shot_event = None
            self.is_moving = False
            if self.stun_remaining <= 0:
                self._enter('CHASE')
            return
        if self._update_light_response(delta_time, player, stage, light):
            return
        if self.state in ('RANGED_WINDUP', 'RANGED_RELEASE'):
            self.is_moving = False
            if not self.combat_bounds[0] <= player.x <= self.combat_bounds[1]:
                self._enter('PATROL')
            elif self.state == 'RANGED_WINDUP' and self.state_time >= RANGED_WINDUP:
                origin = (self.x + self.face_dir * 30, self.feet_y + 44)
                self.shot_event = (origin, self.shot_target)
                self.shot_cooldown = RANGED_COOLDOWN
                self._enter('RANGED_RELEASE')
            elif self.state == 'RANGED_RELEASE' and self.state_time >= RANGED_RELEASE:
                self._enter('RECOVER')
            return
        if self.state in ('WINDUP', 'STRIKE', 'RECOVER'):
            self.is_moving = False
            if not self.combat_bounds[0] <= player.x <= self.combat_bounds[1]:
                self._enter('PATROL')
            elif self.state == 'WINDUP' and self.state_time >= WINDUP_TIME:
                if overlaps(self._reach_box(), player.get_bb()):
                    self._enter('STRIKE')
                    self.attack_event = self._reach_box()
                else:
                    self._enter('CHASE')
            elif self.state == 'STRIKE' and self.state_time >= STRIKE_TIME:
                self._enter('RECOVER')
            elif self.state == 'RECOVER' and self.state_time >= RECOVER_TIME:
                self._enter('CHASE')
            return
        if pushed:
            return
        if self.can_see(player):
            self.state = 'CHASE'
            if abs(player.x - self.x) > 1:
                self.face_dir = 1 if player.x > self.x else -1
            distance = abs(player.x - self.x)
            if (self.can_shoot and 112 <= distance <= 352 and self.shot_cooldown <= 0
                    and not any(bolt.active for bolt in self.bolts)):
                self.shot_target = (player.x, player.feet_y + 40)
                self._enter('RANGED_WINDUP')
            elif overlaps(self._reach_box(), player.get_bb()):
                self._enter('WINDUP')
            else:
                self._move(delta_time, self.face_dir, 80, stage)
        else:
            self.state = 'PATROL'
            self._patrol(delta_time, stage)

    def draw(self, camera_x=0):
        if self.state == 'DEAD':
            return
        opacity = 1.0
        if self.state == 'DYING':
            fade_start = 0.26 if self.death_by_hit else 0
            opacity = max(0.0, min(1.0, (DEATH_TIME - self.state_time) / (DEATH_TIME - fade_start)))
        reaction = self.reaction_frame
        data, image = self.motion_data, self.image
        ranged_frame = None
        if self.ranged_data is not None:
            if self.state == 'RANGED_WINDUP':
                ranged_frame = min(2, int(self.state_time / (RANGED_WINDUP / 3)))
            elif self.state == 'RANGED_RELEASE':
                ranged_frame = 3 + min(2, int(self.state_time / (RANGED_RELEASE / 3)))
        if ranged_frame is not None:
            data, image = self.ranged_data, self.ranged_image
        facing, recoil_x = self.face_dir, 0
        if reaction is not None:
            data, image = self.reaction_data, self.reaction_image
            facing = -self.hit_direction
            if self.alive:
                recoil_x = self.hit_direction * (6 if self.reaction_heavy else 3) * (
                    self.hurt_time / self.hurt_duration) ** 2
        frame_index = reaction if reaction is not None else ranged_frame if ranged_frame is not None else self.animation_frame
        frame = data['frames'][frame_index]
        left, bottom, width, height = frame['rect']
        feet_x, feet_y = frame['feet']
        from math import sin
        breathing = sin(self.state_time * 2.8) * 0.9 if self.state == 'LIGHT_WAIT' else 0
        scale = (DRAW_HEIGHT + breathing) / data['reference_height']
        # 원본 동작은 왼쪽을 본다. 반전해도 각 프레임의 발 기준은 유지한다.
        image.opacify(opacity)
        image.clip_composite_draw(
            left, bottom, width, height, 0, 'h' if facing > 0 else '',
            self.x - camera_x + recoil_x + (width / 2 - feet_x) * scale * -facing,
            self.feet_y + (height / 2 - feet_y) * scale, width * scale, height * scale,
        )
        image.opacify(1.0)
        if not self.alive:
            return
        for index in range(2):
            left = self.x - camera_x - 12 + index * 13
            color = (202, 91, 214) if index < self.health else (69, 57, 78)
            pico2d.draw_rectangle(left, self.feet_y + 112, left + 10,
                                  self.feet_y + 116, *color, filled=True)
        if self.state == 'WINDUP':
            left = self.x - camera_x - 12
            top = self.feet_y + 124
            pico2d.draw_rectangle(left, top - 3, left + 24, top,
                                  66, 38, 63, filled=True)
            pico2d.draw_rectangle(left, top - 3, left + 24 * self.state_time / WINDUP_TIME,
                                  top, 255, 108, 160, filled=True)
        if self.can_shoot:
            pico2d.draw_circle(self.x - camera_x + 21, self.feet_y + 114, 3,
                               192, 107, 242, filled=True)
        if self.stun_remaining > 0:
            from math import cos, sin
            from effects import blended, glow
            with blended():
                for index in range(3):
                    angle = self.state_time * 6 + index * 2.094
                    sx = self.x - camera_x + cos(angle) * 14
                    sy = self.feet_y + 104 + sin(angle) * 5
                    glow(sx, sy, 5, (255, 227, 154), alpha=125)
                    pico2d.draw_circle(sx, sy, 2, 255, 240, 184, filled=True)
            pico2d.draw_rectangle(self.x - camera_x - 14, self.feet_y + 123,
                                  self.x - camera_x + 14, self.feet_y + 126, 67, 60, 49, filled=True)
            pico2d.draw_rectangle(self.x - camera_x - 14, self.feet_y + 123,
                                  self.x - camera_x - 14 + 28 * self.stun_remaining / FLASH_STUN,
                                  self.feet_y + 126, 255, 220, 133, filled=True)
        if self.state == 'RANGED_WINDUP' and self.shot_target is not None:
            from effects import blended, glow, segment
            origin = (self.x - camera_x + self.face_dir * 30, self.feet_y + 44)
            target = (self.shot_target[0] - camera_x, self.shot_target[1])
            progress = min(1, self.state_time / RANGED_WINDUP)
            with blended():
                for index in range(0, 16, 2):
                    a, b = index / 16, (index + 1) / 16
                    pico2d.draw_line(origin[0] + (target[0] - origin[0]) * a,
                                      origin[1] + (target[1] - origin[1]) * a,
                                      origin[0] + (target[0] - origin[0]) * b,
                                      origin[1] + (target[1] - origin[1]) * b,
                                      221, 103, 231, a=int(60 + progress * 90))
                glow(origin[0] - self.face_dir * 48, self.feet_y + 58,
                     9 + progress * 7, (201, 88, 244), alpha=150)
                for direction in (-1, 1):
                    segment((target[0] + direction * 7, target[1] - 6),
                            (target[0] + direction * 7, target[1] + 6), (231, 126, 242), 2)

    def draw_debug(self, camera_x=0):
        if not self.alive:
            return
        left, bottom, right, top = self.get_bb()
        pico2d.draw_rectangle(left - camera_x, bottom, right - camera_x, top,
                              r=195, g=119, b=230)
        attack = self.get_attack_box()
        if attack is not None:
            left, bottom, right, top = attack
            pico2d.draw_rectangle(left - camera_x, bottom, right - camera_x, top,
                                  r=255, g=100, b=140)

    def draw_effects(self, camera_x=0):
        for bolt in self.bolts:
            bolt.draw(camera_x)
        if self.impact is not None:
            self.impact.draw(camera_x)
