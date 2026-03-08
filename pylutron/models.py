"""Models representing Lutron concepts like rooms/areas."""

from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .repeater import Lutron
    from .devices.occupancy import OccupancyGroup
    from .devices.output import Output
    from .devices.keypad import Keypad
    from .devices.sensor import MotionSensor


class Area:
    """An area (i.e. a room) that contains devices/outputs/etc."""

    def __init__(
        self,
        lutron: "Lutron",
        name: str,
        integration_id: int,
        occupancy_group: Optional["OccupancyGroup"],
    ) -> None:
        self._lutron = lutron
        self._name = name
        self._integration_id = integration_id
        if occupancy_group is None:
            from .devices.occupancy import (
                OccupancyGroup,
            )  # localized import to avoid circular dep

            occupancy_group = OccupancyGroup(lutron, "", "")
        self._occupancy_group = occupancy_group
        self._outputs: List["Output"] = []
        self._keypads: List["Keypad"] = []
        self._sensors: List["MotionSensor"] = []
        self._occupancy_group._bind_area(self)

    def add_output(self, output: "Output") -> None:
        """Adds an output object that's part of this area, only used during
        initial parsing."""
        self._outputs.append(output)

    def add_keypad(self, keypad: "Keypad") -> None:
        """Adds a keypad object that's part of this area, only used during
        initial parsing."""
        self._keypads.append(keypad)

    def add_sensor(self, sensor: "MotionSensor") -> None:
        """Adds a motion sensor object that's part of this area, only used during
        initial parsing."""
        self._sensors.append(sensor)

    @property
    def name(self) -> str:
        """Returns the name of this area."""
        return self._name

    @property
    def id(self) -> int:
        """The integration id of the area."""
        return self._integration_id

    @property
    def occupancy_group(self) -> "OccupancyGroup":
        """Returns the OccupancyGroup for this area."""
        return self._occupancy_group

    @property
    def outputs(self) -> Tuple["Output", ...]:
        """Return the tuple of the Outputs from this area."""
        return tuple(output for output in self._outputs)

    @property
    def keypads(self) -> Tuple["Keypad", ...]:
        """Return the tuple of the Keypads from this area."""
        return tuple(keypad for keypad in self._keypads)

    @property
    def sensors(self) -> Tuple["MotionSensor", ...]:
        """Return the tuple of the MotionSensors from this area."""
        return tuple(sensor for sensor in self._sensors)
