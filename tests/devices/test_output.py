import unittest
from unittest.mock import MagicMock
from pylutron import Lutron, Output

from typing import cast


class TestOutput(unittest.TestCase):
    def setUp(self) -> None:
        self.lutron = Lutron("localhost", "user", "pass")
        self.lutron._conn.send = MagicMock()  # type: ignore[method-assign]
        self.output = Output(self.lutron, "Ceiling Light", 100, "DIMMER", 1, "UUID-1")

    def test_properties(self) -> None:
        self.assertEqual(self.output.name, "Ceiling Light")
        self.assertEqual(self.output.watts, 100)
        self.assertEqual(self.output.type, "DIMMER")
        self.assertEqual(self.output.id, 1)

    def test_is_dimmable(self) -> None:
        # DIMMER should be dimmable
        self.assertTrue(self.output.is_dimmable)

        # NON_DIM should not be dimmable
        non_dim = Output(self.lutron, "Fan", 100, "NON_DIM", 2, "UUID-2")
        self.assertFalse(non_dim.is_dimmable)

    def test_set_level_executes_command(self) -> None:
        self.output.level = 50.0
        # Verify that setting the level sends the correct command without fade time
        cast(MagicMock, self.lutron._conn.send).assert_called_with("#OUTPUT,1,1,50.00")
        self.assertEqual(self.output.last_level(), 50.0)

    def test_handle_update(self) -> None:
        # Simulate receiving an update from the controller
        # Action 1 (ZONE_LEVEL), Level 75.00
        handled = self.output.handle_update(["1", "75.00"])
        self.assertTrue(handled)
        self.assertEqual(self.output.last_level(), 75.0)

    def test_output_flash(self) -> None:
        self.output.flash()
        cast(MagicMock, self.lutron._conn.send).assert_called_with("#OUTPUT,1,5")

    def test_output_is_dimmable_edge_cases(self) -> None:
        # Test various non-dimmable types
        non_dim_types = [
            "NON_DIM",
            "NON_DIM_INC",
            "NON_DIM_ELV",
            "EXHAUST_FAN_TYPE",
            "RELAY_LIGHTING",
            "SWITCHED_MOTOR",
            "CCO_SOMETHING",
        ]
        for i, t in enumerate(non_dim_types):
            out = Output(self.lutron, "N", 0, t, 1000 + i, "u")
            self.assertFalse(out.is_dimmable, f"Type {t} should not be dimmable")

    def test_string_representations(self) -> None:
        self.assertIn("Ceiling Light", str(self.output))
        self.assertIn("DIMMER", repr(self.output))
        self.assertEqual(self.output.legacy_uuid, "1-0")


if __name__ == "__main__":
    unittest.main()
