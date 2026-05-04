"""Redfish connector for HPE iLO/BIOS endpoints."""
from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from aegis.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class RedfishConnector(BaseConnector):
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = f"https://{host}/redfish/v1"
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._session: requests.Session | None = None

    def connect(self) -> None:
        self._session = requests.Session()
        self._session.auth = (self.username, self.password)
        self._session.verify = self.verify_ssl
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self._session.mount("https://", HTTPAdapter(max_retries=retry))
        # Validate connectivity
        resp = self._session.get(f"{self.base_url}/", timeout=self.timeout)
        resp.raise_for_status()
        logger.info("Redfish connected to %s", self.base_url)

    def disconnect(self) -> None:
        if self._session:
            self._session.close()
            self._session = None

    def run_command(self, command: str) -> ConnectorResult:
        """For Redfish, `command` is a relative URL path (GET). Use get/post/patch directly for complex ops."""
        return self.get(command)

    def get(self, path: str) -> ConnectorResult:
        if self._session is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            resp = self._session.get(f"{self.base_url}{path}", timeout=self.timeout)
            resp.raise_for_status()
            return ConnectorResult(success=True, output=resp.text, raw=resp.json())
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    def patch(self, path: str, payload: dict[str, Any]) -> ConnectorResult:
        if self._session is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            resp = self._session.patch(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return ConnectorResult(success=True, output=resp.text, raw=resp.json() if resp.content else {})
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    def post(self, path: str, payload: dict[str, Any]) -> ConnectorResult:
        if self._session is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            resp = self._session.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return ConnectorResult(success=True, output=resp.text, raw=resp.json() if resp.content else {})
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))
