<!-- markdownlint-disable-file -->

# Task Details: Nautobot Golden Configuration Integration for Policy Evaluation

## Research Reference

**Source Research**: #file:../research/20260507-nautobot-golden-config-integration-research.md

## Phase 1: Database & Model Changes

### Task 1.1: Create Alembic Migration 007

Create migration file `backend/migrations/versions/007_nautobot_golden_config.py` that adds:

**Table `policy_rules` — new columns:**

```python
op.add_column('policy_rules', sa.Column('evaluation_method', sa.Enum('script', 'nautobot_golden_config', name='evaluation_method', create_type=False), nullable=False, server_default='script'))
op.add_column('policy_rules', sa.Column('golden_config_data', sa.Text(), nullable=True))
op.add_column('policy_rules', sa.Column('golden_config_format', sa.Enum('cli', 'json', name='golden_config_format', create_type=False), nullable=True))
op.add_column('policy_rules', sa.Column('golden_config_status', sa.Enum('pending', 'generating', 'generated', 'reviewed', 'approved', name='golden_config_status', create_type=False), nullable=True))
```

**Table `blueprint_rules` — new columns:**

```python
op.add_column('blueprint_rules', sa.Column('evaluation_method', sa.Enum('script', 'nautobot_golden_config', name='evaluation_method', create_type=False), nullable=False, server_default='script'))
op.add_column('blueprint_rules', sa.Column('golden_config_data', sa.Text(), nullable=True))
op.add_column('blueprint_rules', sa.Column('golden_config_format', sa.Enum('cli', 'json', name='golden_config_format', create_type=False), nullable=True))
```

**Create enum types first:**

```python
evaluation_method_enum = sa.Enum('script', 'nautobot_golden_config', name='evaluation_method')
golden_config_format_enum = sa.Enum('cli', 'json', name='golden_config_format')
golden_config_status_enum = sa.Enum('pending', 'generating', 'generated', 'reviewed', 'approved', name='golden_config_status')

evaluation_method_enum.create(op.get_bind(), checkfirst=True)
golden_config_format_enum.create(op.get_bind(), checkfirst=True)
golden_config_status_enum.create(op.get_bind(), checkfirst=True)
```

**Downgrade:**

```python
op.drop_column('policy_rules', 'golden_config_status')
op.drop_column('policy_rules', 'golden_config_format')
op.drop_column('policy_rules', 'golden_config_data')
op.drop_column('policy_rules', 'evaluation_method')
op.drop_column('blueprint_rules', 'golden_config_format')
op.drop_column('blueprint_rules', 'golden_config_data')
op.drop_column('blueprint_rules', 'evaluation_method')
# Drop enums
sa.Enum(name='golden_config_status').drop(op.get_bind(), checkfirst=True)
sa.Enum(name='golden_config_format').drop(op.get_bind(), checkfirst=True)
sa.Enum(name='evaluation_method').drop(op.get_bind(), checkfirst=True)
```

- **Files**:
  - `backend/migrations/versions/007_nautobot_golden_config.py` — New migration file
- **Success**:
  - Migration runs forward and backward without error
  - New columns exist in both tables with correct defaults
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 173-180) — Implementation components list
- **Dependencies**:
  - Migration 006 must exist and be applied

### Task 1.2: Update PolicyRule ORM Model

Add new mapped columns to `backend/aegis/models/policy.py` in `PolicyRule` class:

```python
# Evaluation method: script (default, exec-based) or nautobot_golden_config (data-driven)
evaluation_method: Mapped[str] = mapped_column(
    Enum("script", "nautobot_golden_config", name="evaluation_method", create_type=False),
    nullable=False,
    default="script",
    server_default="script",
)

# Golden configuration data (CLI text or JSON) for Nautobot integration
golden_config_data: Mapped[str | None] = mapped_column(Text, nullable=True)
golden_config_format: Mapped[str | None] = mapped_column(
    Enum("cli", "json", name="golden_config_format", create_type=False),
    nullable=True,
)
golden_config_status: Mapped[str | None] = mapped_column(
    Enum("pending", "generating", "generated", "reviewed", "approved", name="golden_config_status", create_type=False),
    nullable=True,
)
```

Place these after the existing `rollback_code` field and before `code_status`.

- **Files**:
  - `backend/aegis/models/policy.py` — PolicyRule class extension
- **Success**:
  - Model reflects database schema
  - Existing functionality unaffected (script is the default)
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 76-82) — PolicyRule current structure
- **Dependencies**:
  - Task 1.1 migration applied

### Task 1.3: Update BlueprintRule ORM Model

Add new mapped columns to `backend/aegis/models/hardening_blueprint.py` in `BlueprintRule` class:

