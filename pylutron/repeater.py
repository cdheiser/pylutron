"""Main repeater controller and XML parser."""

import logging
from xml.etree import ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Union

from .connection import LutronConnection
from .const import OP_EXECUTE, OP_QUERY, OP_RESPONSE
from .exceptions import IntegrationIdExistsError, InvalidSubscription
from .models import Area
from .devices.base import LutronEntity
from .devices.keypad import Button, Keypad, Led
from .devices.occupancy import OccupancyGroup
from .devices.output import Output
from .devices.sensor import MotionSensor
from .devices.shade import Shade

_LOGGER = logging.getLogger(__name__)


class LutronXmlDbParser:
    """The parser for Lutron XML database.

    The database describes all the rooms (Area), keypads (Device), and switches
    (Output). We handle the most relevant features, but some things like LEDs,
    etc. are not implemented."""

    def __init__(self, lutron: "Lutron", xml_db_str: Union[str, bytes]) -> None:
        """Initializes the XML parser, takes the raw XML data as string input."""
        self._lutron = lutron
        self._xml_db_str = xml_db_str
        self.areas: List[Area] = []
        self._occupancy_groups: Dict[str, OccupancyGroup] = {}
        self.project_name: Optional[str] = None

    def parse(self) -> bool:
        """Main entrypoint into the parser. It interprets and creates all the
        relevant Lutron objects and stuffs them into the appropriate hierarchy."""
        root = ET.fromstring(self._xml_db_str)
        # The structure is something like this:
        # <Areas>
        #   <Area ...>
        #     <DeviceGroups ...>
        #     <Scenes ...>
        #     <ShadeGroups ...>
        #     <Outputs ...>
        #     <Areas ...>
        #       <Area ...>

        # The GUID is unique to the repeater and is useful for constructing unique
        # identifiers that won't change over time.
        guid_xml = root.find("GUID")
        if guid_xml is not None and guid_xml.text:
            self._lutron.set_guid(guid_xml.text)

        # Parse Occupancy Groups
        # OccupancyGroups are referenced by entities in the rest of the XML.  The
        # current structure of the code expects to go from areas -> devices ->
        # other assets and attributes.  Here we index the groups to be bound to
        # Areas later.
        groups = root.find("OccupancyGroups")
        if groups is not None:
            for group_xml in groups.iter("OccupancyGroup"):
                group = self._parse_occupancy_group(group_xml)
                if group.group_number:
                    self._occupancy_groups[group.group_number] = group
                else:
                    _LOGGER.warning(
                        "Occupancy Group has no number.  XML: %s", group_xml
                    )

        # First area is useless, it's the top-level project area that defines the
        # "house". It contains the real nested Areas tree, which is the one we want.
        areas_xml = root.find("Areas")
        if areas_xml is not None:
            top_area = areas_xml.find("Area")
            if top_area is not None:
                self.project_name = top_area.get("Name")
                areas = top_area.find("Areas")
                if areas is not None:
                    for area_xml in areas.iter("Area"):
                        area = self._parse_area(area_xml)
                        self.areas.append(area)
        return True

    def _parse_area(self, area_xml: ET.Element) -> Area:
        """Parses an Area tag, which is effectively a room, depending on how the
        Lutron controller programming was done."""
        occupancy_group_id = area_xml.get("OccupancyGroupAssignedToID")
        occupancy_group = (
            self._occupancy_groups.get(occupancy_group_id)
            if occupancy_group_id
            else None
        )
        area_name = area_xml.get("Name") or "Unknown Area"
        if not occupancy_group and occupancy_group_id:
            _LOGGER.warning(
                "Occupancy Group not found for Area: %s; ID: %s",
                area_name,
                occupancy_group_id,
            )
        area = Area(
            self._lutron,
            name=area_name,
            integration_id=int(area_xml.get("IntegrationID") or 0),
            occupancy_group=occupancy_group,
        )
        outputs = area_xml.find("Outputs")
        if outputs is not None:
            for output_xml in outputs:
                output = self._parse_output(output_xml)
                area.add_output(output)
        # device group in our case means keypad
        # device_group.get('Name') is the location of the keypad
        device_groups = area_xml.find("DeviceGroups")
        if device_groups is not None:
            for device_group in device_groups:
                devs: List[ET.Element] = []
                if device_group.tag == "DeviceGroup":
                    devices_xml = device_group.find("Devices")
                    if devices_xml is not None:
                        devs = list(devices_xml)
                elif device_group.tag == "Device":
                    devs = [device_group]
                else:
                    _LOGGER.info(
                        "Unknown tag in DeviceGroups child %s", device_group.tag
                    )

                for device_xml in devs:
                    if device_xml.tag != "Device":
                        continue
                    device_type = device_xml.get("DeviceType")
                    if device_type in (
                        "HWI_SEETOUCH_KEYPAD",
                        "SEETOUCH_KEYPAD",
                        "INTERNATIONAL_SEETOUCH_KEYPAD",
                        "SEETOUCH_TABLETOP_KEYPAD",
                        "PICO_KEYPAD",
                        "HYBRID_SEETOUCH_KEYPAD",
                        "MAIN_REPEATER",
                        "HOMEOWNER_KEYPAD",
                        "PALLADIOM_KEYPAD",
                        "HWI_SLIM",
                        "GRAFIK_T_HYBRID_KEYPAD",
                    ):
                        keypad = self._parse_keypad(device_xml, device_group)
                        area.add_keypad(keypad)
                    elif device_type == "MOTION_SENSOR":
                        motion_sensor = self._parse_motion_sensor(device_xml)
                        area.add_sensor(motion_sensor)
        return area

    def _parse_output(self, output_xml: ET.Element) -> Output:
        """Parses an output, which is generally a switch controlling a set of
        lights/outlets, etc."""
        output_type = output_xml.get("OutputType") or "Unknown"
        name = output_xml.get("Name") or "Unknown Output"
        watts = int(output_xml.get("Wattage") or 0)
        integration_id = int(output_xml.get("IntegrationID") or 0)
        uuid = output_xml.get("UUID") or ""

        if output_type in ("SYSTEM_SHADE", "MOTOR"):
            return Shade(self._lutron, name, watts, output_type, integration_id, uuid)
        return Output(self._lutron, name, watts, output_type, integration_id, uuid)

    def _parse_keypad(self, keypad_xml: ET.Element, device_group: ET.Element) -> Keypad:
        """Parses a keypad device (the Visor receiver is technically a keypad too)."""
        keypad = Keypad(
            self._lutron,
            name=keypad_xml.get("Name") or "Unknown Keypad",
            keypad_type=keypad_xml.get("DeviceType") or "Unknown Type",
            location=device_group.get("Name") or "Unknown Location",
            integration_id=int(keypad_xml.get("IntegrationID") or 0),
            uuid=keypad_xml.get("UUID") or "",
        )
        components = keypad_xml.find("Components")
        if components is None:
            return keypad
        for comp in components:
            if comp.tag != "Component":
                continue
            comp_type = comp.get("ComponentType")
            if comp_type == "BUTTON":
                button = self._parse_button(keypad, comp)
                keypad.add_button(button)
            elif comp_type == "LED":
                led = self._parse_led(keypad, comp)
                keypad.add_led(led)
        return keypad

    def _parse_button(self, keypad: Keypad, component_xml: ET.Element) -> Button:
        """Parses a button device that part of a keypad."""
        button_xml = component_xml.find("Button")
        assert button_xml is not None
        name = button_xml.get("Engraving")
        button_type = button_xml.get("ButtonType") or "Unknown"
        direction = button_xml.get("Direction")
        # Hybrid keypads have dimmer buttons which have no engravings.
        if button_type == "SingleSceneRaiseLower" or button_type == "MasterRaiseLower":
            name = "Dimmer " + (direction or "")
        if not name:
            name = "Unknown Button"
        button = Button(
            self._lutron,
            keypad,
            name=name,
            num=int(component_xml.get("ComponentNumber") or 0),
            button_type=button_type,
            direction=direction,
            uuid=button_xml.get("UUID") or "",
        )
        return button

    def _parse_led(self, keypad: Keypad, component_xml: ET.Element) -> Led:
        """Parses an LED device that part of a keypad."""
        component_num = int(component_xml.get("ComponentNumber") or 0)
        led_base = 80
        if keypad.type == "MAIN_REPEATER":
            led_base = 100
        led_num = component_num - led_base
        led_xml = component_xml.find("LED")
        assert led_xml is not None
        led = Led(
            self._lutron,
            keypad,
            name=("LED %d" % led_num),
            led_num=led_num,
            component_num=component_num,
            uuid=led_xml.get("UUID") or "",
        )
        return led

    def _parse_motion_sensor(self, sensor_xml: ET.Element) -> MotionSensor:
        """Parses a motion sensor object."""
        return MotionSensor(
            self._lutron,
            name=sensor_xml.get("Name") or "Unknown Sensor",
            integration_id=int(sensor_xml.get("IntegrationID") or 0),
            uuid=sensor_xml.get("UUID") or "",
        )

    def _parse_occupancy_group(self, group_xml: ET.Element) -> OccupancyGroup:
        """Parses an Occupancy Group object."""
        return OccupancyGroup(
            self._lutron,
            group_number=group_xml.get("OccupancyGroupNumber") or "",
            uuid=group_xml.get("UUID") or "",
        )


