<!-- markdownlint-disable-file -->

# Task Details: Policy-Level Hardening Implementation

## Research Reference

**Source Research**: #file:../research/20260506-policy-level-hardening-research.md

## Phase 1: Database & Model Changes

### Task 1.1: Create Alembic migration 006

Create `backend/migrations/versions/006_policy_profiles_and_rule_review.py`:

- **Files**:
  - `backend/migrations/versions/006_policy_profiles_and_rule_review.py` — New migration file
- **Success**:
  - Migration runs without errors on existing database
  - `policy_rules` table has new columns: code_source, imported_filename, reviewed_by, reviewed_at
  - `policy_profiles` table exists with all specified columns
  - `hardening_blueprints` table has `component_profile_map` and no longer has `component_policy_map` or `policy_id`
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 230-278) — Migration 006 specification
- **Dependencies**:
  - Existing migration 005 must be the current head

**Specification:**

```python
revision = "006"
down_revision = "005"

def upgrade() -> None:
    # 1. Create code_source enum
    op.execute("CREATE TYPE code_source AS ENUM ('llm', 'manual', 'imported')")

    # 2. Extend policy_rules
    op.add_column("policy_rules", sa.Column("code_source",
        sa.Enum("llm", "manual", "imported", name="code_source", create_type=False),
        server_default="llm", nullable=False))
    op.add_column("policy_rules", sa.Column("imported_filename", sa.String(500), nullable=True))
    op.add_column("policy_rules", sa.Column("reviewed_by",
        sa.UUID(), nullable=True))
    op.create_foreign_key("fk_policy_rules_reviewed_by", "policy_rules", "users", ["reviewed_by"], ["id"], ondelete="SET NULL")
    op.add_column("policy_rules", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))

    # 3. Create profile_type and profile_status enums
    op.execute("CREATE TYPE profile_type AS ENUM ('standard', 'tailored')")
    op.execute("CREATE TYPE profile_status AS ENUM ('draft', 'in_review', 'approved', 'locked')")

    # 4. Create policy_profiles table
    op.create_table(
        "policy_profiles",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("policy_id", sa.UUID(), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_version_id", sa.UUID(), sa.ForeignKey("policy_profiles.id"), nullable=True),
        sa.Column("profile_type", sa.Enum("standard", "tailored", name="profile_type", create_type=False), nullable=False, server_default="standard"),
        sa.Column("status", sa.Enum("draft", "in_review", "approved", "locked", name="profile_status", create_type=False), nullable=False, server_default="draft"),
        sa.Column("included_rule_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. Replace component_policy_map with component_profile_map on hardening_blueprints
    op.add_column("hardening_blueprints", sa.Column("component_profile_map", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.drop_column("hardening_blueprints", "component_policy_map")
    op.drop_constraint("hardening_blueprints_policy_id_fkey", "hardening_blueprints", type_="foreignkey")
    op.drop_column("hardening_blueprints", "policy_id")
```

### Task 1.2: Update PolicyRule model with review/import tracking fields

Add new columns to existing `PolicyRule` class in `backend/aegis/models/policy.py`.

- **Files**:
  - `backend/aegis/models/policy.py` — Add code_source, imported_filename, reviewed_by, reviewed_at columns
