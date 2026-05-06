"""Evaluator: runs evaluation_code for each BlueprintRule against a real endpoint."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from aegis.services.connectors.base import BaseConnector, ConnectorResult
from aegis.services.connectors.factory import create_connector
from aegis.services.connectors.vault_connector import VaultConnector

logger = logging.getLogger(__name__)


@dataclass
class EvalRuleResult:
    blueprint_rule_id: str
    rule_id: str
    title: str
    component_type: str
    compliant: bool
    details: str
    error: str = ""


@dataclass
class EvalReport:
    instance_id: str
    component_type: str
    endpoint: str
    results: list[EvalRuleResult] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.compliant)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.compliant)


class Evaluator:
    def evaluate(
        self,
        instance_id: str,
        component_type: str,
        endpoint_config: dict,
        blueprint_rules: list[dict],
        vault_connector: VaultConnector | None = None,
    ) -> EvalReport:
        """
        Run evaluation_code for each blueprint_rule against the endpoint.
        endpoint_config may contain vault:// references resolved if vault_connector is provided.
        """
        resolved_config = self._resolve_config(endpoint_config, vault_connector)
        report = EvalReport(
            instance_id=instance_id,
            component_type=component_type,
            endpoint=resolved_config.get("host", "unknown"),
        )

        with create_connector(component_type, resolved_config) as connector:
            for rule in blueprint_rules:
                result = self._eval_rule(connector, rule)
                report.results.append(result)

        return report

    def _resolve_config(
        self, config: dict, vault_connector: VaultConnector | None
    ) -> dict:
        if vault_connector is None:
            return config
        return vault_connector.resolve_vault_refs(config)

    def _eval_rule(self, connector: BaseConnector, rule: dict) -> EvalRuleResult:
        code = rule.get("evaluation_code", "")
        result: dict = {}
        namespace = {
            "connector": connector,
            "result": result,
            "logger": logging.getLogger(f"eval.{rule.get('rule_id', 'unknown')}"),
            "BaseConnector": BaseConnector,
            "ConnectorResult": ConnectorResult,
        }
        try:
            exec(compile(code, f"eval_{rule['blueprint_rule_id']}", "exec"), namespace)  # noqa: S102
        except Exception as exc:
            logger.exception("Evaluation code exec failed for rule %s: %s", rule.get("rule_id"), exc)
            return EvalRuleResult(
                blueprint_rule_id=rule["blueprint_rule_id"],
                rule_id=rule.get("rule_id", ""),
                title=rule.get("title", ""),
                component_type=rule.get("component_type", ""),
                compliant=False,
                details="",
                error=str(exc),
            )

        r = namespace.get("result", {})
        return EvalRuleResult(
            blueprint_rule_id=rule["blueprint_rule_id"],
            rule_id=rule.get("rule_id", ""),
            title=rule.get("title", ""),
            component_type=rule.get("component_type", ""),
            compliant=bool(r.get("compliant", False)),
            details=str(r.get("details", "")),
            error="",
        )
