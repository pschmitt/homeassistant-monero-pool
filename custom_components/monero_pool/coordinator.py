"""Data update coordinator for Monero pool stats."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HashvaultClient, MoneroPoolData, P2poolClient, XmrigProxyClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .exceptions import MoneroPoolAuthError, MoneroPoolConnectionError

_LOGGER = logging.getLogger(__name__)


class MoneroPoolCoordinator(DataUpdateCoordinator[MoneroPoolData]):
    """Coordinate periodic fetches for one Monero pool source."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: HashvaultClient | P2poolClient | XmrigProxyClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(
                seconds=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> MoneroPoolData:
        """Fetch data from the configured source."""
        try:
            return await self.client.async_fetch_data()
        except MoneroPoolAuthError as err:
            raise ConfigEntryAuthFailed from err
        except MoneroPoolConnectionError as err:
            raise UpdateFailed(str(err)) from err
