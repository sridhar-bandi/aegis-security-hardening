"""LLM prompt templates for code generation."""
from __future__ import annotations

CODE_GEN_SYSTEM = """You are an expert security automation engineer.
Generate Python code for HPE Private Cloud security hardening.
The code runs inside a pre-imported namespace that provides:
  - `connector`: an instance of a BaseConnector subclass (SSH/Redfish/Netmiko/K8s/Vault)
  - `result`: a dict to populate with findings
  - `logger`: standard Python logger
Output ONLY valid Python code, no markdown fences, no explanation."""

EVAL_CODE_TEMPLATE = """Generate evaluation (check) Python code for the following security rule.

Rule ID: {rule_id}
Title: {title}
Severity: {severity}
Component Type: {component_type}
Description: {description}
Check Guidance: {check_content}

--- Similar rules (few-shot context) ---
{few_shot}
--- End few-shot context ---

Requirements:
1. Use `connector` to connect and query the target system
2. Populate `result["compliant"]` (bool) and `result["details"]` (str)
3. Handle exceptions and log them via `logger`
4. Code must be self-contained; do NOT import external libraries
5. Return at end of code (no `return` statement — this is exec'd at module level)

Python code:"""

REMEDIATION_CODE_TEMPLATE = """Generate remediation Python code to fix the following security rule violation.

Rule ID: {rule_id}
Title: {title}
Severity: {severity}
Component Type: {component_type}
Fix Guidance: {fix_text}

--- Similar rules (few-shot context) ---
{few_shot}
--- End few-shot context ---

Requirements:
1. FIRST save current state to `result["saved_state"]` (dict) so rollback is possible
2. Apply the remediation using `connector`
3. Verify the change was applied; populate `result["success"]` (bool) and `result["details"]` (str)
4. Handle exceptions; log via `logger`

Python code:"""

ROLLBACK_CODE_TEMPLATE = """Generate rollback Python code to restore the previous state for:

Rule ID: {rule_id}
Title: {title}
Component Type: {component_type}

The previous state is available as `saved_state` (dict) in the namespace.

Requirements:
1. Restore state from `saved_state` using `connector`
2. Populate `result["success"]` (bool) and `result["details"]` (str)
3. Handle exceptions; log via `logger`

Python code:"""


def format_few_shot(examples: list[dict]) -> str:
    if not examples:
        return "(no similar rules found)"
    lines = []
    for ex in examples[:3]:
        lines.append(f"Example: {ex.get('title','')}\n{ex.get('code','')[:300]}")
    return "\n\n".join(lines)


# ── Golden Config Generation Prompts (Nautobot) ──────────────────────────────

GOLDEN_CONFIG_SYSTEM = """You are an expert network and infrastructure security engineer.
Generate golden configuration snippets that represent the compliant state for a security rule.
The output should be a configuration fragment that can be pushed to Nautobot as the intended
(golden) configuration for compliance checking.
Output ONLY the configuration text, no markdown fences, no explanation."""

GOLDEN_CONFIG_CLI_TEMPLATE = """Generate a CLI-format golden configuration snippet for the following security rule.
The output should be the exact CLI commands/configuration lines that represent compliance.

Rule ID: {rule_id}
Title: {title}
Severity: {severity}
Component Type: {component_type}
Description: {description}
Check Guidance: {check_content}

--- Similar rules (few-shot context) ---
{few_shot}
--- End few-shot context ---

Requirements:
1. Output ONLY the CLI configuration lines (one per line)
2. These lines represent the COMPLIANT state of the device/system
3. Be specific and use industry-standard CLI syntax for the component type
4. Include comments (! or #) to explain each section if helpful

CLI configuration:"""

GOLDEN_CONFIG_JSON_TEMPLATE = """Generate a JSON-format golden configuration for the following security rule.
The output should be a JSON object representing the compliant configuration state.

Rule ID: {rule_id}
Title: {title}
Severity: {severity}
Component Type: {component_type}
Description: {description}
Check Guidance: {check_content}

--- Similar rules (few-shot context) ---
{few_shot}
--- End few-shot context ---

Requirements:
1. Output ONLY valid JSON (no markdown, no explanation)
2. The JSON should represent the COMPLIANT state of the device/system
3. Use descriptive keys that match the component type's configuration schema
4. Include only configuration relevant to this specific security rule

JSON configuration:"""
