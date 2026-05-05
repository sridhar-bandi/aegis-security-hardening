"""Add component_policy_map to hardening_profiles, make policy_id nullable.

Revision ID: 003
Revises: 002
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add component_policy_map JSONB column (stores {component_type: policy_id})
    op.add_column(
        "hardening_profiles",
        sa.Column("component_policy_map", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    # 2. Backfill component_policy_map from existing policy_id so existing rows are valid
    op.execute(
        """
        UPDATE hardening_profiles
        SET component_policy_map = json_build_object('default', policy_id::text)
        WHERE policy_id IS NOT NULL AND component_policy_map IS NULL
        """
    )

    # 3. Make policy_id nullable (was NOT NULL) — it becomes informational only
    op.alter_column("hardening_profiles", "policy_id", nullable=True)


def downgrade() -> None:
    # Re-populate policy_id from first value in map before restoring NOT NULL
    op.execute(
        """
        UPDATE hardening_profiles
        SET policy_id = (
            SELECT value::uuid
            FROM json_each_text(component_policy_map)
            LIMIT 1
        )
        WHERE policy_id IS NULL AND component_policy_map IS NOT NULL
        """
    )
    op.alter_column("hardening_profiles", "policy_id", nullable=False)
    op.drop_column("hardening_profiles", "component_policy_map")