```python
# Evaluation method override (inherits from PolicyRule if not set)
evaluation_method: Mapped[str] = mapped_column(
    Enum("script", "nautobot_golden_config", name="evaluation_method", create_type=False),
    nullable=False,
    default="script",
    server_default="script",
)

# Instance-specific golden configuration (overrides PolicyRule golden_config_data)
golden_config_data: Mapped[str | None] = mapped_column(Text, nullable=True)
golden_config_format: Mapped[str | None] = mapped_column(
    Enum("cli", "json", name="golden_config_format", create_type=False),
    nullable=True,
)
```

Place after `rollback_code` and before `code_status`.

- **Files**:
  - `backend/aegis/models/hardening_blueprint.py` — BlueprintRule class extension
- **Success**:
  - BlueprintRule model matches DB schema
  - Existing blueprint functionality unaffected
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 84-87) — BlueprintRule current structure
- **Dependencies**:
  - Task 1.1 migration applied

## Phase 2: Configuration & Nautobot Connector

### Task 2.1: Add Nautobot Settings to config.py

Add to `backend/aegis/config.py` `Settings` class:

```python
# Nautobot Integration (optional — golden config push)
NAUTOBOT_URL: str = ""
NAUTOBOT_API_TOKEN: str = ""
NAUTOBOT_GOLDEN_CONFIG_REPO: str = ""  # Git repo URL for intended configs
NAUTOBOT_VERIFY_SSL: bool = True
```

These settings are optional. When `NAUTOBOT_URL` is empty, Nautobot integration features gracefully degrade (API returns 503 or appropriate error).

- **Files**:
  - `backend/aegis/config.py` — Settings class
- **Success**:
  - Settings load from .env file
  - Application starts successfully with empty Nautobot settings
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 108-109) — Config settings needed
- **Dependencies**:
  - None

### Task 2.2: Create NautobotConnector Service

Create `backend/aegis/services/connectors/nautobot_connector.py`:

```python
"""NautobotConnector — REST client for Nautobot Golden Config integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from aegis.config import settings

logger = logging.getLogger(__name__)


class NautobotConnectionError(Exception):
    pass


@dataclass
class NautobotDevice:
    id: str
    name: str
    platform: str | None
    config_context: dict


class NautobotConnector:
    """REST client for pushing golden configs to Nautobot and triggering compliance jobs."""

    def __init__(self, url: str | None = None, token: str | None = None):
        self.base_url = (url or settings.NAUTOBOT_URL).rstrip("/")
        self.token = token or settings.NAUTOBOT_API_TOKEN
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._session.verify = settings.NAUTOBOT_VERIFY_SSL

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.token)

    def list_devices(self, **filters) -> list[NautobotDevice]:
        """List devices from Nautobot DCIM."""
        resp = self._get("/api/dcim/devices/", params=filters)
        return [
            NautobotDevice(
                id=d["id"], name=d["display"],
                platform=d.get("platform", {}).get("display") if d.get("platform") else None,
                config_context=d.get("local_config_context_data") or {},
            )
            for d in resp.get("results", [])
        ]

    def update_config_context(self, device_id: str, config_context: dict) -> dict:
        """Update a device's local_config_context_data in Nautobot."""
        return self._patch(f"/api/dcim/devices/{device_id}/", json={
            "local_config_context_data": config_context,
        })

    def push_intended_config(self, device_id: str, config_content: str, feature: str) -> dict:
        """
        Push intended configuration for a device.
        Uses Nautobot's config-compliance API for JSON configs,
        or commits to Git repo for CLI configs.
        """
        # For now, update config_context with structured golden config
        # Full Git-based push is Phase 2 enhancement
        return self.update_config_context(device_id, {
            "aegis_golden_config": {
                "feature": feature,
                "config": config_content,
            }
        })

    def trigger_compliance_job(self, device_ids: list[str] | None = None) -> dict:
        """Trigger a Golden Config compliance job via Nautobot Jobs API."""
        payload: dict[str, Any] = {}
        if device_ids:
            payload["device"] = device_ids
        return self._post("/api/extras/jobs/Perform Configuration Compliance/run/", json=payload)

    def get_compliance_status(self, device_id: str) -> list[dict]:
        """Get compliance results for a specific device."""
        resp = self._get("/api/plugins/golden-config/config-compliance/", params={"device_id": device_id})
        return resp.get("results", [])

    def _get(self, path: str, **kwargs) -> dict:
        try:
            resp = self._session.get(f"{self.base_url}{path}", **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise NautobotConnectionError(f"Nautobot GET {path} failed: {exc}") from exc

    def _post(self, path: str, **kwargs) -> dict:
        try:
            resp = self._session.post(f"{self.base_url}{path}", **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise NautobotConnectionError(f"Nautobot POST {path} failed: {exc}") from exc

    def _patch(self, path: str, **kwargs) -> dict:
        try:
            resp = self._session.patch(f"{self.base_url}{path}", **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise NautobotConnectionError(f"Nautobot PATCH {path} failed: {exc}") from exc
```

