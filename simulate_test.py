import sys
import types

# Minimal mocks so that importing the integration doesn't require full Home Assistant
ha_core = types.ModuleType('homeassistant.core')
ha_helpers = types.ModuleType('homeassistant.helpers')
ha_helpers.typing = types.ModuleType('homeassistant.helpers.typing')
ha_components = types.ModuleType('homeassistant.components')
device_tracker_mod = types.ModuleType('homeassistant.components.device_tracker')
device_tracker_mod.DOMAIN = 'device_tracker'
class DummyDeviceScanner:
    pass
device_tracker_mod.DeviceScanner = DummyDeviceScanner
device_tracker_mod.PLATFORM_SCHEMA = object()
ha_const = types.ModuleType('homeassistant.const')
ha_const.CONF_HOST = 'host'
ha_const.CONF_USERNAME = 'username'
ha_const.CONF_PASSWORD = 'password'
ha_util = types.ModuleType('homeassistant.util')
def Throttle(x):
    def deco(f):
        return f
    return deco
ha_util.Throttle = Throttle
ha_helpers.config_validation = types.SimpleNamespace()
sys.modules['homeassistant'] = types.ModuleType('homeassistant')
sys.modules['homeassistant.core'] = ha_core
sys.modules['homeassistant.components'] = ha_components
sys.modules['homeassistant.components.device_tracker'] = device_tracker_mod
sys.modules['homeassistant.const'] = ha_const
sys.modules['homeassistant.helpers'] = ha_helpers
sys.modules['homeassistant.helpers.config_validation'] = ha_helpers.config_validation
sys.modules['homeassistant.util'] = ha_util

from custom_components.phicomm_k3.device_tracker import PhicommDeviceScanner

import requests

responses = []

class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        return
    def json(self):
        return self._payload

call_count = {"login":0, "device":0}

def fake_post(url, json=None, **kwargs):
    if 'stok=' in url:
        call_count['device'] += 1
        # First device list call returns token expired, second returns data
        if call_count['device'] == 1:
            return FakeResponse({"error_code": -10401})
        else:
            return FakeResponse({
                "module": {"device_manage": {"client_list": [
                    {"mac": "AA:BB:CC:DD:EE:FF", "name": "TestDevice", "online_status": 1}
                ]}}
            })
    else:
        call_count['login'] += 1
        return FakeResponse({
            "module": {"security": {"login": {"stok": f"TOKEN{call_count['login']}"}}},
            "error_code": 0
        })

# Patch
requests.post = fake_post

# Run
scanner = PhicommDeviceScanner({"host":"router.local","username":"u","password":"p"})
print('Init success:', scanner.success_init, 'Token:', scanner.token)
print('Devices:', scanner._get_device_list())
print('Requests counts:', call_count)
