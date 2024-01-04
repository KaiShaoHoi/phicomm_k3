"""
Support for PHICOMM K3 router.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.asuswrt/
"""
import logging
import re
import socket
import telnetlib
from collections import namedtuple
import threading
import voluptuous as vol
from datetime import timedelta
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import (
    CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_PORT)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

REQUIREMENTS = ['pexpect==4.0.1']

_LOGGER = logging.getLogger(__name__)

MAIN = 'phicomm_k3'

CONF_PROTOCOL = 'protocol'
CONF_PUB_KEY = 'pub_key'
CONF_SSH_KEY = 'ssh_key'

DEFAULT_SSH_PORT = 22

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=5)

SECRET_GROUP = 'Password or SSH Key'

PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_PASSWORD, CONF_PUB_KEY, CONF_SSH_KEY),
    PLATFORM_SCHEMA.extend({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PROTOCOL, default='ssh'):
            vol.In(['ssh', 'telnet']),
        vol.Optional(CONF_PORT, default=DEFAULT_SSH_PORT): cv.port,
        vol.Exclusive(CONF_PASSWORD, SECRET_GROUP): cv.string,
        vol.Exclusive(CONF_SSH_KEY, SECRET_GROUP): cv.isfile,
        vol.Exclusive(CONF_PUB_KEY, SECRET_GROUP): cv.isfile
    }))


_WL_CMD = "wl -i eth1 assoclist;wl -i eth2 assoclist;cat /proc/net/arp | awk '{if(NR>1) print $4}'"



# pylint: disable=unused-argument
def get_scanner(hass, config):
    """Validate the configuration and return an ASUS-WRT scanner."""
    scanner = PhicommDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None



class PhicommDeviceScanner(DeviceScanner):
    """This class queries a router running ASUSWRT firmware."""

    # Eighth attribute needed for mode (AP mode vs router mode)
    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config.get(CONF_PASSWORD, '')
        self.ssh_key = config.get('ssh_key', config.get('pub_key', ''))
        self.protocol = config[CONF_PROTOCOL]
        self.port = config[CONF_PORT]

        if self.protocol == 'ssh':
            if not (self.ssh_key or self.password):
                _LOGGER.error("No password or private key specified")
                self.success_init = False
                return

            self.connection = SshConnection(self.host, self.port,
                                            self.username,
                                            self.password,
                                            self.ssh_key)
        else:
            if not self.password:
                _LOGGER.error("No password specified")
                self.success_init = False
                return

            self.connection = TelnetConnection(self.host, self.port,
                                               self.username,
                                               self.password)

        self.lock = threading.Lock()

        self.last_results = {}

        # Test the router is accessible.
        data = self.connection.get_result()
        self.success_init = data is not None

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        return self.last_results

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        return None


    def _update_info(self):
        """Ensure the information from the ASUSWRT router is up to date.
        Return boolean if scanning successful.
        """
        if not self.success_init:
            return False

        with self.lock:
            _LOGGER.info('Checking Devices')
            data = self.connection.get_result()
            if not data:
                return False

            self.last_results = []

            for key in data:
                if data[key]['status'] == 'IN_ASSOCLIST':
                    self.last_results.append(key)
            return True

class _Connection:
    def __init__(self):
        self._connected = False

    @property
    def connected(self):
        """Return connection state."""
        return self._connected

    def connect(self):
        """Mark currenct connection state as connected."""
        self._connected = True

    def disconnect(self):
        """Mark current connection state as disconnected."""
        self._connected = False


class SshConnection(_Connection):
    """Maintains an SSH connection to an ASUS-WRT router."""

    def __init__(self, host, port, username, password, ssh_key):
        """Initialize the SSH connection properties."""
        super(SshConnection, self).__init__()

        self._ssh = None
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssh_key = ssh_key



    def get_result(self):
        """Retrieve a single PhicommResult through an SSH connection.
        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        from pexpect import pxssh, exceptions



        try:
            if not self.connected:
                self.connect()
            neighbors = []
            neighbors_list = []
            self._ssh.sendline(_WL_CMD)
            self._ssh.prompt()
            neighbors_list = str(self._ssh.before,encoding = 'utf8').split('\n')[:-1]
            for i in neighbors_list:
                neighbors.append(i.replace('assoclist ','').replace('\n','').replace('\r',''))
            devices = {}
            for i in range(len(neighbors)):
                devices[neighbors[i]] = {
                    'host': 'phicomm_k3_device'+str(i),
                    'status': 'IN_ASSOCLIST',
                    'mac':neighbors[i],
                }
            return devices
        except exceptions.EOF as err:
            _LOGGER.error("Connection refused. SSH enabled?")
            self.disconnect()
            return None
        except pxssh.ExceptionPxssh as err:
            _LOGGER.error("Unexpected SSH error: %s", str(err))
            self.disconnect()
            return None
        except AssertionError as err:
            _LOGGER.error("Connection to router unavailable: %s", str(err))
            self.disconnect()
            return None




    def connect(self):
        """Connect to the ASUS-WRT SSH server."""
        from pexpect import pxssh
        self._ssh = pxssh.pxssh()
        if self._ssh_key:
            self._ssh.login(self._host, self._username,
                            ssh_key=self._ssh_key, port=self._port)
        else:
            self._ssh.login(self._host, self._username,
                            password=self._password, port=self._port)

        super(SshConnection, self).connect()

    def disconnect(self):   \
            # pylint: disable=broad-except
        """Disconnect the current SSH connection."""
        try:
            self._ssh.logout()
        except Exception:
            pass
        finally:
            self._ssh = None

        super(SshConnection, self).disconnect()
