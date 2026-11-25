from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).parents[1]))

from custom_components.pawprint_light.sensor import PawPrintBatterySensor


class FakeBridge:
    address = "18:26:20:07:1B:42"
    battery = 70


class AutoDiscoveryBridge:
    address = None
    battery = 70


class PawPrintBatterySensorTest(unittest.TestCase):
    def test_exposes_bridge_battery_as_diagnostic_percentage(self):
        sensor = PawPrintBatterySensor(FakeBridge())

        self.assertEqual(sensor.native_value, 70)
        self.assertEqual(sensor.unique_id, "pawprint-182620071b42-battery")
        self.assertEqual(sensor.name, "PawPrint Battery")
        self.assertIsNone(sensor.device_info)

    def test_auto_discovery_sensor_has_no_unique_id(self):
        sensor = PawPrintBatterySensor(AutoDiscoveryBridge())

        self.assertIsNone(sensor.unique_id)


if __name__ == "__main__":
    unittest.main()
