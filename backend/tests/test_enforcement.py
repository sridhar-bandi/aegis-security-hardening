"""Unit tests for ImpactAssessor and DryRunEngine."""
import pytest

from aegis.services.enforcement.impact_assessor import (
    ImpactAssessor,
    _tls_score,
    _cipher_score,
)
from aegis.services.enforcement.dry_run import DryRunEngine


# ---------------------------------------------------------------------------
# TLS / cipher score helpers
# ---------------------------------------------------------------------------

class TestTLSScore:
    def test_tlsv1_is_high_risk(self):
        assert _tls_score(["TLSv1"]) == 9.0

    def test_tlsv1_1_is_high_risk(self):
        assert _tls_score(["TLSv1.1"]) == 7.0

    def test_tlsv1_2_is_low_risk(self):
        assert _tls_score(["TLSv1.2"]) == 2.0

    def test_tlsv1_3_is_zero_risk(self):
        assert _tls_score(["TLSv1.3"]) == 0.0

    def test_max_used_for_mixed_versions(self):
        assert _tls_score(["TLSv1.3", "TLSv1"]) == 9.0

    def test_empty_defaults_to_5(self):
        assert _tls_score([]) == 5.0


class TestCipherScore:
    def test_rc4_is_max(self):
        assert _cipher_score(["TLS_RSA_WITH_RC4_128_SHA"]) == 10.0

    def test_safe_cipher_scores_zero(self):
        assert _cipher_score(["TLS_AES_256_GCM_SHA384"]) == 0.0

    def test_max_used_for_mixed_ciphers(self):
        score = _cipher_score(["TLS_AES_256_GCM_SHA384", "TLS_RSA_WITH_RC4_128_SHA"])
        assert score == 10.0


# ---------------------------------------------------------------------------
# ImpactAssessor
# ---------------------------------------------------------------------------

class TestImpactAssessor:
    def _build_assessor(self):
        a = ImpactAssessor()
        a.build_topology([
            {
                "source": "WebServer",
                "target": "Database",
                "protocol": "TCP",
                "tls_versions": ["TLSv1.2"],
                "cipher_suites": [],
                "port": 5432,
            },
            {
                "source": "LoadBalancer",
                "target": "WebServer",
                "protocol": "HTTPS",
                "tls_versions": ["TLSv1"],
                "cipher_suites": ["RC4"],
                "port": 443,
            },
        ])
        return a

    def test_assess_returns_channels(self):
        report = self._build_assessor().assess("inst-1")
        assert len(report.communication_channels) == 2

    def test_channels_sorted_by_risk_desc(self):
        report = self._build_assessor().assess("inst-1")
        scores = [ch.risk_score for ch in report.communication_channels]
        assert scores == sorted(scores, reverse=True)

    def test_high_risk_channel_identified(self):
        report = self._build_assessor().assess("inst-1")
        top = report.communication_channels[0]
        # LB→WebServer has TLSv1 + RC4 — highest risk
        assert top.source == "LoadBalancer"
        assert top.risk_score > 5.0

    def test_find_affected_paths(self):
        a = self._build_assessor()
        paths = a.find_affected_paths("WebServer")
        # All paths that include WebServer
        assert all("WebServer" in p for p in paths)
        assert len(paths) > 0

    def test_instance_id_preserved(self):
        report = self._build_assessor().assess("my-instance")
        assert report.instance_id == "my-instance"


# ---------------------------------------------------------------------------
# DryRunEngine
# ---------------------------------------------------------------------------

class TestDryRunEngine:
    def _run(self, topology, rules):
        a = ImpactAssessor()
        a.build_topology(topology)
        engine = DryRunEngine(a)
        return engine.run("test-instance", rules)

    def test_safe_rule_no_channel_impact(self):
        topology = [
            {"source": "A", "target": "B", "tls_versions": ["TLSv1.3"],
             "cipher_suites": [], "port": 443},
        ]
        rules = [{"rule_id": "r1", "blueprint_rule_id": "pr1", "title": "T",
                  "component_type": "Vault", "risk_score": 0}]
        report = self._run(topology, rules)
        # Component "Vault" not in graph → no impacted channels → safe
        assert len(report.safe_rules) == 1
        assert len(report.breaking_rules) == 0

    def test_high_risk_rule_classified_as_breaking(self):
        topology = [
            {"source": "WebServer", "target": "DB", "tls_versions": ["TLSv1"],
             "cipher_suites": ["RC4"], "port": 5432},
        ]
        rules = [{"rule_id": "r2", "blueprint_rule_id": "pr2", "title": "Disable RC4",
                  "component_type": "WebServer", "risk_score": 9}]
        report = self._run(topology, rules)
        assert len(report.breaking_rules) == 1
        assert report.breaking_rules[0].rule_id == "r2"

    def test_report_has_instance_id(self):
        a = ImpactAssessor()
        engine = DryRunEngine(a)
        report = engine.run("inst-xyz", [])
        assert report.instance_id == "inst-xyz"

    def test_empty_rules_produces_empty_report(self):
        report = self._run([], [])
        assert report.safe_rules == []
        assert report.risky_rules == []
        assert report.breaking_rules == []
