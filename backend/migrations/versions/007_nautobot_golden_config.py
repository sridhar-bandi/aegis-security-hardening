"""Add golden config fields for Nautobot integration

Revision ID: 007
Revises: 006
Create Date: 2026-05-07 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create new enum types
    op.execute("CREATE TYPE evaluation_method AS ENUM ('script', 'nautobot_golden_config')")
    op.execute("CREATE TYPE golden_config_format AS ENUM ('cli', 'json')")
    op.execute("CREATE TYPE golden_config_status AS ENUM ('pending', 'generating', 'generated', 'reviewed', 'approved')")

    # 2. Add columns to policy_rules
    op.add_column(
        "policy_rules",
        sa.Column(
            "evaluation_method",
            sa.Enum("script", "nautobot_golden_config", name="evaluation_method", create_type=False),
            nullable=False,
            server_default="script",
        ),
    )
    op.add_column("policy_rules", sa.Column("golden_config_data", sa.Text(), nullable=True))
    op.add_column(
        "policy_rules",
        sa.Column(
            "golden_config_format",
            sa.Enum("cli", "json", name="golden_config_format", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "policy_rules",
        sa.Column(
            "golden_config_status",
            sa.Enum("pending", "generating", "generated", "reviewed", "approved", name="golden_config_status", create_type=False),
            nullable=True,
        ),
    )

    # 3. Add columns to blueprint_rules
    op.add_column(
        "blueprint_rules",
        sa.Column(
            "evaluation_method",
            sa.Enum("script", "nautobot_golden_config", name="evaluation_method", create_type=False),
            nullable=False,
            server_default="script",
        ),
    )
    op.add_column("blueprint_rules", sa.Column("golden_config_data", sa.Text(), nullable=True))
    op.add_column(
        "blueprint_rules",
        sa.Column(
            "golden_config_format",
            sa.Enum("cli", "json", name="golden_config_format", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Drop columns from blueprint_rules
    op.drop_column("blueprint_rules", "golden_config_format")
    op.drop_column("blueprint_rules", "golden_config_data")
    op.drop_column("blueprint_rules", "evaluation_method")

    # Drop columns from policy_rules
    op.drop_column("policy_rules", "golden_config_status")
    op.drop_column("policy_rules", "golden_config_format")
    op.drop_column("policy_rules", "golden_config_data")
    op.drop_column("policy_rules", "evaluation_method")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS golden_config_status")
    op.execute("DROP TYPE IF EXISTS golden_config_format")
    op.execute("DROP TYPE IF EXISTS evaluation_method")
