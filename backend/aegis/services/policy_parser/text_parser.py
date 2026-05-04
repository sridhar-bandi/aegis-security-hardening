"""LLM-assisted plain-text/JSON policy parser."""
from __future__ import annotations

import hashlib
import json
import logging

from aegis.services.policy_parser.base import PolicyRuleData, PolicyParseError

logger = logging.getLogger(__name__)

TEXT_PARSE_PROMPT = """You are a security policy expert. Extract structured security rules from the following text.

For each distinct rule found, output a JSON array where each element has:
- rule_id: string (use format CUSTOM-<short-slug> if not present)
- title: string (concise rule title)
- description: string
- rationale: string (why this rule matters)
- severity: one of "critical", "high", "medium", "low", "informational"
- category: one of "filesystem", "network", "authentication", "audit", "logging", "ssh", "tls", "service", "kernel", "general"
- target_component_types: list of strings (e.g. ["VM-RHEL9", "ArubaSwitch", "iLO"])
- check_content: string (how to evaluate/check this rule)
- fix_text: string (how to remediate this rule)

Output ONLY valid JSON array, no markdown, no explanation.

TEXT:
{text}
"""


class TextPolicyParser:
    async def parse(self, text: str) -> list[PolicyRuleData]:
        """Parse English/JSON policy text into PolicyRuleData using LLM."""
        from aegis.services.llm.client import AegisLLMClient  # late import to avoid circular

        client = AegisLLMClient()
        prompt = TEXT_PARSE_PROMPT.format(text=text[:8000])

        raw = ""
        rules_data = []
        for attempt in range(2):
            try:
                raw = await client.generate(prompt)
                rules_data = json.loads(raw)
                break
            except (json.JSONDecodeError, Exception) as exc:
                if attempt == 1:
                    raise PolicyParseError(f"LLM text parser failed after 2 attempts: {exc}") from exc
                prompt += f"\n\nPrevious response was invalid JSON. Error: {exc}. Try again, output ONLY a JSON array."

        rules: list[PolicyRuleData] = []
        for item in rules_data:
            rule_id = item.get("rule_id") or f"CUSTOM-{hashlib.md5(item.get('title','').encode()).hexdigest()[:8]}"
            rules.append(PolicyRuleData(
                rule_id=rule_id,
                title=item.get("title", "Untitled Rule"),
                description=item.get("description", ""),
                rationale=item.get("rationale", ""),
                severity=item.get("severity", "medium"),
                category=item.get("category", "general"),
                target_component_types=item.get("target_component_types", []),
                check_content=item.get("check_content", ""),
                fix_text=item.get("fix_text", ""),
            ))

        logger.info("Text parser extracted %d rules via LLM", len(rules))
        return rules
