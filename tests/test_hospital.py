import unittest
from unittest.mock import Mock, patch

from hospital import HospitalStage
from player import Player
from physics import Motion, MOVE_SPEED, RUN_SPEED
from progress import ProgressRecords
from enemy import Shade
from world import update_world, restore_enemies
from inventory import SHIELD


class HospitalTests(unittest.TestCase):
    def setUp(self):
        loader = patch('pico2d.load_image', return_value=Mock())
        loader.start()
        self.addCleanup(loader.stop)
        self.s = HospitalStage()
        self.p = Player(*self.s.start)

    def at(self, x, y=96):
        self.p.x, self.p.feet_y = x, y
        self.p.motion.on_ground = True

    def interact(self, position):
        self.at(*position)
        return self.s.interact(self.p)

    def test_initial_circuit_lights_corridor_but_not_part_rooms(self):
        self.assertEqual(len(self.s.enemy_placements), 8)
        self.assertTrue(self.s.doors['A'].is_open)
        self.assertFalse(self.s.doors['B'].is_open)
        for x, lit in ((192, False), (1200, True), (1920, True), (2600, False), (3712, False)):
            self.at(x)
            self.assertEqual(self.s.is_temporarily_lit(self.p.get_bb()), lit)

    def test_switch_uses_sliding_door_collision_and_return_latch_persists(self):
        self.interact(self.s.latch_positions['A'])
        self.interact(self.s.terminal_position)
        self.assertEqual(self.s.circuit, 'B')
        self.s.update(.3)
        self.assertFalse(self.s.doors['B'].is_open)
        self.assertIn(self.s.doors['B'].solid, self.s.solids)
        self.s.update(.25)
        self.assertTrue(self.s.doors['B'].is_open)
        self.assertTrue(self.s.doors['A'].is_open)
        self.assertNotIn(self.s.doors['B'].solid, self.s.solids)

    def test_either_part_order_requires_both_and_grants_reward_once(self):
        for order in (('A', 'B'), ('B', 'A')):
            self.s = HospitalStage()
            self.p.fragments = 0
            for i, key in enumerate(order):
                x, y = self.s.part_positions[key]
                self.at(x, y-16)
                self.s.collect_pickups(self.p)
                self.assertEqual(self.s.part_count, i+1)
                self.interact(self.s.fixture_position)
                self.assertEqual(self.s.fixture_powered, i == 1)
            self.s.apply_rewards(self.p)
            self.assertEqual(self.p.fragments, 2)
            self.assertFalse(self.s.completed)
            self.interact((2088, 96))
            self.assertFalse(self.s.completed)
            self.s.update(.55)
            self.interact(self.s.exit_position)
            self.assertTrue(self.s.completed)

    def test_fuse_cannot_be_collected_from_ground_and_cache_is_optional(self):
        self.at(192)
        self.s.collect_pickups(self.p)
        self.assertFalse(self.s.parts['A'])
        self.at(704)
        self.assertFalse(self.s.interact(self.p))
        self.at(704, 336)
        self.s.interact(self.p)
        self.s.interact(self.p)
        self.assertEqual(self.p.fragments, 1)
        self.assertEqual(self.s.part_count, 0)

    def test_hub_shield_requires_first_part_and_battery_does_not_waste_at_full(self):
        shield = next(b for b in self.s.supply_boxes if b.item == SHIELD)
        self.interact((shield.x, shield.feet_y))
        self.assertFalse(shield.opened)
        self.s.parts['B'] = True
        self.s.interact(self.p)
        self.assertTrue(shield.opened)
        self.at(1760)
        self.s.collect_pickups(self.p)
        self.assertFalse(self.s.battery_pack_collected)
        self.p.battery = 20
        self.s.collect_pickups(self.p)
        self.assertEqual(self.p.battery, 70)
        self.s.collect_pickups(self.p)
        self.assertEqual(self.p.battery, 70)

    def test_latest_restore_keeps_parts_latches_cache_and_spent_battery(self):
        records = ProgressRecords(self.p, self.s)
        self.s.parts['A'] = True
        self.interact(self.s.latch_positions['A'])
        self.interact(self.s.terminal_position)
        self.interact((704, 336))
        self.p.battery = 0
        records.remember(self.p, self.s)
        records.restore_after_death(self.p, self.s)
        self.assertEqual(self.s.circuit, 'B')
        self.assertTrue(self.s.parts['A'] and self.s.return_open['A'])
        self.assertTrue(self.s.fragment_cache.opened)
        self.assertEqual((self.p.x, self.p.feet_y), self.s.start)
        self.assertEqual((self.p.health, self.p.battery, self.p.fragments), (3, 0, 1))
        records.restore_entry(self.p, self.s)
        self.assertEqual(self.s.circuit, 'A')
        self.assertEqual(self.s.part_count, 0)
        self.assertFalse(self.s.fragment_cache.opened or self.s.return_open['A'])
        self.assertEqual((self.p.battery, self.p.fragments), (100, 0))

    def test_powered_corridor_pauses_respawn_then_darkness_resumes_delay(self):
        enemies = [Shade(e.x, e.feet_y, identity=e.identity, combat_bounds=e.bounds, can_shoot=e.ranged)
                   for e in self.s.enemy_placements]
        restore_enemies(enemies, self.s)
        point = self.s.respawns.points[2]
        for _ in range(120):
            update_world(1/60, self.p, enemies, self.s)
        self.assertFalse(enemies[2].alive)
        self.assertEqual(point.remaining, 9)
        self.interact(self.s.terminal_position)
        for _ in range(541):
            update_world(1/60, self.p, enemies, self.s)
        self.assertEqual(point.state, 'WARNING')
        self.assertFalse(enemies[2].alive)
        for _ in range(61):
            update_world(1/60, self.p, enemies, self.s)
        self.assertTrue(enemies[2].alive)
        self.assertFalse(enemies[4].alive)
        self.s.fixture_powered = True
        update_world(0, self.p, enemies, self.s)
        self.assertTrue(all(p.state == 'SEALED' for p in self.s.respawns.points))
        self.assertFalse(any(e.alive for e in enemies))

    def walk(self, motion, x, speed=MOVE_SPEED):
        direction = 1 if x > motion.x else -1
        for _ in range(1200):
            motion.step(min(1/120, abs(x-motion.x)/speed), direction, self.s.solids, self.s.width, speed=speed)
            if abs(x-motion.x) < 1e-5:
                return
        self.fail(f'보행 실패 {motion.x, motion.feet_y} -> {x}')

    def hop(self, motion, x, y):
        self.assertTrue(motion.jump())
        self.walk(motion, x)
        for _ in range(180):
            motion.step(1/120, 0, self.s.solids, self.s.width)
            if motion.on_ground:
                break
        self.assertAlmostEqual(motion.feet_y, y, places=3)

    def test_basic_jump_reaches_archive_fuse_optional_gallery_and_ground_return(self):
        m = Motion(912, 96)
        for x, y, takeoff in ((848, 144, 912), (712, 192, 780), (584, 240, 652), (456, 288, 524)):
            self.walk(m, takeoff)
            self.hop(m, x, y)
        self.walk(m, 192)
        self.at(m.x, m.feet_y)
        self.s.collect_pickups(self.p)
        self.assertTrue(self.s.parts['A'])
        self.walk(m, 460)
        self.hop(m, 528, 336)
        self.walk(m, 704)
        self.interact((m.x, m.feet_y))
        self.assertEqual(self.p.fragments, 1)
        self.walk(m, 912)
        for _ in range(120):
            m.step(1/120, 0, self.s.solids, self.s.width)
        self.assertEqual(m.feet_y, 96)

    def test_b_room_covers_are_jumpable_and_closed_door_cannot_be_bypassed(self):
        m = Motion(2820, 96)
        m.jump()
        for _ in range(100):
            m.step(1/120, 1, self.s.solids, self.s.width, speed=RUN_SPEED*1.3)
        self.assertLessEqual(m.x, self.s.doors['B'].solid.left-12)
        self.interact(self.s.terminal_position)
        self.s.update(.55)
        m = Motion(2992, 96)
        self.walk(m, 3072)
        self.hop(m, 3136, 144)
        self.walk(m, 3392)
        self.hop(m, 3456, 144)
        self.walk(m, 3712)
        self.at(m.x, m.feet_y)
        self.s.collect_pickups(self.p)
        self.assertTrue(self.s.parts['B'])


if __name__ == '__main__':
    unittest.main()
