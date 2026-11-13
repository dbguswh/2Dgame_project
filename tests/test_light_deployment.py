import unittest
from unittest.mock import Mock, patch

import pico2d

from lighting import LightRegion, PortableLight
from player import Player


def tap(player, keycode):
    for kind in (pico2d.SDL_KEYDOWN, pico2d.SDL_KEYUP):
        event = pico2d.Event(kind)
        event.key = keycode
        player.handle_event(event)


class LightDeploymentTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pico2d.load_image', side_effect=lambda path: Mock())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = Player(400, 96)

    def test_air_install_is_rejected_without_cost_or_delayed_auto_install(self):
        tap(self.player, pico2d.SDLK_SPACE)
        self.player.update(0.05, 960)
        tap(self.player, pico2d.SDLK_r)
        self.player.update(0.01, 960)
        self.assertIsNone(self.player.light)
        self.assertEqual(self.player.battery, 100)
        self.assertGreater(self.player.notice_time, 0)
        for _ in range(90):
            self.player.update(1 / 120, 960)
        self.assertTrue(self.player.motion.on_ground)
        self.assertIsNone(self.player.light)
        tap(self.player, pico2d.SDLK_r)
        self.player.update(0.01, 960)
        self.assertIsNotNone(self.player.light)
        self.assertEqual(self.player.battery, 50)

    def test_air_reinstall_keeps_existing_light_and_energy(self):
        tap(self.player, pico2d.SDLK_r)
        self.player.update(0.01, 960)
        old = self.player.light
        for _ in range(30):
            self.player.update(1 / 120, 960)
        tap(self.player, pico2d.SDLK_SPACE)
        self.player.update(0.05, 960)
        tap(self.player, pico2d.SDLK_r)
        self.player.update(0.01, 960)
        self.assertIs(self.player.light, old)
        self.assertEqual(self.player.battery, 50)

    def test_install_uses_three_poses_with_constant_body_and_shared_art(self):
        tap(self.player, pico2d.SDLK_r)
        self.player.update(0, 960)
        body = self.player.get_bb()
        self.assertIs(self.player.light.art, self.player.light_deploy_image)
        sources = []
        for elapsed in (0, 0.07, 0.13):
            self.player.light_cast = 0.18 - elapsed
            self.assertEqual(self.player.animation_state, 'light_cast')
            self.player.draw()
            args = self.player.light_deploy_image.clip_composite_draw.call_args.args
            sources.append(args[0])
            self.assertEqual(self.player.get_bb(), body)
        self.assertEqual(len(set(sources)), 3)

    def test_ignition_warning_and_shutdown_do_not_change_protection_radius(self):
        light = PortableLight(400, 120, LightRegion(0, 96, 960, 540))
        inside, outside = (464, 120, 480, 150), (465, 120, 481, 150)
        initial = light.visual_strength
        self.assertGreater(initial, 0)
        for elapsed in (0, 0.1, 0.3, 6.5, 7.9):
            light.remaining = 8 - elapsed
            self.assertTrue(light.illuminates(inside))
            self.assertFalse(light.illuminates(outside))
            self.assertGreater(light.visual_strength, 0)
        light.remaining = 0
        self.assertEqual(light.visual_strength, 0)
        self.assertFalse(light.illuminates(inside))

    def test_device_opens_in_order_without_restarting_on_zero_time(self):
        light = PortableLight(400, 120, LightRegion(0, 96, 960, 540))
        frames = []
        for _ in range(30):
            frames.append(light.device_frame)
            light.update(1 / 120)
        self.assertEqual(set(frames), {0, 1, 2})
        age = light.age
        light.update(0)
        self.assertEqual(light.age, age)
        self.assertEqual(light.device_frame, 2)
