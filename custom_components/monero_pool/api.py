"""Async clients and normalized models for Monero pool stats."""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import shlex
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlparse

import asyncssh
from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import DEFAULT_REQUEST_TIMEOUT, PICOMONERO
from .exceptions import MoneroPoolAuthError, MoneroPoolConnectionError

_LOGGER = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Normalize a configured URL."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url.rstrip("/")


def _as_float(value: Any) -> float | None:
    """Return value as float when possible."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    """Return value as int when possible."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        number = _as_float(value)
        return int(number) if number is not None else None


def _xmr_from_atomic(value: Any) -> float | None:
    """Convert atomic/piconero integer amounts to XMR."""
    atomic = _as_float(value)
    if atomic is None:
        return None
    return atomic / PICOMONERO


def _safe_rate(rates: Any, index: int) -> float | None:
    """Return one hashrate value from an XMRig rate array."""
    if not isinstance(rates, list) or index >= len(rates):
        return None
    return _as_float(rates[index])


@dataclass(slots=True, frozen=True)
class HashvaultWorker:
    """Normalized Hashvault worker data."""

    worker_id: str
    name: str
    hash_rate: float | None
    active_miners: int | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class HashvaultStats:
    """Normalized Hashvault wallet stats."""

    wallet: str
    server_name: str
    hash_rate: float | None
    avg24_hash_rate: float | None
    miners: int
    workers_count: int
    confirmed_balance: float | None
    payout_threshold: float | None
    payout_progress: float | None
    daily_credited: float | None
    total_paid: float | None
    last_withdrawal: int | None
    workers: dict[str, HashvaultWorker]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class XmrigWorker:
    """Normalized XMRig proxy worker stats."""

    worker_id: str
    name: str
    hashrate_1m: float | None
    hashrate_10m: float | None
    hashrate_1h: float | None
    hashrate_12h: float | None
    hashrate_24h: float | None
    hashrate_lifetime: float | None
    raw: list[Any] | dict[str, Any] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class XmrigProxyStats:
    """Normalized XMRig proxy stats."""

    server_name: str
    hashrate_1m: float | None
    hashrate_10m: float | None
    hashrate_1h: float | None
    hashrate_12h: float | None
    hashrate_24h: float | None
    hashrate_lifetime: float | None
    accepted: int | None
    rejected: int | None
    workers_count: int
    workers: dict[str, XmrigWorker]
    raw: dict[str, Any] = field(default_factory=dict)


MoneroPoolData = HashvaultStats | XmrigProxyStats


