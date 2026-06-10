"""Constants for the Monero Pool integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "monero_pool"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_MODE = "mode"
CONF_WALLET = "wallet"
CONF_API_URL = "api_url"
CONF_SSH_HOST = "ssh_host"
CONF_SSH_KNOWN_HOSTS = "ssh_known_hosts"
CONF_SSH_PRIVATE_KEY = "ssh_private_key"
CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"

MODE_HASHVAULT = "hashvault"
MODE_XMRIG_PROXY = "xmrig_proxy"

DEFAULT_HASHVAULT_API_URL = "https://api.hashvault.pro"
DEFAULT_XMRIG_PROXY_URL = "http://127.0.0.1:9674/1/workers"
DEFAULT_SCAN_INTERVAL = 120
MIN_SCAN_INTERVAL = 30
DEFAULT_REQUEST_TIMEOUT = 20
DEFAULT_VERIFY_SSL = True

PICOMONERO = 1_000_000_000_000
