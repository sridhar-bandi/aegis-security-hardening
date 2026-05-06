"""Policy profiles and rule review fields

Revision ID: 006
Revises: 005
Create Date: 2026-05-06 00:00:00.000000
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create enums
    op.execute("CREATE TYPE code_source AS ENUM ('llm', 'manual', 'imported')")
    op.execute("CREATE TYPE profile_type AS ENUM ('standard', 'tailored')")
    op.execute("CREATE TYPE profile_status AS ENUM ('draft', 'in_review', 'approved', 'locked')")

    # 2. Extend policy_rules
    op.execute("""
        ALTER TABLE policy_rules
            ADD COLUMN code_source code_source NOT NULL DEFAULT 'llm',
            ADD COLUMN imported_filename VARCHAR(500),
            ADD COLUMN reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN reviewed_at TIMESTAMPTZ
    """)

    # 3. Create policy_profiles table
    op.execute("""
        CREATE TABLE policy_profiles (
            id UUID PRIMARY KEY,
            policy_id UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name VARCHAR(300) NOT NULL,
            description TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            parent_version_id UUID REFERENCES policy_profiles(id),
            profile_type profile_type NOT NULL DEFAULT 'standard',
            status profile_status NOT NULL DEFAULT 'draft',
            included_rule_ids JSON,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            locked_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_policy_profiles_policy_id ON policy_profiles(policy_id)")
    op.execute("CREATE INDEX ix_policy_profiles_workspace_id ON policy_profiles(workspace_id)")

    # 4. Update hardening_blueprints
    op.execute("ALTER TABLE hardening_blueprints ADD COLUMN component_profile_map JSON")
    op.execute("ALTER TABLE hardening_blueprints DROP CONSTRAINT hardening_profiles_policy_id_fkey")
    op.execute("ALTER TABLE hardening_blueprints DROP COLUMN component_policy_map")
    op.execute("ALTER TABLE hardening_blueprints DROP COLUMN policy_id")


def downgrade() -> None:
    # Restore hardening_blueprints columns
    op.add_column(
        "hardening_blueprints",
        sa.Column("policy_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "hardening_blueprints_policy_id_fkey",
        "hardening_blueprints",
        "policies",
        ["policy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "hardening_blueprints",
        sa.Column("component_policy_map", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.drop_column("hardening_blueprints", "component_profile_map")

    # Drop policy_profiles table
    op.drop_table("policy_profiles")

    # Drop enums
    op.execute("DROP TYPE profile_status")
    op.execute("DROP TYPE profile_type")

    # Remove policy_rules columns
    op.drop_constraint("fk_policy_rules_reviewed_by", "policy_rules", type_="foreignkey")
    op.drop_column("policy_rules", "reviewed_at")
    op.drop_column("policy_rules", "reviewed_by")
    op.drop_column("policy_rules", "imported_filename")
    op.drop_column("policy_rules", "code_source")

    # Drop code_source enum
    op.execute("DROP TYPE code_source")
