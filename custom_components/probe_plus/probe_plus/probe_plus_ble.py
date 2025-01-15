"""Probe Plus BLE Base."""

import asyncio
import logging
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak_retry_connector import establish_connection

from .bluetooth import create_adv_receiver
from .parser import ParserBase, ProbePlusData

_LOGGER = logging.getLogger(__name__)

class ProbePlusDevice(ParserBase):
    """Represent a ProbePlus device."""

    _notification_callback = None
    _address: str = ""
    _client: BleakClient = None
    _connect_lock = asyncio.Lock()

    def __init__(
            self,
            address: str,
            notification_callback: Callable[[ProbePlusData], None],
            unavailble_callback
    ):
        """Init Probe Plus Device."""
        self._address = address
        self._notification_callback = notification_callback
        self._scanner = create_adv_receiver(self._advertisement_callback)
        self._notification_callback = notification_callback
        self._unavailable_callback = unavailble_callback

    async def async_start(self) -> None:
        """Start the callbacks."""
        _LOGGER.debug(
            "Starting EtekcitySmartFitnessScale for address: %s", self._address
        )
        await self._scanner.start()

    async def async_stop(self) -> None:
        """Stop the callbacks."""
        _LOGGER.debug(
            "Stopping EtekcitySmartFitnessScale for address: %s", self._address
        )
        await self._scanner.stop()

    def _notification_handler(self, _sender: int, data: bytearray):
        """Handle notifications from Probe or Relay."""
        _LOGGER.debug("%s: Notification received: %s", self._address, data.hex())
        return self.parse_data(data)

    async def _advertisement_callback(
        self, ble_device: BLEDevice, _: AdvertisementData
    ) -> None:
        """Connects to the device through BLE and retrieves relevant data."""
        if ble_device.address != self._address or self._client:
            return
        try:
            async with self._connect_lock:
                if self._client:
                    return
                self._scanner.unset_adv_callback()
                self._client = await establish_connection(
                    BleakClient,
                    ble_device,
                    self._address,
                    self._unavailable_callback
                )
                _LOGGER.debug("Connected to probe %s", self._address)
            await self._client.start_notify(
                "",
                self._notification_handler
            )
        except Exception as ex:
            self._client = None
            self._scanner.set_adv_callback(self._advertisement_callback)
            _LOGGER.exception("%s(%s)", type(ex), ex.args)
