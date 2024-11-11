import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import timedelta
import aiohttp
import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.persistent_notification import create
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
AUTH_URL = "https://r1-2.qvcloud.net/auth/user;jus_duplex=down"
LOGIN_URL = "https://r1-2.qvcloud.net/auth/user;jus_duplex=up"
CONTROL_URL = "https://tdkopenapir1.qvcloud.net/openapi-tdk/devctr/synccontrol/singledev"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
CLIENT_ID = ""
OEM = ""
APP = ""

async def async_setup_entry(hass, config_entry):
    username = config_entry.data["username"]
    password = config_entry.data["password"]

    session_manager = SessionManager(username, password, hass)
    await session_manager.async_initialize()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Golmar Session Manager",
        update_interval=timedelta(minutes=30),
        update_method=session_manager.async_refresh_session,
    )

    await coordinator.async_refresh()
    hass.data[DOMAIN] = session_manager

    return True

class SessionManager:
    def __init__(self, username, password, hass):
        self._username = username
        self._password = password
        self._jsessionid = None
        self._jwt_token = None
        self._device_ids = []
        self._hass = hass

    async def async_initialize(self):
        await self.async_refresh_session()
        await self.async_login()
        await self.async_get_device_ids()

    async def async_refresh_session(self):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(30):
                    async with session.post(AUTH_URL, headers=headers, ssl=False) as response:
                        if response.status == 200:
                            cookies = response.cookies
                            self._jsessionid = cookies.get("jsessionid").value if cookies.get("jsessionid") else None
                            _LOGGER.info(f"Session refreshed successfully, jsessionid: {self._jsessionid}")
                        else:
                            _LOGGER.error("Failed to refresh session.")
                            create(self._hass, "Failed to refresh session for Golmar G2Call+", title="Golmar Integration Error")
                            raise UpdateFailed("Session refresh failed.")
            except asyncio.TimeoutError:
                _LOGGER.error("Login attempt timed out.")
                raise UpdateFailed("Timeout error during login.")
            except asyncio.CancelledError:
                _LOGGER.error("Login attempt was cancelled.")
                raise UpdateFailed("Login cancelled.")
            except Exception as e:
                _LOGGER.error("Error in async_refresh_session: %s", e)
                raise UpdateFailed("Error in session refresh")

    async def async_login(self):
        MAX_RETRIES = 3
        retry_count = 0

        headers = {
            "Content-Type": "application/xml",
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "es-ES,es;q=0.9",
            "Connection": "keep-alive",
        }
        
        if self._jsessionid:
            headers["Cookie"] = f"jsessionid={self._jsessionid}"

        xml_body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <envelope>
            <header>
                <flag>tdkcloud</flag>
                <version>1.10</version>
                <command>login</command>
                <seq>1</seq>
                <session></session>
                <user-data></user-data>
                <client>
                    <id>{CLIENT_ID}</id>
                    <type>2</type>
                    <oem>{OEM}</oem>
                    <app>{APP}</app>
                </client>
            </header>
            <content>
                <account>{self._username}</account>
                <password>{self._password}</password>
                <auth-type>0</auth-type>
                <auth-code></auth-code>
                <ip-region-id>0</ip-region-id>
            </content>
        </envelope>
        """

        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.post(LOGIN_URL, headers=headers, data=xml_body, ssl=False) as response:
                        if response.status == 200:
                            if response.content_type == "application/xml":
                                xml_content = await response.text()
                                _LOGGER.info("Received XML response for login.")
                                root = ET.fromstring(xml_content)
                                token = root.find(".//token")
                                if token is not None:
                                    self._jwt_token = token.text
                                    _LOGGER.info("JWT token successfully parsed.")
                                else:
                                    _LOGGER.warning("Token not found in XML response.")
                            elif response.content_type == "application/json":
                                json_content = await response.json()
                                self._jwt_token = json_content.get("token")
                                _LOGGER.info("Login successful with JSON response.")
                            elif response.content_type == "application/octet-stream":
                                binary_content = await response.read()
                                if len(binary_content) == 0:
                                    _LOGGER.warning("Retrying login due to empty binary response.")
                                    await asyncio.sleep(2)  # Wait before retrying
                                    retry_count += 1
                                    if retry_count >= MAX_RETRIES:
                                        _LOGGER.error("Max retries reached. Login failed due to repeated empty responses.")
                                        raise UpdateFailed("Login failed after max retries due to empty binary response.")
                                    return await self.async_login()
                                else:
                                    _LOGGER.warning("Received binary response for login. Length: %d bytes", len(binary_content))
                            else:
                                text_content = await response.text()
                                _LOGGER.error(f"Unexpected response format. Content-Type: {response.content_type}, Response: {text_content}")
                                raise UpdateFailed("Unexpected response format during login.")
                        else:
                            _LOGGER.error(f"Unexpected response. Status: {response.status}, Headers: {response.headers}")
                            raise UpdateFailed("Login failed with non-200 status.")
            except Exception as e:
                _LOGGER.error("Error in async_login: %s", e)
                raise UpdateFailed("Error in login")

    async def async_get_device_ids(self):
        headers = {
            "Cookie": f"jsessionid={self._jsessionid}",
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {self._jwt_token}",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        }
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.post(CONTROL_URL, headers=headers, ssl=False) as response:
                        if response.status == 200:
                            data = await response.json()
                            devices = data.get("content", {}).get("main-devlist", [])
                            self._device_ids = [device["deviceId"] for device in devices]
                            if self._device_ids:
                                _LOGGER.info(f"Device IDs retrieved: {self._device_ids}")
                            else:
                                raise UpdateFailed("No device IDs found.")
                        else:
                            _LOGGER.error("Failed to retrieve device IDs.")
                            create(self._hass, "Failed to retrieve device IDs", title="Golmar Integration Error")
                            raise UpdateFailed("Device ID retrieval failed.")
            except Exception as e:
                _LOGGER.error("Error in async_get_device_ids: %s", e)
                raise UpdateFailed("Error retrieving device IDs")
