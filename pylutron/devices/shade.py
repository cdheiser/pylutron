"""Shade devices."""

from ..const import OP_EXECUTE
from .output import Output


class Shade(Output):
    """This is the output entity for shades in Lutron universe."""

    _ACTION_RAISE = 2
    _ACTION_LOWER = 3
    _ACTION_STOP = 4

    def start_raise(self) -> None:
        """Starts raising the shade."""
        self._lutron.send(
            OP_EXECUTE, Output._CMD_TYPE, self._integration_id, Shade._ACTION_RAISE
        )

    def start_lower(self) -> None:
        """Starts lowering the shade."""
        self._lutron.send(
            OP_EXECUTE, Output._CMD_TYPE, self._integration_id, Shade._ACTION_LOWER
        )

    def stop(self) -> None:
        """Starts raising the shade."""
        self._lutron.send(
            OP_EXECUTE, Output._CMD_TYPE, self._integration_id, Shade._ACTION_STOP
        )
