"""Pytest configuration — sets minimal env vars so settings can be imported."""
import os
import pytest

# Provide minimal required env vars before any aegis module is imported
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("MILVUS_PORT", "19530")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-not-for-production")
os.environ.setdefault("REPORTS_DIR", "/tmp/aegis_reports")
