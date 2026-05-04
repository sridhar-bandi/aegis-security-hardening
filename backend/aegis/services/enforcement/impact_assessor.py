"""Impact Assessor using NetworkX to model communication channels between components."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import networkx as nx

from aegis.schemas.instance import ChannelRisk, ImpactAssessmentReport

logger = logging.getLogger(__name__)

TLS_RISK_WEIGHT = {
    "TLSv1": 9.0,
    "TLSv1.1": 7.0,
    "TLSv1.2": 2.0,
    "TLSv1.3": 0.0,
}

CIPHER_RISK_WEIGHT = {
    "RC4": 10.0,
    "DES": 10.0,
    "3DES": 8.0,
    "MD5": 7.0,
    "NULL": 10.0,
    "EXPORT": 9.0,
    "ANON": 9.0,
}


def _cipher_score(ciphers: list[str]) -> float:
    score = 0.0
    for c in ciphers:
        for weak, weight in CIPHER_RISK_WEIGHT.items():
            if weak in c.upper():
                score = max(score, weight)
    return score


def _tls_score(versions: list[str]) -> float:
    return max((TLS_RISK_WEIGHT.get(v, 0.0) for v in versions), default=5.0)


class ImpactAssessor:
    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def build_topology(self, topology: list[dict]) -> None:
        """
        topology: list of dicts with keys:
          source, target, protocol, tls_versions, cipher_suites, port
        """
        for edge in topology:
            self._graph.add_edge(
                edge["source"],
                edge["target"],
                protocol=edge.get("protocol", "TCP"),
                tls_versions=edge.get("tls_versions", []),
                cipher_suites=edge.get("cipher_suites", []),
                port=edge.get("port", 443),
            )

    def assess(self, instance_id: str) -> ImpactAssessmentReport:
        channels: list[ChannelRisk] = []
        for src, tgt, data in self._graph.edges(data=True):
            tls = data.get("tls_versions", [])
            ciphers = data.get("cipher_suites", [])
            risk = (_tls_score(tls) + _cipher_score(ciphers)) / 2.0
            channels.append(ChannelRisk(
                source=src,
                target=tgt,
                protocol=data.get("protocol", "TCP"),
                tls_versions=tls,
                cipher_suites=ciphers,
                port=data.get("port", 443),
                risk_score=risk,
            ))

        channels.sort(key=lambda c: c.risk_score, reverse=True)
        return ImpactAssessmentReport(
            instance_id=instance_id,
            communication_channels=channels,
            generated_at=datetime.now(timezone.utc),
        )

    def find_affected_paths(self, changed_component: str) -> list[list[str]]:
        """Return all paths that pass through changed_component."""
        paths = []
        for src in self._graph.nodes:
            for tgt in self._graph.nodes:
                if src == tgt:
                    continue
                try:
                    for path in nx.all_simple_paths(self._graph, src, tgt):
                        if changed_component in path:
                            paths.append(path)
                except nx.NetworkXNoPath:
                    pass
        return paths
