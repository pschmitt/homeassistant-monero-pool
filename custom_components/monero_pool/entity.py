"""Base entities for Monero pool stats."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import MoneroPoolCoordinator


def suggest_entity_id(domain: str, coordinator: MoneroPoolCoordinator, suffix: str) -> str:
    """Suggest an entity ID based on the config entry title."""
    return f"{domain}.{slugify(f'{coordinator.config_entry.title} {suffix}')}"


class MoneroPoolEntity(CoordinatorEntity[MoneroPoolCoordinator]):
    """Base entity for Monero pool sensors."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the monitored pool source."""
        entry = self.coordinator.config_entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=self.coordinator.client.manufacturer,
            model=self.coordinator.client.server_name,
            entry_type=DeviceEntryType.SERVICE,
        )

