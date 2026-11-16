from enemy import Shade
from brute import Brute
from wraith import Wraith


def create_enemy(placement):
    actor={'shade':Shade,'brute':Brute,'wraith':Wraith}[placement.kind]
    return actor(placement.x,placement.feet_y,identity=placement.identity,
                 combat_bounds=placement.bounds,can_shoot=placement.ranged)
