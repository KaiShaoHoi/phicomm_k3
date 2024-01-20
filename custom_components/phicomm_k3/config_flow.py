"""Config flow for PHICOMM K3 router."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_PROTOCOL
)
from .const import DOMAIN

class PhicommK3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PHICOMM K3 router."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # TODO: Implement your connection and authentication logic here
            # If the connection is successful:
            return self.async_create_entry(title="PHICOMM K3", data=user_input)
            # Otherwise, add an error to indicate what went wrong:
            # errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_PORT, default=22): int,
            vol.Optional(CONF_PROTOCOL, default="ssh"): vol.In(["ssh", "telnet"]),
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )