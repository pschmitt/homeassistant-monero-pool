"""Diagnostics support for Monero Pool."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import CONF_TOKEN, CONF_WALLET, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = dict(config_entry.data)
    if data.get(CONF_TOKEN):
        data[CONF_TOKEN] = "**REDACTED**"
    if data.get(CONF_WALLET):
        wallet = data[CONF_WALLET]
        data[CONF_WALLET] = f"{wallet[:8]}...{wallet[-8:]}" if len(wallet) > 20 else "**REDACTED**"
    return {
        "entry": {
            "title": config_entry.title,
            "data": data,
            "options": dict(config_entry.options),
        },
        "last_update_success": hass.data[DOMAIN][config_entry.entry_id][
            "coordinator"
        ].last_update_success,
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    del device
    return await async_get_config_entry_diagnostics(hass, config_entry)