class Lutron:
    """Main Lutron Controller class.

    This object owns the connection to the controller, the rooms that exist in the
    network, handles dispatch of incoming status updates, etc.
    """

    # Maintain API compatibility
    OP_EXECUTE = OP_EXECUTE
    OP_QUERY = OP_QUERY
    OP_RESPONSE = OP_RESPONSE

    def __init__(self, host: str, user: str, password: str) -> None:
        """Initializes the Lutron object. No connection is made to the remote
        device."""
        self._host = host
        self._user = user
        self._password = password
        self._name = ""
        self._conn = LutronConnection(host, user, password, self._recv)
        self._ids: Dict[str, Dict[int, LutronEntity]] = {}
        self._legacy_subscribers: Dict[
            LutronEntity, Callable[[LutronEntity], None]
        ] = {}
        self._areas: List[Area] = []
        self._guid = ""

    @property
    def areas(self) -> List[Area]:
        """Return the areas that were discovered for this Lutron controller."""
        return self._areas

    def set_guid(self, guid: str) -> None:
        self._guid = guid

    @property
    def guid(self) -> str:
        return self._guid

    @property
    def name(self) -> str:
        return self._name

    def subscribe(
        self, obj: LutronEntity, handler: Callable[[LutronEntity], None]
    ) -> None:
        """Subscribes to status updates of the requested object.

        DEPRECATED

        The handler will be invoked when the controller sends a notification
        regarding changed state. The user can then further query the object for the
        state itself."""
        if not isinstance(obj, LutronEntity):
            raise InvalidSubscription("Subscription target not a LutronEntity")
        _LOGGER.warning(
            "DEPRECATED: Subscribing via Lutron.subscribe is obsolete. "
            "Please use LutronEntity.subscribe"
        )
        if obj not in self._legacy_subscribers:
            self._legacy_subscribers[obj] = handler
            obj.subscribe(self._dispatch_legacy_subscriber, None)

    def register_id(self, cmd_type: str, obj: LutronEntity) -> None:
        """Registers an object (through its integration id) to receive update
        notifications. This is the core mechanism how Output and Keypad objects get
        notified when the controller sends status updates."""
        ids = self._ids.setdefault(cmd_type, {})
        if obj.id in ids:
            raise IntegrationIdExistsError
        self._ids[cmd_type][obj.id] = obj

    def _dispatch_legacy_subscriber(
        self, obj: LutronEntity, *args: Any, **kwargs: Any
    ) -> None:
        """This dispatches the registered callback for 'obj'. This is only used
        for legacy subscribers since new users should register with the target
        object directly."""
        if obj in self._legacy_subscribers:
            self._legacy_subscribers[obj](obj)

    def _recv(self, line: str) -> None:
        """Invoked by the connection manager to process incoming data."""
        if line == "":
            return
        # Only handle query response messages, which are also sent on remote status
        # updates (e.g. user manually pressed a keypad button)
        if line[0] != OP_RESPONSE:
            _LOGGER.debug("ignoring %s", line)
            return
        parts = line[1:].split(",")
        cmd_type = parts[0]
        integration_id = int(parts[1])
        args = parts[2:]
        if cmd_type not in self._ids:
            _LOGGER.info("Unknown cmd %s (%s)", cmd_type, line)
            return
        ids = self._ids[cmd_type]
        if integration_id not in ids:
            _LOGGER.warning("Unknown id %d (%s)", integration_id, line)
            return
        obj = ids[integration_id]
        obj.handle_update(args)

    def connect(self) -> None:
        """Connects to the Lutron controller to send and receive commands and status"""
        self._conn.connect()

    def send(self, op: str, cmd: str, integration_id: int, *args: Any) -> None:
        """Formats and sends the requested command to the Lutron controller."""
        out_cmd = ",".join(
            (cmd, str(integration_id)) + tuple((str(x) for x in args if x is not None))
        )
        self._conn.send(op + out_cmd)

    def load_xml_db(self, cache_path: Optional[str] = None) -> bool:
        """Load the Lutron database from the server.

        If a locally cached copy is available, use that instead.
        """

        xml_db: Optional[bytes] = None
        loaded_from: Optional[str] = None
        if cache_path:
            try:
                with open(cache_path, "rb") as f:
                    xml_db = f.read()
                    loaded_from = "cache"
            except Exception:
                pass
        if not loaded_from:
            import urllib.request

            url = "http://" + self._host + "/DbXmlInfo.xml"
            with urllib.request.urlopen(url) as xmlfile:
                xml_db = xmlfile.read()
                loaded_from = "repeater"

        _LOGGER.info("Loaded xml db from %s", loaded_from)

        assert xml_db is not None

        parser = LutronXmlDbParser(lutron=self, xml_db_str=xml_db)
        assert parser.parse()  # throw our own exception
        self._areas = parser.areas
        self._name = parser.project_name or ""

        _LOGGER.info("Found Lutron project: %s, %d areas", self._name, len(self.areas))

        if cache_path and loaded_from == "repeater":
            with open(cache_path, "wb") as f:
                f.write(xml_db)

        return True
