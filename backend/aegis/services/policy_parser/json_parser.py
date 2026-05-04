"""Parser for structured JSON policy files (no LLM required)."""
from __future__ import annotations

import hashlib
import json
import logging
import re

from aegis.services.policy_parser.base import PolicyParseError, PolicyRuleData

logger = logging.getLogger(__name__)

# Valid JSON escape characters after a backslash
_VALID_ESCAPE = re.compile(r'\\([^"\\/bfnrtu])')


def _fix_invalid_escapes(text: str) -> str:
    """Double-escape any backslash not part of a valid JSON escape sequence."""
    return _VALID_ESCAPE.sub(r'\\\\\1', text)


class JSONPolicyParser:
    """Parses a JSON file that is already a list of policy rule objects."""

    def parse(self, file_path: str) -> list[PolicyRuleData]:
        try:
            with open(file_path, encoding="utf-8") as f:
                raw = f.read()
        except OSError as exc:
            raise PolicyParseError(f"JSON policy parse error: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Retry after fixing invalid escape sequences (e.g. \$ \s \d in shell commands)
            try:
                data = json.loads(_fix_invalid_escapes(raw))
            except json.JSONDecodeError as exc:
                raise PolicyParseError(f"JSON policy parse error: {exc}") from exc

        if not isinstance(data, list):
            raise PolicyParseError("JSON policy file must contain a top-level array of rule objects.")

        rules: list[PolicyRuleData] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            rule_id = item.get("rule_id") or f"CUSTOM-{hashlib.md5(item.get('title', '').encode()).hexdigest()[:8]}"
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

        logger.info("JSON parser loaded %d rules from %s", len(rules), file_path)
        return rules
