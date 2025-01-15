"""Support for Probe Plus BLE sensors."""

import logging

from homeassistant import config_entries
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTemperature,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory
)
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ProbePlusData, ProbePlusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="probe_temperature",
        icon="mdi:thermometer-bluetooth",
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    SensorEntityDescription(
        key="probe_battery",
        icon="mdi:battery",
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=PERCENTAGE
    ),
    SensorEntityDescription(
        key="relay_battery",
        icon="mdi:battery",
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=PERCENTAGE
    ),
    SensorEntityDescription(
        key="probe_rssi",
        icon="mdi:bluetooth-connect",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="relay_voltage",
        icon="mdi:flash-triangle",
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="probe_voltage",
        icon="mdi:flash-triangle",
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the scale sensors."""
    _LOGGER.debug("Setting up scale sensors for entry: %s", entry.entry_id)
    address = entry.unique_id
    coordinator: ProbePlusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    entities += [
        ProbeSensor(entry.title, address, coordinator, desc)
        for desc in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)
    await coordinator.async_start()
    _LOGGER.debug("Probe sensors setup completed for entry: %s", entry.entry_id)


class ProbeSensor(RestoreSensor):
    """Base sensor implementation for Etekcity scale measurements."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False

    def __init__(
        self,
        name: str,
        address: str,
        coordinator: ProbePlusDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the scale sensor.

        Args:
            name: The name of the sensor.
            address: The Bluetooth address of the scale.
            coordinator: The data update coordinator for the scale.
            entity_description: Description of the sensor entity.

        """
        self.entity_description = entity_description
        self._attr_device_class = entity_description.device_class
        self._attr_state_class = entity_description.state_class
        self._attr_native_unit_of_measurement = (
            entity_description.native_unit_of_measurement
        )
        self._attr_icon = entity_description.icon

        self._attr_name = f"{entity_description.key.replace("_", " ").title()}"

        self._attr_unique_id = f"{name}_{entity_description.key}"

        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            name=name,
            manufacturer="Etekcity",
        )
        self._coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        _LOGGER.debug("Adding sensor to Home Assistant: %s", self.entity_id)
        await super().async_added_to_hass()

        self._attr_available = await self.async_restore_data()

        self.async_on_remove(self._coordinator.add_listener(self.handle_update))
        _LOGGER.info("Sensor added to Home Assistant: %s", self.entity_id)

    async def async_restore_data(self) -> bool:
        """Restore last state from storage."""
        if last_state := await self.async_get_last_sensor_data():
            _LOGGER.debug("Restoring previous state for sensor: %s", self.entity_id)
            self._attr_native_value = last_state.native_value
            return True
        return False

    def handle_update(
        self,
        data: ProbePlusData,
    ) -> None:
        """Handle updated data from the probe.

        This method is called when new data is received from the probe.
        It updates the sensor's state and triggers a state update in Home Assistant.

        Args:
            data: The new probe data.

        """
        if hasattr(data, self.entity_description.key):
            _LOGGER.debug(
                "Received update for sensor %s: %s",
                self.entity_id,
                self.entity_description.key,
            )
            self._attr_available = True
            self._attr_native_value = getattr(data, self.entity_description.key)

            self.async_write_ha_state()
            _LOGGER.debug("Sensor %s updated successfully", self.entity_id)
