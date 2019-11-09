"""Platform to retrieve Energy Consumption from United Energy."""
"""
The "United Energy" custom component.
Configuration:
To use the United Energy sensor you will need to add the following to your
configuration.yaml file.
sensor:
  - platform: unitedenergy
    username: <username>
    password: <password>

Current implementation does
* Only caters for a single default meter on the account
* Only reads peak load and does not report on offpeak, shoulder or regen
* Reports as the data becomes available on UE's platform actual hour by hour data is likely to trial by a couple of hours
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_NAME,
    DEVICE_CLASS_POWER,
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
from . import unitedenergy, enums

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "unitedenergy"

HOURLY_SCAN_INTERVAL = timedelta(hours=1)
DAILY_SCAN_INTERVAL = timedelta(hours=1)
MONTHLY_SCAN_INTERVAL = timedelta(days=1)


HOURLY_NAME = "United Energy Hourly"
DAILY_NAME = "United Energy Daily"
MONTHLY_NAME = "United Energy Monthly"
MONTHLY_CUMULATIVE_NAME = "United Energy Monthly Cumulative"

HOURLY_TYPE = "hourly"
DAILY_TYPE = "daily"
MONTHLY_TYPE = "monthly"
MONTHLY_CUMULATIVE_TYPE = "monthly_cumulative"

ICON = "mdi:flash"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]

    try:
        ue_client = unitedenergy.UnitedEnergy(username, password, True)
    except Exception as exp:
        _LOGGER.error(exp)
        return

    data = UEData(ue_client)

    sensors = []
    sensors.append(UESensor(data, HOURLY_NAME, HOURLY_TYPE))
    sensors.append(UESensor(data, DAILY_NAME, DAILY_TYPE))
    sensors.append(UESensor(data, MONTHLY_NAME, MONTHLY_TYPE))
    sensors.append(UESensor(data, MONTHLY_CUMULATIVE_NAME, MONTHLY_CUMULATIVE_TYPE))
    add_entities(sensors, True)

class UEData:

    def __init__(self, client: unitedenergy.UnitedEnergy):
        self.ue_client = client

        self._last_hourly_timestamp = None
        self._hourly_usage = None
        self._hourly_price = None

        self._last_daily_usage_timestamp = None
        self._daily_usage = None
        self._daily_price = None

        self._last_monthly_usage_timestamp = None
        self._monthly_usage = None
        self._monthly_price = None

        self._last_monthly_cumulative_usage_timestamp = None
        self._monthly_cumulative_usage = None
        self._monthly_cumulative_price = None

    @property
    def hourly_usage(self):
        return self._hourly_usage

    @property
    def last_hourly_timestamp(self):
        return self._last_hourly_timestamp

    @property
    def hourly_price(self):
        return self._hourly_price

    @Throttle(HOURLY_SCAN_INTERVAL)
    def update_hourly_usage(self):
        try:
            result = self.ue_client.fetch_last_reading(enums.ReportPeriod.day, enums.PeriodOffset.current)
            self._hourly_usage = result["total"]
            self._hourly_price = result["price"]
            self._last_hourly_timestamp = result["timestamp"]
        except KeyError as error:
            _LOGGER.error("Missing key in result: %s: %s", result, error)

    @property
    def daily_usage(self):
        return self._daily_usage

    @property
    def last_daily_timestamp(self):
        return self._last_daily_timestamp

    @property
    def daily_price(self):
        return self._daily_price

    @Throttle(DAILY_SCAN_INTERVAL)
    def update_daily_usage(self):
        try:
            result = self.ue_client.fetch_last_reading(enums.ReportPeriod.month, enums.PeriodOffset.current)
            self._daily_usage = result["total"]
            self._daily_price = result["price"]
            self._last_daily_timestamp = result["timestamp"]
        except KeyError as error:
            _LOGGER.error("Missing key in result: %s: %s", result, error)

    @property
    def monthly_usage(self):
        return self._monthly_usage

    @property
    def last_monthly_timestamp(self):
        return self._last_monthly_timestamp

    @property
    def monthly_price(self):
        return self._monthly_price

    @Throttle(MONTHLY_SCAN_INTERVAL)
    def update_monthly_usage(self):
        try:
            result = self.ue_client.fetch_last_reading(enums.ReportPeriod.year, enums.PeriodOffset.current)
            self._monthly_usage = result["total"]
            self._monthly_price = result["price"]
            self._last_monthly_timestamp = result["timestamp"]
        except KeyError as error:
            _LOGGER.error("Missing key in result: %s: %s", result, error)

    @property
    def monthly_cumulative_usage(self):
        return self._monthly_cumulative_usage

    @property
    def last_monthly_cumulative_timestamp(self):
        return self._last_monthly_cumulative_timestamp

    @property
    def monthly_cumulative_price(self):
        return self._monthly_cumulative_price

    @Throttle(MONTHLY_SCAN_INTERVAL)
    def update_monthly_cumulative_usage(self):
        try:
            result = self.ue_client.fetch_cumilitive_reading(enums.ReportPeriod.year, enums.PeriodOffset.current)
            self._monthly_cumulative_usage = result["total"]
            self._monthly_cumulative_price = result["price"]
            self._last_monthly_cumulative_timestamp = result["timestamp"]
        except KeyError as error:
            _LOGGER.error("Missing key in result: %s: %s", result, error)

class UESensor(Entity):

    def __init__(self, data, name, sensor_type):
        self._name = name
        self._data = data
        self._state = None
        self._prev_timestamp = None
        self._attributes = {}
        self._sensor_type = sensor_type
        self._unit_of_measurement = ENERGY_KILO_WATT_HOUR

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def device_state_attributes(self):
        return self._attributes

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def icon(self):
        return ICON

    @property
    def device_class(self):
        return DEVICE_CLASS_POWER

    def update(self):
        update_function = getattr(self._data, f"update_{self._sensor_type}_usage")
        update_function()

        self._attributes["last_update_timestamp"] = getattr(
            self._data, f"last_{self._sensor_type}_timestamp"
        )
        _LOGGER.debug("Current reporting timestamp: %s Previous timestamp: %s", self._attributes["last_update_timestamp"], self._prev_timestamp)
        # dont track the same value twice.
        if self._attributes["last_update_timestamp"] == self._prev_timestamp:
            return
        self._prev_timestamp = self._attributes["last_update_timestamp"]

        self._state = getattr(self._data, f"{self._sensor_type}_usage")

        self._attributes["price"] = getattr(
            self._data, f"{self._sensor_type}_price"
        )
