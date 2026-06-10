"""Config flow for Monero Pool."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import create_client
from .api import normalize_url
from .const import (
    CONF_API_URL,
    CONF_MODE,
    CONF_SSH_HOST,
    CONF_SSH_KNOWN_HOSTS,
    CONF_SSH_PRIVATE_KEY,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    CONF_WALLET,
    DEFAULT_HASHVAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DEFAULT_XMRIG_PROXY_URL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    MODE_HASHVAULT,
    MODE_XMRIG_PROXY,
)
from .exceptions import MoneroPoolAuthError, MoneroPoolConnectionError

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate config flow input."""
    client = create_client(hass, data)
    try:
        await client.async_validate()
    finally:
        await client.async_close()

    unique_source = data[CONF_WALLET] if data[CONF_MODE] == MODE_HASHVAULT else (
        f"{data.get(CONF_SSH_HOST, '')}:{data[CONF_URL]}"
    )
    return {
        "title": data.get(CONF_NAME) or client.server_name,
        "unique_id": f"{data[CONF_MODE]}:{unique_source}",
    }


def hashvault_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the Hashvault form schema."""
    return vol.Schema(
        {
            vol.Required(CONF_WALLET, default=defaults.get(CONF_WALLET, "")): TextSelector(),
            vol.Optional(
                CONF_API_URL,
                default=defaults.get(CONF_API_URL, DEFAULT_HASHVAULT_API_URL),
            ): TextSelector(),
            vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, "Hashvault")): TextSelector(),
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): BooleanSelector(),
        }
    )


def xmrig_proxy_schema(
    defaults: dict[str, Any],
    *,
    token_required: bool = False,
) -> vol.Schema:
    """Return the XMRig proxy form schema."""
    token_marker: vol.Marker
    if token_required:
        token_marker = vol.Required(CONF_TOKEN, default=defaults.get(CONF_TOKEN, ""))
    else:
        token_marker = vol.Optional(CONF_TOKEN)
    return vol.Schema(
        {
            vol.Required(
                CONF_URL,
                default=defaults.get(CONF_URL, DEFAULT_XMRIG_PROXY_URL),
            ): TextSelector(),
            vol.Optional(CONF_SSH_HOST, default=defaults.get(CONF_SSH_HOST, "")): TextSelector(),
            vol.Optional(CONF_SSH_KNOWN_HOSTS): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            vol.Optional(CONF_SSH_PRIVATE_KEY): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            token_marker: TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(
                CONF_NAME,
                default=defaults.get(CONF_NAME, "XMRig Proxy"),
            ): TextSelector(),
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): BooleanSelector(),
        }
    )


class MoneroPoolConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Monero Pool."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MoneroPoolOptionsFlow:
        """Return the options flow for this handler."""
        return MoneroPoolOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Let the user pick a stats source."""
        del user_input
        return self.async_show_menu(
            step_id="user",
            menu_options=[MODE_HASHVAULT, MODE_XMRIG_PROXY],
        )

    async def async_step_hashvault(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle adding a Hashvault wallet."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_MODE: MODE_HASHVAULT,
                CONF_WALLET: user_input[CONF_WALLET].strip(),
                CONF_API_URL: normalize_url(user_input[CONF_API_URL]),
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            try:
                info = await validate_input(self.hass, data)
            except MoneroPoolAuthError:
                errors["base"] = "invalid_auth"
            except MoneroPoolConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while validating Hashvault config")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or info["title"],
                    data=data,
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id=MODE_HASHVAULT,
            data_schema=hashvault_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_xmrig_proxy(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle adding an XMRig proxy endpoint."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_MODE: MODE_XMRIG_PROXY,
                CONF_URL: normalize_url(user_input[CONF_URL]),
                CONF_SSH_HOST: user_input.get(CONF_SSH_HOST, "").strip(),
                CONF_SSH_KNOWN_HOSTS: user_input.get(CONF_SSH_KNOWN_HOSTS, ""),
                CONF_SSH_PRIVATE_KEY: user_input.get(CONF_SSH_PRIVATE_KEY, ""),
                CONF_TOKEN: user_input.get(CONF_TOKEN, ""),
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            try:
                info = await validate_input(self.hass, data)
            except MoneroPoolAuthError:
                errors["base"] = "invalid_auth"
            except MoneroPoolConnectionError as err:
                _LOGGER.warning("XMRig proxy connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while validating XMRig proxy config")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or info["title"],
                    data=data,
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id=MODE_XMRIG_PROXY,
            data_schema=xmrig_proxy_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()
        mode = entry.data[CONF_MODE]
        if mode == MODE_HASHVAULT:
            return await self._async_reconfigure_hashvault(entry, user_input)
        return await self._async_reconfigure_xmrig_proxy(entry, user_input)

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Handle re-authentication when the source rejects credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Prompt for fresh credentials (mode-appropriate) and validate them."""
        entry = self._get_reauth_entry()
        mode = entry.data[CONF_MODE]
        errors: dict[str, str] = {}

        if user_input is not None:
            if mode == MODE_HASHVAULT:
                data = {
                    **entry.data,
                    CONF_WALLET: user_input[CONF_WALLET].strip(),
                    CONF_API_URL: normalize_url(user_input[CONF_API_URL]),
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                }
            else:
                data = {
                    **entry.data,
                    CONF_URL: normalize_url(user_input[CONF_URL]),
                    CONF_SSH_HOST: user_input.get(CONF_SSH_HOST, "").strip(),
                    CONF_SSH_KNOWN_HOSTS: user_input.get(CONF_SSH_KNOWN_HOSTS)
                    or entry.data.get(CONF_SSH_KNOWN_HOSTS, ""),
                    CONF_SSH_PRIVATE_KEY: user_input.get(CONF_SSH_PRIVATE_KEY)
                    or entry.data.get(CONF_SSH_PRIVATE_KEY, ""),
                    CONF_TOKEN: user_input.get(CONF_TOKEN)
                    or entry.data.get(CONF_TOKEN, ""),
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                }
            try:
                info = await validate_input(self.hass, data)
            except MoneroPoolAuthError:
                errors["base"] = "invalid_auth"
            except MoneroPoolConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during Monero Pool reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data=data,
                    unique_id=info["unique_id"],
                )

        defaults = {**entry.data, CONF_NAME: entry.title}
        schema = (
            hashvault_schema(defaults)
            if mode == MODE_HASHVAULT
            else xmrig_proxy_schema(defaults)
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def _async_reconfigure_hashvault(
        self,
        entry: ConfigEntry,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Reconfigure Hashvault."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **entry.data,
                CONF_WALLET: user_input[CONF_WALLET].strip(),
                CONF_API_URL: normalize_url(user_input[CONF_API_URL]),
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            try:
                info = await validate_input(self.hass, data)
            except MoneroPoolAuthError:
                errors["base"] = "invalid_auth"
            except MoneroPoolConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while reconfiguring Hashvault")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    title=user_input.get(CONF_NAME) or info["title"],
                    data=data,
                    unique_id=info["unique_id"],
                )

        defaults = {**entry.data, CONF_NAME: entry.title}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=hashvault_schema(defaults),
            errors=errors,
        )

    async def _async_reconfigure_xmrig_proxy(
        self,
        entry: ConfigEntry,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Reconfigure XMRig proxy."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **entry.data,
                CONF_URL: normalize_url(user_input[CONF_URL]),
                CONF_SSH_HOST: user_input.get(CONF_SSH_HOST, "").strip(),
                CONF_SSH_KNOWN_HOSTS: user_input.get(CONF_SSH_KNOWN_HOSTS)
                or entry.data.get(CONF_SSH_KNOWN_HOSTS, ""),
                CONF_SSH_PRIVATE_KEY: user_input.get(CONF_SSH_PRIVATE_KEY) or entry.data.get(CONF_SSH_PRIVATE_KEY, ""),
                CONF_TOKEN: user_input.get(CONF_TOKEN) or entry.data.get(CONF_TOKEN, ""),
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            try:
                info = await validate_input(self.hass, data)
            except MoneroPoolAuthError:
                errors["base"] = "invalid_auth"
            except MoneroPoolConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while reconfiguring XMRig proxy")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    title=user_input.get(CONF_NAME) or info["title"],
                    data=data,
                    unique_id=info["unique_id"],
                )

        defaults = {**entry.data, CONF_NAME: entry.title}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=xmrig_proxy_schema(defaults),
            errors=errors,
        )


class MoneroPoolOptionsFlow(OptionsFlow):
    """Handle options for Monero Pool."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage Monero Pool options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            mode=NumberSelectorMode.BOX,
                            step=1,
                        )
                    )
                }
            ),
        )
