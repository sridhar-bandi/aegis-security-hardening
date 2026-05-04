"""ARF (Asset Reporting Format) XML generator compatible with OpenSCAP ARF 1.1."""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from lxml import etree


ARF_NS = "http://scap.nist.gov/schema/asset-reporting-format/1.1"
CORE_NS = "http://scap.nist.gov/schema/reporting-core/1.1"
AI_NS = "http://scap.nist.gov/schema/asset-identification/1.1"
OVAL_RES_NS = "http://oval.mitre.org/XMLSchema/oval-results-5"

NSMAP = {
    "arf": ARF_NS,
    "rc": CORE_NS,
    "ai": AI_NS,
}


class ARFGenerator:
    def __init__(self, reports_dir: str) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        instance_id: str,
        job_id: str,
        eval_results: list[dict],
        system_info: dict,
    ) -> str:
        """
        Generate an ARF report XML and return the file path.
        eval_results: list of {rule_id, title, compliant, details, severity, component_type}
        system_info: {hostname, ip_address, os}
        """
        report_id = f"arf-{job_id}"
        root = etree.Element(f"{{{ARF_NS}}}asset-report-collection", nsmap=NSMAP)
        root.set("schemaVersion", "1.1")

        # Relationships
        relationships = etree.SubElement(root, f"{{{CORE_NS}}}relationships")
        rel = etree.SubElement(relationships, f"{{{CORE_NS}}}relationship")
        rel.set("type", "isAbout")
        rel.set("subjectRef", report_id)
        etree.SubElement(rel, f"{{{CORE_NS}}}ref").text = f"asset-{instance_id}"

        # Assets
        assets = etree.SubElement(root, f"{{{ARF_NS}}}assets")
        asset = etree.SubElement(assets, f"{{{ARF_NS}}}asset")
        asset.set("id", f"asset-{instance_id}")
        system = etree.SubElement(asset, f"{{{AI_NS}}}system")
        etree.SubElement(system, f"{{{AI_NS}}}hostname").text = system_info.get("hostname", "unknown")
        etree.SubElement(system, f"{{{AI_NS}}}ip-address").text = system_info.get("ip_address", "0.0.0.0")
        etree.SubElement(system, f"{{{AI_NS}}}os").text = system_info.get("os", "unknown")

        # Reports
        reports = etree.SubElement(root, f"{{{ARF_NS}}}reports")
        report = etree.SubElement(reports, f"{{{ARF_NS}}}report")
        report.set("id", report_id)

        content = etree.SubElement(report, f"{{{ARF_NS}}}content")
        results_el = etree.SubElement(content, f"{{{OVAL_RES_NS}}}oval_results")
        results_el.set("xmlns:oval-res", OVAL_RES_NS)
        results_el.set("schema_version", "5.11")

        results_list = etree.SubElement(results_el, f"{{{OVAL_RES_NS}}}results")
        system_el = etree.SubElement(results_list, f"{{{OVAL_RES_NS}}}system")
        etree.SubElement(system_el, f"{{{OVAL_RES_NS}}}oval_system_characteristics")

        definitions_results = etree.SubElement(system_el, f"{{{OVAL_RES_NS}}}definitions")
        for rule in eval_results:
            defn_el = etree.SubElement(definitions_results, f"{{{OVAL_RES_NS}}}definition")
            defn_el.set("definition_id", rule.get("rule_id", "unknown"))
            defn_el.set("result", "true" if rule.get("compliant") else "false")
            defn_el.set("version", "1")
            msg_el = etree.SubElement(defn_el, f"{{{OVAL_RES_NS}}}message")
            msg_el.text = rule.get("details", "")

        # Write to file
        filename = f"arf_{job_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.xml"
        file_path = self.reports_dir / filename
        tree = etree.ElementTree(root)
        tree.write(str(file_path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        return str(file_path)
