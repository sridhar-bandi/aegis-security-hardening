"""Netmiko connector for Aruba AOS-CX and AOS-S network switches."""
from __future__ import annotations

import logging

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

from aegis.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)

DEVICE_TYPE_MAP = {
    "ArubaAOS-CX": "aruba_aoscx",
    "ArubaAOS-S": "aruba_aos",
    "aruba_aoscx": "aruba_aoscx",
    "aruba_aos": "aruba_aos",
}


class NetmikoConnector(BaseConnector):
    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        device_type: str = "ArubaAOS-CX",
        port: int = 22,
        timeout: float = 30.0,
    ) -> None:
        self.hostname = hostname
        self.username = username
        self.password = password
        self.device_type = DEVICE_TYPE_MAP.get(device_type, device_type)
        self.port = port
        self.timeout = timeout
        self._connection = None

    def connect(self) -> None:
        try:
            self._connection = ConnectHandler(
                device_type=self.device_type,
                host=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=self.timeout,
            )
            logger.info("Netmiko connected to %s (%s)", self.hostname, self.device_type)
        except NetmikoAuthenticationException as exc:
            raise ConnectionError(f"Authentication failed for {self.hostname}: {exc}") from exc
        except NetmikoTimeoutException as exc:
            raise TimeoutError(f"Connection timed out for {self.hostname}: {exc}") from exc

    def disconnect(self) -> None:
        if self._connection:
            self._connection.disconnect()
            self._connection = None

    def run_command(self, command: str) -> ConnectorResult:
        if self._connection is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            output = self._connection.send_command(command)
            return ConnectorResult(success=True, output=output)
        except Exception as exc:
            logger.exception("Netmiko command failed on %s: %s", self.hostname, exc)
            return ConnectorResult(success=False, error=str(exc))

    def run_config_commands(self, commands: list[str]) -> ConnectorResult:
        if self._connection is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            output = self._connection.send_config_set(commands)
            return ConnectorResult(success=True, output=output)
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))
