"""
pytest configuration for HA integration tests.

These tests run against a real (test) Home Assistant instance provided by
pytest-homeassistant-custom-component.  They live in tests_ha/ (not tests/)
so they do NOT inherit the HA module stubs in tests/conftest.py.
"""
