# Monero Pool for Home Assistant

`monero_pool` is a Home Assistant custom integration for Monero mining stats.
It supports Hashvault.pro wallet stats and XMRig proxy `/1/workers` stats.

## Features

- UI config flow for Hashvault.pro and XMRig proxy sources
- Aggregate hashrate, worker count, and miner count sensors
- Hashvault payout sensors for confirmed balance, payout progress, total paid,
  payout threshold, and last withdrawal time
- XMRig proxy sensors for 1m, 10m, and 1h aggregate hashrates plus accepted and
  rejected shares when exposed by the proxy
- Dynamic per-worker hashrate sensors
- Options flow for the poll interval

## Installation

[![Open this integration in Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=pschmitt&repository=homeassistant-monero-pool&category=integration)

### Home Assistant Marketplace

Click the badge above to add this repository. For older installations, add
`https://github.com/pschmitt/homeassistant-monero-pool` to HACS as a custom
integration repository. Install **Monero Pool**, then restart Home Assistant.

### Manual

Copy `custom_components/monero_pool/` into your Home Assistant
`custom_components/` directory, then restart Home Assistant.

## Configuration

Go to **Settings -> Devices & services -> Add integration** and search for
**Monero Pool**.

For Hashvault.pro, enter the wallet address. The default API URL is
`https://api.hashvault.pro`.

For XMRig proxy, enter the full workers endpoint URL, for example:

```text
http://10.0.0.10:9674/1/workers
```

If the proxy HTTP API is only bound to localhost on the mining host, set the
endpoint URL to the remote localhost URL and fill **SSH host** with the host HA
should SSH into:

```text
Workers endpoint URL: http://127.0.0.1:9674/1/workers
SSH host: pschmitt@rofl-12.brkn.lol
```

If your proxy API requires an access token, enter it in the token field.

## License

GPL-3.0-or-later - see [LICENSE](LICENSE).
