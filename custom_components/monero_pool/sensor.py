"""Sensor platform for Monero pool stats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HashvaultStats, HashvaultWorker, XmrigProxyStats, XmrigWorker
from .const import DOMAIN, MODE_HASHVAULT, MODE_XMRIG_PROXY
from .coordinator import MoneroPoolCoordinator
from .entity import MoneroPoolEntity, suggest_entity_id

HASHRATE_UNIT = "H/s"


@dataclass(frozen=True, kw_only=True)
class MoneroPoolSensorDescription(SensorEntityDescription):
    """Description for a Monero pool sensor."""

    value_attr: str


HASHVAULT_DESCRIPTIONS: tuple[MoneroPoolSensorDescription, ...] = (
    MoneroPoolSensorDescription(
        key="hash_rate",
        translation_key="hash_rate",
        icon="mdi:speedometer",
        native_unit_of_measurement=HASHRATE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_attr="hash_rate",
    ),
    MoneroPoolSensorDescription(
        key="miners",
        translation_key="miners",
        icon="mdi:pickaxe",
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="miners",
    ),
    MoneroPoolSensorDescription(
        key="workers_count",
        translation_key="workers",
        icon="mdi:account-hard-hat",
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="workers_count",
    ),
    MoneroPoolSensorDescription(
        key="confirmed_balance",
        translation_key="confirmed_balance",
        icon="mdi:wallet",
        native_unit_of_measurement="XMR",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=6,
        value_attr="confirmed_balance",
    ),
    MoneroPoolSensorDescription(
        key="payout_progress",
        translation_key="payout_progress",
        icon="mdi:progress-check",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_attr="payout_progress",
    ),
    MoneroPoolSensorDescription(
        key="total_paid",
        translation_key="total_paid",
        icon="mdi:cash-multiple",
        native_unit_of_measurement="XMR",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=6,
        value_attr="total_paid",
    ),
    MoneroPoolSensorDescription(
        key="payout_threshold",
        translation_key="payout_threshold",
        icon="mdi:cash-lock",
        native_unit_of_measurement="XMR",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=6,
        value_attr="payout_threshold",
    ),
    MoneroPoolSensorDescription(
        key="daily_credited",
        translation_key="daily_credited",
        icon="mdi:calendar-today",
        native_unit_of_measurement="XMR",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=6,
        value_attr="daily_credited",
    ),
    MoneroPoolSensorDescription(
        key="avg24_hash_rate",
        translation_key="avg24_hash_rate",
        icon="mdi:speedometer-medium",
        native_unit_of_measurement=HASHRATE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_attr="avg24_hash_rate",
    ),
    MoneroPoolSensorDescription(
        key="last_withdrawal",
        translation_key="last_withdrawal",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_attr="last_withdrawal",
    ),
)

XMRIG_PROXY_DESCRIPTIONS: tuple[MoneroPoolSensorDescription, ...] = (
    MoneroPoolSensorDescription(
        key="hashrate_1m",
        translation_key="hashrate_1m",
        icon="mdi:speedometer",
        native_unit_of_measurement=HASHRATE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_attr="hashrate_1m",
    ),
    MoneroPoolSensorDescription(
        key="hashrate_10m",
        translation_key="hashrate_10m",
        icon="mdi:speedometer-medium",
        native_unit_of_measurement=HASHRATE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_attr="hashrate_10m",
    ),
    MoneroPoolSensorDescription(
        key="hashrate_1h",
        translation_key="hashrate_1h",
        icon="mdi:speedometer-slow",
        native_unit_of_measurement=HASHRATE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_attr="hashrate_1h",
    ),
    MoneroPoolSensorDescription(
        key="accepted",
        translation_key="accepted",
        icon="mdi:check-circle-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_attr="accepted",
    ),
    MoneroPoolSensorDescription(
        key="rejected",
        translation_key="rejected",
        icon="mdi:close-circle-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_attr="rejected",
    ),
    MoneroPoolSensorDescription(
        key="workers_count",
        translation_key="workers",
        icon="mdi:account-hard-hat",
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="workers_count",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monero Pool sensors from a config entry."""
    coordinator: MoneroPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]
    mode = config_entry.data["mode"]
    aggregate_descriptions = (
        HASHVAULT_DESCRIPTIONS if mode == MODE_HASHVAULT else XMRIG_PROXY_DESCRIPTIONS
    )
    entities: list[SensorEntity] = [
        MoneroPoolAggregateSensor(coordinator, description)
        for description in aggregate_descriptions
    ]
    if mode == MODE_HASHVAULT:
        entities.append(HashvaultEtaSensor(coordinator))
    async_add_entities(entities)

    known_workers: set[str] = set()

    @callback
    def async_add_missing_worker_entities() -> None:
        data = coordinator.data
        new_entities: list[SensorEntity] = []
        if isinstance(data, HashvaultStats):
            for worker_id, worker in data.workers.items():
                if worker_id in known_workers:
                    continue
                known_workers.add(worker_id)
                new_entities.append(HashvaultWorkerHashrateSensor(coordinator, worker))
        elif isinstance(data, XmrigProxyStats):
            for worker_id, worker in data.workers.items():
                if worker_id in known_workers:
                    continue
                known_workers.add(worker_id)
                new_entities.append(XmrigWorkerHashrateSensor(coordinator, worker))

        if new_entities:
            async_add_entities(new_entities)

    async_add_missing_worker_entities()
    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_missing_worker_entities)
    )


