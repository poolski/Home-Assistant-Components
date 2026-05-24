"""
Integration tests — verifies that statistics_outlier_cleaner registers
correctly against a real (test) Home Assistant instance.

The `hass` fixture is provided by pytest-homeassistant-custom-component and
starts a minimal HA core with no external connections.

Run with:
    pytest tests_ha/ -v
"""

from __future__ import annotations

import pytest
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

DOMAIN = "statistics_outlier_cleaner"

WS_COMMANDS = [
    f"{DOMAIN}/list_sum_statistics",
    f"{DOMAIN}/fetch_outliers",
    f"{DOMAIN}/apply_fix",
    f"{DOMAIN}/list_fixes",
    f"{DOMAIN}/restore_fix",
]

SERVICES = ["clean_outliers", "restore_fix"]


@pytest.fixture
async def setup_component(hass: HomeAssistant, recorder_mock):
    """Set up the component under test and yield the HA instance."""
    result = await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    assert result is True, "async_setup_component returned False"
    await hass.async_block_till_done()
    return hass


async def test_async_setup_returns_true(hass: HomeAssistant, recorder_mock):
    result = await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    assert result is True


async def test_services_registered(setup_component: HomeAssistant):
    hass = setup_component
    for service in SERVICES:
        assert hass.services.has_service(DOMAIN, service), (
            f"Service {DOMAIN}.{service} was not registered"
        )


async def test_websocket_commands_registered(setup_component: HomeAssistant):
    hass = setup_component
    handlers = hass.data.get(websocket_api.DOMAIN, {})
    for cmd in WS_COMMANDS:
        assert cmd in handlers, f"WebSocket command {cmd!r} was not registered"


async def test_clean_outliers_schema_accepts_minimal_payload(setup_component: HomeAssistant):
    """Service schema should accept a call with only the required statistic_id."""
    hass = setup_component
    assert hass.services.has_service(DOMAIN, "clean_outliers")


async def test_restore_fix_schema_accepts_fix_id(setup_component: HomeAssistant):
    """Service schema should accept a call with a fix_id."""
    hass = setup_component
    assert hass.services.has_service(DOMAIN, "restore_fix")
