"""Unit tests for OVAL and XCCDF policy parsers using minimal XML fixtures."""
import io
import textwrap
import pytest

from aegis.services.policy_parser.base import PolicyRuleData, PolicyParseError


# ---------------------------------------------------------------------------
# Helpers to write temp XML files
# ---------------------------------------------------------------------------

def _write_tmp(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# OVAL parser
# ---------------------------------------------------------------------------

OVAL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<oval_definitions
    xmlns="http://oval.mitre.org/XMLSchema/oval-definitions-5"
    xmlns:oval="http://oval.mitre.org/XMLSchema/oval-common-5">
  <definitions>
    <definition id="oval:test:def:1" class="compliance">
      <metadata>
        <title>Disable Telnet</title>
        <description>Telnet must be disabled.</description>
        <affected family="unix">
          <platform>Linux</platform>
        </affected>
        <oval_repository>
          <dates><submitted date="2020-01-01"/></dates>
          <status>ACCEPTED</status>
        </oval_repository>
      </metadata>
      <criteria/>
    </definition>
    <definition id="oval:test:def:2" class="compliance">
      <metadata>
        <title>Enforce SSH MaxAuthTries</title>
        <description>MaxAuthTries must be set to 3.</description>
        <affected family="unix">
          <platform>Linux</platform>
        </affected>
        <oval_repository>
          <dates><submitted date="2020-01-01"/></dates>
          <status>ACCEPTED</status>
        </oval_repository>
      </metadata>
      <criteria/>
    </definition>
  </definitions>
</oval_definitions>
"""


class TestOVALParser:
    def test_parses_two_rules(self, tmp_path):
        from aegis.services.policy_parser.oval_parser import OVALParser
        path = _write_tmp(tmp_path, "test.oval.xml", OVAL_XML)
        rules = OVALParser().parse(path)
        assert len(rules) == 2

    def test_rule_ids_extracted(self, tmp_path):
        from aegis.services.policy_parser.oval_parser import OVALParser
        path = _write_tmp(tmp_path, "test.oval.xml", OVAL_XML)
        rules = OVALParser().parse(path)
        ids = {r.rule_id for r in rules}
        assert "oval:test:def:1" in ids
        assert "oval:test:def:2" in ids

    def test_rule_titles_extracted(self, tmp_path):
        from aegis.services.policy_parser.oval_parser import OVALParser
        path = _write_tmp(tmp_path, "test.oval.xml", OVAL_XML)
        rules = OVALParser().parse(path)
        titles = {r.title for r in rules}
        assert "Disable Telnet" in titles

    def test_rule_descriptions_extracted(self, tmp_path):
        from aegis.services.policy_parser.oval_parser import OVALParser
        path = _write_tmp(tmp_path, "test.oval.xml", OVAL_XML)
        rules = OVALParser().parse(path)
        for rule in rules:
            assert len(rule.description) > 0

    def test_invalid_xml_raises(self, tmp_path):
        from aegis.services.policy_parser.oval_parser import OVALParser
        path = _write_tmp(tmp_path, "bad.xml", "<not valid xml")
        with pytest.raises(PolicyParseError):
            OVALParser().parse(path)

    def test_missing_file_raises(self):
        from aegis.services.policy_parser.oval_parser import OVALParser
        with pytest.raises(PolicyParseError):
            OVALParser().parse("/nonexistent/path/file.xml")


# ---------------------------------------------------------------------------
# XCCDF parser
# ---------------------------------------------------------------------------

XCCDF_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Benchmark xmlns="http://checklists.nist.gov/xccdf/1.2"
           id="xccdf_test_benchmark_1">
  <title>Test Hardening Benchmark</title>
  <Rule id="xccdf_test_rule_ssh_1" severity="high" selected="true">
    <title>Disable Root Login via SSH</title>
    <description>PermitRootLogin must be set to no.</description>
    <rationale>Root login over SSH increases attack surface.</rationale>
    <fix>
      <fixtext>Set PermitRootLogin no in /etc/ssh/sshd_config</fixtext>
    </fix>
    <check>
      <check-content>Verify PermitRootLogin is no</check-content>
    </check>
  </Rule>
  <Rule id="xccdf_test_rule_pw_1" severity="medium" selected="true">
    <title>Set Password Minimum Length</title>
    <description>PASS_MIN_LEN must be at least 14.</description>
    <rationale>Longer passwords are harder to guess.</rationale>
    <fix>
      <fixtext>Set PASS_MIN_LEN=14 in /etc/login.defs</fixtext>
    </fix>
    <check>
      <check-content>Verify PASS_MIN_LEN &gt;= 14</check-content>
    </check>
  </Rule>
</Benchmark>
"""


class TestXCCDFParser:
    def test_parses_two_rules(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "test.xccdf.xml", XCCDF_XML)
        rules = XCCDFParser().parse(path)
        assert len(rules) == 2

    def test_rule_ids_extracted(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "test.xccdf.xml", XCCDF_XML)
        rules = XCCDFParser().parse(path)
        ids = {r.rule_id for r in rules}
        assert "xccdf_test_rule_ssh_1" in ids

    def test_severity_extracted(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "test.xccdf.xml", XCCDF_XML)
        rules = {r.rule_id: r for r in XCCDFParser().parse(path)}
        assert rules["xccdf_test_rule_ssh_1"].severity == "high"
        assert rules["xccdf_test_rule_pw_1"].severity == "medium"

    def test_fix_text_extracted(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "test.xccdf.xml", XCCDF_XML)
        rules = {r.rule_id: r for r in XCCDFParser().parse(path)}
        assert "PermitRootLogin" in rules["xccdf_test_rule_ssh_1"].fix_text

    def test_check_content_extracted(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "test.xccdf.xml", XCCDF_XML)
        rules = {r.rule_id: r for r in XCCDFParser().parse(path)}
        assert "PermitRootLogin" in rules["xccdf_test_rule_ssh_1"].check_content

    def test_get_profiles(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "test.xccdf.xml", XCCDF_XML)
        # No Profile elements in this doc → empty list
        profiles = XCCDFParser().get_profiles(path)
        assert isinstance(profiles, list)

    def test_invalid_xml_raises(self, tmp_path):
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        path = _write_tmp(tmp_path, "bad.xml", "<broken")
        with pytest.raises(PolicyParseError):
            XCCDFParser().parse(path)