- **Success**:
  - PolicyRule model has all 4 new mapped_column definitions
  - code_source defaults to "llm"
  - reviewed_by has FK to users.id
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 85-96) — Field specifications
- **Dependencies**:
  - Migration 006 must exist (but run order doesn't matter for model definition)

**Add after the `updated_at` column on PolicyRule:**
```python
    code_source: Mapped[str] = mapped_column(
        Enum("llm", "manual", "imported", name="code_source", create_type=False),
        nullable=False,
        default="llm",
        server_default="llm",
    )
    imported_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Task 1.3: Create PolicyProfile ORM model

Create new file `backend/aegis/models/policy_profile.py`.

- **Files**:
  - `backend/aegis/models/policy_profile.py` — New model file
- **Success**:
  - PolicyProfile class with all columns matching migration
  - Relationships: policy (back_populates="profiles"), workspace, parent_version (self-referential)
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 98-125) — PolicyProfile model specification
- **Dependencies**:
  - Task 1.1 (migration exists)

**Full model:**
```python
"""PolicyProfile ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class PolicyProfile(Base):
    __tablename__ = "policy_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("policy_profiles.id"), nullable=True)
    profile_type: Mapped[str] = mapped_column(
        Enum("standard", "tailored", name="profile_type", create_type=False),
        nullable=False, default="standard", server_default="standard",
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "in_review", "approved", "locked", name="profile_status", create_type=False),
        nullable=False, default="draft", server_default="draft",
    )
    included_rule_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    policy: Mapped["Policy"] = relationship("Policy", back_populates="profiles")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    parent_version: Mapped["PolicyProfile | None"] = relationship("PolicyProfile", remote_side=[id])


from aegis.models.policy import Policy  # noqa: F401, E402
from aegis.models.workspace import Workspace  # noqa: F401, E402
```

### Task 1.4: Update HardeningBlueprint model

Modify `backend/aegis/models/hardening_blueprint.py` to replace `component_policy_map` and `policy_id` with `component_profile_map`.

- **Files**:
  - `backend/aegis/models/hardening_blueprint.py` — Remove policy_id + component_policy_map, add component_profile_map
- **Success**:
  - `policy_id` column and `policy` relationship removed
  - `component_policy_map` column removed
  - `component_profile_map` column added (JSON, nullable=True)
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 127-133) — Blueprint model changes
- **Dependencies**:
  - Task 1.1 (migration)

**Changes:**
- Remove: `policy_id` mapped_column, `policy` relationship
- Remove: `component_policy_map` mapped_column
- Add: `component_profile_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)`

### Task 1.5: Update models/__init__.py and add relationships

Register PolicyProfile in models package and add `profiles` back_populates on Policy model.

- **Files**:
  - `backend/aegis/models/__init__.py` — Import PolicyProfile
  - `backend/aegis/models/policy.py` — Add `profiles` relationship to Policy class
- **Success**:
  - `PolicyProfile` importable from `aegis.models`
  - `Policy.profiles` relationship works
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 98-125) — Relationship definitions
- **Dependencies**:
  - Tasks 1.2, 1.3, 1.4

## Phase 2: Backend API — Policy Rule Review Endpoints

### Task 2.1: Add PATCH /policies/{policy_id}/rules/{rule_id}/code endpoint

Add endpoint to `backend/aegis/api/v1/policies.py` for updating rule implementation code manually.

- **Files**:
  - `backend/aegis/api/v1/policies.py` — New endpoint
  - `backend/aegis/schemas/policy.py` — New PolicyRuleCodeUpdate schema
- **Success**:
  - PATCH endpoint accepts evaluation_code, remediation_code, rollback_code (all optional)
  - Sets code_source="manual" and code_status="reviewed"
  - Returns updated PolicyRuleResponse
  - Requires admin/security_officer role
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 140-141) — Endpoint spec
- **Dependencies**:
  - Phase 1 complete

**Schema:**
```python
class PolicyRuleCodeUpdate(BaseModel):
    evaluation_code: str | None = None
    remediation_code: str | None = None
    rollback_code: str | None = None
```

**Endpoint pattern:** Validates policy_id/rule_id pair, checks workspace access, updates non-None code fields, sets code_source="manual", code_status="reviewed".

### Task 2.2: Add POST /policies/{policy_id}/rules/{rule_id}/approve endpoint

- **Files**:
  - `backend/aegis/api/v1/policies.py` — New endpoint
- **Success**:
  - Sets code_status="approved", reviewed_by=current_user.id, reviewed_at=now
  - Validates that rule has at least evaluation_code populated
  - Returns updated PolicyRuleResponse
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 285-306) — Complete example
- **Dependencies**:
  - Task 2.5 (updated schema)

### Task 2.3: Add POST /policies/{policy_id}/rules/{rule_id}/reject endpoint

- **Files**:
  - `backend/aegis/api/v1/policies.py` — New endpoint
- **Success**:
  - Sets code_status="rejected", reviewed_by=current_user.id, reviewed_at=now
  - Returns updated PolicyRuleResponse
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 140-143) — Endpoint spec
- **Dependencies**:
  - Task 2.5 (updated schema)

**Accept optional rejection reason in request body:**
```python
class PolicyRuleRejectRequest(BaseModel):
    reason: str | None = None
```

### Task 2.4: Add POST /policies/{policy_id}/rules/{rule_id}/import endpoint

File upload endpoint that imports a script as rule implementation code.

- **Files**:
  - `backend/aegis/api/v1/policies.py` — New endpoint
- **Success**:
  - Accepts `code_type` query param ("evaluation" | "remediation" | "rollback")
  - Accepts file upload
  - Reads file content as UTF-8, stores in appropriate code field
  - Sets code_source="imported", imported_filename=file.filename, code_status="reviewed"
  - Returns updated PolicyRuleResponse
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 308-342) — Complete example
- **Dependencies**:
  - Task 2.5 (updated schema)

### Task 2.5: Update PolicyRuleResponse schema with new fields

- **Files**:
  - `backend/aegis/schemas/policy.py` — Add fields to PolicyRuleResponse
- **Success**:
  - PolicyRuleResponse includes: code_source, imported_filename, reviewed_by, reviewed_at
  - All are optional/nullable in response
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 202-214) — TypeScript types mirror
- **Dependencies**:
  - Task 1.2 (model fields exist)

**Add to PolicyRuleResponse:**
```python
    code_source: str = "llm"
    imported_filename: str | None = None
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
```

## Phase 3: Backend API — Profile CRUD & Lifecycle

### Task 3.1: Create Pydantic schemas for profiles

Create `backend/aegis/schemas/profile.py`.

- **Files**:
  - `backend/aegis/schemas/profile.py` — New schema file
- **Success**:
  - PolicyProfileCreate: name, description, profile_type, included_rule_ids (optional list of UUIDs)
  - PolicyProfileResponse: all fields + computed rule_count + approved_count
  - PolicyProfileUpdate: name, description, included_rule_ids (all optional)
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 215-230) — TypeScript type mirrors Pydantic schema
- **Dependencies**:
  - Task 1.3 (model exists)

**Schemas:**
```python
class PolicyProfileCreate(BaseModel):
    name: str
    description: str | None = None
    profile_type: str = "standard"  # "standard" | "tailored"
    included_rule_ids: list[uuid.UUID] | None = None  # required if tailored

class PolicyProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    included_rule_ids: list[uuid.UUID] | None = None

class PolicyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    policy_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    version: int
    parent_version_id: uuid.UUID | None
    profile_type: str
    status: str
    included_rule_ids: list[str] | None
    created_by: uuid.UUID | None
    created_at: datetime
    locked_at: datetime | None
    rule_count: int = 0
    approved_count: int = 0
```

### Task 3.2: Create profiles router — create and list profiles

Create `backend/aegis/api/v1/profiles.py` with POST and GET under /policies/{policy_id}/profiles.

- **Files**:
  - `backend/aegis/api/v1/profiles.py` — New router file
- **Success**:
  - POST creates a PolicyProfile; validates policy exists; validates included_rule_ids belong to policy if tailored
  - GET returns list of profiles for a policy with computed rule_count/approved_count
  - Router prefix: `/profiles` (profile-specific endpoints)
  - Policy-scoped endpoints mounted at `/policies` (on existing policies router, or separate)
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 145-157) — Endpoint list
- **Dependencies**:
  - Task 3.1 (schemas)

**Key logic for create:**
- If profile_type=="standard": included_rule_ids=None (all rules)
- If profile_type=="tailored": validate included_rule_ids not empty, all IDs belong to the policy
- Set workspace_id from the policy's workspace_id

**Key logic for list:**
- Query PolicyProfiles where policy_id matches
- For each profile, compute rule_count (len(included_rule_ids) or total policy rules if null)
- Compute approved_count by querying PolicyRule.code_status=="approved" for the included rules

### Task 3.3: Add GET, PATCH, DELETE for individual profiles

- **Files**:
  - `backend/aegis/api/v1/profiles.py` — Add endpoints
- **Success**:
  - GET /profiles/{profile_id}: returns single profile with computed counts
  - PATCH /profiles/{profile_id}: updates name/description/included_rule_ids (only if status=="draft")
  - DELETE /profiles/{profile_id}: deletes (only if status=="draft")
  - 409 error if trying to modify/delete non-draft profile
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 149-151) — Endpoint specs
- **Dependencies**:
  - Task 3.2 (router exists)

### Task 3.4: Add POST /profiles/{profile_id}/promote

Lock a profile, making it READ_ONLY.

- **Files**:
  - `backend/aegis/api/v1/profiles.py` — New endpoint
- **Success**:
  - Validates all included PolicyRules have code_status=="approved"
  - Sets status="locked", locked_at=now
  - Returns 422 with count of unapproved rules if validation fails
  - Returns 409 if already locked
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 344-376) — Complete example
- **Dependencies**:
  - Task 3.2

### Task 3.5: Add POST /profiles/{profile_id}/new-version

Create a new draft version from a locked profile.

- **Files**:
  - `backend/aegis/api/v1/profiles.py` — New endpoint
- **Success**:
  - Only works on locked profiles (409 otherwise)
  - Creates new PolicyProfile with parent_version_id=source, version=source.version+1, status="draft"
  - Copies name (appended " v{N}"), description, profile_type, included_rule_ids
  - Returns new draft profile
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 155) — Endpoint spec
- **Dependencies**:
  - Task 3.2

### Task 3.6: Register profiles router in main.py

- **Files**:
  - `backend/aegis/main.py` — Import and include profiles router
- **Success**:
  - `/api/v1/profiles/*` endpoints accessible
  - `/api/v1/policies/{policy_id}/profiles` endpoints accessible
- **Research References**:
  - Pattern from existing router registrations in main.py
- **Dependencies**:
  - Task 3.2 (router exists)

**Note:** The profiles router may need to be split — policy-scoped endpoints (create/list) can be added to the existing policies router, or a sub-router can be mounted. Alternatively, create a single profiles router and use both `/policies/{pid}/profiles` and `/profiles/{id}` path patterns within it.

## Phase 4: Backend API — Blueprint Update

### Task 4.1: Update HardeningBlueprintCreate schema

- **Files**:
  - `backend/aegis/schemas/blueprint.py` — Replace component_policy_map with component_profile_map
- **Success**:
  - `component_policy_map` field removed
  - `component_profile_map: dict[str, uuid.UUID]` added
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 127-133) — Model spec
- **Dependencies**:
  - Phase 1 complete

### Task 4.2: Update create_blueprint endpoint

- **Files**:
  - `backend/aegis/api/v1/blueprints.py` — Rewrite create_blueprint
- **Success**:
  - Validates all profiles in component_profile_map are status=="locked"
  - Creates BlueprintRules from the profile's PolicyRules (resolved via included_rule_ids or all rules)
  - BlueprintRules inherit evaluation_code, remediation_code, rollback_code from PolicyRule
  - BlueprintRules have code_status="approved" (inherited)
  - Serializes component_profile_map UUID values to strings for JSON storage
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 378-424) — Complete example
- **Dependencies**:
  - Task 4.1

### Task 4.3: Update HardeningBlueprintResponse schema

- **Files**:
  - `backend/aegis/schemas/blueprint.py` — Update response schema
- **Success**:
  - Remove `policy_id` field
  - Replace `component_policy_map` with `component_profile_map: dict | None`
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 127-133)
- **Dependencies**:
  - Task 4.1

## Phase 5: Frontend — Types & API Layer

### Task 5.1: Extend PolicyRule type with code/review fields

- **Files**:
  - `frontend/src/types/index.ts` — Update PolicyRule interface
- **Success**:
  - PolicyRule interface includes: evaluation_code, remediation_code, rollback_code, code_status, code_source, imported_filename, reviewed_by, reviewed_at
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 202-214) — TypeScript types
- **Dependencies**:
  - Phase 2 (backend returns these fields)

### Task 5.2: Add PolicyProfile type

- **Files**:
  - `frontend/src/types/index.ts` — Add PolicyProfile interface
- **Success**:
  - Interface matches backend PolicyProfileResponse
  - Includes rule_count and approved_count computed fields
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 215-230)
- **Dependencies**:
  - None

### Task 5.3: Update HardeningBlueprint type

- **Files**:
  - `frontend/src/types/index.ts` — Update HardeningBlueprint interface
- **Success**:
  - Remove `policy_id` field
  - Replace `component_policy_map` with `component_profile_map: Record<string, string> | null`
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 127-133)
- **Dependencies**:
  - None

### Task 5.4: Add API endpoint functions for rule review

- **Files**:
  - `frontend/src/api/endpoints.ts` — Add functions
- **Success**:
  - `updatePolicyRuleCode(policyId, ruleId, codes)` — PATCH
  - `approvePolicyRule(policyId, ruleId)` — POST
  - `rejectPolicyRule(policyId, ruleId, reason?)` — POST
  - `importPolicyRuleCode(policyId, ruleId, codeType, file)` — POST with FormData
- **Research References**:
  - Pattern from existing endpoints in `frontend/src/api/endpoints.ts`
- **Dependencies**:
  - Task 5.1 (types)

### Task 5.5: Add API endpoint functions for profiles

- **Files**:
  - `frontend/src/api/endpoints.ts` — Add functions
- **Success**:
  - `createProfile(policyId, data)` — POST
  - `listProfiles(policyId)` — GET
  - `getProfile(profileId)` — GET
  - `updateProfile(profileId, data)` — PATCH
  - `deleteProfile(profileId)` — DELETE
  - `promoteProfile(profileId)` — POST
  - `newProfileVersion(profileId)` — POST
  - `listLockedProfiles(workspaceId)` — GET with status=locked filter
- **Research References**:
  - Pattern from existing endpoints
- **Dependencies**:
  - Task 5.2 (types)

### Task 5.6: Update createBlueprint API function

- **Files**:
  - `frontend/src/api/endpoints.ts` — Update createBlueprint
- **Success**:
  - Function signature changes from `componentPolicyMap` to `componentProfileMap`
  - Request body sends `component_profile_map` instead of `component_policy_map`
- **Research References**:
  - Existing `createBlueprint` function in endpoints.ts
- **Dependencies**:
  - Task 5.3 (types)

## Phase 6: Frontend — Policy Implementation Editor Page

### Task 6.1: Create PolicyImplementationEditorPage

Create `frontend/src/pages/PolicyImplementationEditorPage.tsx`.

- **Files**:
  - `frontend/src/pages/PolicyImplementationEditorPage.tsx` — New page component
- **Success**:
  - Route: `/policies/:policyId/implementation`
  - Left sidebar: scrollable rules list grouped by category with status dot indicators (pending/generated/reviewed/approved/rejected)
  - Right panel: Monaco Editor with 3 tabs (Evaluate / Remediate / Rollback)
  - Action buttons: Save (PATCH code), Approve, Reject, Import (file upload), Re-generate (trigger LLM)
  - Re-generate button triggers existing generatePolicyCodes endpoint for selected rule
  - WebSocket progress indicator when LLM generation is active
  - Status badge shown prominently per rule
  - Mirrors layout/UX of existing HardeningBlueprintEditorPage
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 172-181) — Frontend spec
  - `frontend/src/pages/HardeningBlueprintEditorPage.tsx` — Layout pattern to follow
- **Dependencies**:
  - Phase 5 (types + API functions)

**Key UI elements:**
- Use `@monaco-editor/react` MonacoEditor component (already a project dependency)
- Use TanStack Query for data fetching (`useQuery` for rules, `useMutation` for actions)
- Category grouping: group rules by `category` field
- Status colors: same STATUS_COLOR/STATUS_DOT maps as HardeningBlueprintEditorPage
- Import modal: simple file input + code_type selector (evaluation/remediation/rollback)

### Task 6.2: Add route registration in App.tsx

- **Files**:
  - `frontend/src/App.tsx` — Add Route for PolicyImplementationEditorPage
- **Success**:
  - Route `/policies/:policyId/implementation` renders PolicyImplementationEditorPage
  - Lazy-loaded or direct import (follow existing pattern)
- **Research References**:
  - Existing route registrations in App.tsx
- **Dependencies**:
  - Task 6.1

## Phase 7: Frontend — Profile Management UI

### Task 7.1: Add profile list and management to PolicyManagerPage

Extend `frontend/src/pages/PolicyManagerPage.tsx` with a profiles section.

- **Files**:
  - `frontend/src/pages/PolicyManagerPage.tsx` — Add profiles panel below rules table
- **Success**:
  - When a policy is selected, show "Profiles" section below or beside rules
  - List profiles with status badges (draft/in_review/approved/locked)
  - Show rule_count and approved_count for each profile
  - "Create Profile" button opens modal
  - "Promote" button (enabled only when approved_count == rule_count)
  - "New Version" button on locked profiles
  - "Delete" button on draft profiles
  - Link to PolicyImplementationEditorPage for reviewing rule implementations
  - "Review Implementation" link/button navigates to /policies/{id}/implementation
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 184-192) — UI spec
- **Dependencies**:
  - Phase 5 (API functions + types)

### Task 7.2: Create Profile Creation modal

- **Files**:
  - `frontend/src/pages/PolicyManagerPage.tsx` — Add CreateProfileModal component (inline or separate)
- **Success**:
  - Modal with: name input, description textarea, profile_type radio (standard/tailored)
  - If tailored: show checkboxes for each rule in the policy (fetched via listPolicyRules)
  - Group checkboxes by category/severity for easier selection
  - "Select All" / "Deselect All" helpers
  - Submit calls createProfile API
  - On success: invalidate profiles query, close modal
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 184-192) — UI spec
  - Pattern: ImportPolicyModal in existing PolicyManagerPage
- **Dependencies**:
  - Task 7.1

## Phase 8: Frontend — Blueprint Manager Update

### Task 8.1: Update HardeningBlueprintManagerPage to use locked profiles

- **Files**:
  - `frontend/src/pages/HardeningBlueprintManagerPage.tsx` — Replace policy dropdowns with profile dropdowns
- **Success**:
  - Component mapping section shows locked profiles instead of raw policies
  - Dropdown options: "Profile Name (Policy Name) — v{N}" for each locked profile in workspace
  - Uses `listLockedProfiles(workspaceId)` to fetch available profiles
  - State: `componentProfileMap` replaces `componentPolicyMap`
  - Create button calls updated `createBlueprint` with `component_profile_map`
  - Existing blueprint tiles show profile names from component_profile_map
  - Auto-matching logic updated to match profiles (by policy keywords) instead of policies directly
- **Research References**:
  - #file:../research/20260506-policy-level-hardening-research.md (Lines 194-199) — UI spec
  - Existing HardeningBlueprintManagerPage code for current implementation pattern
- **Dependencies**:
  - Phase 5 (API functions)
  - Phase 4 (backend accepts profiles)

**Key changes:**
- Remove `policies` query, replace with `profiles` query (locked status, workspace filtered)
- Replace `componentPolicyMap` state with `componentProfileMap`
- Update `findBestPolicy` → `findBestProfile` (match by parent policy keywords)
- Update `createMut` to call `createBlueprint(name, solutionTypeId, componentProfileMap)`
- Blueprint tiles: resolve profile names from the profile list for display

## Dependencies

- PostgreSQL with existing schema through migration 005
- Alembic CLI for running migrations
- FastAPI + SQLAlchemy async + Pydantic v2
- Celery + Redis (existing code gen pipeline)
- React + TanStack Query + @monaco-editor/react + Tailwind CSS

## Success Criteria

- Migration 006 runs cleanly on existing database
- All new API endpoints pass manual testing (curl/httpie)
- Policy Implementation Editor page renders rules with Monaco Editor
- Rules can be approved/rejected/edited/imported at policy level
- Profiles can be created (standard + tailored), promoted, and versioned
- Blueprints only accept locked profiles in component_profile_map
- End-to-end: Policy → LLM Gen → Review → Approve → Profile → Lock → Blueprint