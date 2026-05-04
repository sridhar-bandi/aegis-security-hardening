"""SSH connector via Paramiko for VMs and Linux servers."""
from __future__ import annotations

import logging
from typing import Any

import paramiko

from aegis.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class SSHConnector(BaseConnector):
    def __init__(
        self,
        hostname: str,
        username: str,
        password: str | None = None,
        private_key_path: str | None = None,
        port: int = 22,
        timeout: float = 30.0,
    ) -> None:
        self.hostname = hostname
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.port = port
        self.timeout = timeout
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        connect_kwargs: dict[str, Any] = dict(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            timeout=self.timeout,
        )
        if self.private_key_path:
            connect_kwargs["key_filename"] = self.private_key_path
        elif self.password:
            connect_kwargs["password"] = self.password
        else:
            raise ValueError("SSHConnector requires either password or private_key_path")
        self._client.connect(**connect_kwargs)
        logger.info("SSH connected to %s:%s as %s", self.hostname, self.port, self.username)

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def run_command(self, command: str) -> ConnectorResult:
        if self._client is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            _, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)  # noqa: S601
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            return ConnectorResult(
                success=exit_code == 0,
                output=out.strip(),
                error=err.strip(),
            )
        except Exception as exc:
            logger.exception("SSH command failed on %s: %s", self.hostname, exc)
            return ConnectorResult(success=False, error=str(exc))

    def put_file(self, local_path: str, remote_path: str) -> ConnectorResult:
        if self._client is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            sftp = self._client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return ConnectorResult(success=True, output=f"Uploaded to {remote_path}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))
