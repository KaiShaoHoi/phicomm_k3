"""
Support for PHICOMM K3 router.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.asuswrt/
"""
import logging
import requests
from datetime import timedelta
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

def get_scanner(hass, config):
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
        self.success_init = self._login()

    def _login(self):
        """Login to the router to obtain a token."""
        login_data = {
            "method": "set",
            "module": {"security": {"login": {"username": self.username, "password": self.password}}},
            "_deviceType": "pc"
        }
        try:
            response = requests.post(LOGIN_URL.format(self.host), json=login_data)
            response.raise_for_status()
            data = response.json()
            if "module" in data and "security" in data["module"] and "login" in data["module"]["security"]:
                self.token = data["module"]["security"]["login"]["stok"]
                return True
            else:
                _LOGGER.error("Unexpected response format: %s", data)
                return False
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Error logging in to the router: %s", err)
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
            response = requests.post(DEVICE_LIST_URL.format(self.host, self.token), json=device_list_data)
            response.raise_for_status()
            data = response.json()
            if "module" in data and "device_manage" in data["module"] and "client_list" in data["module"]["device_manage"]:
                return {
                    unquote(device["mac"]): {
                        'host': unquote(device["name"]),
                        'status': 'IN_ASSOCLIST',
                        'mac': unquote(device["mac"])
                    }
                    for device in data["module"]["device_manage"]["client_list"]
                    if device["online_status"] == 1
                }
            else:
                _LOGGER.error("Unexpected response format: %s", data)
                return {}
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Error retrieving device list from the router: %s", err)
            return {}

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        return self._get_device_list().get(device, {}).get('host')