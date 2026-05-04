"""Dry-run engine: assess rule risk before actual enforcement."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from dataclasses import dataclass

from aegis.schemas.instance import ChannelRisk, DryRunReport, DryRunRuleResult
from aegis.services.enforcement.impact_assessor import ImpactAssessor

logger = logging.getLogger(__name__)

RISK_THRESHOLDS = {"critical": 8.0, "high": 6.0, "medium": 3.0, "low": 1.0}


def _break_risk_label(score: float) -> str:
    if score >= RISK_THRESHOLDS["critical"]:
        return "critical"
    if score >= RISK_THRESHOLDS["high"]:
        return "high"
    if score >= RISK_THRESHOLDS["medium"]:
        return "medium"
    if score >= RISK_THRESHOLDS["low"]:
        return "low"
    return "none"


class DryRunEngine:
    def __init__(self, assessor: ImpactAssessor) -> None:
        self._assessor = assessor

    def run(self, instance_id: str, profile_rules: list[dict]) -> DryRunReport:
        impact = self._assessor.assess(instance_id)

        safe: list[DryRunRuleResult] = []
        risky: list[DryRunRuleResult] = []
        breaking: list[DryRunRuleResult] = []

        for rule in profile_rules:
            component_type = rule.get("component_type", "")
            affected_paths = self._assessor.find_affected_paths(component_type)
            affected_channel_ids = {
                (src, tgt)
                for path in affected_paths
                for src, tgt in zip(path, path[1:])
            }
            impacted_channels = [
                ch for ch in impact.communication_channels
                if (ch.source, ch.target) in affected_channel_ids
            ]
            max_risk = max((ch.risk_score for ch in impacted_channels), default=0.0)
            # Also factor in the rule's own risk score
            rule_risk = float(rule.get("risk_score", 5.0)) / 10.0 * 10.0
            composite_risk = (max_risk + rule_risk) / 2.0
            label = _break_risk_label(composite_risk)

            explanation = (
                f"Rule affects {component_type}. "
                f"Max channel risk: {max_risk:.1f}/10. "
                f"Rule risk score: {rule_risk:.1f}/10. "
                f"Composite: {composite_risk:.1f}/10."
            )

            dr_result = DryRunRuleResult(
                rule_id=rule.get("rule_id", ""),
                profile_rule_id=rule.get("profile_rule_id", ""),
                title=rule.get("title", ""),
                risk_score=composite_risk,
                impacted_channels=impacted_channels,
                break_risk=label,
                explanation=explanation,
            )

            if label in ("critical", "high"):
                breaking.append(dr_result)
            elif label in ("medium", "low"):
                risky.append(dr_result)
            else:
                safe.append(dr_result)

        return DryRunReport(
            instance_id=instance_id,
            safe_rules=safe,
            risky_rules=risky,
            breaking_rules=breaking,
            generated_at=datetime.now(timezone.utc),
        )
