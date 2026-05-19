"""Unit tests for the NautobotConnector (no real network calls)."""
import pytest
from unittest.mock import patch, MagicMock

import os
os.environ.setdefault("NAUTOBOT_URL", "http://nautobot.test:8080")
os.environ.setdefault("NAUTOBOT_API_TOKEN", "test-token-abc123")


class TestNautobotConnectorInit:
    def test_raises_when_no_url_configured(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector, NautobotConfigError
        with patch("aegis.services.connectors.nautobot_connector.settings") as mock_settings:
            mock_settings.NAUTOBOT_URL = ""
            mock_settings.NAUTOBOT_API_TOKEN = ""
            mock_settings.NAUTOBOT_VERIFY_SSL = True
            with pytest.raises(NautobotConfigError, match="must be configured"):
                NautobotConnector()

    def test_initializes_with_valid_settings(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        with patch("aegis.services.connectors.nautobot_connector.settings") as mock_settings:
            mock_settings.NAUTOBOT_URL = "http://nautobot.test:8080"
            mock_settings.NAUTOBOT_API_TOKEN = "test-token"
            mock_settings.NAUTOBOT_VERIFY_SSL = True
            connector = NautobotConnector()
            assert connector.base_url == "http://nautobot.test:8080"
            assert connector.api_token == "test-token"

    def test_override_params(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://custom:9090/",
            api_token="custom-token",
            verify_ssl=False,
        )
        assert connector.base_url == "http://custom:9090"
        assert connector.api_token == "custom-token"
        assert connector.verify_ssl is False


class TestNautobotConnectorHeaders:
    def test_headers_contain_token(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="my-secret-token",
        )
        headers = connector._headers
        assert headers["Authorization"] == "Token my-secret-token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestNautobotHealthCheck:
    def test_health_check_success(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="token",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance
            assert connector.health_check() is True

    def test_health_check_failure(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="token",
        )
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance
            assert connector.health_check() is False


class TestNautobotGetDevice:
    def test_get_device_found(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="token",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 1,
            "results": [{"id": "device-uuid-123", "name": "switch01"}],
        }
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance
            device = connector.get_device("switch01")
            assert device is not None
            assert device["id"] == "device-uuid-123"

    def test_get_device_not_found(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="token",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0, "results": []}
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.get.return_value = mock_response
            MockClient.return_value = mock_client_instance
            device = connector.get_device("nonexistent")
            assert device is None


class TestNautobotPushGoldenConfig:
    def test_push_golden_config_success(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="token",
        )
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "config-uuid", "status": "created"}
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = mock_response
            MockClient.return_value = mock_client_instance
            result = connector.push_golden_config(
                device_id="device-uuid-123",
                intended_config="ntp server 10.0.0.1\nhostname secure-switch",
                config_format="cli",
            )
            assert result["status"] == "created"
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert call_args[1]["json"]["device"] == "device-uuid-123"
            assert "ntp server" in call_args[1]["json"]["intended_config"]

    def test_push_golden_config_fallback_on_404(self):
        from aegis.services.connectors.nautobot_connector import NautobotConnector
        connector = NautobotConnector(
            base_url="http://nautobot.test:8080",
            api_token="token",
        )
        # First call returns 404 (intended-configs endpoint missing), second succeeds
        mock_404 = MagicMock()
        mock_404.status_code = 404
        mock_success = MagicMock()
        mock_success.status_code = 201
        mock_success.json.return_value = {"id": "config-uuid", "status": "created"}
        mock_success.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.side_effect = [mock_404, mock_success]
            MockClient.return_value = mock_client_instance
            result = connector.push_golden_config(
                device_id="device-uuid-123",
                intended_config="config data",
                config_format="cli",
            )
            assert result["status"] == "created"
            assert mock_client_instance.post.call_count == 2
