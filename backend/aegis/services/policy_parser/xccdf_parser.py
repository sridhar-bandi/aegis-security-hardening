"""XCCDF 1.2 XML policy parser."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from lxml import etree

from aegis.services.policy_parser.base import PolicyRuleData, PolicyParseError

logger = logging.getLogger(__name__)

XCCDF_NS = "http://checklists.nist.gov/xccdf/1.2"
XCCDF = f"{{{XCCDF_NS}}}"

XCCDF_SEVERITY_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "informational",
}


@dataclass
class ProfileInfo:
    profile_id: str
    title: str
    selected_rule_ids: list[str]


class XCCDFParser:
    def _get_benchmark(self, root: etree._Element) -> etree._Element:
        """Handle both standalone Benchmark and data stream collection."""
        tag = root.tag.lower()
        if "benchmark" in tag:
            return root
        # Data stream: look for Benchmark component
        for elem in root.iter():
            if "Benchmark" in elem.tag:
                return elem
        raise PolicyParseError("No <Benchmark> element found in XCCDF file")

    def parse(self, file_path: str) -> list[PolicyRuleData]:
        try:
            tree = etree.parse(file_path)
        except etree.XMLSyntaxError as exc:
            raise PolicyParseError(f"Invalid XCCDF XML: {exc}") from exc

        root = tree.getroot()
        benchmark = self._get_benchmark(root)

        # Detect namespace prefix
        ns = XCCDF if benchmark.tag.startswith("{") else ""

        rules: list[PolicyRuleData] = []
        for rule_el in benchmark.iter(f"{ns}Rule"):
            if rule_el.get("selected", "true").lower() == "false":
                continue

            rule_id = rule_el.get("id", "")
            severity_raw = rule_el.get("severity", "medium")
            severity = XCCDF_SEVERITY_MAP.get(severity_raw, "medium")

            title_el = rule_el.find(f"{ns}title")
            title = title_el.text.strip() if title_el is not None and title_el.text else rule_id

            desc_el = rule_el.find(f"{ns}description")
            description = ""
            if desc_el is not None:
                description = etree.tostring(desc_el, encoding="unicode", method="text").strip()[:2000]

            rat_el = rule_el.find(f"{ns}rationale")
            rationale = ""
            if rat_el is not None:
                rationale = etree.tostring(rat_el, encoding="unicode", method="text").strip()[:1000]

            # fix_text — prefer <fixtext>, fallback to <fix>
            fix_text = ""
            fix_el = rule_el.find(f"{ns}fixtext")
            if fix_el is None:
                fix_el = rule_el.find(f"{ns}fix")
            if fix_el is not None:
                fix_text = etree.tostring(fix_el, encoding="unicode", method="text").strip()[:2000]

            # check_content
            check_content = ""
            check_el = rule_el.find(f".//{ns}check-content")
            if check_el is not None:
                check_content = etree.tostring(check_el, encoding="unicode", method="text").strip()[:2000]

            # Category from metadata or group parent
            category = self._infer_category(rule_el, ns)

            if not rule_id:
                continue

            rules.append(PolicyRuleData(
                rule_id=rule_id,
                title=title,
                description=description,
                rationale=rationale,
                severity=severity,
                category=category,
                check_content=check_content,
                fix_text=fix_text,
            ))

        logger.info("XCCDF parser extracted %d rules from %s", len(rules), file_path)
        return rules

    def get_profiles(self, file_path: str) -> list[ProfileInfo]:
        try:
            tree = etree.parse(file_path)
        except etree.XMLSyntaxError as exc:
            raise PolicyParseError(f"Invalid XCCDF XML: {exc}") from exc

        root = tree.getroot()
        benchmark = self._get_benchmark(root)
        ns = XCCDF if benchmark.tag.startswith("{") else ""

        profiles: list[ProfileInfo] = []
        for profile_el in benchmark.findall(f"{ns}Profile"):
            profile_id = profile_el.get("id", "")
            title_el = profile_el.find(f"{ns}title")
            title = title_el.text.strip() if title_el is not None and title_el.text else profile_id
            selected = [
                sel.get("idref", "")
                for sel in profile_el.findall(f"{ns}select")
                if sel.get("selected", "true").lower() == "true"
            ]
            profiles.append(ProfileInfo(profile_id=profile_id, title=title, selected_rule_ids=selected))

        return profiles

    def _infer_category(self, rule_el: etree._Element, ns: str) -> str:
        """Infer category from rule ID or parent group tag."""
        rule_id = rule_el.get("id", "").lower()
        for keyword in ("filesystem", "network", "authentication", "audit", "logging", "ssh",
                        "tls", "firewall", "kernel", "cron", "service", "user", "password"):
            if keyword in rule_id:
                return keyword
        return "general"
