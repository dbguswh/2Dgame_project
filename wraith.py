"""선회·고정 경로 급강하·낮은 회복을 반복하는 비행 침입자."""

from math import hypot,sin
from enemy import Shade
from physics import Motion
from combat import overlaps
from light_bomb import blocked_segment


class Wraith(Shade):
    kind='wraith'

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.motion.width,self.motion.height=48,48
        self.home_y=self.spawn_position[1]+112
        self.motion.feet_y=self.home_y
        self.clock=0
        self.dive_target=None
        self.dive_hit=False
        self.dive_cooldown=1.2
        self.state='FLY_PATROL'
        self.can_shoot=False

    def reset(self):
        super().reset()
        self.motion.feet_y=self.home_y
        self.state='FLY_PATROL'
        self.clock=0
        self.dive_target=None
        self.dive_hit=False
        self.dive_cooldown=1.2

    def _free(self,x,y):
        box=(x-24,y,x+24,y+48)
        return not any(overlaps(box,(s.left,s.bottom,s.right,s.top)) for s in self.solids)

    def _fly(self,target,speed,dt):
        length=hypot(target[0]-self.x,target[1]-self.feet_y)
        if length<1:self.is_moving=False;return True
        distance=min(length,speed*max(0,dt));steps=max(1,int(distance/2)+1)
        dx=(target[0]-self.x)/length*distance/steps;dy=(target[1]-self.feet_y)/length*distance/steps
        moved=False
        for _ in range(steps):
            nx=max(self.combat_bounds[0]+24,min(self.combat_bounds[1]-24,self.x+dx))
            ny=max(self.spawn_position[1]+8,min(430,self.feet_y+dy))
            if (self.state!='RETREAT' and self.active_light is not None
                    and self.active_light.illuminates((nx-24,ny,nx+24,ny+48))):
                self.is_moving=moved
                return False
            if self._free(nx,ny):
                moved=moved or abs(nx-self.x)+abs(ny-self.feet_y)>1e-6
                self.motion.x,self.motion.feet_y=nx,ny
            elif self.state=='DIVE':
                self.is_moving=False;return False
            elif self._free(self.x,ny):self.motion.feet_y=ny;moved=True
            elif self._free(nx,self.feet_y):self.motion.x=nx;moved=True
            else:break
        self.is_moving=moved
        return moved

    def mark_attack_contact(self):
        self.dive_hit=True

    def get_attack_box(self):
        return self.get_bb() if self.state=='DIVE' and not self.dive_hit else None

    def update(self,dt,player,stage,light=None):
        self.solids=stage.solids;self.active_light=light
        self.attack_event=self.shot_event=None
        self.clock+=max(0,dt)
        self.state_time+=max(0,dt)
        self.hurt_time=max(0,self.hurt_time-dt)
        self.dive_cooldown=max(0,self.dive_cooldown-dt)
        if self.impact is not None:
            self.impact.update(dt)
            if not self.impact.active:self.impact=None
        if not self.alive:
            if self.state_time>=.8:self.state='DEAD'
            return
        if light is not None and light.illuminates(self.get_bb()):
            self._enter('RETREAT') if self.state!='RETREAT' else None
            self.dive_target=None;self.dive_cooldown=1.5
            candidates=[]
            for x in (self.combat_bounds[0]+28,self.combat_bounds[1]-28,self.x):
                for y in (self.home_y,self.home_y+80,min(420,self.home_y+160)):
                    if self._free(x,y) and not light.illuminates((x-24,y,x+24,y+48)):
                        candidates.append((hypot(x-self.x,y-self.feet_y),(x,y)))
            goal=min(candidates,key=lambda v:v[0])[1] if candidates else (
                self.combat_bounds[0]+28 if self.x<light.x else self.combat_bounds[1]-28,self.home_y)
            self._fly(goal,190,dt)
            return
        if self.stun_remaining>0:
            self.stun_remaining=max(0,self.stun_remaining-dt)
            self._enter('STUNNED') if self.state!='STUNNED' else None
            return
        if self.state in ('STUNNED','RETREAT'):
            self._enter('FLY_PATROL');self.dive_cooldown=1.0
        if self.state=='DIVE_WINDUP':
            if self.state_time>=.75:
                self._enter('DIVE');self.dive_hit=False
            return
        if self.state=='DIVE':
            if (self.state_time>=.5 or self.dive_target is None
                    or not self._fly(self.dive_target,460,dt)):
                self._enter('RECOVER')
                return
            self.attack_event=self.get_attack_box()
            return
        if self.state=='RECOVER':
            if self.state_time>=1:
                self._enter('FLY_PATROL');self.dive_cooldown=1.6
            return
        # 빛을 가로질러 플레이어에게 진입하지 않는다.
        left,right=self.combat_bounds
        target=(player.x,player.feet_y+10)
        clear=not blocked_segment((self.x,self.feet_y+24),(target[0],target[1]+24),self.solids)
        path_lit=(light is not None and light.active and
                  light.illuminates((min(self.x,player.x)-24,min(self.feet_y,player.feet_y),
                                     max(self.x,player.x)+24,max(self.feet_y+48,player.feet_y+88))))
        if (left<=player.x<=right and abs(player.x-self.x)<384 and clear and not path_lit
                and self.dive_cooldown<=0 and self.feet_y>player.feet_y+50):
            self.face_dir=1 if player.x>self.x else -1
            self.dive_target=target;self._enter('DIVE_WINDUP');return
        target_x=left+40 if self.face_dir<0 else right-40
        if abs(self.x-target_x)<5:self.face_dir*=-1
        y=self.home_y+sin(self.clock*2.2)*10
        if light is not None and light.active and light.illuminates((target_x-24,y,target_x+24,y+48)):
            target_x=left+40 if self.x<light.x else right-40
            y=max(self.feet_y,y)
        self._fly((target_x,y),65,dt)

    def draw(self,camera_x=0,signals=True):
        if self.state=='DEAD':return
        from enemy_art import draw_enemy
        frame=5 if not self.alive or self.hurt_time>0 else 4 if self.state=='DIVE' else 3 if self.state=='DIVE_WINDUP' else int(self.clock*7)%3
        draw_enemy(self,'wraith',frame,camera_x)
        if signals:self.draw_signals(camera_x)

    def draw_signals(self,camera_x=0,show_health=True):
        if not self.alive:return
        import pico2d
        from effects import blended,glow
        if show_health:
            for i in range(2):
                pico2d.draw_rectangle(self.x-camera_x-14+i*16,self.feet_y+78,
                                      self.x-camera_x-2+i*16,self.feet_y+82,
                                      *((189,122,238) if i<self.health else (52,39,65)),filled=True)
        if self.state=='DIVE_WINDUP' and self.dive_target:
            tx,ty=self.dive_target
            with blended():
                for i in range(0,20,2):
                    a,b=i/20,(i+1)/20
                    pico2d.draw_line(self.x-camera_x+(tx-self.x)*a,self.feet_y+24+(ty-self.feet_y)*a,
                                      self.x-camera_x+(tx-self.x)*b,self.feet_y+24+(ty-self.feet_y)*b,
                                      232,121,248,a=170)
                glow(tx-camera_x,ty,18,(207,91,240),alpha=95)