- **Files**:
  - `backend/aegis/services/connectors/nautobot_connector.py` — New file
- **Success**:
  - Connector can authenticate and make API calls to a Nautobot instance
  - Raises `NautobotConnectionError` on failures
  - `is_configured` property returns False when settings are empty
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 148-158) — Nautobot API endpoints
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 125-140) — Integration approach
- **Dependencies**:
  - Task 2.1 (Nautobot settings in config.py)

## Phase 3: LLM Golden Config Generation

### Task 3.1: Add Golden Config Prompt Templates

Add to `backend/aegis/services/llm/prompts.py`:

```python
GOLDEN_CONFIG_SYSTEM = """You are an expert network security engineer.
Generate the intended (golden) device configuration that represents the secure/hardened state.
Output ONLY the configuration itself — no explanation, no markdown fences, no comments about the format.
The output must be directly usable as a device's intended configuration for compliance checking."""

GOLDEN_CONFIG_CLI_TEMPLATE = """Generate the intended CLI configuration snippet that represents the hardened state for the following security rule.

Rule ID: {rule_id}
Title: {title}
Severity: {severity}
Component Type: {component_type}
Description: {description}
Fix Guidance: {fix_text}

--- Similar rules (few-shot context) ---
{few_shot}
--- End few-shot context ---

Requirements:
1. Output ONLY valid device CLI configuration commands that represent the desired secure state
2. Include commands that SHOULD be present on a compliant device
3. Include negation commands (e.g., "no ip http server") for features that must be disabled
4. Use standard vendor CLI syntax appropriate for the component_type
5. Do NOT include comments or explanations — only raw configuration lines
6. Order logically: global config first, then interface/line-level config
7. This configuration will be compared against the device's running config for drift detection

CLI configuration:"""

GOLDEN_CONFIG_JSON_TEMPLATE = """Generate the intended configuration as a JSON structure representing the hardened state for the following security rule.

Rule ID: {rule_id}
Title: {title}
Severity: {severity}
Component Type: {component_type}
Description: {description}
Fix Guidance: {fix_text}

--- Similar rules (few-shot context) ---
{few_shot}
--- End few-shot context ---

Requirements:
1. Output ONLY valid JSON (no markdown, no explanation)
2. Structure should represent the desired secure state of the configuration feature
3. Use boolean values for enable/disable settings
4. Use descriptive key names matching vendor configuration terminology
5. Include all settings relevant to this security rule
6. The JSON will be compared against the device's actual configuration for drift detection

JSON configuration:"""
```

- **Files**:
  - `backend/aegis/services/llm/prompts.py` — Append new templates
- **Success**:
  - Templates produce valid CLI/JSON when used with LLM
  - Templates follow same variable pattern as existing templates ({rule_id}, {title}, etc.)
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 130-165) — Golden config format examples
- **Dependencies**:
  - None (additive change to existing file)

### Task 3.2: Extend CodeGenerator with generate_golden_config()

Add method to `backend/aegis/services/llm/code_generator.py` `CodeGenerator` class:

```python
async def generate_golden_config(
    self,
    *,
    rule_id: str,
    title: str,
    description: str,
    severity: str,
    component_type: str,
    fix_text: str,
    config_format: str = "cli",  # "cli" or "json"
) -> str:
    """Generate intended golden configuration (CLI or JSON) for Nautobot compliance."""
    from aegis.services.llm.prompts import (
        GOLDEN_CONFIG_SYSTEM,
        GOLDEN_CONFIG_CLI_TEMPLATE,
        GOLDEN_CONFIG_JSON_TEMPLATE,
    )

    query_text = f"{title} {description}"
    try:
        similar = await self._store.search_similar(query_text, top_k=3)
        few_shot_ctx = format_few_shot([
            {"title": s.metadata.get("title", ""), "code": s.metadata.get("eval_code", "")}
            for s in similar
        ])
    except Exception:
        few_shot_ctx = "(retrieval unavailable)"

    template = GOLDEN_CONFIG_CLI_TEMPLATE if config_format == "cli" else GOLDEN_CONFIG_JSON_TEMPLATE
    prompt = GOLDEN_CONFIG_SYSTEM + "\n\n" + template.format(
        rule_id=rule_id,
        title=title,
        severity=severity,
        component_type=component_type,
        description=description,
        fix_text=fix_text,
        few_shot=few_shot_ctx,
    )

    result = await self._llm.generate(prompt)

    # For JSON format, validate it parses correctly
    if config_format == "json":
        import json
        try:
            json.loads(result)
        except json.JSONDecodeError:
            # Attempt to extract JSON from response if wrapped in markdown
            import re
            match = re.search(r'\{[\s\S]*\}', result)
            if match:
                result = match.group(0)

    return result
```

