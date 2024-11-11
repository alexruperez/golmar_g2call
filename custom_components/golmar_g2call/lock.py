import requests
import logging
from homeassistant.components.lock import LockEntity
from homeassistant.components.persistent_notification import create
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CONTROL_URL = "https://tdkopenapir1.qvcloud.net/openapi-tdk/devctr/synccontrol/singledev"

async def async_setup_entry(hass, config_entry, async_add_entities):
    session_manager = hass.data[DOMAIN]
    entities = []

    # Create a Front Door and Back Door lock for each detected device
    for device_id in session_manager._device_ids:
        entities.append(GolmarLock(session_manager, device_id, 1, f"{device_id} - Front Door"))
        entities.append(GolmarLock(session_manager, device_id, 2, f"{device_id} - Back Door"))

    async_add_entities(entities)

class GolmarLock(LockEntity):
    def __init__(self, session_manager, device_id, locknumber, name):
        self._session_manager = session_manager
        self._device_id = device_id
        self._locknumber = locknumber
        self._name = name
        self._is_locked = True

    @property
    def name(self):
        return self._name

    @property
    def is_locked(self):
        return self._is_locked

    async def async_open(self):
        headers = {
            "Content-Type": "application/json",
            "Cookie": f"jsessionid={self._session_manager._jsessionid}",
        }
        payload = {
            "password": "encrypted_password_here",
            "deviceId": self._device_id,
            "content": {"password": "hashed_device_password", "door": 1, "locknumber": self._locknumber},
            "command": "set.device.opendoor"
        }
        response = requests.post(CONTROL_URL, json=payload, headers=headers)
        if response.status_code == 200 and response.json().get("result") == 0:
            _LOGGER.info(f"{self._name} opened successfully.")
            self._is_locked = False
        else:
            error_message = response.json().get("message", "Unknown error")
            _LOGGER.error(f"Failed to open {self._name}: {error_message}")
            create(self.hass, f"Failed to open {self._name}: {error_message}", title="Golmar Integration Error")
