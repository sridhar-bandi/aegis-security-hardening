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


@celery_app.task(bind=True, base=_BaseTask, name="codegen.generate_profile_codes", max_retries=2)
def generate_profile_codes(self: _BaseTask, profile_id: str, rule_ids: list[str] | None = None) -> dict:
    """
    Generate evaluate/remediate/rollback code for all pending ProfileRules in a HardeningProfile.
    Publishes progress events to Redis pub/sub channel `ws:codegen:{profile_id}`.
    """
    return self.run_async(_generate_profile_codes_async(profile_id, rule_ids, self))


async def _generate_profile_codes_async(
    profile_id: str,
    rule_ids: list[str] | None,
    task: _BaseTask,
) -> dict:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

    from aegis.models.hardening_profile import HardeningProfile, ProfileRule
    from aegis.models.policy import PolicyRule
    from aegis.services.llm.code_generator import CodeGenerator

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:codegen:{profile_id}"
    generator = CodeGenerator()

    results = {"generated": 0, "failed": 0, "skipped": 0}

    async with SessionFactory() as db:
        # Load profile rules to generate
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
                # Load associated policy rule
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
                    .values(code_status="pending")  # keep pending for retry
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


def _publish(redis_client: Redis, channel: str, data: dict) -> None:
    import json
    try:
        redis_client.publish(channel, json.dumps(data))
    except Exception as exc:
        logger.warning("Redis publish failed on channel %s: %s", channel, exc)