- **Files**:
  - `backend/aegis/services/llm/code_generator.py` — Add method to CodeGenerator class
- **Success**:
  - Method generates valid CLI text or JSON structure from policy rule data
  - Integrates with existing Milvus RAG for few-shot context
  - JSON output is validated/cleaned
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 45-54) — CodeGenerator current structure
- **Dependencies**:
  - Task 3.1 (prompt templates exist)

## Phase 4: Celery Tasks & Backend Logic

### Task 4.1: Add Celery Task for Golden Config Generation

Add to `backend/aegis/tasks/codegen_tasks.py` (or new file `backend/aegis/tasks/golden_config_tasks.py`):

```python
@celery_app.task(bind=True, base=_BaseTask, name="codegen.generate_golden_configs", max_retries=2)
def generate_golden_configs(self: "_BaseTask", policy_id: str, rule_ids: list[str] | None = None, config_format: str = "cli") -> dict:
    """
    Generate golden configuration (CLI or JSON) for PolicyRules that have
    evaluation_method='nautobot_golden_config'. Stores result in golden_config_data.
    """
    return self.run_async(_generate_golden_configs_async(policy_id, rule_ids, config_format, self))


async def _generate_golden_configs_async(
    policy_id: str,
    rule_ids: list[str] | None,
    config_format: str,
    task: "_BaseTask",
) -> dict:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from aegis.models.policy import Policy, PolicyRule
    from aegis.services.llm.code_generator import CodeGenerator

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:golden-config:policy:{policy_id}"
    generator = CodeGenerator()

    results = {"generated": 0, "failed": 0}

    async with SessionFactory() as db:
        query = (
            select(PolicyRule)
            .where(PolicyRule.policy_id == uuid.UUID(policy_id))
            .where(PolicyRule.evaluation_method == "nautobot_golden_config")
        )
        if rule_ids:
            query = query.where(PolicyRule.id.in_([uuid.UUID(r) for r in rule_ids]))

        result = await db.execute(query)
        rules: list[PolicyRule] = list(result.scalars().all())

        total = len(rules)
        _publish(redis_client, channel, {"type": "started", "total": total})

        for idx, pol_rule in enumerate(rules, start=1):
            try:
                _publish(redis_client, channel, {
                    "type": "generating",
                    "rule_id": str(pol_rule.id),
                    "index": idx,
                    "total": total,
                })

                golden_config = await generator.generate_golden_config(
                    rule_id=pol_rule.rule_id,
                    title=pol_rule.title,
                    description=pol_rule.description or "",
                    severity=pol_rule.severity,
                    component_type=(
                        pol_rule.target_component_types[0]
                        if pol_rule.target_component_types
                        else "generic"
                    ),
                    fix_text=pol_rule.fix_text or pol_rule.check_content or "",
                    config_format=config_format,
                )

                await db.execute(
                    update(PolicyRule)
                    .where(PolicyRule.id == pol_rule.id)
                    .values(
                        golden_config_data=golden_config,
                        golden_config_format=config_format,
                        golden_config_status="generated",
                    )
                )
                await db.commit()

                _publish(redis_client, channel, {
                    "type": "done",
                    "rule_id": str(pol_rule.id),
                    "index": idx,
                    "total": total,
                })
                results["generated"] += 1

            except Exception as exc:
                logger.exception("Golden config generation failed for rule %s: %s", pol_rule.id, exc)
                _publish(redis_client, channel, {"type": "error", "rule_id": str(pol_rule.id), "error": str(exc)})
                results["failed"] += 1

    _publish(redis_client, channel, {"type": "completed", **results})
    redis_client.close()
    await engine.dispose()
    return results
```

- **Files**:
  - `backend/aegis/tasks/codegen_tasks.py` — Add new task (appended after existing tasks)
- **Success**:
  - Task generates golden config for all rules with `evaluation_method='nautobot_golden_config'`
  - Publishes progress via Redis pub/sub
  - Stores results in `golden_config_data` column
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 95-103) — Existing codegen task pattern
- **Dependencies**:
  - Phase 1 (model fields exist)
  - Phase 3 (CodeGenerator.generate_golden_config() exists)

### Task 4.2: Add Celery Task for Pushing to Nautobot

Add task for pushing golden configs to Nautobot:

