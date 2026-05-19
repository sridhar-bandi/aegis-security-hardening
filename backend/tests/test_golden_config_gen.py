"""Unit tests for golden config generation via LLM."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestGoldenConfigPrompts:
    def test_golden_config_system_prompt_exists(self):
        from aegis.services.llm.prompts import GOLDEN_CONFIG_SYSTEM
        assert "golden configuration" in GOLDEN_CONFIG_SYSTEM.lower()

    def test_golden_config_cli_template_exists(self):
        from aegis.services.llm.prompts import GOLDEN_CONFIG_CLI_TEMPLATE
        assert "{rule_id}" in GOLDEN_CONFIG_CLI_TEMPLATE
        assert "{title}" in GOLDEN_CONFIG_CLI_TEMPLATE
        assert "CLI" in GOLDEN_CONFIG_CLI_TEMPLATE

    def test_golden_config_json_template_exists(self):
        from aegis.services.llm.prompts import GOLDEN_CONFIG_JSON_TEMPLATE
        assert "{rule_id}" in GOLDEN_CONFIG_JSON_TEMPLATE
        assert "{title}" in GOLDEN_CONFIG_JSON_TEMPLATE
        assert "JSON" in GOLDEN_CONFIG_JSON_TEMPLATE

    def test_cli_template_formatting(self):
        from aegis.services.llm.prompts import GOLDEN_CONFIG_CLI_TEMPLATE
        result = GOLDEN_CONFIG_CLI_TEMPLATE.format(
            rule_id="CIS-1.1.1",
            title="Ensure NTP is configured",
            severity="high",
            component_type="NetworkSwitch",
            description="Test description",
            check_content="Check NTP settings",
            few_shot="(no similar rules found)",
        )
        assert "CIS-1.1.1" in result
        assert "Ensure NTP is configured" in result

    def test_json_template_formatting(self):
        from aegis.services.llm.prompts import GOLDEN_CONFIG_JSON_TEMPLATE
        result = GOLDEN_CONFIG_JSON_TEMPLATE.format(
            rule_id="CIS-2.1.1",
            title="Ensure SSH is properly configured",
            severity="critical",
            component_type="Server",
            description="SSH hardening",
            check_content="Check SSH settings",
            few_shot="(no similar rules found)",
        )
        assert "CIS-2.1.1" in result
        assert "SSH" in result


class TestCodeGeneratorGoldenConfig:
    @pytest.mark.asyncio
    async def test_generate_golden_config_cli(self):
        from aegis.services.llm.code_generator import CodeGenerator

        with patch.object(CodeGenerator, "__init__", lambda self: None):
            gen = CodeGenerator()
            gen._llm = MagicMock()
            gen._llm.generate = AsyncMock(return_value="ntp server 10.0.0.1\nhostname secure-switch")
            gen._store = MagicMock()
            gen._store.search_similar = AsyncMock(return_value=[])

            result = await gen.generate_golden_config(
                rule_id="CIS-1.1.1",
                title="Ensure NTP is configured",
                description="NTP should be set to authorized time server",
                severity="high",
                component_type="NetworkSwitch",
                check_content="Verify NTP configuration",
                config_format="cli",
            )
            assert "ntp server" in result
            gen._llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_golden_config_json(self):
        from aegis.services.llm.code_generator import CodeGenerator

        with patch.object(CodeGenerator, "__init__", lambda self: None):
            gen = CodeGenerator()
            gen._llm = MagicMock()
            gen._llm.generate = AsyncMock(return_value='{"ntp": {"servers": ["10.0.0.1"]}}')
            gen._store = MagicMock()
            gen._store.search_similar = AsyncMock(return_value=[])

            result = await gen.generate_golden_config(
                rule_id="CIS-1.1.1",
                title="Ensure NTP is configured",
                description="NTP should be set to authorized time server",
                severity="high",
                component_type="NetworkSwitch",
                check_content="Verify NTP configuration",
                config_format="json",
            )
            assert "ntp" in result
            gen._llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_golden_config_milvus_failure_graceful(self):
        from aegis.services.llm.code_generator import CodeGenerator

        with patch.object(CodeGenerator, "__init__", lambda self: None):
            gen = CodeGenerator()
            gen._llm = MagicMock()
            gen._llm.generate = AsyncMock(return_value="hostname secure")
            gen._store = MagicMock()
            gen._store.search_similar = AsyncMock(side_effect=Exception("Milvus down"))

            result = await gen.generate_golden_config(
                rule_id="CIS-1.1.1",
                title="Ensure hostname is set",
                description="Set device hostname",
                severity="medium",
                component_type="Server",
                check_content="Check hostname",
                config_format="cli",
            )
            assert result == "hostname secure"


class TestEvaluationMethodSchema:
    def test_evaluation_method_update_schema(self):
        from aegis.schemas.policy import EvaluationMethodUpdate
        schema = EvaluationMethodUpdate(evaluation_method="nautobot_golden_config")
        assert schema.evaluation_method == "nautobot_golden_config"

    def test_golden_config_gen_request_schema(self):
        from aegis.schemas.policy import GoldenConfigGenRequest
        schema = GoldenConfigGenRequest(config_format="json")
        assert schema.config_format == "json"
        assert schema.rule_ids is None

    def test_nautobot_push_request_schema(self):
        from aegis.schemas.policy import NautobotPushRequest
        schema = NautobotPushRequest(device_name="switch01")
        assert schema.device_name == "switch01"
        assert schema.rule_ids is None


class TestPolicyRuleResponseSchema:
    def test_policy_rule_response_has_golden_config_fields(self):
        from aegis.schemas.policy import PolicyRuleResponse
        import uuid
        from datetime import datetime
        rule = PolicyRuleResponse(
            id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            rule_id="CIS-1.1",
            title="Test",
            description=None,
            rationale=None,
            severity="high",
            category=None,
            target_component_types=None,
            check_content=None,
            fix_text=None,
            evaluation_code=None,
            remediation_code=None,
            rollback_code=None,
            code_status="pending",
            code_source="llm",
            imported_filename=None,
            reviewed_by=None,
            reviewed_at=None,
            evaluation_method="nautobot_golden_config",
            golden_config_data="ntp server 10.0.0.1",
            golden_config_format="cli",
            golden_config_status="generated",
            created_at=datetime.now(),
        )
        assert rule.evaluation_method == "nautobot_golden_config"
        assert rule.golden_config_data == "ntp server 10.0.0.1"
        assert rule.golden_config_format == "cli"
        assert rule.golden_config_status == "generated"
