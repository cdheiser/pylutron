"""Base classes for Lutron devices."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..repeater import Lutron

class LutronEvent(Enum):
    """Base class for the events LutronEntity-derived objects can produce."""
    pass

# This describes the type signature of the callback that LutronEntity
# subscribers must provide.
LutronEventHandler = Callable[['LutronEntity', Any, 'LutronEvent', Dict[str, Any]], None]

class LutronEntity:
    """Base class for all the Lutron objects we'd like to manage. Just holds basic
    common info we'd rather not manage repeatedly."""

    def __init__(self, lutron: 'Lutron', name: str, uuid: str) -> None:
        """Initializes the base class with common, basic data."""
        self._lutron = lutron
        self._name = name
        self._subscribers: List[Tuple[LutronEventHandler, Any]] = []
        self._uuid = uuid

    @property
    def name(self) -> str:
        """Returns the entity name (e.g. Pendant)."""
        return self._name

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def legacy_uuid(self) -> Optional[str]:
        """Return a synthesized uuid."""
        return None

    @property
    def id(self) -> int:
        """The integration id"""
        raise NotImplementedError

    def _dispatch_event(self, event: LutronEvent, params: Dict[str, Any]) -> None:
        """Dispatches the specified event to all the subscribers."""
        for handler, context in self._subscribers:
            handler(self, context, event, params)

    def subscribe(self, handler: LutronEventHandler, context: Any) -> Callable[[], None]:
        """Subscribes to events from this entity.

        handler: A callable object that takes the following arguments (in order)
                 obj: the LutrongEntity object that generated the event
                 context: user-supplied (to subscribe()) context object
                 event: the LutronEvent that was generated.
                 params: a dict of event-specific parameters

        context: User-supplied, opaque object that will be passed to handler.
        Returns: A callable that can be used to unsubscribe from the event.
        """
        self._subscribers.append((handler, context))
        return lambda: self._subscribers.remove((handler, context))

    def handle_update(self, args: List[str]) -> bool:
        """The handle_update callback is invoked when an event is received
        for the this entity.

        Returns:
          True - If event was valid and was handled.
          False - otherwise.
        """
        return False
