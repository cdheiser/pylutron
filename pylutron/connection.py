"""Encapsulates the connection to the Lutron controller."""

import asyncio
import logging
import socket
import threading
from typing import Any, Callable, Optional, Union

import telnetlib3

from .const import _EXPECTED_NETWORK_EXCEPTIONS
from .exceptions import ConnectionExistsError, LutronException

_LOGGER = logging.getLogger(__name__)


class LutronConnection(threading.Thread):
    """Encapsulates the connection to the Lutron controller."""

    USER_PROMPT = b"login: "
    PW_PROMPT = b"password: "
    PROMPT = b"GNET> "

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        recv_callback: Callable[[str], None],
        connection_factory: Any = telnetlib3.open_connection,
    ) -> None:
        """Initializes the lutron connection, doesn't actually connect."""
        threading.Thread.__init__(self)

        self._host = host
        self._user = user.encode("ascii")
        self._password = password.encode("ascii")
        self._reader: Optional[telnetlib3.TelnetReader] = None
        self._writer: Optional[telnetlib3.TelnetWriter] = None
        self._connected = False
        self._lock = threading.Lock()
        self._connect_cond = threading.Condition(lock=self._lock)
        self._recv_cb = recv_callback
        self._connection_factory = connection_factory
        self._done = False
        self._loop = asyncio.new_event_loop()

        self.daemon = True

    def connect(self) -> None:
        """Connects to the lutron controller."""
        if self._connected or self.is_alive():
            raise ConnectionExistsError("Already connected")
        # After starting the thread we wait for it to post us
        # an event signifying that connection is established. This
        # ensures that the caller only resumes when we are fully connected.
        self.start()
        with self._lock:
            self._connect_cond.wait_for(lambda: self._connected)

    def send(self, cmd: str) -> None:
        """Sends the specified command to the lutron controller.

        Must not hold self._lock.
        """
        _LOGGER.debug("Sending: %s", cmd)
        with self._lock:
            if not self._connected:
                _LOGGER.debug("Ignoring send of '%s' because we are disconnected.", cmd)
                return
            asyncio.run_coroutine_threadsafe(self._send_coro(cmd), self._loop)

    async def _send_coro(self, cmd: Union[str, bytes]) -> None:
        """Coroutine to send data and drain."""
        if self._writer:
            try:
                if isinstance(cmd, str):
                    cmd = cmd.encode("ascii")
                self._writer.write(cmd + b"\r\n")
                await self._writer.drain()
            except _EXPECTED_NETWORK_EXCEPTIONS:
                _LOGGER.exception("Error sending %r", cmd)
                with self._lock:
                    self._disconnect_locked()

    async def _do_login(self) -> None:
        """Executes the login procedure (telnet) as well as setting up some
        connection defaults like turning off the prompt, etc."""
        _LOGGER.info("Starting login to %s", self._host)
        self._reader, self._writer = await self._connection_factory(
            self._host, 23, connect_timeout=5, encoding=None
        )

        # Ensure we know that connection goes away somewhat quickly
        try:
            sock = self._writer.get_extra_info("socket")
            assert sock is not None
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Some operating systems may not include TCP_KEEPIDLE (macOS, variants of Windows)
            if hasattr(socket, "TCP_KEEPIDLE"):
                # Send keepalive probes after 60 seconds of inactivity
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            # Wait 10 seconds for an ACK
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            # Send 3 probes before we give up
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        except OSError:
            _LOGGER.exception("error configuring socket")

        assert self._reader is not None
        assert self._writer is not None

        await self._reader.readuntil(LutronConnection.USER_PROMPT)
        self._writer.write(self._user + b"\r\n")
        await self._reader.readuntil(LutronConnection.PW_PROMPT)
        self._writer.write(self._password + b"\r\n")

        # If we get USER_PROMPT again, it means login failed
        try:
            await asyncio.wait_for(
                self._reader.readuntil(LutronConnection.PROMPT), timeout=3.0
            )
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Timeout waiting for GNET prompt, checking if we are back at login"
            )
            raise LutronException("Login failed (timeout or invalid credentials)")

        await self._send_coro("#MONITORING,12,2")
        await self._send_coro("#MONITORING,255,2")
        await self._send_coro("#MONITORING,3,1")
        await self._send_coro("#MONITORING,4,1")
        await self._send_coro("#MONITORING,5,1")
        await self._send_coro("#MONITORING,6,1")
        await self._send_coro("#MONITORING,8,1")

    def _disconnect_locked(self) -> None:
        """Closes the current connection. Assume self._lock is held."""
        was_connected = self._connected
        self._connected = False
        self._connect_cond.notify_all()
        if self._writer:
            self._writer.close()
        self._writer = None
        self._reader = None
        if was_connected:
            _LOGGER.warning("Disconnected")

    async def _main_loop(self) -> None:
        """Main body of the the thread function.

        This will maintain connection and receive remote status updates.
        """
        while not self._done:
            try:
                await self._do_login()
                with self._lock:
                    self._connected = True
                    self._connect_cond.notify_all()
                _LOGGER.info("Connected")

                while not self._done:
                    assert self._reader is not None
                    line = await self._reader.readline()
                    if not line:
                        _LOGGER.warning("Connection closed by remote")
                        break
                    self._recv_cb(line.decode("ascii").rstrip())
            except LutronException:
                _LOGGER.exception("Fatal error during login")
                # For fatal errors like auth failure, we might want to stop or notify
                # For now, let's stop the loop to avoid infinite spamming
                self._done = True
            except _EXPECTED_NETWORK_EXCEPTIONS:
                _LOGGER.exception("Network exception in main loop")
            except Exception:
                _LOGGER.exception("Uncaught exception in main loop")

            with self._lock:
                self._disconnect_locked()

            if not self._done:
                # don't spam reconnect
                await asyncio.sleep(5)

    def run(self) -> None:
        """Main entry point into our receive thread.

        It just wraps _main_loop() so we can catch exceptions.
        """
        _LOGGER.info("Started")
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception:
            _LOGGER.exception("Uncaught exception in run")
            raise
