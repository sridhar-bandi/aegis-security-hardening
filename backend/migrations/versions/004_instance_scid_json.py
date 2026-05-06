"""Add scid_json and scid_filename to solution_instances.

Revision ID: 004
Revises: 003
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "solution_instances",
        sa.Column("scid_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "solution_instances",
        sa.Column("scid_filename", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("solution_instances", "scid_filename")
    op.drop_column("solution_instances", "scid_json")