```python
@celery_app.task(bind=True, base=_BaseTask, name="enforcement.push_golden_config_to_nautobot", max_retries=2)
def push_golden_config_to_nautobot(self: "_BaseTask", instance_id: str, device_id: str | None = None) -> dict:
    """
    Push golden configuration from an instance's blueprint rules to Nautobot.
    Uses the NautobotConnector to update device config_context and trigger compliance.
    """
    return self.run_async(_push_golden_config_async(instance_id, device_id))


async def _push_golden_config_async(instance_id: str, device_id: str | None) -> dict:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from aegis.models.solution_instance import SolutionInstance
    from aegis.models.hardening_blueprint import BlueprintRule, HardeningBlueprint
    from aegis.models.policy import PolicyRule
    from aegis.services.connectors.nautobot_connector import NautobotConnector, NautobotConnectionError

    connector = NautobotConnector()
    if not connector.is_configured:
        return {"error": "Nautobot is not configured", "pushed": 0}

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    results = {"pushed": 0, "failed": 0, "skipped": 0}

    async with SessionFactory() as db:
        # Load instance
        inst_result = await db.execute(
            select(SolutionInstance).where(SolutionInstance.id == uuid.UUID(instance_id))
        )
        instance = inst_result.scalar_one_or_none()
        if not instance:
            return {"error": f"Instance {instance_id} not found"}

        # Load blueprint rules with nautobot evaluation method
        query = (
            select(BlueprintRule)
            .join(HardeningBlueprint, BlueprintRule.blueprint_id == HardeningBlueprint.id)
            .where(HardeningBlueprint.id == instance.blueprint_id)
            .where(BlueprintRule.evaluation_method == "nautobot_golden_config")
        )
        br_result = await db.execute(query)
        blueprint_rules = list(br_result.scalars().all())

        # Aggregate golden configs per component_type
        golden_configs: dict[str, list[str]] = {}
        for br in blueprint_rules:
            config_data = br.golden_config_data
            if not config_data:
                # Fall back to PolicyRule golden_config_data
                pr_result = await db.execute(
                    select(PolicyRule).where(PolicyRule.id == br.policy_rule_id)
                )
                pr = pr_result.scalar_one_or_none()
                if pr and pr.golden_config_data:
                    config_data = pr.golden_config_data
            if config_data:
                golden_configs.setdefault(br.component_type, []).append(config_data)
            else:
                results["skipped"] += 1

        # Push aggregated config to Nautobot
        target_device_id = device_id or (instance.scid_json or {}).get("nautobot_device_id")
        if not target_device_id:
            return {"error": "No Nautobot device_id found in instance SCID or request"}

        try:
            combined_config = "\n!\n".join(
                config for configs in golden_configs.values() for config in configs
            )
            connector.push_intended_config(
                device_id=target_device_id,
                config_content=combined_config,
                feature="aegis_security_hardening",
            )
            results["pushed"] = sum(len(v) for v in golden_configs.values())

            # Optionally trigger compliance job
            connector.trigger_compliance_job(device_ids=[target_device_id])
        except NautobotConnectionError as exc:
            logger.exception("Nautobot push failed: %s", exc)
            results["failed"] = sum(len(v) for v in golden_configs.values())

    await engine.dispose()
    return results
```

- **Files**:
  - `backend/aegis/tasks/codegen_tasks.py` or new `backend/aegis/tasks/nautobot_tasks.py` — New task
- **Success**:
  - Task aggregates golden configs from blueprint rules
  - Pushes to Nautobot via NautobotConnector
  - Handles missing config gracefully (skips)
  - Returns push results summary
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 185-198) — Integration flow
- **Dependencies**:
  - Phase 2 (NautobotConnector exists)
  - Phase 1 (model fields exist)

## Phase 5: API Endpoints & Schemas

### Task 5.1: Add Pydantic Schemas

Add to `backend/aegis/schemas/policy.py`:

```python
class GoldenConfigGenRequest(BaseModel):
    rule_ids: list[str] | None = None
    config_format: str = "cli"  # "cli" or "json"

    @field_validator("config_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ("cli", "json"):
            raise ValueError("config_format must be 'cli' or 'json'")
        return v


class EvaluationMethodUpdate(BaseModel):
    evaluation_method: str  # "script" or "nautobot_golden_config"

    @field_validator("evaluation_method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in ("script", "nautobot_golden_config"):
            raise ValueError("evaluation_method must be 'script' or 'nautobot_golden_config'")
        return v


class NautobotPushRequest(BaseModel):
    device_id: str | None = None  # Nautobot device UUID; if None, uses SCID mapping


class NautobotPushResponse(BaseModel):
    task_id: str
    instance_id: str
    status: str = "queued"
```

- **Files**:
  - `backend/aegis/schemas/policy.py` — Add new schema classes
