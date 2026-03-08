"""Keypad devices."""

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, cast

from ..const import OP_EXECUTE, OP_QUERY
from ..util import _RequestHelper
from .base import LutronEntity, LutronEvent

if TYPE_CHECKING:
    from ..repeater import Lutron

_LOGGER = logging.getLogger(__name__)


class KeypadComponent(LutronEntity):
    """Base class for a keypad component such as a button, or an LED."""

    def __init__(self, lutron: 'Lutron', keypad: 'Keypad', name: str, num: int, component_num: int, uuid: str) -> None:
        """Initializes the base keypad component class."""
        super(KeypadComponent, self).__init__(lutron, name, uuid)
        self._keypad = keypad
        self._num = num
        self._component_num = component_num

    @property
    def id(self) -> int:
        """The integration id"""
        return self._keypad.id

    @property
    def number(self) -> int:
        """Returns the user-friendly number of this component (e.g. Button 1,
        or LED 1."""
        return self._num

    @property
    def component_number(self) -> int:
        """Return the lutron component number, which is referenced in commands and
        events. This is different from KeypadComponent.number because this property
        is only used for interfacing with the controller."""
        return self._component_num

    @property
    def legacy_uuid(self) -> str:
        return '%d-%d' % (self._keypad.id, self._component_num)

    def handle_update(self, action: int, params: List[int]) -> bool: # type: ignore[override]
        """Handle the specified action on this component."""
        _LOGGER.debug('Keypad: "%s" Handling "%s" Action: %s Params: %s"' % (
                      self._keypad.name, self.name, action, params))
        return False


class Button(KeypadComponent):
    """This object represents a keypad button that we can trigger and handle
    events for (button presses)."""
    _ACTION_PRESS = 3
    _ACTION_RELEASE = 4
    _ACTION_DOUBLE_CLICK = 6

    class Event(LutronEvent):
        """Button events that can be generated.

        PRESSED: The button has been pressed.
            Params: None

        RELEASED: The button has been released. Not all buttons
                  generate this event.
            Params: None

        DOUBLE_CLICKED: The button was double-clicked. Not all buttons
                  generate this event.
            Params: None
        """
        PRESSED = 1
        RELEASED = 2
        DOUBLE_CLICKED = 3

    def __init__(self, lutron: 'Lutron', keypad: 'Keypad', name: str, num: int, button_type: str, direction: Optional[str], uuid: str) -> None:
        """Initializes the Button class."""
        super(Button, self).__init__(lutron, keypad, name, num, num, uuid)
        self._button_type = button_type
        self._direction = direction

    def __str__(self) -> str:
        """Pretty printed string value of the Button object."""
        return 'Button name: "%s" num: %d type: "%s" direction: "%s"' % (
            self.name, self.number, self._button_type, self._direction)

    def __repr__(self) -> str:
        """String representation of the Button object."""
        return str({'name': self.name, 'num': self.number,
                   'type': self._button_type, 'direction': self._direction})

    @property
    def button_type(self) -> str:
        """Returns the button type (Toggle, MasterRaiseLower, etc.)."""
        return self._button_type

    def press(self) -> None:
        """Triggers a simulated button press to the Keypad."""
        self._lutron.send(OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id,
                          self.component_number, Button._ACTION_PRESS)

    def release(self) -> None:
        """Triggers a simulated button release to the Keypad."""
        self._lutron.send(OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id,
                          self.component_number, Button._ACTION_RELEASE)

    def double_click(self) -> None:
        """Triggers a simulated button double_click to the Keypad."""
        self._lutron.send(OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id,
                          self.component_number, Button._ACTION_DOUBLE_CLICK)

    def tap(self) -> None:
        """Triggers a simulated button tap to the Keypad."""
        self.press()
        self.release()

    def handle_update(self, action: int, params: List[int]) -> bool: # type: ignore[override]
        """Handle the specified action on this component."""
        _LOGGER.debug('Keypad: "%s" %s Action: %s Params: %s"' % (
                      self._keypad.name, self, action, params))
        ev_map = {
            Button._ACTION_PRESS: Button.Event.PRESSED,
            Button._ACTION_RELEASE: Button.Event.RELEASED,
            Button._ACTION_DOUBLE_CLICK: Button.Event.DOUBLE_CLICKED
        }
        if action not in ev_map:
            _LOGGER.debug("Unknown action %d for button %d in keypad %s" % (
                action, self.number, self._keypad.name))
            return False
        self._dispatch_event(cast(LutronEvent, ev_map[action]), {})
        return True


