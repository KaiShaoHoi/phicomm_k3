"""
Config flow for PHICOMM K3 router.
"""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from .const import DOMAIN
import requests

class PhicommK3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PHICOMM K3 router."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Attempt to login and get a token
            try:
                login_data = {
                    "method": "set",
                    "module": {
                        "security": {
                            "login": {
                                "username": user_input[CONF_USERNAME],
                                "password": user_input[CONF_PASSWORD]
                            }
                        }
                    },
                    "_deviceType": "pc"
                }
                response = requests.post(f"http://{user_input[CONF_HOST]}/cgi-bin/", json=login_data)
                response.raise_for_status()
                data = response.json()
                
                if "error_code" in data and data["error_code"] != 0:
                    raise ValueError("Login failed")

                token = data["module"]["security"]["login"]["stok"]
                user_input["token"] = token

                return self.async_create_entry(title="PHICOMM K3", data=user_input)

            except requests.exceptions.RequestException:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_auth"

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "host": "Host (IP address or hostname of your router)",
                "username": "Username (Your router's login username)",
                "password": "Password (Your router's login password)"
            }
        )