- **Success**:
  - Schemas validate input correctly
  - Consistent with existing schema patterns
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 173-180) — New API endpoint requirements
- **Dependencies**:
  - None

### Task 5.2: Add API Endpoint — POST /policies/{id}/generate-golden-config

Add to `backend/aegis/api/v1/policies.py`:

```python
@router.post("/{policy_id}/generate-golden-config")
async def generate_golden_config(
    policy_id: uuid.UUID,
    body: GoldenConfigGenRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Trigger LLM generation of golden configuration for rules using nautobot evaluation method."""
    # Verify policy exists
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    from aegis.tasks.codegen_tasks import generate_golden_configs
    task = generate_golden_configs.delay(str(policy_id), body.rule_ids, body.config_format)

    return {
        "task_id": task.id,
        "channel": f"ws:golden-config:policy:{policy_id}",
        "policy_id": str(policy_id),
    }
```

- **Files**:
  - `backend/aegis/api/v1/policies.py` — Add endpoint
- **Success**:
  - Endpoint triggers async golden config generation task
  - Returns task_id and WebSocket channel for progress tracking
  - Requires admin/security_officer role
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 176-177) — API endpoint specs
- **Dependencies**:
  - Task 4.1 (Celery task exists)
  - Task 5.1 (schemas exist)

### Task 5.3: Add API Endpoint — POST /instances/{id}/push-nautobot

Add to `backend/aegis/api/v1/instances.py`:

```python
@router.post("/{instance_id}/push-nautobot")
async def push_to_nautobot(
    instance_id: uuid.UUID,
    body: NautobotPushRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Push golden configuration from instance's blueprint to Nautobot for drift monitoring."""
    from aegis.services.connectors.nautobot_connector import NautobotConnector

    connector = NautobotConnector()
    if not connector.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nautobot integration is not configured. Set NAUTOBOT_URL and NAUTOBOT_API_TOKEN.",
        )

    # Verify instance exists
    result = await db.execute(
        select(SolutionInstance).where(SolutionInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    if not instance.blueprint_id:
        raise HTTPException(status_code=400, detail="Instance has no associated blueprint")

    from aegis.tasks.codegen_tasks import push_golden_config_to_nautobot
    task = push_golden_config_to_nautobot.delay(str(instance_id), body.device_id)

    return NautobotPushResponse(
        task_id=task.id,
        instance_id=str(instance_id),
        status="queued",
    )
```

- **Files**:
  - `backend/aegis/api/v1/instances.py` — Add endpoint
- **Success**:
  - Endpoint validates Nautobot is configured (returns 503 if not)
  - Triggers async push task
  - Validates instance exists and has a blueprint
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 185-198) — Push flow
- **Dependencies**:
  - Task 4.2 (push task exists)
  - Task 5.1 (schemas exist)

### Task 5.4: Add API Endpoint — PATCH /policies/{id}/rules/{rule_id}/evaluation-method

Add to `backend/aegis/api/v1/policies.py`:

```python
@router.patch("/{policy_id}/rules/{rule_id}/evaluation-method")
async def update_evaluation_method(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: EvaluationMethodUpdate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Toggle a policy rule's evaluation method between script and nautobot_golden_config."""
    result = await db.execute(
        select(PolicyRule)
        .where(PolicyRule.id == rule_id)
        .where(PolicyRule.policy_id == policy_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Policy rule not found")

    await db.execute(
        update(PolicyRule)
        .where(PolicyRule.id == rule_id)
        .values(evaluation_method=body.evaluation_method)
    )
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)
```

- **Files**:
  - `backend/aegis/api/v1/policies.py` — Add endpoint
- **Success**:
  - Users can toggle individual rules between script and nautobot methods
  - Returns updated rule with new evaluation_method
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 173-174) — Evaluation method enum
- **Dependencies**:
  - Task 1.2 (model field exists)
  - Task 5.1 (schema exists)

## Phase 6: Frontend Updates

### Task 6.1: Update TypeScript Types

Update `frontend/src/types/index.ts`:

Add to `PolicyRule` interface:

```typescript
evaluation_method: 'script' | 'nautobot_golden_config'
golden_config_data: string | null
golden_config_format: 'cli' | 'json' | null
golden_config_status: 'pending' | 'generating' | 'generated' | 'reviewed' | 'approved' | null
```

Add to `BlueprintRule` interface:

```typescript
evaluation_method: 'script' | 'nautobot_golden_config'
golden_config_data: string | null
golden_config_format: 'cli' | 'json' | null
```

- **Files**:
  - `frontend/src/types/index.ts` — Extend existing interfaces
