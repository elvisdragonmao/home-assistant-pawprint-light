import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "pawprint_light"
    / "gesture.py"
)
spec = importlib.util.spec_from_file_location("pawprint_gesture", MODULE_PATH)
gesture = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gesture)


class DecodeBatteryTest(unittest.TestCase):
    def test_decodes_pawprint_v11_battery_report(self):
        self.assertEqual(gesture.decode_battery(bytes([0x51, 0x01, 0x03, 0x46])), 70)

    def test_rejects_non_battery_and_out_of_range_reports(self):
        invalid_reports = (
            bytes([0xD0, 0x01, 0x03, 0x46]),
            bytes([0x51, 0x01, 0x02, 0x46]),
            bytes([0x51, 0x01, 0x03]),
            bytes([0x51, 0x01, 0x03, 101]),
        )
        for report in invalid_reports:
            with self.subTest(report=report.hex()):
                self.assertIsNone(gesture.decode_battery(report))

    def test_rejects_invalid_main_indicator_color(self):
        for color in (0x00, 0x07):
            with self.subTest(color=color):
                self.assertIsNone(
                    gesture.decode_battery(bytes([0x51, color, 0x03, 0x46]))
                )


if __name__ == "__main__":
    unittest.main()
