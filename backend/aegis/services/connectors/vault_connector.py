"""HashiCorp Vault connector via hvac."""
from __future__ import annotations

import logging

import hvac

from aegis.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class VaultConnector(BaseConnector):
    def __init__(
        self,
        url: str,
        token: str | None = None,
        role_id: str | None = None,
        secret_id: str | None = None,
    ) -> None:
        self.url = url
        self.token = token
        self.role_id = role_id
        self.secret_id = secret_id
        self._client: hvac.Client | None = None

    def connect(self) -> None:
        self._client = hvac.Client(url=self.url, token=self.token)
        if self.role_id and self.secret_id:
            result = self._client.auth.approle.login(role_id=self.role_id, secret_id=self.secret_id)
            self._client.token = result["auth"]["client_token"]
        if not self._client.is_authenticated():
            raise ConnectionError("Vault authentication failed")
        logger.info("Vault connected to %s", self.url)

    def disconnect(self) -> None:
        self._client = None

    def run_command(self, command: str) -> ConnectorResult:
        """For Vault, command is a KV path like 'secret/data/my-path'."""
        return self.read_secret(command)

    def read_secret(self, path: str) -> ConnectorResult:
        """Read a secret from Vault KV v2. path should be like 'secret/my-path'."""
        if self._client is None:
            return ConnectorResult(success=False, error="Not connected")
        try:
            parts = path.split("/", 1)
            mount = parts[0] if len(parts) > 1 else "secret"
            secret_path = parts[1] if len(parts) > 1 else parts[0]
            response = self._client.secrets.kv.v2.read_secret_version(
                path=secret_path, mount_point=mount
            )
            data = response["data"]["data"]
            return ConnectorResult(success=True, raw=data, output=str(list(data.keys())))
        except Exception as exc:
            logger.exception("Vault read failed for path %s: %s", path, exc)
            return ConnectorResult(success=False, error=str(exc))

    def resolve_vault_refs(self, config: dict) -> dict:
        """
        Recursively resolve `vault://secret/path#key` references in a config dict.
        Never logs resolved values.
        """
        resolved: dict = {}
        for k, v in config.items():
            if isinstance(v, str) and v.startswith("vault://"):
                # Format: vault://mount/path#key
                ref = v[len("vault://"):]
                if "#" in ref:
                    vault_path, secret_key = ref.rsplit("#", 1)
                else:
                    vault_path, secret_key = ref, None
                result = self.read_secret(vault_path)
                if result.success and isinstance(result.raw, dict):
                    resolved[k] = result.raw.get(secret_key, result.raw) if secret_key else result.raw
                else:
                    raise RuntimeError(f"Failed to resolve Vault ref {v}: {result.error}")
            elif isinstance(v, dict):
                resolved[k] = self.resolve_vault_refs(v)
            else:
                resolved[k] = v
        return resolved
