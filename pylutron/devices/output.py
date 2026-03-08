"""Output devices."""

import logging
from datetime import timedelta
from typing import List, Optional, TYPE_CHECKING

from ..const import OP_EXECUTE, OP_QUERY
from ..util import _RequestHelper
from .base import LutronEntity, LutronEvent

if TYPE_CHECKING:
    from ..repeater import Lutron

_LOGGER = logging.getLogger(__name__)


class Output(LutronEntity):
    """This is the output entity in Lutron universe. This generally refers to a
    switched/dimmed load, e.g. light fixture, outlet, etc."""
    _CMD_TYPE = 'OUTPUT'
    _ACTION_ZONE_LEVEL = 1
    _ACTION_ZONE_FLASH = 5

    class Event(LutronEvent):
        """Output events that can be generated.

        LEVEL_CHANGED: The output level has changed.
            Params:
              level: new output level (float)
        """
        LEVEL_CHANGED = 1

    def __init__(self, lutron: 'Lutron', name: str, watts: int, output_type: str, integration_id: int, uuid: str) -> None:
        """Initializes the Output."""
        super(Output, self).__init__(lutron, name, uuid)
        self._watts = watts
        self._output_type = output_type
        self._level = 0.0
        self._query_waiters = _RequestHelper()
        self._integration_id = integration_id

        self._lutron.register_id(Output._CMD_TYPE, self)

    def __str__(self) -> str:
        """Returns a pretty-printed string for this object."""
        return 'Output name: "%s" watts: %d type: "%s" id: %d' % (
            self._name, self._watts, self._output_type, self._integration_id)

    def __repr__(self) -> str:
        """Returns a stringified representation of this object."""
        return str({'name': self._name, 'watts': self._watts,
                    'type': self._output_type, 'id': self._integration_id})

    @property
    def id(self) -> int:
        """The integration id"""
        return self._integration_id

    @property
    def legacy_uuid(self) -> str:
        return '%d-0' % self.id

    def handle_update(self, args: List[str]) -> bool:
        """Handles an event update for this object, e.g. dimmer level change."""
        _LOGGER.debug("handle_update %d -- %s" % (self._integration_id, args))
        state = int(args[0])
        if state != Output._ACTION_ZONE_LEVEL:
            return False
        level = float(args[1])
        _LOGGER.debug("Updating %d(%s): s=%d l=%f" % (
            self._integration_id, self._name, state, level))
        self._level = level
        self._query_waiters.notify()
        self._dispatch_event(Output.Event.LEVEL_CHANGED, {'level': self._level})
        return True

    def _do_query_level(self) -> None:
        """Helper to perform the actual query the current dimmer level of the
        output. For pure on/off loads the result is either 0.0 or 100.0."""
        self._lutron.send(OP_QUERY, Output._CMD_TYPE, self._integration_id,
                Output._ACTION_ZONE_LEVEL)

    def last_level(self) -> float:
        """Returns last cached value of the output level, no query is performed."""
        return self._level

    @property
    def level(self) -> float:
        """Returns the current output level by querying the remote controller."""
        ev = self._query_waiters.request(self._do_query_level)
        ev.wait(1.0)
        return self._level

    @level.setter
    def level(self, new_level: float) -> None:
        """Sets the new output level."""
        self.set_level(new_level)

    @staticmethod
    def _fade_time(seconds: Optional[float]) -> Optional[str]:
        if seconds is None:
            return None
        return str(timedelta(seconds=seconds))

    def set_level(self, new_level: float, fade_time_seconds: Optional[float] = None) -> None:
        """Sets the new output level."""
        if self._level == new_level:
            return
        self._lutron.send(OP_EXECUTE, Output._CMD_TYPE, self._integration_id,
            Output._ACTION_ZONE_LEVEL, "%.2f" % new_level, self._fade_time(fade_time_seconds))
        self._level = new_level

    def flash(self, fade_time_seconds: Optional[float] = None) -> None:
        """Flashes the zone until a new level is set."""
        self._lutron.send(OP_EXECUTE, Output._CMD_TYPE, self._integration_id,
            Output._ACTION_ZONE_FLASH, self._fade_time(fade_time_seconds))

    @property
    def watts(self) -> int:
        """Returns the configured maximum wattage for this output (not an actual
        measurement)."""
        return self._watts

    @property
    def type(self) -> str:
        """Returns the output type. At present AUTO_DETECT or NON_DIM."""
        return self._output_type

    @property
    def is_dimmable(self) -> bool:
        """Returns a boolean of whether or not the output is dimmable."""
        return self.type not in ('NON_DIM', 'NON_DIM_INC', 'NON_DIM_ELV', 'EXHAUST_FAN_TYPE', 'RELAY_LIGHTING', 'SWITCHED_MOTOR') and not self.type.startswith('CCO_')
