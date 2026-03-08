"""Occupancy sensors."""

import logging
from enum import Enum
from typing import List, Optional, TYPE_CHECKING, cast

from ..const import OP_QUERY
from ..util import _RequestHelper
from .base import LutronEntity, LutronEvent

if TYPE_CHECKING:
    from ..repeater import Lutron
    from ..models import Area

_LOGGER = logging.getLogger(__name__)


class OccupancyGroup(LutronEntity):
    """Represents one or more occupancy/vacancy sensors grouped into an Area."""
    _CMD_TYPE = 'GROUP'
    _ACTION_STATE = 3

    class State(Enum):
        """Possible states of an OccupancyGroup."""
        UNINITIALIZED = -1
        OCCUPIED = 3
        VACANT = 4
        UNKNOWN = 255

    class Event(LutronEvent):
        """OccupancyGroup event that can be generated.
        OCCUPANCY: Occupancy state has changed.
            Params:
              state: an OccupancyGroup.State
        """
        OCCUPANCY = 1

    def __init__(self, lutron: 'Lutron', group_number: str, uuid: str) -> None:
        super(OccupancyGroup, self).__init__(lutron, "", uuid)
        self._area: Optional['Area'] = None
        self._group_number = group_number
        self._integration_id: Optional[int] = None
        self._state = OccupancyGroup.State.UNINITIALIZED
        self._query_waiters = _RequestHelper()

    def _bind_area(self, area: 'Area') -> None:
        self._area = area
        self._integration_id = area.id
        if self._integration_id != 0:
            self._lutron.register_id(OccupancyGroup._CMD_TYPE, self)

    @property
    def id(self) -> int:
        """The integration id, which is the area's integration_id"""
        return self._integration_id or 0

    @property
    def legacy_uuid(self) -> str:
        assert self._area is not None
        return '%s-%s' % (self._area.id, self._group_number)

    @property
    def group_number(self) -> str:
        """The OccupancyGroupNumber"""
        return self._group_number

    @property
    def name(self) -> str:
        """Return the name of this OccupancyGroup, which is 'Occ' plus the name of the area."""
        assert self._area is not None
        return 'Occ {}'.format(self._area.name)

    @property
    def state(self) -> State:
        """Returns the current occupancy state."""
        # Poll for the first request.
        if self._state == OccupancyGroup.State.UNINITIALIZED:
            ev = self._query_waiters.request(self._do_query_state)
            ev.wait(1.0)
        return self._state

    def __str__(self) -> str:
        """Returns a pretty-printed string for this object."""
        assert self._area is not None
        return 'OccupancyGroup for Area "{}" Id: {} State: {}'.format(
            self._area.name, self.id, self.state.name)

    def __repr__(self) -> str:
        """Returns a stringified representation of this object."""
        assert self._area is not None
        return str({'area_name' : self._area.name,
                    'id' : self.id,
                    'state' : self.state})

    def _do_query_state(self) -> None:
        """Helper to perform the actual query for the current OccupancyGroup state."""
        self._lutron.send(OP_QUERY, OccupancyGroup._CMD_TYPE, self._integration_id or 0,
                                 OccupancyGroup._ACTION_STATE)

    def handle_update(self, args: List[str]) -> bool:
        """Handles an event update for this object, e.g. occupancy state change."""
        action = int(args[0])
        if action != OccupancyGroup._ACTION_STATE or len(args) != 2:
            return False
        try:
            self._state = OccupancyGroup.State(int(args[1]))
        except ValueError:
            self._state = OccupancyGroup.State.UNKNOWN
        self._query_waiters.notify()
        self._dispatch_event(cast(LutronEvent, OccupancyGroup.Event.OCCUPANCY), {'state': self._state})
        return True
