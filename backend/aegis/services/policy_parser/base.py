"""Shared data classes for policy parsing results."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PolicyRuleData:
    rule_id: str
    title: str
    description: str = ""
    rationale: str = ""
    severity: str = "medium"
    category: str = ""
    target_component_types: list[str] = field(default_factory=list)
    check_content: str = ""
    fix_text: str = ""


class PolicyParseError(Exception):
    pass
