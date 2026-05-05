"""Add LLM-generated code fields to policy_rules and policies.

Revision ID: 002
Revises: 001
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Re-use existing code_status enum (already created in 001 for profile_rules)
    code_status = postgresql.ENUM(
        "pending", "generating", "generated", "reviewed", "approved", "rejected",
        name="code_status",
        create_type=False,
    )

    # Add policy-level code_status to policies table
    op.add_column(
        "policies",
        sa.Column(
            "code_status",
            code_status,
            nullable=False,
            server_default="pending",
        ),
    )

    # Add generated code columns to policy_rules
    op.add_column("policy_rules", sa.Column("evaluation_code", sa.Text(), nullable=True))
    op.add_column("policy_rules", sa.Column("remediation_code", sa.Text(), nullable=True))
    op.add_column("policy_rules", sa.Column("rollback_code", sa.Text(), nullable=True))
    op.add_column(
        "policy_rules",
        sa.Column(
            "code_status",
            code_status,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "policy_rules",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Extend code_status enum to include "generating" if not already present
    # (PostgreSQL ALTER TYPE ADD VALUE is idempotent with IF NOT EXISTS)
    op.execute("ALTER TYPE code_status ADD VALUE IF NOT EXISTS 'generating'")


def downgrade() -> None:
    op.drop_column("policy_rules", "updated_at")
    op.drop_column("policy_rules", "code_status")
    op.drop_column("policy_rules", "rollback_code")
    op.drop_column("policy_rules", "remediation_code")
    op.drop_column("policy_rules", "evaluation_code")
    op.drop_column("policies", "code_status")
