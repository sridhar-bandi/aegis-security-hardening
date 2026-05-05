"""MilvusDB vector store for policy rule embeddings and retrieval."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from aegis.config import settings
from aegis.services.llm.client import AegisLLMClient

logger = logging.getLogger(__name__)

COLLECTION_NAME = "policy_rules"
EMBED_DIM = 768  # nomic-embed-text output dimension


@dataclass
class SimilarRule:
    rule_id: str
    policy_id: str
    score: float
    metadata: dict


class MilvusRuleStore:
    def __init__(self):
        self._collection: Collection | None = None
        self._client = AegisLLMClient()

    def connect(self) -> None:
        connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
        self._ensure_collection()
        logger.info("Connected to MilvusDB at %s:%s", settings.MILVUS_HOST, settings.MILVUS_PORT)

    def _ensure_collection(self) -> None:
        if not utility.has_collection(COLLECTION_NAME):
            schema = CollectionSchema(fields=[
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="rule_id", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="policy_id", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBED_DIM),
                FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=4096),
            ], description="AEGIS policy rule embeddings")
            self._collection = Collection(COLLECTION_NAME, schema)
            self._collection.create_index("embedding", {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            })
            logger.info("Created MilvusDB collection: %s", COLLECTION_NAME)
        else:
            self._collection = Collection(COLLECTION_NAME)
        self._collection.load()

    async def upsert_rule(self, rule_id: str, policy_id: str, text: str, metadata: dict) -> None:
        if self._collection is None:
            self.connect()
        embedding = await self._client.embed(text)
        data = [
            [rule_id],
            [policy_id],
            [embedding],
            [json.dumps(metadata)[:4000]],
        ]
        self._collection.insert(data)  # type: ignore[arg-type]
        self._collection.flush()

    async def search_similar(self, query_text: str, top_k: int = 5) -> list[SimilarRule]:
        if self._collection is None:
            self.connect()
        embedding = await self._client.embed(query_text)
        results = self._collection.search(
            data=[embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["rule_id", "policy_id", "metadata_json"],
        )
        similar: list[SimilarRule] = []
        for hit in results[0]:
            try:
                meta = json.loads(hit.entity.get("metadata_json", "{}"))
            except json.JSONDecodeError:
                meta = {}
            similar.append(SimilarRule(
                rule_id=hit.entity.get("rule_id", ""),
                policy_id=hit.entity.get("policy_id", ""),
                score=hit.score,
                metadata=meta,
            ))
        return similar

    async def get_codes_by_rule_id(
        self, rule_id: str, component_type: str | None = None
    ) -> dict[str, str]:
        """
        Retrieve generated code (eval/rem/rollback) from the contextual store
        for a given rule_id.  If component_type is supplied, prefers the
        component-specific variant (stored as ``rule_id:component_type``).

        Returns a dict with keys ``eval_code``, ``rem_code``, ``rollback_code``
        (empty strings when not found).
        """
        if self._collection is None:
            self.connect()

        empty: dict[str, str] = {"eval_code": "", "rem_code": "", "rollback_code": ""}

        # Try component-specific variant first
        candidates = [f"{rule_id}:{component_type}"] if component_type else []
        candidates.append(rule_id)

        for rid in candidates:
            try:
                query_embedding = await self._client.embed(rid)
                results = self._collection.search(
                    data=[query_embedding],
                    anns_field="embedding",
                    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                    limit=5,
                    output_fields=["rule_id", "metadata_json"],
                )
                for hit in results[0]:
                    if hit.entity.get("rule_id", "") == rid:
                        try:
                            meta = json.loads(hit.entity.get("metadata_json", "{}"))
                        except json.JSONDecodeError:
                            meta = {}
                        return {
                            "eval_code": meta.get("eval_code", ""),
                            "rem_code": meta.get("rem_code", ""),
                            "rollback_code": meta.get("rollback_code", ""),
                        }
            except Exception as exc:
                logger.warning(
                    "Milvus get_codes_by_rule_id failed for rule_id=%s: %s", rid, exc
                )

        return empty
