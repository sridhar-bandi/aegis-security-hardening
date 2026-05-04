"""Unit tests for the connector factory (no network calls)."""
import pytest

from aegis.services.connectors.factory import _resolve_connector_class, create_connector
from aegis.services.connectors.ssh_connector import SSHConnector
from aegis.services.connectors.redfish_connector import RedfishConnector
from aegis.services.connectors.netmiko_connector import NetmikoConnector
from aegis.services.connectors.kubernetes_connector import KubernetesConnector
from aegis.services.connectors.vault_connector import VaultConnector


class TestResolveConnectorClass:
    def test_vm_maps_to_ssh(self):
        assert _resolve_connector_class("VM") == "ssh"

    def test_server_maps_to_ssh(self):
        assert _resolve_connector_class("Server-01") == "ssh"

    def test_linux_maps_to_ssh(self):
        assert _resolve_connector_class("Linux") == "ssh"

    def test_ilo_maps_to_redfish(self):
        assert _resolve_connector_class("iLO") == "redfish"

    def test_bios_maps_to_redfish(self):
        assert _resolve_connector_class("BIOS") == "redfish"

    def test_aruba_maps_to_netmiko(self):
        assert _resolve_connector_class("ArubaSwitch") == "netmiko"

    def test_switch_maps_to_netmiko(self):
        assert _resolve_connector_class("Switch-Core") == "netmiko"

    def test_kubernetes_maps_to_kubernetes(self):
        assert _resolve_connector_class("Kubernetes") == "kubernetes"

    def test_k8s_maps_to_kubernetes(self):
        assert _resolve_connector_class("K8s-prod") == "kubernetes"

    def test_vault_maps_to_vault(self):
        assert _resolve_connector_class("Vault") == "vault"

    def test_unknown_defaults_to_ssh(self):
        assert _resolve_connector_class("SomeUnknownType") == "ssh"


class TestCreateConnector:
    _SSH_CFG = {"host": "10.0.0.1", "username": "admin", "password": "pass"}
    _RF_CFG = {"host": "10.0.0.2", "username": "admin", "password": "pass"}
    _NM_CFG = {"host": "10.0.0.3", "username": "admin", "password": "pass"}
    _K8S_CFG = {}
    _VAULT_CFG = {"vault_url": "https://vault:8200", "vault_token": "tok"}

    def test_ssh_connector_returned(self):
        c = create_connector("VM", self._SSH_CFG)
        assert isinstance(c, SSHConnector)

    def test_redfish_connector_returned(self):
        c = create_connector("iLO", self._RF_CFG)
        assert isinstance(c, RedfishConnector)

    def test_netmiko_connector_returned(self):
        c = create_connector("Aruba", self._NM_CFG)
        assert isinstance(c, NetmikoConnector)

    def test_kubernetes_connector_returned(self):
        c = create_connector("Kubernetes", self._K8S_CFG)
        assert isinstance(c, KubernetesConnector)

    def test_vault_connector_returned(self):
        c = create_connector("Vault", self._VAULT_CFG)
        assert isinstance(c, VaultConnector)

    def test_explicit_connector_type_overrides_component_type(self):
        # component_type=VM (→ssh) but connector_type=redfish in config
        cfg = {**self._RF_CFG, "connector_type": "redfish"}
        c = create_connector("VM", cfg)
        assert isinstance(c, RedfishConnector)
