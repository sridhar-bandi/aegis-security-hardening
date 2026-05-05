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
# Profile-level code generation (per component × policy rule)
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, base=_BaseTask, name="codegen.generate_profile_codes", max_retries=2)
def generate_profile_codes(self: _BaseTask, profile_id: str, rule_ids: list[str] | None = None) -> dict:
    """
    Generate evaluate/remediate/rollback code for all pending ProfileRules in a
    HardeningProfile. Falls back to policy-level baseline code from Milvus as
    few-shot context. Publishes progress to Redis pub/sub channel
    ``ws:codegen:{profile_id}``.
    """
    return self.run_async(_generate_profile_codes_async(profile_id, rule_ids, self))


async def _generate_profile_codes_async(
    profile_id: str,
    rule_ids: list[str] | None,
    task: _BaseTask,
) -> dict:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from aegis.models.hardening_profile import HardeningProfile, ProfileRule
    from aegis.models.policy import PolicyRule
    from aegis.services.llm.code_generator import CodeGenerator
    from aegis.services.llm.milvus_store import MilvusRuleStore

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:codegen:{profile_id}"
    generator = CodeGenerator()
    store = MilvusRuleStore()

    results = {"generated": 0, "failed": 0, "skipped": 0}

    async with SessionFactory() as db:
        query = (
            select(ProfileRule)
            .where(ProfileRule.profile_id == uuid.UUID(profile_id))
            .where(ProfileRule.code_status == "pending")
        )
        if rule_ids:
            query = query.where(ProfileRule.id.in_([uuid.UUID(r) for r in rule_ids]))

        result = await db.execute(query)
        pending_rules: list[ProfileRule] = list(result.scalars().all())

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
                    update(ProfileRule)
                    .where(ProfileRule.id == pr.id)
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
                    "profile_id": profile_id,
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
                        "Milvus upsert failed for profile_rule %s: %s", pr.id, milvus_exc
                    )

                _publish(redis_client, channel, {
                    "type": "done",
                    "rule_id": str(pr.id),
                    "index": idx,
                    "total": total,
                })
                results["generated"] += 1

            except Exception as exc:
                logger.exception("Code generation failed for profile_rule %s: %s", pr.id, exc)
                await db.execute(
                    update(ProfileRule)
                    .where(ProfileRule.id == pr.id)
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
