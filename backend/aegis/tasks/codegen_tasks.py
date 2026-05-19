"""Celery tasks for LLM code generation."""
from __future__ import annotations

import asyncio
import logging
import uuid

from celery import Task
from redis import Redis

from aegis.config import settings
from aegis.worker import celery_app

logger = logging.getLogger(__name__)


class _BaseTask(Task):
    """Celery Task base with async runner helper."""
    def run_async(self, coro):
        return asyncio.run(coro)


def _publish(redis_client: Redis, channel: str, data: dict) -> None:
    import json
    try:
        redis_client.publish(channel, json.dumps(data))
    except Exception as exc:
        logger.warning("Redis publish failed on channel %s: %s", channel, exc)


# ---------------------------------------------------------------------------
# Policy-level code generation (development stage)
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, base=_BaseTask, name="codegen.generate_policy_codes", max_retries=2)
def generate_policy_codes(self: "_BaseTask", policy_id: str, rule_ids: list[str] | None = None) -> dict:
    """
    Development-stage task: generate evaluate/remediate/rollback code for every
    PolicyRule in a Policy. Generated code is stored on the PolicyRule record
    (canonical/baseline) and upserted into Milvus for contextual retrieval.

    Publishes progress to Redis pub/sub channel ``ws:codegen:policy:{policy_id}``.
    """
    return self.run_async(_generate_policy_codes_async(policy_id, rule_ids, self))


async def _generate_policy_codes_async(
    policy_id: str,
    rule_ids: list[str] | None,
    task: "_BaseTask",
) -> dict:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from aegis.models.policy import Policy, PolicyRule
    from aegis.services.llm.code_generator import CodeGenerator
    from aegis.services.llm.milvus_store import MilvusRuleStore

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:codegen:policy:{policy_id}"
    generator = CodeGenerator()
    store = MilvusRuleStore()

    results = {"generated": 0, "failed": 0, "skipped": 0}

    async with SessionFactory() as db:
        # Mark policy as generating
        await db.execute(
            update(Policy)
            .where(Policy.id == uuid.UUID(policy_id))
            .values(code_status="generating")
        )
        await db.commit()

        query = (
            select(PolicyRule)
            .where(PolicyRule.policy_id == uuid.UUID(policy_id))
            .where(PolicyRule.code_status == "pending")
        )
        if rule_ids:
            query = query.where(PolicyRule.id.in_([uuid.UUID(r) for r in rule_ids]))

        result = await db.execute(query)
        pending_rules: list[PolicyRule] = list(result.scalars().all())

        total = len(pending_rules)
        _publish(redis_client, channel, {"type": "started", "total": total})

        for idx, pol_rule in enumerate(pending_rules, start=1):
            try:
                # Use the primary target component type for baseline code;
                # fall back to "generic" when none specified.
                component_type = (
                    pol_rule.target_component_types[0]
                    if pol_rule.target_component_types
                    else "generic"
                )

                _publish(redis_client, channel, {
                    "type": "generating",
                    "rule_id": str(pol_rule.id),
                    "index": idx,
                    "total": total,
                })

                codes = await generator.generate_all(
                    rule_id=pol_rule.rule_id,
                    title=pol_rule.title,
                    description=pol_rule.description or "",
                    severity=pol_rule.severity,
                    component_type=component_type,
                    check_content=pol_rule.check_content or "",
                    fix_text=pol_rule.fix_text or "",
                )

                await db.execute(
                    update(PolicyRule)
                    .where(PolicyRule.id == pol_rule.id)
                    .values(
                        evaluation_code=codes["evaluation_code"],
                        remediation_code=codes["remediation_code"],
                        rollback_code=codes["rollback_code"],
                        code_status="generated",
                    )
                )
                await db.commit()

                # Upsert into Milvus with generated code in metadata
                metadata = {
                    "title": pol_rule.title,
                    "severity": pol_rule.severity,
                    "component_type": component_type,
                    "category": pol_rule.category or "",
                    "eval_code": codes["evaluation_code"][:1500],
                    "rem_code": codes["remediation_code"][:1500],
                    "rollback_code": codes["rollback_code"][:1000],
                }
                try:
                    await store.upsert_rule(
                        rule_id=pol_rule.rule_id,
                        policy_id=policy_id,
                        text=f"{pol_rule.title} {pol_rule.description or ''}",
                        metadata=metadata,
                    )
                except Exception as milvus_exc:
                    logger.warning(
                        "Milvus upsert failed for policy_rule %s: %s",
                        pol_rule.id,
                        milvus_exc,
                    )

                _publish(redis_client, channel, {
                    "type": "done",
                    "rule_id": str(pol_rule.id),
                    "index": idx,
                    "total": total,
                })
                results["generated"] += 1

            except Exception as exc:
                logger.exception(
                    "Policy-level code generation failed for policy_rule %s: %s",
                    pol_rule.id,
                    exc,
                )
                await db.execute(
                    update(PolicyRule)
                    .where(PolicyRule.id == pol_rule.id)
                    .values(code_status="pending")
                )
                await db.commit()
                _publish(redis_client, channel, {
                    "type": "error",
                    "rule_id": str(pol_rule.id),
                    "error": str(exc),
                })
                results["failed"] += 1

        # Update policy-level code_status
        final_status = "generated" if results["failed"] == 0 else "pending"
        await db.execute(
            update(Policy)
            .where(Policy.id == uuid.UUID(policy_id))
            .values(code_status=final_status)
        )
        await db.commit()

    _publish(redis_client, channel, {"type": "completed", **results})
    redis_client.close()
    await engine.dispose()
    return results


