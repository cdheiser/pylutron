"""Utility classes for pylutron."""

import threading
from typing import Any, Callable, List


class _RequestHelper:
    """A class to help with sending queries to the controller and waiting for
    responses.

    It is a wrapper used to help with executing a user action
    and then waiting for an event when that action completes.

    The user calls request() and gets back a threading.Event on which they then
    wait.

    If multiple clients of a lutron object (say an Output) want to get a status
    update on the current brightness (output level), we don't want to spam the
    controller with (near)identical requests. So, if a request is pending, we
    just enqueue another waiter on the pending request and return a new Event
    object. All waiters will be woken up when the reply is received and the
    wait list is cleared.

    NOTE: Only the first enqueued action is executed as the assumption is that the
    queries will be identical in nature.
    """

    def __init__(self) -> None:
        """Initialize the request helper class."""
        self.__lock = threading.Lock()
        self.__events: List[threading.Event] = []

    def request(self, action: Callable[[], Any]) -> threading.Event:
        """Request an action to be performed, in case one."""
        ev = threading.Event()
        first = False
        with self.__lock:
            if len(self.__events) == 0:
                first = True
            self.__events.append(ev)
        if first:
            action()
        return ev

    def notify(self) -> None:
        with self.__lock:
            events = self.__events
            self.__events = []
        for ev in events:
            ev.set()
