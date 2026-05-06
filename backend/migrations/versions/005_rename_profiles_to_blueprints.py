"""Rename profiles to blueprints

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename tables
    op.rename_table('hardening_profiles', 'hardening_blueprints')
    op.rename_table('profile_rules', 'blueprint_rules')

    # Rename columns
    op.alter_column('blueprint_rules', 'profile_id', new_column_name='blueprint_id')
    op.alter_column('hitl_comments', 'profile_rule_id', new_column_name='blueprint_rule_id')
    op.alter_column('solution_instances', 'profile_id', new_column_name='blueprint_id')

    # Rename enum type
    op.execute("ALTER TYPE profile_status RENAME TO blueprint_status")

    # Rename foreign key constraints (PostgreSQL auto-renames with table, but explicit for clarity)
    # Rename indexes if needed (PostgreSQL auto-updates)


def downgrade() -> None:
    op.execute("ALTER TYPE blueprint_status RENAME TO profile_status")
    op.alter_column('solution_instances', 'blueprint_id', new_column_name='profile_id')
    op.alter_column('hitl_comments', 'blueprint_rule_id', new_column_name='profile_rule_id')
    op.alter_column('blueprint_rules', 'blueprint_id', new_column_name='profile_id')
    op.rename_table('blueprint_rules', 'profile_rules')
    op.rename_table('hardening_blueprints', 'hardening_profiles')
