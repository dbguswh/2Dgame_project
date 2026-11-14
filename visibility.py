"""월드만 어둡게 하고 시야·강한 조명·영구 복구를 구분한다. 전투 판정은 만들지 않는다."""

from ctypes import byref, c_uint8
from math import ceil, sqrt

import pico2d
from pico2d import pico2d as canvas
import sdl2

from effects import blended, glow


GRID_STEP = 8
DARK_ALPHA = 218
POWER_FADE_TIME = 1.2
_texture = None
_renderer = None
_size = None


class DarknessField:
    def __init__(self, width, height, alpha=DARK_ALPHA):
        self.width, self.height = width, height
        self.cols, self.rows = ceil(width / GRID_STEP), ceil(height / GRID_STEP)
        self.alpha = max(0, min(255, round(alpha)))
        self.values = bytearray([self.alpha]) * (self.cols * self.rows)

    def reveal(self, x, y, rx, ry, strength, region=None):
        if rx <= 0 or ry <= 0 or strength <= 0:
            return
        strength = min(1, strength)
        for row in range(max(0, int((y - ry) // GRID_STEP)),
                         min(self.rows, ceil((y + ry) / GRID_STEP))):
            py = (row + 0.5) * GRID_STEP
            for col in range(max(0, int((x - rx) // GRID_STEP)),
                             min(self.cols, ceil((x + rx) / GRID_STEP))):
                px = (col + 0.5) * GRID_STEP
                if region is not None and not (region[0] <= px <= region[2]
                                                and region[1] <= py <= region[3]):
                    continue
                distance = sqrt(((px - x) / rx) ** 2 + ((py - y) / ry) ** 2)
                if distance >= 1:
                    continue
                t = max(0, (distance - 0.35) / 0.65)
                weight = 1 - t * t * (3 - 2 * t)
                index = row * self.cols + col
                self.values[index] = min(self.values[index], round(self.alpha * (1 - strength * weight)))

    def sample(self, x, y):
        col = min(self.cols - 1, max(0, int(x // GRID_STEP)))
        row = min(self.rows - 1, max(0, int(y // GRID_STEP)))
        return self.values[row * self.cols + col]

    def rgba(self):
        pixels = bytearray(self.cols * self.rows * 4)
        for row in range(self.rows):
            # SDL의 위쪽 원점으로 변환한다. 월드 계산은 아래쪽 원점이다.
            for col in range(self.cols):
                index = ((self.rows - row - 1) * self.cols + col) * 4
                pixels[index:index + 4] = bytes((3, 7, 16, self.values[row * self.cols + col]))
        return pixels


def restoration_progress(stage):
    if not stage.fixture_powered:
        return 0.0
    if hasattr(stage, 'power_restore_elapsed'):
        return min(1, stage.power_restore_elapsed / POWER_FADE_TIME)
    if not hasattr(stage, 'BRIDGE_TIME'):
        return 1.0
    return max(0.0, min(1.0, stage.bridge_elapsed / POWER_FADE_TIME))


def build_field(stage, player, camera_x, width=960, height=540):
    progress = restoration_progress(stage)
    field = DarknessField(width, height, DARK_ALPHA * (1 - progress))
    # 랜턴은 시야만 제공하며 배터리·적 상태를 변경하지 않는다.
    field.reveal(player.x - camera_x + player.face_dir * 14, player.feet_y + 42,
                 144, 136, 0.68)
    start_x, start_y = stage.start
    field.reveal(start_x - camera_x, start_y + 88, 172, 184, 0.78)
    for region in getattr(stage, 'local_light_regions', getattr(stage, 'fixed_light_regions', ())):
        for row in range(field.rows):
            y = (row + .5) * GRID_STEP
            if not region.bottom <= y <= region.top:
                continue
            for col in range(field.cols):
                x = camera_x + (col + .5) * GRID_STEP
                if region.left <= x <= region.right:
                    index = row * field.cols + col
                    field.values[index] = min(field.values[index], round(field.alpha * .16))
    light = player.light
    if light is not None and light.active:
        region = (light.region.left - camera_x, light.region.bottom,
                  light.region.right - camera_x, light.region.top)
        field.reveal(light.x - camera_x, light.y, light.radius, light.radius,
                     0.98 * light.visual_strength, region)
    return field


def clear_resources():
    global _texture, _renderer, _size
    if _texture is not None and _renderer is canvas.renderer:
        sdl2.SDL_DestroyTexture(_texture)
    _texture, _renderer, _size = None, None, None


def draw_darkness(stage, player, camera_x, width=960, height=540):
    global _texture, _renderer, _size
    if restoration_progress(stage) >= 1:
        return
    field = build_field(stage, player, camera_x, width, height)
    size = field.cols, field.rows
    if _texture is None or _renderer is not canvas.renderer or _size != size:
        clear_resources()
        _texture = sdl2.SDL_CreateTexture(canvas.renderer, sdl2.SDL_PIXELFORMAT_RGBA32,
                                         sdl2.SDL_TEXTUREACCESS_STREAMING, *size)
        if not _texture:
            raise RuntimeError('어둠 마스크를 생성할 수 없습니다')
        _renderer, _size = canvas.renderer, size
        sdl2.SDL_SetTextureBlendMode(_texture, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetTextureScaleMode(_texture, sdl2.SDL_ScaleModeLinear)
    pixels = field.rgba()
    buffer = (c_uint8 * len(pixels)).from_buffer(pixels)
    if sdl2.SDL_UpdateTexture(_texture, None, buffer, field.cols * 4) != 0:
        raise RuntimeError('어둠 마스크를 갱신할 수 없습니다')
    target = sdl2.SDL_FRect(0, 0, width, height)
    sdl2.SDL_RenderCopyF(canvas.renderer, _texture, None, byref(target))


def draw_navigation(stage, player, camera_x, width=960):
    """먼 길은 희미한 윤곽만 남기고 공격 예고와 별도로 읽히게 한다."""
    strength = 1 - restoration_progress(stage)
    if strength <= 0:
        return
    with blended():
        for solid in stage.solids:
            if solid.right < camera_x or solid.left > camera_x + width:
                continue
            if getattr(stage, 'bridge_gate', None) is solid:
                continue
            left, right = max(0, solid.left - camera_x), min(width, solid.right - camera_x)
            pico2d.draw_line(left, solid.top, right, solid.top,
                              104, 123, 145, a=int(62 * strength))
            for x in (left, right):
                pico2d.draw_line(x, solid.top, x, solid.top - 5,
                                  117, 134, 151, a=int(80 * strength))
        glow(player.x - camera_x + player.face_dir * 14, player.feet_y + 42,
             28, (255, 194, 104), alpha=45 * strength)


def enemy_is_visible(stage, player, enemy):
    return (stage.fixture_powered or stage.is_temporarily_lit(enemy.get_bb())
            or abs(player.x - enemy.x) < 160
            and abs(player.feet_y - enemy.feet_y) < 112
            or player.light is not None and player.light.illuminates(enemy.get_bb()))