class Led(KeypadComponent):
    """This object represents a keypad LED that we can turn on/off and
    handle events for (led toggled by scenes)."""
    _ACTION_LED_STATE = 9

    # LED indicators states
    LED_OFF = 0
    LED_ON = 1
    LED_SLOW_FLASH = 2
    LED_FAST_FLASH = 3

    class Event(LutronEvent):
        """Led events that can be generated.

        STATE_CHANGED: The LED state has changed.
            Params:
              state: The integer value of the new LED state.
              0: Off, 1: On, 2: Slow Flash (1Hz), 3: Fast Flash (10Hz).
        """
        STATE_CHANGED = 1

    def __init__(self, lutron: 'Lutron', keypad: 'Keypad', name: str, led_num: int, component_num: int, uuid: str) -> None:
        """Initializes the Keypad LED class."""
        super(Led, self).__init__(lutron, keypad, name, led_num, component_num, uuid)
        self._state = Led.LED_OFF
        self._query_waiters = _RequestHelper()

    def __str__(self) -> str:
        """Pretty printed string value of the Led object."""
        return 'LED keypad: "%s" name: "%s" num: %d component_num: %d"' % (
            self._keypad.name, self.name, self.number, self.component_number)

    def __repr__(self) -> str:
        """String representation of the Led object."""
        return str({'keypad': self._keypad, 'name': self.name,
                    'num': self.number, 'component_num': self.component_number})

    def _do_query_state(self) -> None:
        """Helper to perform the actual query for the current LED state."""
        self._lutron.send(OP_QUERY, Keypad._CMD_TYPE, self._keypad.id,
                self.component_number, Led._ACTION_LED_STATE)

    @property
    def last_state(self) -> int:
        """Returns last cached value of the LED state, no query is performed."""
        return self._state

    @property
    def state(self) -> int:
        """Returns the current LED state by querying the remote controller."""
        ev = self._query_waiters.request(self._do_query_state)
        ev.wait(1.0)
        return self._state

    @state.setter
    def state(self, new_state: int) -> None:
        """Sets the new led state.

        new_state: int
        """
        if new_state not in [Led.LED_OFF, Led.LED_ON, Led.LED_SLOW_FLASH, Led.LED_FAST_FLASH]:
            raise ValueError("Invalid LED state: %s" % new_state)
        self._lutron.send(OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id,
                          self.component_number, Led._ACTION_LED_STATE,
                          new_state)
        self._state = new_state

    def handle_update(self, action: int, params: List[int]) -> bool: # type: ignore[override]
        """Handle the specified action on this component."""
        _LOGGER.debug('Keypad: "%s" %s Action: %s Params: %s"' % (
                      self._keypad.name, self, action, params))
        if action != Led._ACTION_LED_STATE:
            _LOGGER.debug("Unknown action %d for led %d in keypad %s" % (
                action, self.number, self._keypad.name))
            return False
        elif len(params) < 1:
            _LOGGER.debug("Unknown params %s (action %d on led %d in keypad %s)" % (
                params, action, self.number, self._keypad.name))
            return False
        self._state = params[0]
        self._query_waiters.notify()
        self._dispatch_event(Led.Event.STATE_CHANGED, {'state': self._state})
        return True


class Keypad(LutronEntity):
    """Object representing a Lutron keypad.

    Currently we don't really do much with it except handle the events
    (and drop them on the floor).
    """
    _CMD_TYPE = 'DEVICE'

    def __init__(self, lutron: 'Lutron', name: str, keypad_type: str, location: str, integration_id: int, uuid: str) -> None:
        """Initializes the Keypad object."""
        super(Keypad, self).__init__(lutron, name, uuid)
        self._buttons: List[Button] = []
        self._leds: List[Led] = []
        self._components: Dict[int, KeypadComponent] = {}
        self._location = location
        self._integration_id = integration_id
        self._type = keypad_type

        self._lutron.register_id(Keypad._CMD_TYPE, self)

    def add_button(self, button: Button) -> None:
        """Adds a button that's part of this keypad. We'll use this to
        dispatch button events."""
        self._buttons.append(button)
        self._components[button.component_number] = button

    def add_led(self, led: Led) -> None:
        """Add an LED that's part of this keypad."""
        self._leds.append(led)
        self._components[led.component_number] = led

    @property
    def id(self) -> int:
        """The integration id"""
        return self._integration_id

    @property
    def legacy_uuid(self) -> str:
        return '%d-0' % self.id

    @property
    def type(self) -> str:
        """Returns the keypad type"""
        return self._type

    @property
    def location(self) -> str:
        """Returns the location in which the keypad is installed"""
        return self._location

    @property
    def buttons(self) -> Tuple[Button, ...]:
        """Return a tuple of buttons for this keypad."""
        return tuple(button for button in self._buttons)

    @property
    def leds(self) -> Tuple[Led, ...]:
        """Return a tuple of leds for this keypad."""
        return tuple(led for led in self._leds)

    def handle_update(self, args: List[str]) -> bool:
        """The callback invoked by the main event loop if there's an event from this keypad."""
        component = int(args[0])
        action = int(args[1])
        params = [int(x) for x in args[2:]]
        _LOGGER.debug("Updating %d(%s): c=%d a=%d params=%s" % (
            self._integration_id, self._name, component, action, params))
        if component in self._components:
            return self._components[component].handle_update(action, params)
        return False
