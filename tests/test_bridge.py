from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).parents[1]))

from custom_components.pawprint_light import Bridge


CONFIG = {
    "axis": "x",
    "left": -60,
    "right": 60,
    "hold_seconds": 0.5,
    "motion_threshold": 12,
    "speed_threshold": 35,
    "address": "18:26:20:07:1B:42",
}


class FakeBatterySensor:
    def __init__(self, hass=object()):
        self.hass = hass
        self.write_count = 0

    def async_write_ha_state(self):
        self.write_count += 1


class BridgeBatteryTest(unittest.TestCase):
    def test_records_battery_report_and_notifies_sensor(self):
        bridge = Bridge(None, CONFIG)
        sensor = FakeBatterySensor()
        bridge.battery_sensor = sensor

        self.assertTrue(bridge.record_battery(bytes([0x51, 0x01, 0x03, 0x46])))
        self.assertEqual(bridge.battery, 70)
        self.assertEqual(sensor.write_count, 1)

    def test_records_battery_without_writing_unadded_sensor(self):
        bridge = Bridge(None, CONFIG)
        sensor = FakeBatterySensor(hass=None)
        bridge.battery_sensor = sensor

        self.assertTrue(bridge.record_battery(bytes([0x51, 0x01, 0x03, 0x46])))
        self.assertEqual(bridge.battery, 70)
        self.assertEqual(sensor.write_count, 0)

    def test_ignores_non_battery_report(self):
        bridge = Bridge(None, CONFIG)

        self.assertFalse(bridge.record_battery(bytes([0xD0, 0x01, 0x00])))
        self.assertIsNone(bridge.battery)


if __name__ == "__main__":
    unittest.main()
