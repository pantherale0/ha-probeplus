"""The probe_plus integration."""

from __future__ import annotations

import logging

from typing import Final

from bleak.backends.device import BLEDevice
from bleak_retry_connector import close_stale_connections_by_address

from homeassistant.components.bluetooth import async_ble_device_from_address, async_rediscover_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import ProbePlusDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up scale from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id

    assert address is not None
    await close_stale_connections_by_address(address)

    ble_device: Final[BLEDevice | None] = async_ble_device_from_address(
        hass, entry.unique_id, True
    )

    if ble_device is None:
        _LOGGER.debug("Failed to discover device %s via Bluetooth", entry.unique_id)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "MAC": entry.unique_id,
            },
        )

    coordinator = ProbePlusDataUpdateCoordinator(ble_device)

    hass.data.setdefault(DOMAIN, {})
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: ProbePlusDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
        async_rediscover_address(hass, coordinator.address)

    return unload_ok
