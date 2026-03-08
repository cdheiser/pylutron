import unittest
from unittest.mock import MagicMock
from pylutron import Lutron, PowerSource, BatteryStatus
from pylutron.devices.sensor import MotionSensor


class TestSensor(unittest.TestCase):
    def setUp(self) -> None:
        self.lutron = Lutron("localhost", "user", "pass")
        self.lutron._conn = MagicMock()

    def test_motion_sensor_battery_status(self) -> None:
        sensor = MotionSensor(self.lutron, "Sensor", 500, "uuid-sensor")

        # Mock handle_update to set values
        # args: _, action, _, power, battery, _
        # power: 1 -> BATTERY
        # battery: 2 -> LOW
        sensor.handle_update(["DEVICE", "22", "1", "1", "2", "0"])

        self.assertEqual(sensor.power_source, PowerSource.BATTERY)
        self.assertEqual(sensor.battery_status, BatteryStatus.LOW)
        self.assertEqual(sensor.id, 500)
        self.assertEqual(sensor.legacy_uuid, "500")

        # Test __str__ and __repr__
        self.assertIn("Sensor", str(sensor))
        self.assertIn("battery", repr(sensor))


if __name__ == "__main__":
    unittest.main()