class HashvaultClient:
    """Client for Hashvault wallet stats."""

    manufacturer = "Hashvault"

    def __init__(
        self,
        session: ClientSession,
        api_url: str,
        wallet: str,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self.api_url = normalize_url(api_url)
        self.wallet = wallet.strip()
        self._request_timeout = request_timeout

    @property
    def server_name(self) -> str:
        """Return a friendly server name."""
        parsed = urlparse(self.api_url)
        return parsed.hostname or self.api_url

    async def async_close(self) -> None:
        """Close the underlying session."""
        await self._session.close()

    async def async_validate(self) -> HashvaultStats:
        """Validate by fetching one stats payload."""
        return await self.async_fetch_data()

    async def async_fetch_data(self) -> HashvaultStats:
        """Fetch and normalize Hashvault stats."""
        wallet = quote(self.wallet, safe="")
        payload = await self._async_request_json(
            f"/v3/monero/wallet/{wallet}/stats",
            params={"workers": "true"},
        )
        if not isinstance(payload, Mapping):
            raise MoneroPoolConnectionError("Unexpected Hashvault response")
        return self._normalize(payload)

    async def _async_request_json(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Request JSON from Hashvault."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            async with asyncio.timeout(self._request_timeout):
                response = await self._session.get(url, params=params)
                response.raise_for_status()
                return await response.json(content_type=None)
        except ClientResponseError as err:
            if err.status in {401, 403}:
                raise MoneroPoolAuthError("Hashvault rejected the request") from err
            raise MoneroPoolConnectionError(f"HTTP error {err.status} for Hashvault") from err
        except (ClientError, TimeoutError, ValueError) as err:
            raise MoneroPoolConnectionError("Failed to fetch Hashvault stats") from err

    def _normalize(self, payload: Mapping[str, Any]) -> HashvaultStats:
        """Normalize the Hashvault payload."""
        collective = payload.get("collective")
        revenue = payload.get("revenue")
        workers_payload = payload.get("collectiveWorkers")
        if not isinstance(collective, Mapping):
            collective = {}
        if not isinstance(revenue, Mapping):
            revenue = {}
        if not isinstance(workers_payload, list):
            workers_payload = []

        workers: dict[str, HashvaultWorker] = {}
        for index, worker in enumerate(workers_payload):
            if not isinstance(worker, Mapping):
                continue
            name = str(worker.get("name") or worker.get("worker") or f"worker_{index + 1}")
            worker_id = name.lower()
            workers[worker_id] = HashvaultWorker(
                worker_id=worker_id,
                name=name,
                hash_rate=_as_float(worker.get("hashRate") or worker.get("hashrate")),
                active_miners=_as_int(worker.get("activeMiners")),
                raw=dict(worker),
            )

        confirmed_balance = _xmr_from_atomic(revenue.get("confirmedBalance"))
        payout_threshold = _xmr_from_atomic(revenue.get("payoutThreshold"))
        payout_progress = None
        if confirmed_balance is not None and payout_threshold:
            payout_progress = confirmed_balance / payout_threshold * 100

        miners = sum(worker.active_miners or 0 for worker in workers.values())
        if not miners:
            miners = _as_int(collective.get("activeMiners")) or 0

        return HashvaultStats(
            wallet=self.wallet,
            server_name=self.server_name,
            hash_rate=_as_float(collective.get("hashRate") or collective.get("hashrate")),
            avg24_hash_rate=_as_float(collective.get("avg24hashRate")),
            miners=miners,
            workers_count=len(workers),
            confirmed_balance=confirmed_balance,
            payout_threshold=payout_threshold,
            payout_progress=payout_progress,
            daily_credited=_xmr_from_atomic(revenue.get("dailyCredited")),
            total_paid=_xmr_from_atomic(revenue.get("totalPaid")),
            last_withdrawal=_as_int(revenue.get("lastWithdrawal")),
            workers=workers,
            raw=dict(payload),
        )


class XmrigProxyClient:
    """Client for XMRig proxy /1/workers stats."""

    manufacturer = "XMRig"

    def __init__(
        self,
        session: ClientSession,
        url: str,
        token: str = "",
        ssh_host: str = "",
        ssh_known_hosts: str = "",
        ssh_private_key: str = "",
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        """Initialize the client."""
        self.url = normalize_url(url)
        self._session = session
        self._token = token
        self._ssh_host = ssh_host.strip()
        self._ssh_known_hosts = ssh_known_hosts.strip()
        self._ssh_private_key = ssh_private_key.strip()
        self._request_timeout = request_timeout

    @property
    def server_name(self) -> str:
        """Return a friendly server name."""
        parsed = urlparse(self.url)
        if parsed.hostname:
            return parsed.hostname
        return self.url

    async def async_close(self) -> None:
        """Close the underlying session."""
        await self._session.close()

    async def async_validate(self) -> XmrigProxyStats:
        """Validate by fetching one stats payload."""
        return await self.async_fetch_data()

    async def async_fetch_data(self) -> XmrigProxyStats:
        """Fetch and normalize XMRig proxy stats."""
        if self._ssh_host:
            return self._normalize(await self._async_fetch_data_via_ssh())

        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            async with asyncio.timeout(self._request_timeout):
                response = await self._session.get(self.url, headers=headers)
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except ClientResponseError as err:
            if err.status in {401, 403}:
                raise MoneroPoolAuthError("XMRig proxy rejected the request") from err
            raise MoneroPoolConnectionError(f"HTTP error {err.status} for XMRig proxy") from err
        except (ClientError, TimeoutError, ValueError) as err:
            raise MoneroPoolConnectionError("Failed to fetch XMRig proxy stats") from err

        if not isinstance(payload, Mapping):
            raise MoneroPoolConnectionError("Unexpected XMRig proxy response")
        return self._normalize(payload)

    async def _async_fetch_data_via_ssh(self) -> Mapping[str, Any]:
        """Fetch XMRig proxy stats via asyncssh by running curl on the remote host."""
        # Build known_hosts: prefer inline config, fall back to discovered files
        if self._ssh_known_hosts:
            try:
                known_hosts: Any = asyncssh.import_known_hosts(
                    self._ssh_known_hosts + "\n"
                )
            except (ValueError, asyncssh.Error) as err:
                raise MoneroPoolConnectionError(
                    f"Invalid SSH known_hosts data: {err}"
                ) from err
        else:
            known_hosts = [
                p
                for p in (
                    "/root/.ssh/known_hosts",
                    "/config/.ssh/known_hosts",
                    "/config/.config/ssh/known_hosts",
                )
                if os.path.isfile(p)
            ] or None

        # Build client_keys: use provided key or auto-discover identity files
        if self._ssh_private_key:
            try:
                # PEM/OpenSSH key material expects a trailing newline.
                client_keys: Any = [
                    asyncssh.import_private_key(self._ssh_private_key + "\n")
                ]
            except asyncssh.KeyImportError as err:
                raise MoneroPoolAuthError(f"Invalid SSH private key: {err}") from err
        else:
            discovered: list[str] = []
            for pattern in (
                "/root/.ssh/id_*",
                "/config/.ssh/id_*",
                "/config/.config/ssh/id_*",
            ):
                discovered.extend(
                    p
                    for p in sorted(glob.glob(pattern))
                    if not p.endswith(".pub") and os.path.isfile(p)
                )
            client_keys = discovered or None

        # Parse user@host
        if "@" in self._ssh_host:
            username, hostname = self._ssh_host.split("@", 1)
        else:
            username = None
            hostname = self._ssh_host

        # Build the remote curl command
        cmd_parts = ["curl", "-fsSL", "--max-time", str(self._request_timeout)]
        if self._token:
            cmd_parts.extend(["-H", f"Authorization: Bearer {self._token}"])
        cmd_parts.append(self.url)
        cmd = shlex.join(cmd_parts)

        connect_kwargs: dict[str, Any] = {
            "known_hosts": known_hosts,
            "client_keys": client_keys,
        }
        if username:
            connect_kwargs["username"] = username

        _LOGGER.debug(
            "SSH connecting to %s as %s (known_hosts=%s, client_keys=%s)",
            hostname, username, known_hosts, client_keys,
        )

        try:
            async with asyncio.timeout(self._request_timeout + 15):
                async with asyncssh.connect(hostname, **connect_kwargs) as conn:
                    result = await conn.run(cmd)
        except asyncssh.Error as err:
            err_str = str(err).lower()
            if "permission denied" in err_str or "authentication" in err_str:
                raise MoneroPoolAuthError(f"SSH authentication failed: {err}") from err
            raise MoneroPoolConnectionError(f"SSH error: {err}") from err
        except (OSError, TimeoutError) as err:
            raise MoneroPoolConnectionError("Failed to fetch XMRig proxy stats via SSH") from err

        if result.exit_status != 0:
            msg = (result.stderr or "").strip()
            _LOGGER.debug("SSH fetch failed (exit %d): %s", result.exit_status, msg)
            raise MoneroPoolConnectionError(
                f"XMRig proxy SSH fetch failed: {msg or result.exit_status}"
            )

        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, ValueError) as err:
            raise MoneroPoolConnectionError("Unexpected XMRig proxy SSH response") from err

        if not isinstance(payload, Mapping):
            raise MoneroPoolConnectionError("Unexpected XMRig proxy SSH response")
        return payload

    def _normalize(self, payload: Mapping[str, Any]) -> XmrigProxyStats:
        """Normalize an XMRig proxy workers payload."""
        hashrate = payload.get("hashrate")
        if not isinstance(hashrate, Mapping):
            hashrate = {}
        total_rates = hashrate.get("total")

        workers_payload = payload.get("workers")
        if not isinstance(workers_payload, list):
            workers_payload = []

        workers: dict[str, XmrigWorker] = {}
        for index, worker in enumerate(workers_payload):
            normalized = self._normalize_worker(worker, index)
            workers[normalized.worker_id] = normalized

        results = payload.get("results")
        if not isinstance(results, Mapping):
            results = {}

        return XmrigProxyStats(
            server_name=self.server_name,
            hashrate_1m=_safe_rate(total_rates, 0),
            hashrate_10m=_safe_rate(total_rates, 1),
            hashrate_1h=_safe_rate(total_rates, 2),
            hashrate_12h=_safe_rate(total_rates, 3),
            hashrate_24h=_safe_rate(total_rates, 4),
            hashrate_lifetime=_safe_rate(total_rates, 5),
            accepted=_as_int(results.get("accepted") or payload.get("accepted")),
            rejected=_as_int(results.get("rejected") or payload.get("rejected")),
            workers_count=len(workers),
            workers=workers,
            raw=dict(payload),
        )

    @staticmethod
    def _normalize_worker(worker: Any, index: int) -> XmrigWorker:
        """Normalize one XMRig worker record."""
        if isinstance(worker, Mapping):
            name = str(worker.get("name") or worker.get("worker") or f"worker_{index + 1}")
            rates = worker.get("hashrate") or worker.get("rates") or []
            raw: list[Any] | dict[str, Any] = dict(worker)
        elif isinstance(worker, list):
            name = str(worker[0] if worker else f"worker_{index + 1}")
            rates = worker[8] if len(worker) > 8 and isinstance(worker[8], list) else worker[8:]
            raw = list(worker)
        else:
            name = f"worker_{index + 1}"
            rates = []
            raw = []

        worker_id = name.lower()
        return XmrigWorker(
            worker_id=worker_id,
            name=name,
            hashrate_1m=_safe_rate(rates, 0),
            hashrate_10m=_safe_rate(rates, 1),
            hashrate_1h=_safe_rate(rates, 2),
            hashrate_12h=_safe_rate(rates, 3),
            hashrate_24h=_safe_rate(rates, 4),
            hashrate_lifetime=_safe_rate(rates, 5),
            raw=raw,
        )
