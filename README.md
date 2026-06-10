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

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pschmitt&repository=homeassistant-monero-pool&category=integration)

Add `https://github.com/pschmitt/homeassistant-monero-pool` as a custom HACS
integration repository, install **Monero Pool**, then restart Home Assistant.

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

If your proxy API requires an access token, enter it in the token field.

## License

GPL-3.0-or-later - see [LICENSE](LICENSE).

