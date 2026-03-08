import unittest
from unittest.mock import MagicMock
from pylutron import Lutron
from pylutron.devices.base import LutronEntity
from typing import cast, Any


class TestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.lutron = Lutron("localhost", "user", "pass")
        self.lutron._conn = MagicMock()

    def test_legacy_subscription(self) -> None:
        """Test #5: Legacy Lutron.subscribe (deprecated)"""
        # Create a dummy entity
        entity = LutronEntity(self.lutron, "Test Entity", "uuid-1")
        handler = MagicMock()

        # This should trigger a warning but function correctly
        self.lutron.subscribe(entity, handler)

        # Simulate an event dispatch from the entity
        # The legacy dispatcher in Lutron class handles this
        entity._dispatch_event(cast(Any, None), {})

        self.assertTrue(handler.called)
        self.assertEqual(handler.call_args[0][0], entity)


if __name__ == "__main__":
    unittest.main()
