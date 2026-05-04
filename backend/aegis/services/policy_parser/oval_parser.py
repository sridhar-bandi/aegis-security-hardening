"""OVAL 5.x XML policy parser."""
from __future__ import annotations

import logging
from lxml import etree

from aegis.services.policy_parser.base import PolicyRuleData, PolicyParseError

logger = logging.getLogger(__name__)

OVAL_NS = "http://oval.mitre.org/XMLSchema/oval-definitions-5"
OVAL_DEF_NS = f"{{{OVAL_NS}}}"

OVAL_CLASS_SEVERITY_MAP = {
    "vulnerability": "critical",
    "patch": "high",
    "compliance": "medium",
    "inventory": "low",
    "miscellaneous": "informational",
}


class OVALParser:
    def parse(self, file_path: str) -> list[PolicyRuleData]:
        try:
            tree = etree.parse(file_path)
        except etree.XMLSyntaxError as exc:
            raise PolicyParseError(f"Invalid OVAL XML: {exc}") from exc
        except OSError as exc:
            raise PolicyParseError(f"Cannot read OVAL file '{file_path}': {exc}") from exc

        root = tree.getroot()
        definitions = root.find(f"{OVAL_DEF_NS}definitions")
        if definitions is None:
            # Try without namespace (some older files)
            definitions = root.find("definitions")
        if definitions is None:
            logger.warning("No <definitions> element found in OVAL file: %s", file_path)
            return []

        rules: list[PolicyRuleData] = []
        ns = OVAL_DEF_NS if root.tag.startswith("{") else ""

        for defn in definitions.findall(f"{ns}definition"):
            rule_id = defn.get("id", "")
            class_attr = defn.get("class", "compliance")
            severity = OVAL_CLASS_SEVERITY_MAP.get(class_attr, "medium")

            metadata = defn.find(f"{ns}metadata")
            title = ""
            description = ""
            if metadata is not None:
                title_el = metadata.find(f"{ns}title")
                desc_el = metadata.find(f"{ns}description")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            # Extract criteria as check_content summary
            criteria = defn.find(f"{ns}criteria")
            check_content = ""
            if criteria is not None:
                check_content = etree.tostring(criteria, encoding="unicode", method="text").strip()[:1000]

            if not rule_id or not title:
                continue

            rules.append(PolicyRuleData(
                rule_id=rule_id,
                title=title,
                description=description,
                severity=severity,
                check_content=check_content,
            ))

        logger.info("OVAL parser extracted %d rules from %s", len(rules), file_path)
        return rules
