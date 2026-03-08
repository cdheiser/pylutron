"""Constants and Enums for pylutron."""

import socket
from enum import Enum

# All Lutron commands start with one of these characters
# See http://www.lutron.com/TechnicalDocumentLibrary/040249.pdf
OP_EXECUTE = '#'
OP_QUERY = '?'
OP_RESPONSE = '~'

# We brute force exception handling in a number of areas to ensure
# connections can be recovered
_EXPECTED_NETWORK_EXCEPTIONS = (
    BrokenPipeError,
    # OSError: [Errno 101] Network unreachable
    OSError,
    EOFError,
    TimeoutError,
    socket.timeout,
)

class PowerSource(Enum):
    """Enum values representing power source, reported by queries to
    battery-powered devices."""

    # Values from ?HELP,?DEVICE,22
    UNINITIALIZED = -1
    UNKNOWN = 0
    BATTERY = 1
    EXTERNAL = 2

class BatteryStatus(Enum):
    """Enum values representing battery state, reported by queries to
    battery-powered devices."""

    # Values from ?HELP,?DEVICE,22 don't match the documentation, using what's in the doc.
    #?HELP says:
    # <0-NOT BATTERY POWERED, 1-DEVICE_BATTERY_STATUS_UNKNOWN, 2-DEVICE_BATTERY_STATUS_GOOD, 3-DEVICE_BATTERY_STATUS_LOW, 4-DEVICE_STATUS_MIA>5-DEVICE_STATUS_NOT_ACTIVATED>
    UNINITIALIZED = -1
    NORMAL = 1
    LOW = 2
    OTHER = 3  # not sure what this value means
