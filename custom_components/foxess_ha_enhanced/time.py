from __future__ import annotations

import logging
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .sensor import setScheduler

_LOGGER = logging.getLogger(__name__)


def _parse_time_str(s: str) -> dt_time:
    """Parse a 'HH:MM' string into a datetime.time object."""
    try:
        h, m = s.split(":")
        return dt_time(int(h), int(m))
    except (ValueError, AttributeError):
        return dt_time(0, 0)


def _format_time(t: dt_time) -> str:
    """Format a datetime.time as 'HH:MM'."""
    return f"{t.hour:02d}:{t.minute:02d}"


def _device_info(coordinator, deviceID):
    from homeassistant.helpers.entity import DeviceInfo

    info = DeviceInfo(
        identifiers={(DOMAIN, deviceID)},
        name=coordinator.name_prefix,
        manufacturer="FoxESS",
    )
    if coordinator.data and "addressbook" in coordinator.data:
        ab = coordinator.data["addressbook"]
        model = ab.get("deviceType")
        if model:
            info["model"] = model
        sw = ab.get("masterVersion")
        if sw and sw != "not provided":
            info["sw_version"] = sw
    return info


class FoxESSSchedulerPeriodTime(CoordinatorEntity, TimeEntity):
    """Time entity for the start or end time of a scheduler period."""

    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator,
        name: str,
        deviceID: str,
        deviceSN: str,
        apiKey: str,
        period: int,
        is_start: bool,
    ):
        super().__init__(coordinator=coordinator)
        self._period = period
        self._is_start = is_start
        boundary = "Start" if is_start else "End"
        self._time_key = "start" if is_start else "end"
        self._attr_name = f"{name} - Scheduler Period {period + 1} {boundary}"
        self._attr_unique_id = f"{deviceID}scheduler-p{period + 1}-{self._time_key}-time"
        self._deviceSN = deviceSN
        self._apiKey = apiKey
        self._deviceID = deviceID

    @property
    def device_info(self):
        return _device_info(self.coordinator, self._deviceID)

    @property
    def available(self) -> bool:
        return self.coordinator.data.get("scheduler", {}).get("loaded", False)

    @property
    def native_value(self) -> dt_time | None:
        groups = self.coordinator.data.get("scheduler", {}).get("groups", [])
        if self._period < len(groups):
            raw = groups[self._period].get(self._time_key, "00:00")
            return _parse_time_str(raw)
        return None

    async def async_set_value(self, value: dt_time) -> None:
        groups = self.coordinator.data["scheduler"]["groups"]
        groups[self._period][self._time_key] = _format_time(value)
        await setScheduler(
            self.hass, self._deviceSN, self._apiKey, groups, coordinator=self.coordinator,
        )
        self.coordinator.async_set_updated_data(self.coordinator.data)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get("name", coordinator.name_prefix)
    device_id = entry.data["deviceID"]
    device_sn = entry.data["deviceSN"]
    api_key = entry.data["apiKey"]

    entities = []
    for i in range(3):
        entities.append(
            FoxESSSchedulerPeriodTime(coordinator, name, device_id, device_sn, api_key, period=i, is_start=True)
        )
        entities.append(
            FoxESSSchedulerPeriodTime(coordinator, name, device_id, device_sn, api_key, period=i, is_start=False)
        )
    async_add_entities(entities)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    return
