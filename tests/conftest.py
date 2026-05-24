"""Shared test fixtures and HA module stubs."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub out homeassistant before any test imports the component modules.
# Only the algorithm functions are tested; they don't touch HA at runtime,
# but they live in a module that has HA imports at the top level.
_HA_STUBS = [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.components",
    "homeassistant.components.recorder",
    "homeassistant.components.recorder.statistics",
    "homeassistant.components.recorder.db_schema",
    "homeassistant.components.websocket_api",
    "homeassistant.components.frontend",
    "homeassistant.config_entries",
    "homeassistant.exceptions",
    "homeassistant.util",
    "homeassistant.util.dt",
    "voluptuous",
]
for _mod in _HA_STUBS:
    sys.modules.setdefault(_mod, MagicMock())
