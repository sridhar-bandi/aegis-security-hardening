"""Kubernetes connector using the official kubernetes-client."""
from __future__ import annotations

import logging

from kubernetes import client as k8s_client, config as k8s_config

from aegis.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class KubernetesConnector(BaseConnector):
    def __init__(
        self,
        kubeconfig_path: str | None = None,
        context: str | None = None,
        in_cluster: bool = False,
    ) -> None:
        self.kubeconfig_path = kubeconfig_path
        self.context = context
        self.in_cluster = in_cluster
        self._core: k8s_client.CoreV1Api | None = None
        self._apps: k8s_client.AppsV1Api | None = None

    def connect(self) -> None:
        if self.in_cluster:
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config(config_file=self.kubeconfig_path, context=self.context)
        self._core = k8s_client.CoreV1Api()
        self._apps = k8s_client.AppsV1Api()
        logger.info("Kubernetes connector initialized (context=%s)", self.context)

    def disconnect(self) -> None:
        self._core = None
        self._apps = None

    def run_command(self, command: str) -> ConnectorResult:
        """Execute a kubectl-style resource get: '<kind>/<name>[/<namespace>]'"""
        parts = command.split("/")
        if len(parts) < 2:
            return ConnectorResult(success=False, error=f"Invalid command format: {command}")
        kind, name = parts[0], parts[1]
        namespace = parts[2] if len(parts) > 2 else "default"
        try:
            if kind == "pod":
                obj = self._core.read_namespaced_pod(name, namespace)
            elif kind == "namespace":
                obj = self._core.read_namespace(name)
            elif kind == "deployment":
                obj = self._apps.read_namespaced_deployment(name, namespace)
            else:
                return ConnectorResult(success=False, error=f"Unsupported kind: {kind}")
            return ConnectorResult(success=True, raw=obj.to_dict(), output=str(obj.metadata.name))
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    @property
    def core(self) -> k8s_client.CoreV1Api:
        if self._core is None:
            raise RuntimeError("KubernetesConnector not connected")
        return self._core

    @property
    def apps(self) -> k8s_client.AppsV1Api:
        if self._apps is None:
            raise RuntimeError("KubernetesConnector not connected")
        return self._apps
