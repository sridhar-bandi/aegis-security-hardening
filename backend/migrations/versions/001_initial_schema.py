"""Initial schema — creates all AEGIS tables.

Revision ID: 001
Revises: 
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    user_role = postgresql.ENUM("admin", "security_officer", "auditor", "user", name="user_role", create_type=False)
    workspace_member_role = postgresql.ENUM("admin", "security_officer", "auditor", "user", name="workspace_member_role", create_type=False)
    policy_standard = postgresql.ENUM("CIS", "STIG", "SRG", "Custom", name="policy_standard", create_type=False)
    policy_format = postgresql.ENUM("OVAL", "XCCDF", "text", "json", name="policy_format", create_type=False)
    rule_severity = postgresql.ENUM("critical", "high", "medium", "low", "informational", name="rule_severity", create_type=False)
    profile_status = postgresql.ENUM("draft", "generating", "ready", name="profile_status", create_type=False)
    code_status = postgresql.ENUM("pending", "generated", "reviewed", "approved", "rejected", name="code_status", create_type=False)
    comment_type = postgresql.ENUM("review", "approval", "rejection", name="comment_type", create_type=False)
    job_type = postgresql.ENUM("evaluate", "remediate", "rollback", "dry_run", "impact_assessment", name="job_type", create_type=False)
    job_status = postgresql.ENUM("pending", "running", "completed", "failed", name="job_status", create_type=False)
    report_type = postgresql.ENUM("arf", "html", "summary", name="report_type", create_type=False)

    for enum in [user_role, workspace_member_role, policy_standard, policy_format, rule_severity,
                 profile_status, code_status, comment_type, job_type, job_status, report_type]:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table("users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table("workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table("workspace_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", workspace_member_role, nullable=False, server_default="user"),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    op.create_table("policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("standard", policy_standard, nullable=False, server_default="Custom"),
        sa.Column("format", policy_format, nullable=False, server_default="text"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_policies_workspace_id", "policies", ["workspace_id"])

    op.create_table("policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(200), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("severity", rule_severity, nullable=False, server_default="medium"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("target_component_types", postgresql.JSON(), nullable=True),
        sa.Column("check_content", sa.Text(), nullable=True),
        sa.Column("fix_text", sa.Text(), nullable=True),
        sa.Column("milvus_embedding_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_policy_rules_policy_id", "policy_rules", ["policy_id"])
    op.create_index("ix_policy_rules_rule_id", "policy_rules", ["rule_id"])

    op.create_table("solution_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_json", postgresql.JSON(), nullable=True),
        sa.Column("component_selection", postgresql.JSON(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_solution_types_workspace_id", "solution_types", ["workspace_id"])

    op.create_table("hardening_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("solution_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solution_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", profile_status, nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hardening_profiles_solution_type_id", "hardening_profiles", ["solution_type_id"])

    op.create_table("profile_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hardening_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policy_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_type", sa.String(100), nullable=False),
        sa.Column("evaluation_code", sa.Text(), nullable=True),
        sa.Column("remediation_code", sa.Text(), nullable=True),
        sa.Column("rollback_code", sa.Text(), nullable=True),
        sa.Column("code_status", code_status, nullable=False, server_default="pending"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("saved_state", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_profile_rules_profile_id", "profile_rules", ["profile_id"])

    op.create_table("hitl_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profile_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("comment_type", comment_type, nullable=False, server_default="review"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hitl_comments_profile_rule_id", "hitl_comments", ["profile_rule_id"])

    op.create_table("solution_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("solution_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solution_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hardening_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("config_json", postgresql.JSON(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_solution_instances_workspace_id", "solution_instances", ["workspace_id"])

    op.create_table("enforcement_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solution_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(200), nullable=True),
        sa.Column("result_summary", postgresql.JSON(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_enforcement_jobs_instance_id", "enforcement_jobs", ["instance_id"])

    op.create_table("compliance_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("solution_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("enforcement_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("report_type", report_type, nullable=False, server_default="arf"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("summary", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_reports_instance_id", "compliance_reports", ["instance_id"])


def downgrade() -> None:
    op.drop_table("compliance_reports")
    op.drop_table("enforcement_jobs")
    op.drop_table("solution_instances")
    op.drop_table("hitl_comments")
    op.drop_table("profile_rules")
    op.drop_table("hardening_profiles")
    op.drop_table("solution_types")
    op.drop_table("policy_rules")
    op.drop_table("policies")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("users")
    for name in ["user_role", "workspace_member_role", "policy_standard", "policy_format",
                 "rule_severity", "profile_status", "code_status", "comment_type",
                 "job_type", "job_status", "report_type"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