# ---------------------------------------------------------------------------
# Blueprint-level code generation (per component × policy rule)
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, base=_BaseTask, name="codegen.generate_blueprint_codes", max_retries=2)
def generate_blueprint_codes(self: _BaseTask, blueprint_id: str, rule_ids: list[str] | None = None) -> dict:
    """
    Generate evaluate/remediate/rollback code for all pending BlueprintRules in a
    HardeningBlueprint. Falls back to policy-level baseline code from Milvus as
    few-shot context. Publishes progress to Redis pub/sub channel
    ``ws:codegen:{blueprint_id}``.
    """
    return self.run_async(_generate_blueprint_codes_async(blueprint_id, rule_ids, self))


async def _generate_blueprint_codes_async(
    blueprint_id: str,
    rule_ids: list[str] | None,
    task: _BaseTask,
) -> dict:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from aegis.models.hardening_blueprint import HardeningBlueprint, BlueprintRule
    from aegis.models.policy import PolicyRule
    from aegis.services.llm.code_generator import CodeGenerator
    from aegis.services.llm.milvus_store import MilvusRuleStore

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:codegen:{blueprint_id}"
    generator = CodeGenerator()
    store = MilvusRuleStore()

    results = {"generated": 0, "failed": 0, "skipped": 0}

    async with SessionFactory() as db:
        query = (
            select(BlueprintRule)
            .where(BlueprintRule.blueprint_id == uuid.UUID(blueprint_id))
            .where(BlueprintRule.code_status == "pending")
        )
        if rule_ids:
            query = query.where(BlueprintRule.id.in_([uuid.UUID(r) for r in rule_ids]))

        result = await db.execute(query)
        pending_rules: list[BlueprintRule] = list(result.scalars().all())

        total = len(pending_rules)
        _publish(redis_client, channel, {"type": "started", "total": total})

        for idx, pr in enumerate(pending_rules, start=1):
            try:
                pr_result = await db.execute(
                    select(PolicyRule).where(PolicyRule.id == pr.policy_rule_id)
                )
                policy_rule = pr_result.scalar_one_or_none()
                if policy_rule is None:
                    results["skipped"] += 1
                    continue

                _publish(redis_client, channel, {
                    "type": "generating",
                    "rule_id": str(pr.id),
                    "index": idx,
                    "total": total,
                })

                codes = await generator.generate_all(
                    rule_id=policy_rule.rule_id,
                    title=policy_rule.title,
                    description=policy_rule.description or "",
                    severity=policy_rule.severity,
                    component_type=pr.component_type,
                    check_content=policy_rule.check_content or "",
                    fix_text=policy_rule.fix_text or "",
                )

                await db.execute(
                    update(BlueprintRule)
                    .where(BlueprintRule.id == pr.id)
                    .values(
                        evaluation_code=codes["evaluation_code"],
                        remediation_code=codes["remediation_code"],
                        rollback_code=codes["rollback_code"],
                        code_status="generated",
                    )
                )
                await db.commit()

                # Feed back into Milvus so component-specific codes enrich the store
                metadata = {
                    "title": policy_rule.title,
                    "severity": policy_rule.severity,
                    "component_type": pr.component_type,
                    "blueprint_id": blueprint_id,
                    "eval_code": codes["evaluation_code"][:1500],
                    "rem_code": codes["remediation_code"][:1500],
                    "rollback_code": codes["rollback_code"][:1000],
                }
                try:
                    await store.upsert_rule(
                        rule_id=f"{policy_rule.rule_id}:{pr.component_type}",
                        policy_id=str(policy_rule.policy_id),
                        text=f"{policy_rule.title} {policy_rule.description or ''} {pr.component_type}",
                        metadata=metadata,
                    )
                except Exception as milvus_exc:
                    logger.warning(
                        "Milvus upsert failed for blueprint_rule %s: %s", pr.id, milvus_exc
                    )

                _publish(redis_client, channel, {
                    "type": "done",
                    "rule_id": str(pr.id),
                    "index": idx,
                    "total": total,
                })
                results["generated"] += 1

            except Exception as exc:
                logger.exception("Code generation failed for blueprint_rule %s: %s", pr.id, exc)
                await db.execute(
                    update(BlueprintRule)
                    .where(BlueprintRule.id == pr.id)
                    .values(code_status="pending")
                )
                await db.commit()
                _publish(redis_client, channel, {
                    "type": "error",
                    "rule_id": str(pr.id),
                    "error": str(exc),
                })
                results["failed"] += 1

    _publish(redis_client, channel, {"type": "completed", **results})
    redis_client.close()
    await engine.dispose()
    return results


