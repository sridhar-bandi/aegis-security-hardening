"""ConnectorFactory — dispatches to the right connector based on component_type config."""
from __future__ import annotations

import logging

from aegis.services.connectors.base import BaseConnector
from aegis.services.connectors.ssh_connector import SSHConnector
from aegis.services.connectors.redfish_connector import RedfishConnector
from aegis.services.connectors.netmiko_connector import NetmikoConnector
from aegis.services.connectors.kubernetes_connector import KubernetesConnector
from aegis.services.connectors.vault_connector import VaultConnector

logger = logging.getLogger(__name__)

# Mapping component_type prefixes to connector factory functions
_TYPE_MAP: dict[str, str] = {
    "VM": "ssh",
    "Server": "ssh",
    "Linux": "ssh",
    "iLO": "redfish",
    "BIOS": "redfish",
    "Redfish": "redfish",
    "SRController": "redfish",
    "Aruba": "netmiko",
    "Switch": "netmiko",
    "Kubernetes": "kubernetes",
    "K8s": "kubernetes",
    "Vault": "vault",
}


def _resolve_connector_class(component_type: str) -> str:
    for prefix, conn_type in _TYPE_MAP.items():
        if component_type.startswith(prefix):
            return conn_type
    return "ssh"  # default to SSH


def create_connector(component_type: str, endpoint_config: dict) -> BaseConnector:
    """
    Create and return an appropriate BaseConnector for the given component_type.
    endpoint_config must have all credential fields already resolved (no vault:// refs).
    """
    conn_type = endpoint_config.get("connector_type") or _resolve_connector_class(component_type)

    if conn_type == "ssh":
        return SSHConnector(
            hostname=endpoint_config["host"],
            username=endpoint_config["username"],
            password=endpoint_config.get("password"),
            private_key_path=endpoint_config.get("private_key_path"),
            port=int(endpoint_config.get("port", 22)),
        )
    elif conn_type == "redfish":
        return RedfishConnector(
            host=endpoint_config["host"],
            username=endpoint_config["username"],
            password=endpoint_config["password"],
            verify_ssl=endpoint_config.get("verify_ssl", False),
        )
    elif conn_type == "netmiko":
        return NetmikoConnector(
            hostname=endpoint_config["host"],
            username=endpoint_config["username"],
            password=endpoint_config["password"],
            device_type=endpoint_config.get("device_type", "ArubaAOS-CX"),
            port=int(endpoint_config.get("port", 22)),
        )
    elif conn_type == "kubernetes":
        return KubernetesConnector(
            kubeconfig_path=endpoint_config.get("kubeconfig_path"),
            context=endpoint_config.get("context"),
            in_cluster=endpoint_config.get("in_cluster", False),
        )
    elif conn_type == "vault":
        return VaultConnector(
            url=endpoint_config["vault_url"],
            token=endpoint_config.get("vault_token"),
            role_id=endpoint_config.get("role_id"),
            secret_id=endpoint_config.get("secret_id"),
        )
    else:
        raise ValueError(f"Unknown connector type: {conn_type}")