- **Success**:
  - TypeScript compilation succeeds
  - New fields are accessible in components
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 173-180) — Field specs
- **Dependencies**:
  - Phase 5 (backend returns these fields)

### Task 6.2: Add API Endpoint Functions

Add to `frontend/src/api/endpoints.ts`:

```typescript
// Golden Config
export const generateGoldenConfig = (policyId: string, ruleIds?: string[], configFormat?: string) =>
  api.post<{ task_id: string; channel: string }>(`/policies/${policyId}/generate-golden-config`, {
    rule_ids: ruleIds ?? null,
    config_format: configFormat ?? 'cli',
  }).then((r) => r.data)

export const updateEvaluationMethod = (policyId: string, ruleId: string, method: string) =>
  api.patch<PolicyRule>(`/policies/${policyId}/rules/${ruleId}/evaluation-method`, {
    evaluation_method: method,
  }).then((r) => r.data)

export const pushToNautobot = (instanceId: string, deviceId?: string) =>
  api.post<{ task_id: string; instance_id: string; status: string }>(`/instances/${instanceId}/push-nautobot`, {
    device_id: deviceId ?? null,
  }).then((r) => r.data)
```

- **Files**:
  - `frontend/src/api/endpoints.ts` — Append new functions
- **Success**:
  - Functions correctly call backend endpoints
  - TypeScript types match expected responses
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 173-180) — API spec
- **Dependencies**:
  - Task 6.1 (types updated)

### Task 6.3: Add Evaluation Method Toggle in PolicyManager

Update the PolicyManager component (likely `frontend/src/components/PolicyManager/`) to add:

1. A dropdown/toggle per PolicyRule row showing "Script" or "Nautobot Golden Config"
2. When "Nautobot Golden Config" is selected, show a "Generate Golden Config" button
3. Display `golden_config_data` in a read-only code viewer (Monaco or pre-formatted)
4. Show `golden_config_status` badge next to the evaluation method

Key UI elements:
- Toggle switch or select dropdown in the rule row/detail view
- "Generate Golden Config" button (disabled when evaluation_method is "script")
- Golden config preview panel (collapsible)
- Status indicator showing generation progress

- **Files**:
  - `frontend/src/components/PolicyManager/` — Update existing component(s)
  - Potentially new sub-component: `GoldenConfigPanel.tsx`
- **Success**:
  - Users can switch evaluation method per rule
  - Golden config generation can be triggered from UI
  - Generated config is viewable
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 180) — Frontend toggle requirement
- **Dependencies**:
  - Task 6.1 and 6.2

### Task 6.4: Add "Push to Nautobot" in EnforcementConsole

Update `frontend/src/components/EnforcementConsole/` to add:

1. A "Push to Nautobot" button (visible only when instance has blueprint rules with nautobot evaluation method)
2. Dialog/modal for confirming push with optional device_id input
3. Status feedback showing push result

Key UI elements:
- Button in enforcement actions toolbar
- Modal with device_id input field and confirmation
- Toast/notification showing push success/failure
- Disabled state when Nautobot is not configured (can check via a health endpoint or config flag)

- **Files**:
  - `frontend/src/components/EnforcementConsole/` — Update existing component(s)
- **Success**:
  - "Push to Nautobot" button appears for appropriate instances
  - Push triggers async task and shows feedback
  - Button is disabled/hidden when no golden config rules exist
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 185-198) — Push flow
- **Dependencies**:
  - Task 6.2 (API function exists)

## Phase 7: Testing & Documentation

### Task 7.1: Add Unit Tests for NautobotConnector

Create `backend/tests/test_nautobot_connector.py`:

```python
"""Tests for NautobotConnector service."""
import pytest
from unittest.mock import patch, MagicMock

from aegis.services.connectors.nautobot_connector import NautobotConnector, NautobotConnectionError


class TestNautobotConnector:
    def test_is_configured_true(self):
        connector = NautobotConnector(url="http://nautobot.local", token="abc123")
        assert connector.is_configured is True

    def test_is_configured_false_no_url(self):
        connector = NautobotConnector(url="", token="abc123")
        assert connector.is_configured is False

    def test_is_configured_false_no_token(self):
        connector = NautobotConnector(url="http://nautobot.local", token="")
        assert connector.is_configured is False

    @patch("aegis.services.connectors.nautobot_connector.requests.Session")
    def test_list_devices(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [
            {"id": "dev-1", "display": "switch-01", "platform": {"display": "aruba_aoscx"}, "local_config_context_data": {}}
        ]}
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        connector = NautobotConnector(url="http://nautobot.local", token="test")
        connector._session = mock_session
        devices = connector.list_devices()
        assert len(devices) == 1
        assert devices[0].name == "switch-01"

    @patch("aegis.services.connectors.nautobot_connector.requests.Session")
    def test_push_intended_config(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "dev-1", "local_config_context_data": {"aegis_golden_config": {}}}
        mock_resp.raise_for_status = MagicMock()
        mock_session.patch.return_value = mock_resp

        connector = NautobotConnector(url="http://nautobot.local", token="test")
        connector._session = mock_session
        result = connector.push_intended_config("dev-1", "ip ssh version 2", "ssh")
        assert "id" in result

    @patch("aegis.services.connectors.nautobot_connector.requests.Session")
    def test_connection_error(self, mock_session_cls):
        import requests as req
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.side_effect = req.ConnectionError("refused")

        connector = NautobotConnector(url="http://nautobot.local", token="test")
        connector._session = mock_session
        with pytest.raises(NautobotConnectionError):
            connector.list_devices()
```

