"""Tests for settings construction and caching."""

from unittest.mock import Mock

from homesure import config


def test_get_settings_caches_the_settings_instance(monkeypatch):
    settings = object()
    settings_factory = Mock(return_value=settings)
    monkeypatch.setattr(config, "Settings", settings_factory)
    config.get_settings.cache_clear()

    try:
        assert config.get_settings() is settings
        assert config.get_settings() is settings
        settings_factory.assert_called_once_with()
    finally:
        config.get_settings.cache_clear()