class MoneroPoolAggregateSensor(MoneroPoolEntity, SensorEntity):
    """Aggregate sensor for one Monero pool source."""

    entity_description: MoneroPoolSensorDescription

    def __init__(
        self,
        coordinator: MoneroPoolCoordinator,
        description: MoneroPoolSensorDescription,
    ) -> None:
        """Initialize the aggregate sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}:{description.key}"
        )
        self.entity_id = suggest_entity_id(
            "sensor",
            coordinator,
            str(description.translation_key or description.key).replace("_", " "),
        )

    @property
    def native_value(self) -> int | float | datetime | None:
        """Return the current aggregate value."""
        data = self.coordinator.data
        value = getattr(data, self.entity_description.value_attr)
        if self.entity_description.key == "last_withdrawal":
            if not value:
                return None
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful aggregate attributes."""
        data = self.coordinator.data
        attrs: dict[str, Any] = {"server_name": data.server_name}
        if isinstance(data, HashvaultStats):
            attrs["wallet"] = data.wallet
            attrs["worker_names"] = [worker.name for worker in data.workers.values()]
        if isinstance(data, XmrigProxyStats):
            attrs.update(
                {
                    "hashrate_12h": data.hashrate_12h,
                    "hashrate_24h": data.hashrate_24h,
                    "hashrate_lifetime": data.hashrate_lifetime,
                }
            )
        return attrs


