"""Nautobot Golden Config REST API connector.

This connector communicates with a Nautobot instance to push golden
configuration data (intended configs) for compliance evaluation.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from aegis.config import settings

logger = logging.getLogger(__name__)


class NautobotConfigError(Exception):
    """Raised when Nautobot interaction fails."""


class NautobotConnector:
    """Client for Nautobot REST API - Golden Configuration plugin."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        verify_ssl: bool | None = None,
    ):
        self.base_url = (base_url or settings.NAUTOBOT_URL).rstrip("/")
        self.api_token = api_token or settings.NAUTOBOT_API_TOKEN
        self.verify_ssl = verify_ssl if verify_ssl is not None else settings.NAUTOBOT_VERIFY_SSL

        if not self.base_url or not self.api_token:
            raise NautobotConfigError(
                "Nautobot URL and API token must be configured via "
                "NAUTOBOT_URL and NAUTOBOT_API_TOKEN environment variables."
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers=self._headers,
            verify=self.verify_ssl,
            timeout=30.0,
        )

    def health_check(self) -> bool:
        """Verify connectivity to the Nautobot instance."""
        try:
            with self._client() as client:
                resp = client.get("/api/status/")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def get_device(self, device_name: str) -> dict[str, Any] | None:
        """Lookup a device by name in Nautobot."""
        with self._client() as client:
            resp = client.get("/api/dcim/devices/", params={"name": device_name})
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return results[0] if results else None

    def push_golden_config(
        self,
        device_id: str,
        intended_config: str,
        config_format: str = "cli",
    ) -> dict[str, Any]:
        """Push golden/intended configuration for a device.

        Args:
            device_id: Nautobot UUID of the target device.
            intended_config: The golden configuration text (CLI or JSON).
            config_format: Format of the config ('cli' or 'json').

        Returns:
            The API response payload from Nautobot.
        """
        payload = {
            "device": device_id,
            "intended_config": intended_config,
            "config_format": config_format,
        }

        with self._client() as client:
            # Try the golden-config plugin endpoint first
            resp = client.post(
                "/api/plugins/golden-config/intended-configs/",
                json=payload,
            )
            if resp.status_code == 404:
                # Fallback: try the config-compliance endpoint
                resp = client.post(
                    "/api/plugins/golden-config/config-compliance/",
                    json=payload,
                )
            resp.raise_for_status()
            return resp.json()

    def get_compliance_status(self, device_id: str) -> dict[str, Any]:
        """Retrieve compliance status for a device from Nautobot Golden Config plugin."""
        with self._client() as client:
            resp = client.get(
                "/api/plugins/golden-config/config-compliance/",
                params={"device": device_id},
            )
            resp.raise_for_status()
            return resp.json()

    def list_golden_configs(self, device_id: str) -> list[dict[str, Any]]:
        """List golden configs for a device."""
        with self._client() as client:
            resp = client.get(
                "/api/plugins/golden-config/intended-configs/",
                params={"device": device_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
