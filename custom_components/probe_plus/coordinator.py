"""Coordinator for the probe_plus integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date
import logging

from homeassistant.core import callback

from .probe_plus.probe_plus_ble import ProbePlusDevice
from .probe_plus.parser import ProbePlusData

_LOGGER = logging.getLogger(__name__)


class ProbePlusDataUpdateCoordinator:
    """Coordinator to manage data updates for a probe device.

    This class handles the communication with Probe Plus devices
    and coordinates updates to the Home Assistant entities.
    """

    _client: ProbePlusDevice = None

    body_metrics_enabled: bool = False

    def __init__(self, address: str) -> None:
        """Initialize the ProbePlusDataUpdateCoordinator.

        Args:
            address (str): The Bluetooth address of the scale.

        """
        self.address = address
        self._lock = asyncio.Lock()
        self._listeners: dict[Callable[[], None], Callable[[ProbePlusData], None]] = {}

    async def _async_start(self) -> None:
        if self._client:
            _LOGGER.debug("Stopping existing client")
            await self._client.async_stop()

        _LOGGER.debug("Initializing new ProbePlusDevice client")
        self._client = ProbePlusDevice(
            self.address, self.update_listeners, None
        )
        await self._client.async_start()

    @callback
    async def async_start(self) -> None:
        """Start the coordinator and initialize the probe client.

        This method sets up the ProbePlusDevice client and starts
        listening for updates from the probe.

        """
        _LOGGER.debug(
            "Starting ProbePlusDataUpdateCoordinator for address: %s", self.address
        )
        async with self._lock:
            await self._async_start()
        _LOGGER.debug("ProbePlusDataUpdateCoordinator started successfully")

    @callback
    async def async_stop(self) -> None:
        """Stop the coordinator and clean up resources."""
        _LOGGER.debug(
            "Stopping ProbePlusDataUpdateCoordinator for address: %s", self.address
        )
        async with self._lock:
            if self._client:
                await self._client.async_stop()
                self._client = None
        _LOGGER.debug("ProbePlusDataUpdateCoordinator stopped successfully")

    @callback
    def add_listener(
        self, update_callback: Callable[[ProbePlusData], None]
    ) -> Callable[[], None]:
        """Listen for data updates."""

        @callback
        def remove_listener() -> None:
            """Remove update listener."""
            self._listeners.pop(remove_listener)

        self._listeners[remove_listener] = update_callback
        return remove_listener

    @callback
    def update_listeners(self, data: ProbePlusData) -> None:
        """Update all registered listeners."""
        for update_callback in list(self._listeners.values()):
            update_callback(data)