class HashvaultEtaSensor(MoneroPoolEntity, SensorEntity):
    """Estimated next payout timestamp for a Hashvault wallet."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:cash-clock"
    _attr_has_entity_name = True

    def __init__(self, coordinator: MoneroPoolCoordinator) -> None:
        """Initialize the ETA sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}:next_payout_eta"
        self._attr_name = "Next Payout ETA"
        self.entity_id = suggest_entity_id("sensor", coordinator, "next payout eta")

    @property
    def native_value(self) -> datetime | None:
        """Return estimated next payout datetime."""
        data = self.coordinator.data
        if not isinstance(data, HashvaultStats):
            return None

        now = datetime.now(tz=UTC)

        # Hashrate-adjusted estimate using pool's daily credited rate
        if (
            data.daily_credited
            and data.daily_credited > 0
            and data.avg24_hash_rate
            and data.avg24_hash_rate > 0
            and data.hash_rate
            and data.hash_rate > 0
            and data.payout_threshold
            and data.confirmed_balance is not None
        ):
            projected_daily = data.daily_credited * (data.hash_rate / data.avg24_hash_rate)
            remaining = data.payout_threshold - data.confirmed_balance
            if projected_daily > 0 and remaining > 0:
                return now + timedelta(seconds=(remaining / projected_daily) * 86400)

        # Fallback: linear extrapolation from last payout
        if data.last_withdrawal and data.payout_progress and data.payout_progress > 0:
            last_dt = datetime.fromtimestamp(data.last_withdrawal / 1000, tz=UTC)
            elapsed_s = (now - last_dt).total_seconds()
            if elapsed_s > 0:
                eta_s = ((100 - data.payout_progress) / data.payout_progress) * elapsed_s
                return now + timedelta(seconds=eta_s)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return human-readable time remaining."""
        eta = self.native_value
        if eta is None:
            return {}
        total_s = max(0.0, (eta - datetime.now(tz=UTC)).total_seconds())
        d = int(total_s // 86400)
        h = int((total_s % 86400) // 3600)
        m = int((total_s % 3600) // 60)
        if d:
            label = f"{d}d"
        elif h:
            label = f"{h}h"
        else:
            label = f"{m}min"
        return {"time_remaining": label}


class HashvaultWorkerHashrateSensor(MoneroPoolEntity, SensorEntity):
    """Hashvault worker hashrate sensor."""

    _attr_icon = "mdi:pickaxe"
    _attr_native_unit_of_measurement = HASHRATE_UNIT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _unrecorded_attributes = frozenset({"raw"})

    def __init__(
        self,
        coordinator: MoneroPoolCoordinator,
        worker: HashvaultWorker,
    ) -> None:
        """Initialize the worker sensor."""
        super().__init__(coordinator)
        self._worker_id = worker.worker_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}:hashvault_worker:{worker.worker_id}:hash_rate"
        )
        self._attr_name = f"{worker.name} Hashrate"
        self.entity_id = suggest_entity_id("sensor", coordinator, f"{worker.name} hashrate")

    @property
    def worker(self) -> HashvaultWorker | None:
        """Return the current worker data."""
        data = self.coordinator.data
        if not isinstance(data, HashvaultStats):
            return None
        return data.workers.get(self._worker_id)

    @property
    def available(self) -> bool:
        """Return whether the worker still exists."""
        return self.coordinator.last_update_success and self.worker is not None

    @property
    def native_value(self) -> float | None:
        """Return worker hashrate."""
        worker = self.worker
        return worker.hash_rate if worker else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return worker attributes."""
        worker = self.worker
        if worker is None:
            return {}
        return {
            "active_miners": worker.active_miners,
            "raw": worker.raw,
        }


class XmrigWorkerHashrateSensor(MoneroPoolEntity, SensorEntity):
    """XMRig worker hashrate sensor."""

    _attr_icon = "mdi:pickaxe"
    _attr_native_unit_of_measurement = HASHRATE_UNIT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _unrecorded_attributes = frozenset({"raw"})

    def __init__(
        self,
        coordinator: MoneroPoolCoordinator,
        worker: XmrigWorker,
    ) -> None:
        """Initialize the worker sensor."""
        super().__init__(coordinator)
        self._worker_id = worker.worker_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}:xmrig_worker:{worker.worker_id}:hashrate_1m"
        )
        self._attr_name = f"{worker.name} Hashrate"
        self.entity_id = suggest_entity_id("sensor", coordinator, f"{worker.name} hashrate")

    @property
    def worker(self) -> XmrigWorker | None:
        """Return the current worker data."""
        data = self.coordinator.data
        if not isinstance(data, XmrigProxyStats):
            return None
        return data.workers.get(self._worker_id)

    @property
    def available(self) -> bool:
        """Return whether the worker still exists."""
        return self.coordinator.last_update_success and self.worker is not None

    @property
    def native_value(self) -> float | None:
        """Return 1 minute worker hashrate."""
        worker = self.worker
        return worker.hashrate_1m if worker else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return XMRig worker attributes."""
        worker = self.worker
        if worker is None:
            return {}
        return {
            "hashrate_10m": worker.hashrate_10m,
            "hashrate_1h": worker.hashrate_1h,
            "hashrate_12h": worker.hashrate_12h,
            "hashrate_24h": worker.hashrate_24h,
            "hashrate_lifetime": worker.hashrate_lifetime,
            "raw": worker.raw,
        }
