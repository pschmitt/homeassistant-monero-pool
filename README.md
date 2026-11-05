<p align="center">
  <img src="logo.png" width="128" alt="Monero Pool integration logo">
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=pschmitt&amp;repository=homeassistant-monero-pool&amp;category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open this integration in Home Assistant Marketplace"></a>
</p>

<h1 align="center">Monero Pool for Home Assistant</h1>

<p align="center">Track Hashvault wallet payouts or XMRig proxy workers in Home Assistant.</p>

## Features

- **Hashvault stats:** Show balance, payout progress, total paid, withdrawal time and aggregate hashrate.
- **XMRig proxy stats:** Report one-, ten- and sixty-minute hashrates and available share counts.
- **Worker sensors:** Create per-worker hashrate sensors from the proxy response.
- **Polling:** Adjust the update interval in the integration options.

## Install

Use the Marketplace badge above on Home Assistant 2026.11 or later to add this
repository as a custom integration. On older versions, add it as a HACS
custom repository of type **Integration**. Install and restart Home Assistant.
The badge does not imply a public catalog listing. For manual installation,
copy `custom_components/monero_pool` into Home Assistant's `custom_components/`
directory and restart.

## Quick start

1. Add **Monero Pool** under **Settings → Devices & services → Add integration**.
2. For Hashvault, enter a wallet address; the default API is
   `https://api.hashvault.pro`.
3. For XMRig proxy, enter the full workers endpoint URL, such as
   `http://miner.example.com:9674/1/workers`.
4. Inspect the aggregate and per-worker sensors.

For a proxy HTTP API bound only to localhost, use
`http://127.0.0.1:9674/1/workers` as the endpoint and enter
`user@miner.example.com` as the SSH host. Enter an access token if the proxy
requires one.

## License

[GPL-3.0-or-later](LICENSE).
