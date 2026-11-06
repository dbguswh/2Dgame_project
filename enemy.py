"""Shade의 위치·이미지와 전투 상태를 관리한다."""

from pathlib import Path
import json

import pico2d

from physics import EPSILON, Motion
from combat import front_box, overlaps


IMAGE_PATH = Path(__file__).resolve().parent / 'assets/images/characters/shade.png'
MOTION_DATA_PATH = IMAGE_PATH.with_name('shade_motion.json')
DRAW_HEIGHT = 104
BODY_WIDTH = 48
BODY_HEIGHT = 88
WINDUP_TIME = 0.7
STRIKE_TIME = 0.18
RECOVER_TIME = 1.0 - STRIKE_TIME
DEATH_TIME = 0.8


class Shade:
    def __init__(self, x, feet_y, identity=0, combat_bounds=(288, 544)):
        self.identity = identity
        self.motion = Motion(x, feet_y, BODY_WIDTH, BODY_HEIGHT)
        self.motion_data = json.loads(MOTION_DATA_PATH.read_text(encoding='utf-8'))
        self.image = pico2d.load_image(str(MOTION_DATA_PATH.with_name(self.motion_data['image'])))
        self.face_dir = -1
        self.health = 2
        self.spawn_position = (x, feet_y)
        self.combat_bounds = combat_bounds
        self.patrol_bounds = (x - 28, x + 16)
        self.state = 'PATROL'
        self.is_moving = False
        self.walk_distance = 0.0
        self.solids = []
        self.state_time = 0.0
        self.attack_event = None
        self.hurt_time = 0.0
        self.death_pose = 0

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
        if self.state == 'WINDUP':
            return self.motion_data['windup']
        if self.state == 'STRIKE':
            return self.motion_data['strike']
        if self.is_moving:
            phase = int(self.walk_distance / self.motion_data['cycle_distance'] * 4) % 4
            return self.motion_data['walk'][phase]
        return self.motion_data['walk'][0]

    def get_bb(self):
        return self.motion.get_bb()

    def can_see(self, player):
        if not self.combat_bounds[0] <= player.x <= self.combat_bounds[1]:
            return False
        if abs(player.x - self.x) > 192 or abs(player.feet_y - self.feet_y) > 48:
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

    def take_damage(self):
        if not self.alive:
            return False
        pose = self.animation_frame
        self.health -= 1
        self.hurt_time = 0.18
        if not self.alive:
            self.death_pose = pose
            self.attack_event = None
            self._enter('DYING')
        return True

    def reset(self):
        self.motion.x, self.motion.feet_y = self.spawn_position
        self.motion.velocity_y = 0
        self.motion.on_ground = True
        self.health = 2
        self.face_dir = -1
        self.walk_distance = 0.0
        self.attack_event = None
        self.hurt_time = 0.0
        self.death_pose = 0
        self._enter('PATROL')

    def _move(self, delta_time, direction, speed, stage):
        old_x = self.x
        probe = self.x + direction * (BODY_WIDTH / 2 + 2 + speed * delta_time)
        has_floor = any(s.left <= probe <= s.right and abs(s.top - self.feet_y) < EPSILON
                        for s in self.solids)
        next_x = self.x + direction * speed * delta_time
        inside = (self.combat_bounds[0] + BODY_WIDTH / 2 <= next_x
                  <= self.combat_bounds[1] - BODY_WIDTH / 2)
        if not has_floor or not inside:
            direction = 0
        self.motion.step(delta_time, direction, self.solids, stage.width,
                         edge_margin=BODY_WIDTH / 2, speed=speed)
        distance = abs(self.x - old_x)
        self.is_moving = distance > EPSILON
        self.walk_distance += distance
        return self.is_moving

    def update(self, delta_time, player, stage):
        self.solids = stage.solids
        self.attack_event = None
        self.state_time += delta_time
        self.hurt_time = max(0.0, self.hurt_time - delta_time)
        if not self.alive:
            self.is_moving = False
            if self.state != 'DEAD' and self.state_time >= DEATH_TIME:
                self._enter('DEAD')
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
        if self.can_see(player):
            self.state = 'CHASE'
            if abs(player.x - self.x) > 1:
                self.face_dir = 1 if player.x > self.x else -1
            if overlaps(self._reach_box(), player.get_bb()):
                self._enter('WINDUP')
            else:
                self._move(delta_time, self.face_dir, 80, stage)
        else:
            self.state = 'PATROL'
            if self.x <= self.patrol_bounds[0]:
                self.face_dir = 1
            elif self.x >= self.patrol_bounds[1]:
                self.face_dir = -1
            if not self._move(delta_time, self.face_dir, 48, stage):
                self.face_dir *= -1

    def draw(self, camera_x=0):
        if self.state == 'DEAD':
            return
        opacity = 1.0
        if self.state == 'DYING':
            opacity = max(0.0, 1 - self.state_time / DEATH_TIME)
        elif self.hurt_time > 0:
            opacity = 0.35 if int(self.hurt_time * 40) % 2 else 1.0
        frame = self.motion_data['frames'][self.animation_frame]
        left, bottom, width, height = frame['rect']
        feet_x, feet_y = frame['feet']
        scale = DRAW_HEIGHT / self.motion_data['reference_height']
        # 원본 동작은 왼쪽을 본다. 반전해도 각 프레임의 발 기준은 유지한다.
        self.image.opacify(opacity)
        self.image.clip_composite_draw(
            left, bottom, width, height, 0, 'h' if self.face_dir > 0 else '',
            self.x - camera_x + (width / 2 - feet_x) * scale * -self.face_dir,
            self.feet_y + (height / 2 - feet_y) * scale, width * scale, height * scale,
        )
        self.image.opacify(1.0)
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
