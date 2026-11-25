"""Battery sensor for the PawPrint Light Controller integration."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, PERCENTAGE

from . import DOMAIN


class PawPrintBatterySensor(SensorEntity):
    """Expose the latest PawPrint V1.1 battery report."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "PawPrint Battery"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, bridge) -> None:
        """Bind the sensor to the BLE bridge."""
        self._bridge = bridge
        self._attr_unique_id = None
        if bridge.address:
            address_key = bridge.address.replace(":", "").lower()
            self._attr_unique_id = f"pawprint-{address_key}-battery"

    @property
    def native_value(self) -> int | None:
        """Return the latest battery percentage."""
        return self._bridge.battery


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the PawPrint battery sensor discovered by the integration."""
    bridge = hass.data[DOMAIN]
    sensor = PawPrintBatterySensor(bridge)
    bridge.battery_sensor = sensor
    async_add_entities([sensor])
