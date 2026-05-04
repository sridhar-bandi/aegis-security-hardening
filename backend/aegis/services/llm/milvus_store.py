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
