"""Celery tasks for enforcement operations (evaluate, remediate, rollback, dry-run, impact)."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from celery import Task
from redis import Redis

from aegis.config import settings
from aegis.worker import celery_app

logger = logging.getLogger(__name__)


class _AsyncTask(Task):
    def run_async(self, coro):
        return asyncio.run(coro)


def _publish(redis_client: Redis, channel: str, data: dict) -> None:
    try:
        redis_client.publish(channel, json.dumps(data))
    except Exception as exc:
        logger.warning("Redis publish failed: %s", exc)


def _make_engine():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, base=_AsyncTask, name="enforcement.evaluate_instance", max_retries=1)
def evaluate_instance(self: _AsyncTask, job_id: str, instance_id: str) -> dict:
    return self.run_async(_evaluate_async(job_id, instance_id))


@celery_app.task(bind=True, base=_AsyncTask, name="enforcement.remediate_instance", max_retries=1)
def remediate_instance(self: _AsyncTask, job_id: str, instance_id: str, rule_ids: list[str] | None = None) -> dict:
    return self.run_async(_remediate_async(job_id, instance_id, rule_ids))


@celery_app.task(bind=True, base=_AsyncTask, name="enforcement.rollback_instance", max_retries=1)
def rollback_instance(self: _AsyncTask, job_id: str, instance_id: str, rule_ids: list[str] | None = None) -> dict:
    return self.run_async(_rollback_async(job_id, instance_id, rule_ids))


@celery_app.task(bind=True, base=_AsyncTask, name="enforcement.dry_run_instance", max_retries=1)
def dry_run_instance(self: _AsyncTask, job_id: str, instance_id: str) -> dict:
    return self.run_async(_dry_run_async(job_id, instance_id))


async def _load_instance_and_rules(
    db,
    instance_id: str,
    rule_ids: list[str] | None = None,
    code_status_filter: str = "approved",
) -> tuple[Any, list[Any]]:
    from sqlalchemy import select
    from aegis.models.solution_instance import SolutionInstance
    from aegis.models.hardening_blueprint import BlueprintRule, HardeningBlueprint
    from aegis.models.policy import PolicyRule

    result = await db.execute(
        select(SolutionInstance).where(SolutionInstance.id == uuid.UUID(instance_id))
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise ValueError(f"Instance {instance_id} not found")

    query = (
        select(BlueprintRule)
        .join(HardeningBlueprint, BlueprintRule.blueprint_id == HardeningBlueprint.id)
        .where(HardeningBlueprint.id == instance.blueprint_id)
        .where(BlueprintRule.code_status == code_status_filter)
    )
    if rule_ids:
        query = query.where(BlueprintRule.id.in_([uuid.UUID(r) for r in rule_ids]))

    pr_result = await db.execute(query)
    blueprint_rules = list(pr_result.scalars().all())

    enriched = []
    for pr in blueprint_rules:
        pol_result = await db.execute(select(PolicyRule).where(PolicyRule.id == pr.policy_rule_id))
        pol_rule = pol_result.scalar_one_or_none()

        # Use blueprint-rule approved code; fall back to policy-rule baseline code
        eval_code = pr.evaluation_code or ""
        rem_code = pr.remediation_code or ""
        rollback_code = pr.rollback_code or ""

        if not eval_code and pol_rule and pol_rule.evaluation_code:
            eval_code = pol_rule.evaluation_code
            logger.debug(
                "Using policy-level baseline eval_code for blueprint_rule %s (rule_id=%s)",
                pr.id, pol_rule.rule_id,
            )
        if not rem_code and pol_rule and pol_rule.remediation_code:
            rem_code = pol_rule.remediation_code
        if not rollback_code and pol_rule and pol_rule.rollback_code:
            rollback_code = pol_rule.rollback_code

        # Secondary fallback: Milvus contextual store
        if pol_rule and (not eval_code or not rem_code or not rollback_code):
            try:
                from aegis.services.llm.milvus_store import MilvusRuleStore
                store = MilvusRuleStore()
                codes = await store.get_codes_by_rule_id(
                    pol_rule.rule_id, component_type=pr.component_type
                )
                if not eval_code:
                    eval_code = codes.get("eval_code", "")
                if not rem_code:
                    rem_code = codes.get("rem_code", "")
                if not rollback_code:
                    rollback_code = codes.get("rollback_code", "")
                if eval_code:
                    logger.debug(
                        "Using Milvus-retrieved code for rule_id=%s component=%s",
                        pol_rule.rule_id, pr.component_type,
                    )
            except Exception as milvus_exc:
                logger.warning(
                    "Milvus code lookup failed for rule_id=%s: %s",
                    pol_rule.rule_id if pol_rule else "?", milvus_exc,
                )

        enriched.append({
            "blueprint_rule_id": str(pr.id),
            "rule_id": pol_rule.rule_id if pol_rule else "",
            "title": pol_rule.title if pol_rule else "",
            "component_type": pr.component_type,
            "evaluation_code": eval_code,
            "remediation_code": rem_code,
            "rollback_code": rollback_code,
            "saved_state": pr.saved_state or {},
            "risk_score": pr.risk_score,
        })

    return instance, enriched


async def _update_job_status(db, job_id: str, status: str, result_summary: dict) -> None:
    from sqlalchemy import update
    from aegis.models.enforcement_job import EnforcementJob
    completed_at = datetime.now(timezone.utc) if status in ("completed", "failed") else None
    await db.execute(
        update(EnforcementJob)
        .where(EnforcementJob.id == uuid.UUID(job_id))
        .values(status=status, result_summary=result_summary, completed_at=completed_at)
    )
    await db.commit()


async def _evaluate_async(job_id: str, instance_id: str) -> dict:
    from aegis.services.enforcement.evaluator import Evaluator
    engine, SessionFactory = _make_engine()
    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:enforcement:{job_id}"

    async with SessionFactory() as db:
        try:
            await _update_job_status(db, job_id, "running", {})
            _publish(redis_client, channel, {"type": "started", "job_id": job_id, "op": "evaluate"})

            instance, enriched = await _load_instance_and_rules(db, instance_id)
            config = instance.config_json or {}
            component_type = config.get("component_type", "VM")

            evaluator = Evaluator()
            report = evaluator.evaluate(instance_id, component_type, config, enriched)

            summary = {
                "pass": report.pass_count,
                "fail": report.fail_count,
                "total": len(report.results),
                "details": [
                    {"rule_id": r.rule_id, "compliant": r.compliant, "details": r.details}
                    for r in report.results
                ],
            }
            await _update_job_status(db, job_id, "completed", summary)
            _publish(redis_client, channel, {"type": "completed", **summary})
            return summary
        except Exception as exc:
            logger.exception("evaluate_instance failed: %s", exc)
            err = {"error": str(exc)}
            await _update_job_status(db, job_id, "failed", err)
            _publish(redis_client, channel, {"type": "failed", "error": str(exc)})
            raise
        finally:
            redis_client.close()
            await engine.dispose()


async def _remediate_async(job_id: str, instance_id: str, rule_ids: list[str] | None) -> dict:
    from sqlalchemy import update
    from aegis.models.hardening_blueprint import BlueprintRule
    from aegis.services.enforcement.remediator import Remediator
    engine, SessionFactory = _make_engine()
    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:enforcement:{job_id}"

    async with SessionFactory() as db:
        try:
            await _update_job_status(db, job_id, "running", {})
            _publish(redis_client, channel, {"type": "started", "job_id": job_id, "op": "remediate"})

            instance, enriched = await _load_instance_and_rules(db, instance_id, rule_ids)
            config = instance.config_json or {}
            component_type = config.get("component_type", "VM")

            remediator = Remediator()
            report = remediator.remediate(instance_id, component_type, config, enriched)

            # Persist saved_state back to DB
            for r in report.results:
                if r.saved_state:
                    await db.execute(
                        update(BlueprintRule)
                        .where(BlueprintRule.id == uuid.UUID(r.blueprint_rule_id))
                        .values(saved_state=r.saved_state)
                    )
            await db.commit()

            summary = {
                "success": report.success_count,
                "failed": report.fail_count,
                "total": len(report.results),
            }
            await _update_job_status(db, job_id, "completed", summary)
            _publish(redis_client, channel, {"type": "completed", **summary})
            return summary
        except Exception as exc:
            err = {"error": str(exc)}
            await _update_job_status(db, job_id, "failed", err)
            _publish(redis_client, channel, {"type": "failed", "error": str(exc)})
            raise
        finally:
            redis_client.close()
            await engine.dispose()


async def _rollback_async(job_id: str, instance_id: str, rule_ids: list[str] | None) -> dict:
    from aegis.services.enforcement.rollback import RollbackEngine
    engine, SessionFactory = _make_engine()
    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:enforcement:{job_id}"

    async with SessionFactory() as db:
        try:
            await _update_job_status(db, job_id, "running", {})
            _publish(redis_client, channel, {"type": "started", "job_id": job_id, "op": "rollback"})

            instance, enriched = await _load_instance_and_rules(db, instance_id, rule_ids, code_status_filter="approved")
            config = instance.config_json or {}
            component_type = config.get("component_type", "VM")

            engine_rb = RollbackEngine()
            report = engine_rb.rollback(instance_id, component_type, config, enriched)

            summary = {
                "success": sum(1 for r in report.results if r.success),
                "failed": sum(1 for r in report.results if not r.success),
                "total": len(report.results),
            }
            await _update_job_status(db, job_id, "completed", summary)
            _publish(redis_client, channel, {"type": "completed", **summary})
            return summary
        except Exception as exc:
            err = {"error": str(exc)}
            await _update_job_status(db, job_id, "failed", err)
            _publish(redis_client, channel, {"type": "failed", "error": str(exc)})
            raise
        finally:
            redis_client.close()
            await engine.dispose()


async def _dry_run_async(job_id: str, instance_id: str) -> dict:
    from aegis.services.enforcement.impact_assessor import ImpactAssessor
    from aegis.services.enforcement.dry_run import DryRunEngine
    engine, SessionFactory = _make_engine()
    redis_client = Redis.from_url(settings.REDIS_URL)
    channel = f"ws:enforcement:{job_id}"

    async with SessionFactory() as db:
        try:
            await _update_job_status(db, job_id, "running", {})
            _publish(redis_client, channel, {"type": "started", "job_id": job_id, "op": "dry_run"})

            instance, enriched = await _load_instance_and_rules(db, instance_id, code_status_filter="approved")
            config = instance.config_json or {}
            topology = config.get("topology", [])

            assessor = ImpactAssessor()
            assessor.build_topology(topology)
            dry_runner = DryRunEngine(assessor)
            report = dry_runner.run(instance_id, enriched)

            summary = {
                "safe": len(report.safe_rules),
                "risky": len(report.risky_rules),
                "breaking": len(report.breaking_rules),
                "report": report.model_dump(mode="json"),
            }
            await _update_job_status(db, job_id, "completed", summary)
            _publish(redis_client, channel, {"type": "completed", **summary})
            return summary
        except Exception as exc:
            err = {"error": str(exc)}
            await _update_job_status(db, job_id, "failed", err)
            _publish(redis_client, channel, {"type": "failed", "error": str(exc)})
            raise
        finally:
            redis_client.close()
            await engine.dispose()