# ---------------------------------------------------------------------------
# Golden Config Generation (Nautobot integration)
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, base=_BaseTask, name="codegen.generate_golden_configs", max_retries=2)
def generate_golden_configs(
    self: "_BaseTask",
    policy_id: str,
    rule_ids: list[str] | None = None,
    config_format: str = "cli",
) -> dict:
    """
    Generate golden configuration data (for Nautobot) for PolicyRules that use
    the nautobot_golden_config evaluation method.
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

    from aegis.models.policy import PolicyRule
    from aegis.services.llm.code_generator import CodeGenerator

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:golden-config:policy:{policy_id}"
    generator = CodeGenerator()

    results = {"generated": 0, "failed": 0, "skipped": 0}

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
                # Mark as generating
                await db.execute(
                    update(PolicyRule)
                    .where(PolicyRule.id == pol_rule.id)
                    .values(golden_config_status="generating")
                )
                await db.commit()

                component_type = (
                    pol_rule.target_component_types[0]
                    if pol_rule.target_component_types
                    else "generic"
                )

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
                    component_type=component_type,
                    check_content=pol_rule.check_content or "",
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
                logger.exception(
                    "Golden config generation failed for policy_rule %s: %s",
                    pol_rule.id,
                    exc,
                )
                await db.execute(
                    update(PolicyRule)
                    .where(PolicyRule.id == pol_rule.id)
                    .values(golden_config_status="pending")
                )
                await db.commit()
                _publish(redis_client, channel, {
                    "type": "error",
                    "rule_id": str(pol_rule.id),
                    "error": str(exc),
                })
                results["failed"] += 1

    _publish(redis_client, channel, {"type": "completed", **results})
    redis_client.close()
    await engine.dispose()
    return results


@celery_app.task(bind=True, base=_BaseTask, name="codegen.push_golden_config_to_nautobot", max_retries=3)
def push_golden_config_to_nautobot(
    self: "_BaseTask",
    instance_id: str,
    device_name: str,
    rule_ids: list[str] | None = None,
) -> dict:
    """
    Push generated golden configuration data to a Nautobot instance for the
    specified device. Collects all golden configs from the instance's blueprint
    rules and pushes the aggregated config.
    """
    return self.run_async(_push_golden_config_async(instance_id, device_name, rule_ids, self))


async def _push_golden_config_async(
    instance_id: str,
    device_name: str,
    rule_ids: list[str] | None,
    task: "_BaseTask",
) -> dict:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from aegis.models.hardening_blueprint import BlueprintRule
    from aegis.models.policy import PolicyRule
    from aegis.models.solution_instance import SolutionInstance
    from aegis.services.connectors.nautobot_connector import NautobotConnector, NautobotConfigError

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        connector = NautobotConnector()
    except NautobotConfigError as e:
        return {"success": False, "error": str(e)}

    # Find the device in Nautobot
    device = connector.get_device(device_name)
    if not device:
        return {"success": False, "error": f"Device '{device_name}' not found in Nautobot"}

    device_id = device["id"]

    async with SessionFactory() as db:
        # Get the instance's blueprint and its rules
        inst_result = await db.execute(
            select(SolutionInstance).where(SolutionInstance.id == uuid.UUID(instance_id))
        )
        instance = inst_result.scalar_one_or_none()
        if not instance:
            return {"success": False, "error": f"Instance {instance_id} not found"}

        # Collect golden configs from blueprint rules or policy rules
        query = (
            select(BlueprintRule, PolicyRule)
            .join(PolicyRule, BlueprintRule.policy_rule_id == PolicyRule.id)
            .where(BlueprintRule.blueprint_id == instance.blueprint_id)
            .where(PolicyRule.evaluation_method == "nautobot_golden_config")
        )
        if rule_ids:
            query = query.where(BlueprintRule.id.in_([uuid.UUID(r) for r in rule_ids]))

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            return {"success": False, "error": "No golden config rules found for this instance"}

        # Aggregate golden config data
        config_parts = []
        config_format = "cli"
        for bp_rule, pol_rule in rows:
            # Blueprint-level override takes precedence
            config_data = bp_rule.golden_config_data or pol_rule.golden_config_data
            if config_data:
                config_parts.append(f"! Rule: {pol_rule.rule_id} - {pol_rule.title}")
                config_parts.append(config_data)
                config_parts.append("")
                config_format = bp_rule.golden_config_format or pol_rule.golden_config_format or "cli"

        if not config_parts:
            return {"success": False, "error": "No golden config data generated yet"}

        aggregated_config = "\n".join(config_parts)

    # Push to Nautobot
    try:
        response = connector.push_golden_config(
            device_id=device_id,
            intended_config=aggregated_config,
            config_format=config_format,
        )
    except Exception as e:
        return {"success": False, "error": f"Nautobot push failed: {e}"}

    await engine.dispose()
    return {"success": True, "device_id": device_id, "response": response}
