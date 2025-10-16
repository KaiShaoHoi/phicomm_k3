"""
Support for PHICOMM K3 router.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.asuswrt/
"""
import logging
import requests
from datetime import timedelta
import time
import voluptuous as vol
from urllib.parse import unquote
from homeassistant.components.device_tracker import (DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import (CONF_HOST, CONF_PASSWORD, CONF_USERNAME)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=5)

# URL Constants
LOGIN_URL = "http://{}/cgi-bin/"
DEVICE_LIST_URL = "http://{}/cgi-bin/stok={}/data"

# Schema
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})

def get_scanner(_hass, config):
    """Validate the configuration and return a Phicomm K3 scanner."""
    scanner = PhicommDeviceScanner(config[DOMAIN])
    return scanner if scanner.success_init else None

class PhicommDeviceScanner(DeviceScanner):
    """This class queries a Phicomm K3 router."""
    
    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]
        self.token = None
        self._last_error_code = None  # remember last error code to avoid log spam
        self._last_error_log_time = None  # monotonic seconds
        self.success_init = self._login(initial=True)

    def _should_log_error(self, error_code):
        """Return True if we should log this error code now (avoid spamming)."""
        now = time.monotonic()
        if (
            error_code != self._last_error_code or
            self._last_error_log_time is None or
            (now - self._last_error_log_time) > 300
        ):
            self._last_error_code = error_code
            self._last_error_log_time = now
            return True
        return False

    def _login(self, initial: bool = False):
        """Login to the router to obtain a token.

        Returns True on success, False otherwise.
        When initial=True we log more explicit errors.
        """
        login_data = {
            "method": "set",
            "module": {"security": {"login": {"username": self.username, "password": self.password}}},
            "_deviceType": "pc"
        }
        try:
            response = requests.post(LOGIN_URL.format(self.host), json=login_data)
            response.raise_for_status()
            data = response.json()
            if not self._validate_login_response(data):
                return False
            self.token = data["module"]["security"]["login"]["stok"]
            if initial:
                _LOGGER.debug("Obtained stok token successfully")
            return True
        except requests.exceptions.RequestException as err:
            # network related
            if initial or self._should_log_error("login_network"):
                _LOGGER.error("Error logging in to the router: %s", err)
            return False

    def _validate_login_response(self, data):
        """Validate login JSON and log errors appropriately."""
        # error_code present & non-zero
        if data.get("error_code") not in (None, 0):
            code = data["error_code"]
            if self._should_log_error(code):
                if code == -10401:
                    _LOGGER.error("Login failed (error_code -10401). Check username/password or firmware compatibility.")
                else:
                    _LOGGER.error("Login failed with error_code %s: %s", code, data)
            return False
        # structure
        try:
            _ = data["module"]["security"]["login"]["stok"]
            return True
        except (KeyError, TypeError):
            if self._should_log_error("login_format"):
                _LOGGER.error("Unexpected login response format: %s", data)
            return False

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        devices = self._get_device_list()
        return list(devices.keys())

    def _get_device_list(self):
        """Get the list of connected devices."""
        if not self.token:
            _LOGGER.error("Not logged in to the router")
            return {}
        
        device_list_data = {
            "method": "get",
            "module": {"device_manage": {"client_list": None}},
            "_deviceType": "pc"
        }
        try:
            data = self._fetch_device_list(device_list_data)
            if not data:
                return {}
            clients = self._extract_clients(data)
            if clients is None:
                return {}
            return {
                unquote(device["mac"]): {
                    'host': unquote(device.get("name", "Unknown")),
                    'status': 'IN_ASSOCLIST',
                    'mac': unquote(device["mac"])
                }
                for device in clients if device.get("online_status") == 1 and device.get("mac")
            }
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Error retrieving device list from the router: %s", err)
            return {}

    def _fetch_device_list(self, payload):
        """Fetch raw device list JSON; handle token expiry and single retry."""
        data = self._post_for_data(payload)
        if data is None:
            return None
        code = data.get("error_code")
        if code in (None, 0):
            return data
        if code == -10401:
            return self._handle_token_expired(payload)
        # other error codes
        if self._should_log_error(code):
            _LOGGER.error("Device list request failed with error_code %s: %s", code, data)
        return None

    def _post_for_data(self, payload):
        url = DEVICE_LIST_URL.format(self.host, self.token)
        response = requests.post(url, json=payload)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            if self._should_log_error("device_list_json"):
                _LOGGER.error("Non-JSON response retrieving device list")
            return None

    def _handle_token_expired(self, payload):
        if self._should_log_error(-10401):
            _LOGGER.warning("Token invalid or expired (error_code -10401). Attempting re-login.")
        if not self._login():
            return None
        data_retry = self._post_for_data(payload)
        if not data_retry:
            return None
        retry_code = data_retry.get("error_code")
        if retry_code not in (None, 0):
            if self._should_log_error(retry_code):
                _LOGGER.error("Retry device list failed with error_code %s: %s", retry_code, data_retry)
            return None
        return data_retry

    def _extract_clients(self, data):
        """Extract client list array from response or log format error."""
        try:
            return data["module"]["device_manage"]["client_list"]
        except (KeyError, TypeError):
            if self._should_log_error("device_list_format"):
                _LOGGER.error("Unexpected device list response format: %s", data)
            return None

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        return self._get_device_list().get(device, {}).get('host')