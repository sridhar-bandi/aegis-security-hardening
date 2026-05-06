"""Rollback engine: restores saved_state using rollback_code."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from aegis.services.connectors.base import BaseConnector, ConnectorResult
from aegis.services.connectors.factory import create_connector
from aegis.services.connectors.vault_connector import VaultConnector

logger = logging.getLogger(__name__)


@dataclass
class RollbackRuleResult:
    blueprint_rule_id: str
    rule_id: str
    success: bool
    details: str
    error: str = ""


@dataclass
class RollbackReport:
    instance_id: str
    results: list[RollbackRuleResult] = field(default_factory=list)


class RollbackEngine:
    def rollback(
        self,
        instance_id: str,
        component_type: str,
        endpoint_config: dict,
        blueprint_rules: list[dict],
        vault_connector: VaultConnector | None = None,
    ) -> RollbackReport:
        """
        blueprint_rules must include `saved_state` (dict) from the DB record.
        Runs rollback_code restoring state.
        """
        resolved_config = endpoint_config
        if vault_connector:
            resolved_config = vault_connector.resolve_vault_refs(endpoint_config)

        report = RollbackReport(instance_id=instance_id)

        with create_connector(component_type, resolved_config) as connector:
            for rule in blueprint_rules:
                result = self._rollback_rule(connector, rule)
                report.results.append(result)

        return report

    def _rollback_rule(self, connector: BaseConnector, rule: dict) -> RollbackRuleResult:
        code = rule.get("rollback_code", "")
        saved_state = rule.get("saved_state") or {}
        result: dict = {}
        namespace = {
            "connector": connector,
            "saved_state": saved_state,
            "result": result,
            "logger": logging.getLogger(f"rollback.{rule.get('rule_id', 'unknown')}"),
            "BaseConnector": BaseConnector,
            "ConnectorResult": ConnectorResult,
        }
        try:
            exec(compile(code, f"rollback_{rule['blueprint_rule_id']}", "exec"), namespace)  # noqa: S102
        except Exception as exc:
            logger.exception("Rollback code exec failed for rule %s: %s", rule.get("rule_id"), exc)
            return RollbackRuleResult(
                blueprint_rule_id=rule["blueprint_rule_id"],
                rule_id=rule.get("rule_id", ""),
                success=False,
                details="",
                error=str(exc),
            )

        r = namespace.get("result", {})
        return RollbackRuleResult(
            blueprint_rule_id=rule["blueprint_rule_id"],
            rule_id=rule.get("rule_id", ""),
            success=bool(r.get("success", False)),
            details=str(r.get("details", "")),
        )