- **Files**:
  - `backend/tests/test_nautobot_connector.py` — New test file
- **Success**:
  - All tests pass
  - Connector behavior is validated with mocked HTTP
  - Error handling is tested
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 173-260) — Connector implementation
- **Dependencies**:
  - Task 2.2 (NautobotConnector exists)

### Task 7.2: Add Unit Tests for Golden Config Generation

Create `backend/tests/test_golden_config_gen.py`:

```python
"""Tests for golden config LLM generation."""
import pytest
from unittest.mock import AsyncMock, patch

from aegis.services.llm.code_generator import CodeGenerator


@pytest.mark.asyncio
class TestGoldenConfigGeneration:
    @patch.object(CodeGenerator, '_store')
    @patch.object(CodeGenerator, '_llm')
    async def test_generate_cli_config(self, mock_llm, mock_store):
        mock_store.search_similar = AsyncMock(return_value=[])
        mock_llm.generate = AsyncMock(return_value="ip ssh version 2\nline vty 0 15\n transport input ssh")

        gen = CodeGenerator()
        gen._llm = mock_llm
        gen._store = mock_store

        result = await gen.generate_golden_config(
            rule_id="CIS-SWITCH-1.1",
            title="Disable Telnet",
            description="Use SSH only",
            severity="critical",
            component_type="switch",
            fix_text="ip ssh version 2",
            config_format="cli",
        )
        assert "ssh" in result
        assert "version 2" in result

    @patch.object(CodeGenerator, '_store')
    @patch.object(CodeGenerator, '_llm')
    async def test_generate_json_config(self, mock_llm, mock_store):
        mock_store.search_similar = AsyncMock(return_value=[])
        mock_llm.generate = AsyncMock(return_value='{"ssh": {"version": 2, "enabled": true}}')

        gen = CodeGenerator()
        gen._llm = mock_llm
        gen._store = mock_store

        result = await gen.generate_golden_config(
            rule_id="CIS-SWITCH-1.1",
            title="Disable Telnet",
            description="Use SSH only",
            severity="critical",
            component_type="switch",
            fix_text="ip ssh version 2",
            config_format="json",
        )
        import json
        parsed = json.loads(result)
        assert "ssh" in parsed
```

- **Files**:
  - `backend/tests/test_golden_config_gen.py` — New test file
- **Success**:
  - Tests validate CLI and JSON generation paths
  - Mocked LLM responses are correctly processed
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 338-392) — generate_golden_config implementation
- **Dependencies**:
  - Task 3.2 (generate_golden_config method exists)

### Task 7.3: Update .env.example with Nautobot Settings

Add to `.env.example`:

```env
# Nautobot Integration (optional — for golden config drift monitoring)
NAUTOBOT_URL=
NAUTOBOT_API_TOKEN=
NAUTOBOT_GOLDEN_CONFIG_REPO=
NAUTOBOT_VERIFY_SSL=true
```

- **Files**:
  - `.env.example` — Append Nautobot settings section
- **Success**:
  - New settings are documented in .env.example
  - Values are empty by default (optional integration)
- **Research References**:
  - #file:../research/20260507-nautobot-golden-config-integration-research.md (Lines 142-171) — Settings spec
- **Dependencies**:
  - Task 2.1 (settings in config.py)

## Dependencies

- `requests` (already in requirements.txt)
- `gitpython` (add to requirements.txt — needed for future Git-based intended config push)

## Success Criteria

- PolicyRules can be toggled between "script" and "nautobot_golden_config" evaluation methods
- LLM generates valid CLI/JSON golden configuration from policy rule fix_text/check_content
- Golden configs are stored in DB and viewable in frontend
- Push to Nautobot works when Nautobot is configured (updates config_context, triggers compliance)
- System gracefully degrades when Nautobot is not configured (503 response, clear messaging)
- Script-based evaluation/remediation/rollback remain the default and are completely unaffected
- All new code has unit test coverage
