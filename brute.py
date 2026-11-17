"""정면 무기를 막고 후방·회복·제압 중 노출되는 갑각형 침입자."""

from enemy import Shade
from combat_balance import BRUTE_HEALTH


class Brute(Shade):
    kind='brute'
    MAX_HEALTH=BRUTE_HEALTH

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.block_flash=0.0

    def reset(self):
        super().reset()
        self.block_flash=0

    @property
    def guarding(self):
        return self.alive and self.state not in ('RECOVER','STUNNED','RETREAT','LIGHT_WAIT','DARK_PATROL')

    def receive_weapon(self,direction,point,kind='sword',heavy=False):
        if self.guarding and direction==-self.face_dir:
            self.block_flash=.2
            return False
        return super().receive_weapon(direction,point,kind,heavy)

    def update(self,dt,*args,**kwargs):
        self.block_flash=max(0,self.block_flash-dt)
        super().update(dt,*args,**kwargs)

    def draw(self,camera_x=0,signals=True):
        if self.state=='DEAD':return
        from enemy_art import draw_enemy
        if self.state in ('STRIKE','LUNGE'):frame=5
        elif self.state in ('WINDUP','LUNGE_WINDUP','RANGED_WINDUP'):frame=4
        elif self.block_flash>0 or self.hurt_time>0:frame=3
        elif self.is_moving:frame=1+int(self.walk_distance/18)%2
        else:frame=0
        draw_enemy(self,'brute',frame,camera_x)
        if signals:self.draw_signals(camera_x)

    def draw_signals(self,camera_x=0,show_health=True):
        # 공격 예고·제압은 공유하고 갑각형도 최대치에 대한 연속 게이지를 쓴다.
        super().draw_signals(camera_x,show_health=False)
        if not self.alive:return
        import pico2d
        from effects import blended,glow
        if show_health:
            from enemy_health import draw_health
            draw_health(self,camera_x,offset=115,color=(225,179,98),width=48)
        if self.block_flash>0:
            with blended():
                glow(self.x-camera_x+self.face_dir*25,self.feet_y+48,24,(255,214,130),alpha=180)
