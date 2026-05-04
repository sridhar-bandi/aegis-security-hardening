"""Remediator: runs remediation_code and persists saved_state for rollback."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from aegis.services.connectors.base import BaseConnector, ConnectorResult
from aegis.services.connectors.factory import create_connector
from aegis.services.connectors.vault_connector import VaultConnector

logger = logging.getLogger(__name__)


@dataclass
class RemRuleResult:
    profile_rule_id: str
    rule_id: str
    success: bool
    details: str
    saved_state: dict
    error: str = ""


@dataclass
class RemReport:
    instance_id: str
    results: list[RemRuleResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.success)


class Remediator:
    def remediate(
        self,
        instance_id: str,
        component_type: str,
        endpoint_config: dict,
        profile_rules: list[dict],
        vault_connector: VaultConnector | None = None,
    ) -> RemReport:
        resolved_config = endpoint_config
        if vault_connector:
            resolved_config = vault_connector.resolve_vault_refs(endpoint_config)

        report = RemReport(instance_id=instance_id)

        with create_connector(component_type, resolved_config) as connector:
            for rule in profile_rules:
                result = self._rem_rule(connector, rule)
                report.results.append(result)

        return report

    def _rem_rule(self, connector: BaseConnector, rule: dict) -> RemRuleResult:
        code = rule.get("remediation_code", "")
        result: dict = {}
        namespace = {
            "connector": connector,
            "result": result,
            "logger": logging.getLogger(f"rem.{rule.get('rule_id', 'unknown')}"),
            "BaseConnector": BaseConnector,
            "ConnectorResult": ConnectorResult,
        }
        try:
            exec(compile(code, f"rem_{rule['profile_rule_id']}", "exec"), namespace)  # noqa: S102
        except Exception as exc:
            logger.exception("Remediation code exec failed for rule %s: %s", rule.get("rule_id"), exc)
            return RemRuleResult(
                profile_rule_id=rule["profile_rule_id"],
                rule_id=rule.get("rule_id", ""),
                success=False,
                details="",
                saved_state={},
                error=str(exc),
            )

        r = namespace.get("result", {})
        return RemRuleResult(
            profile_rule_id=rule["profile_rule_id"],
            rule_id=rule.get("rule_id", ""),
            success=bool(r.get("success", False)),
            details=str(r.get("details", "")),
            saved_state=r.get("saved_state", {}),
            error="",
        )
