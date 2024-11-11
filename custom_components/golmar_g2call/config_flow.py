import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

@config_entries.HANDLERS.register(DOMAIN)
class GolmarG2CallConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Basic field validation
            if not user_input["username"] or not user_input["password"]:
                errors["base"] = "complete_fields"
            else:
                return self.async_create_entry(title="Golmar G2Call+", data=user_input)
        
        data_schema = vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
