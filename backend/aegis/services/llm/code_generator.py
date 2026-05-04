"""Code generator: generates evaluate/remediate/rollback code for profile rules."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from aegis.services.llm.client import AegisLLMClient
from aegis.services.llm.milvus_store import MilvusRuleStore
from aegis.services.llm.prompts import (
    CODE_GEN_SYSTEM,
    EVAL_CODE_TEMPLATE,
    REMEDIATION_CODE_TEMPLATE,
    ROLLBACK_CODE_TEMPLATE,
    format_few_shot,
)

logger = logging.getLogger(__name__)


class CodeGenerator:
    def __init__(self) -> None:
        self._llm = AegisLLMClient()
        self._store = MilvusRuleStore()

    async def generate_all(
        self,
        *,
        rule_id: str,
        title: str,
        description: str,
        severity: str,
        component_type: str,
        check_content: str,
        fix_text: str,
    ) -> dict[str, str]:
        """Generate evaluate, remediate, rollback code for a single rule."""
        query_text = f"{title} {description}"
        try:
            similar = await self._store.search_similar(query_text, top_k=3)
            few_shot_ctx = format_few_shot([
                {"title": s.metadata.get("title", ""), "code": s.metadata.get("eval_code", "")}
                for s in similar
            ])
        except Exception:
            few_shot_ctx = "(retrieval unavailable)"

        common = dict(
            rule_id=rule_id,
            title=title,
            severity=severity,
            component_type=component_type,
            description=description,
            few_shot=few_shot_ctx,
        )

        eval_prompt = CODE_GEN_SYSTEM + "\n\n" + EVAL_CODE_TEMPLATE.format(
            check_content=check_content, **common
        )
        rem_prompt = CODE_GEN_SYSTEM + "\n\n" + REMEDIATION_CODE_TEMPLATE.format(
            fix_text=fix_text, **common
        )
        rollback_prompt = CODE_GEN_SYSTEM + "\n\n" + ROLLBACK_CODE_TEMPLATE.format(**common)

        eval_code = await self._llm.generate(eval_prompt)
        rem_code = await self._llm.generate(rem_prompt)
        rollback_code = await self._llm.generate(rollback_prompt)

        return {
            "evaluation_code": eval_code,
            "remediation_code": rem_code,
            "rollback_code": rollback_code,
        }

    async def stream_generate_eval(
        self,
        *,
        rule_id: str,
        title: str,
        description: str,
        severity: str,
        component_type: str,
        check_content: str,
    ) -> AsyncIterator[str]:
        """Stream evaluation code generation for WebSocket delivery."""
        query_text = f"{title} {description}"
        try:
            similar = await self._store.search_similar(query_text, top_k=3)
            few_shot_ctx = format_few_shot([
                {"title": s.metadata.get("title", ""), "code": s.metadata.get("eval_code", "")}
                for s in similar
            ])
        except Exception:
            few_shot_ctx = "(retrieval unavailable)"

        prompt = CODE_GEN_SYSTEM + "\n\n" + EVAL_CODE_TEMPLATE.format(
            rule_id=rule_id, title=title, severity=severity, component_type=component_type,
            description=description, check_content=check_content, few_shot=few_shot_ctx,
        )
        async for token in self._llm.stream_generate(prompt):
            yield token
