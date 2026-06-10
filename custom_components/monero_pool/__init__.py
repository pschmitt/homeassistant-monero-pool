"""The Monero Pool integration."""

from __future__ import annotations

from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import HashvaultClient, XmrigProxyClient
from .const import (
    CONF_API_URL,
    CONF_MODE,
    CONF_SSH_HOST,
    CONF_SSH_KNOWN_HOSTS,
    CONF_SSH_PRIVATE_KEY,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    CONF_WALLET,
    DOMAIN,
    MODE_HASHVAULT,
    PLATFORMS,
)
from .coordinator import MoneroPoolCoordinator


def create_client(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> HashvaultClient | XmrigProxyClient:
    """Create the API client for the configured mode."""
    session = async_create_clientsession(
        hass,
        verify_ssl=data[CONF_VERIFY_SSL],
        cookie_jar=aiohttp.CookieJar(unsafe=True),
    )
    if data[CONF_MODE] == MODE_HASHVAULT:
        return HashvaultClient(
            session=session,
            api_url=data[CONF_API_URL],
            wallet=data[CONF_WALLET],
        )
    return XmrigProxyClient(
        session=session,
        url=data[CONF_URL],
        token=data.get(CONF_TOKEN, ""),
        ssh_host=data.get(CONF_SSH_HOST, ""),
        ssh_known_hosts=data.get(CONF_SSH_KNOWN_HOSTS, ""),
        ssh_private_key=data.get(CONF_SSH_PRIVATE_KEY, ""),
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Monero Pool integration."""
    del config
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Monero Pool from a config entry."""
    client = create_client(hass, dict(config_entry.data))
    coordinator = MoneroPoolCoordinator(hass, client, config_entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a Monero Pool config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    runtime = hass.data[DOMAIN].pop(config_entry.entry_id)
    await runtime["client"].async_close()
    return unload_ok


async def async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the integration after options changes."""
    await hass.config_entries.async_reload(config_entry.entry_id)
