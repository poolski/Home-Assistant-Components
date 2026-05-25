"""
pytest configuration for HA integration tests.

These tests run against a real (test) Home Assistant instance provided by
pytest-homeassistant-custom-component.  They live in tests_ha/ (not tests/)
so they do NOT inherit the HA module stubs in tests/conftest.py.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

# hass_frontend is not installed in CI/test environments; provide a stub so
# the HA frontend component can be imported without crashing.
if "hass_frontend" not in sys.modules:
    sys.modules["hass_frontend"] = MagicMock()
    sys.modules["hass_frontend.manifest"] = MagicMock()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def hass_config_dir() -> str:
    """Use the project root as HA config dir so custom_components/ is found."""
    return PROJECT_ROOT


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass: HomeAssistant) -> None:
    """Allow loading custom integrations from the test config dir."""
    from homeassistant import loader  # noqa: PLC0415

    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url: str) -> None:
    """Ensure recorder_db_url is resolved before hass starts.

    The default implementation is a no-op, which allows hass to start before
    recorder_db_url runs, causing the 'assert not hass_fixture_setup' guard in
    recorder_db_url to fail.  By depending on recorder_db_url here, we force
    the correct setup order.
    """
