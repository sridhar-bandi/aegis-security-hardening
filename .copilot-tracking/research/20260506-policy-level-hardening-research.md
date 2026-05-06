<!-- markdownlint-disable-file -->

# Task Research Notes: Policy-Level Hardening Implementation

## Design Decisions (User-Confirmed)

1. **Rule implementations live at the Policy level** — code (eval/remediate/rollback) is stored directly on `PolicyRule` records. No duplication into profiles.
2. **No backward compatibility required** — `component_policy_map` on Blueprint will be fully replaced by `component_profile_map`.

## Research Executed

### File Analysis

- `backend/aegis/models/policy.py`
  - `Policy` model: workspace_id, name, standard, format, file_path, code_status
  - `PolicyRule` model: evaluation_code, remediation_code, rollback_code, code_status, milvus_embedding_id
  - code_status enum: pending/generating/generated/reviewed/approved/rejected
  - No review/import tracking fields on PolicyRule yet (no `code_source`, `imported_filename`, `reviewed_by`)

- `backend/aegis/models/hardening_blueprint.py`
  - `HardeningBlueprint`: solution_type_id + component_policy_map (to be replaced)
  - `BlueprintRule`: per-component rule with code fields — will inherit from PolicyRule
  - `HITLComment`: review comments on BlueprintRules

- `backend/aegis/api/v1/policies.py`
  - Endpoints: upload_policy, list_policies, list_policy_rules, trigger_policy_code_generation, delete_policy
  - No rule-level approve/reject/update/import endpoints

- `backend/aegis/api/v1/blueprints.py`
  - Blueprint creation takes `component_policy_map: dict[str, UUID]`
  - HITL review exists at BlueprintRule level (approve/reject/update code)

- `backend/aegis/tasks/codegen_tasks.py`
  - `generate_policy_codes`: generates all 3 code types for PolicyRules via LLM, stores on PolicyRule
  - Publishes progress via Redis pub/sub

- `backend/aegis/services/policy_parser/xccdf_parser.py`
  - Has `get_profiles()` → `ProfileInfo(profile_id, title, selected_rule_ids)`
  - Maps directly to the tailored profile concept

- `frontend/src/pages/HardeningBlueprintEditorPage.tsx`
  - Full HITL review UI with Monaco Editor — pattern to reuse for policy-level review

### Project Conventions

- Backend: FastAPI + SQLAlchemy async + Pydantic v2 schemas + Celery tasks
- Frontend: React + TanStack Query + Tailwind CSS + Monaco Editor
- Auth: JWT + RBAC (admin, security_officer, auditor, user)

## Key Discoveries

### Architecture After Implementation

```
Policy Import → Auto LLM Code Gen → code stored on PolicyRules
       ↓
Policy-level HITL Review (approve/reject/edit/import per PolicyRule)
       ↓
Create Profile(s) from Policy (standard = all rules, tailored = subset)
       ↓
Profile can only be promoted/locked when ALL included PolicyRules are approved
       ↓
Promote Profile → status=locked, READ_ONLY
       ↓
To modify locked profile → create new version (draft copy)
       ↓
Blueprint creation maps components → locked Profiles
       ↓
BlueprintRules inherit code directly from PolicyRules (via profile's rule set)
```

### Key Insight: Implementation at Policy Level, Selection at Profile Level

- **PolicyRule** owns the canonical implementation (eval/remediate/rollback code)
- **PolicyProfile** is a lightweight selection + lifecycle entity (which rules are included, status, versioning)
- Profile promotion validates that all its included PolicyRules have `code_status = "approved"`
- No code duplication — profiles reference PolicyRules, not copy them

### Data Model Changes

#### 1. Extend PolicyRule (add review tracking + import support)

```python
# Add to existing PolicyRule model:
    code_source: Mapped[str] = mapped_column(
        Enum("llm", "manual", "imported", name="code_source"),
        nullable=False, default="llm",
    )
    imported_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

#### 2. New PolicyProfile model

```python
class PolicyProfile(Base):
    __tablename__ = "policy_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("policy_profiles.id"), nullable=True)
    profile_type: Mapped[str] = mapped_column(
        Enum("standard", "tailored", name="profile_type"), nullable=False, default="standard"
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "in_review", "approved", "locked", name="profile_status"), nullable=False, default="draft"
    )
    # JSON array of included PolicyRule UUIDs (null = ALL rules from parent policy)
    included_rule_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    policy: Mapped["Policy"] = relationship("Policy", back_populates="profiles")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    parent_version: Mapped["PolicyProfile | None"] = relationship("PolicyProfile", remote_side=[id])
```

#### 3. Replace component_policy_map on HardeningBlueprint

```python
# On HardeningBlueprint model:
# REMOVE: component_policy_map, policy_id
# ADD:
    component_profile_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # JSON: {"component_type_id": "profile_uuid", ...}
```

### API Endpoints

```
# Policy-level rule implementation management (on existing policies router)
PATCH  /policies/{policy_id}/rules/{rule_id}/code     → Update rule code (edit)
POST   /policies/{policy_id}/rules/{rule_id}/approve  → Approve rule implementation
POST   /policies/{policy_id}/rules/{rule_id}/reject   → Reject rule implementation
POST   /policies/{policy_id}/rules/{rule_id}/import   → Import script/tool for rule
POST   /policies/{policy_id}/generate-codes           → (already exists) Re-trigger LLM gen

# Profile CRUD (new profiles router)
POST   /policies/{policy_id}/profiles                 → Create profile (standard or tailored)
GET    /policies/{policy_id}/profiles                 → List profiles for a policy
GET    /profiles/{profile_id}                         → Get profile with included rules
PATCH  /profiles/{profile_id}                         → Update name/description/rule selection (draft only)
DELETE /profiles/{profile_id}                         → Delete draft profile

# Profile lifecycle
POST   /profiles/{profile_id}/promote                 → Lock profile (READ_ONLY)
POST   /profiles/{profile_id}/new-version             → Create new draft version from locked

# Blueprint (updated)
POST   /blueprints                                    → component_profile_map (not policy_map)
GET    /profiles?workspace_id=X&status=locked         → List lockable profiles for blueprint creation
```

### Frontend Changes

#### 1. Policy Manager Page — Add Rule Review UI

Extend existing `PolicyManagerPage.tsx`:
- Add code columns (eval/remediate/rollback status indicators) to rules table
- "Review Implementation" button per rule → opens Monaco Editor inline or navigates to editor
- Bulk "Generate Codes" button (re-trigger LLM for pending rules)
- Per-rule: Approve / Reject / Edit / Import buttons
- Import modal: file upload for eval/remediate/rollback script

#### 2. New Policy Implementation Editor Page

New `PolicyImplementationEditorPage.tsx` (route: `/policies/:policyId/implementation`):
- Left sidebar: rules list grouped by category with status indicators
- Main panel: Monaco Editor with tabs (Evaluate / Remediate / Rollback)
- Actions: Save, Approve, Reject, Import Script, Re-generate (LLM)
- Progress indicator for LLM generation (WebSocket)
- Mirrors existing `HardeningBlueprintEditorPage` layout

#### 3. New Profile Manager (within Policy page or separate)

Profile management UI in `PolicyManagerPage` or new `PolicyProfilesPage.tsx`:
- List profiles for selected policy with status badges
- Create Profile form: name, type (standard/tailored), rule selection checkboxes
- Promote button (only enabled when all included rules are approved)
- Version history display
- "New Version" button on locked profiles

#### 4. Blueprint Manager — Use Profiles

Update `HardeningBlueprintManagerPage.tsx`:
- Component mapping dropdown shows **locked profiles** instead of raw policies
- Dropdown label: "Profile Name (Policy Name) — v2 — locked"
- Validation: all components must map to locked profiles

### TypeScript Types

```typescript
export interface PolicyRule {
  // ... existing fields ...
  evaluation_code: string | null
  remediation_code: string | null
  rollback_code: string | null
  code_status: 'pending' | 'generating' | 'generated' | 'reviewed' | 'approved' | 'rejected'
  code_source: 'llm' | 'manual' | 'imported'
  imported_filename: string | null
  reviewed_by: string | null
  reviewed_at: string | null
}

export interface PolicyProfile {
  id: string
  policy_id: string
  workspace_id: string
  name: string
  description: string | null
  version: number
  parent_version_id: string | null
  profile_type: 'standard' | 'tailored'
  status: 'draft' | 'in_review' | 'approved' | 'locked'
  included_rule_ids: string[] | null  // null = all rules
  created_by: string | null
  created_at: string
  locked_at: string | null
  rule_count: number  // computed from included_rule_ids or total policy rules
  approved_count: number  // how many included rules have code_status=approved
}
```

### Migration 006

```python
"""Add policy profiles, extend policy_rules with review/import fields, replace component_policy_map.

Revision ID: 006
Revises: 005
"""

def upgrade() -> None:
    # 1. Create code_source enum
    op.execute("CREATE TYPE code_source AS ENUM ('llm', 'manual', 'imported')")
    
    # 2. Extend policy_rules with review/import tracking
    op.add_column("policy_rules", sa.Column("code_source", sa.Enum("llm", "manual", "imported", name="code_source"), server_default="llm", nullable=False))
    op.add_column("policy_rules", sa.Column("imported_filename", sa.String(500), nullable=True))
    op.add_column("policy_rules", sa.Column("reviewed_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
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
        sa.Column("included_rule_ids", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. Replace component_policy_map with component_profile_map on hardening_blueprints
    op.add_column("hardening_blueprints", sa.Column("component_profile_map", sa.JSON(), nullable=True))
    op.drop_column("hardening_blueprints", "component_policy_map")
    op.drop_column("hardening_blueprints", "policy_id")
```

### Complete Examples

```python
# Policy-level: approve a rule implementation
@router.post("/{policy_id}/rules/{rule_id}/approve", response_model=PolicyRuleResponse)
async def approve_policy_rule(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    result = await db.execute(
        select(PolicyRule).where(PolicyRule.id == rule_id, PolicyRule.policy_id == policy_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Policy rule not found")
    if not rule.evaluation_code:
        raise HTTPException(422, "Cannot approve rule without implementation code")
    
    rule.code_status = "approved"
    rule.reviewed_by = current_user.id
    rule.reviewed_at = func.now()
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)
```

```python
# Policy-level: import script for a rule
@router.post("/{policy_id}/rules/{rule_id}/import", response_model=PolicyRuleResponse)
async def import_rule_code(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    code_type: str = Query(...),  # "evaluation" | "remediation" | "rollback"
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    result = await db.execute(
        select(PolicyRule).where(PolicyRule.id == rule_id, PolicyRule.policy_id == policy_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Policy rule not found")

    content = (await file.read()).decode("utf-8")
    if code_type == "evaluation":
        rule.evaluation_code = content
    elif code_type == "remediation":
        rule.remediation_code = content
    elif code_type == "rollback":
        rule.rollback_code = content
    else:
        raise HTTPException(422, "code_type must be evaluation, remediation, or rollback")

    rule.code_source = "imported"
    rule.imported_filename = file.filename
    rule.code_status = "reviewed"
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)
```

```python
# Profile: promote (lock)
@router.post("/{profile_id}/promote", response_model=PolicyProfileResponse)
async def promote_profile(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    profile = await db.get(PolicyProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if profile.status == "locked":
        raise HTTPException(409, "Profile already locked")

    # Resolve included rules
    if profile.included_rule_ids:
        rule_ids = [uuid.UUID(r) for r in profile.included_rule_ids]
        rules_q = select(PolicyRule).where(PolicyRule.id.in_(rule_ids))
    else:
        rules_q = select(PolicyRule).where(PolicyRule.policy_id == profile.policy_id)

    result = await db.execute(rules_q)
    rules = result.scalars().all()
    unapproved = [r for r in rules if r.code_status != "approved"]
    if unapproved:
        raise HTTPException(422, f"{len(unapproved)} rule(s) not yet approved — all rules must be approved before promotion")

    profile.status = "locked"
    profile.locked_at = func.now()
    await db.commit()
    await db.refresh(profile)
    return PolicyProfileResponse.model_validate(profile)
```

```python
# Blueprint creation using profiles
@router.post("", response_model=HardeningBlueprintResponse, status_code=201)
async def create_blueprint(
    body: HardeningBlueprintCreate,  # has component_profile_map: dict[str, UUID]
    current_user: ...,
    db: ...,
) -> HardeningBlueprintResponse:
    st = await db.get(SolutionType, body.solution_type_id)
    # ... workspace access check ...

    # Validate all profiles are locked
    for comp_id, profile_id in body.component_profile_map.items():
        profile = await db.get(PolicyProfile, profile_id)
        if not profile or profile.status != "locked":
            raise HTTPException(422, f"Profile for component '{comp_id}' must be locked")

    blueprint = HardeningBlueprint(
        name=body.name,
        solution_type_id=body.solution_type_id,
        component_profile_map={k: str(v) for k, v in body.component_profile_map.items()},
        created_by=current_user.id,
    )
    db.add(blueprint)
    await db.flush()

    # Create BlueprintRules from profile's included PolicyRules
    for comp_id, profile_id in body.component_profile_map.items():
        profile = await db.get(PolicyProfile, profile_id)
        if profile.included_rule_ids:
            rule_ids = [uuid.UUID(r) for r in profile.included_rule_ids]
            rules_q = select(PolicyRule).where(PolicyRule.id.in_(rule_ids))
        else:
            rules_q = select(PolicyRule).where(PolicyRule.policy_id == profile.policy_id)
        result = await db.execute(rules_q)
        for pol_rule in result.scalars():
            db.add(BlueprintRule(
                blueprint_id=blueprint.id,
                policy_rule_id=pol_rule.id,
                component_type=comp_id,
                evaluation_code=pol_rule.evaluation_code,
                remediation_code=pol_rule.remediation_code,
                rollback_code=pol_rule.rollback_code,
                code_status="approved",  # inherited from approved PolicyRule
            ))

    await db.commit()
    await db.refresh(blueprint)
    return HardeningBlueprintResponse.model_validate(blueprint)
```

## Recommended Approach

**Implementation at PolicyRule level + lightweight PolicyProfile for selection/lifecycle + full replacement of component_policy_map.**

Key design decisions:
1. **No ProfileRuleImplementation table** — code lives solely on PolicyRule; no duplication
2. **PolicyRule extended** with `code_source`, `imported_filename`, `reviewed_by`, `reviewed_at` fields for review/import tracking
3. **PolicyProfile is selection + lifecycle only** — references PolicyRules via `included_rule_ids`, controls promotion/locking
4. **Profile promotion validates PolicyRule status** — all included rules must have `code_status = "approved"` on the PolicyRule record
5. **Versioning via parent_version_id** — modifying a locked profile creates a new version
6. **No backward compatibility** — `component_policy_map` and `policy_id` removed from HardeningBlueprint; replaced with `component_profile_map`
7. **BlueprintRules inherit directly from PolicyRules** (via profile's rule set) — no intermediate layer

## Implementation Guidance

- **Objectives**:
  1. Extend `PolicyRule` model with review/import tracking fields
  2. New `PolicyProfile` model (lightweight: selection + lifecycle)
  3. Policy-level rule HITL endpoints (approve/reject/edit/import on PolicyRule)
  4. Profile CRUD + lifecycle endpoints (create/promote/new-version)
  5. Replace `component_policy_map` → `component_profile_map` on Blueprint
  6. Policy Implementation Editor page (Monaco-based HITL review for PolicyRules)
  7. Profile management UI (create standard/tailored, promote, version)
  8. Blueprint Manager updated to use locked profiles

- **Key Tasks**:
  - DB migration 006: extend `policy_rules` + create `policy_profiles` + replace blueprint columns
  - Backend: add rule review/import endpoints to `policies.py` router
  - Backend: new `profiles.py` router (CRUD + promote + new-version)
  - Backend: update `blueprints.py` to use `component_profile_map` + validate locked profiles
  - Frontend: new `PolicyImplementationEditorPage.tsx` (Monaco editor for PolicyRules)
  - Frontend: profile management in `PolicyManagerPage.tsx`
  - Frontend: update `HardeningBlueprintManagerPage.tsx` component mapping to use profiles
  - Frontend: new types (`PolicyProfile`), extend `PolicyRule` type with code fields
  - Frontend: new API endpoint functions for rule review + profile CRUD

- **Dependencies**:
  - Existing PolicyRule code gen pipeline (already stores code on PolicyRule)
  - Monaco Editor already integrated
  - TanStack Query + Tailwind patterns established
  - RBAC middleware (admin/security_officer roles)

- **Success Criteria**:
  - User can review/approve/reject/edit rule implementations directly on PolicyRules
  - User can import scripts as rule implementations at the policy level
  - User can create standard (all rules) or tailored (subset) profiles from policies
  - Locked profiles are READ_ONLY; modification requires creating a new version
  - Blueprints map components to locked profiles only
  - Full workflow: Policy → Code Gen → Review Rules → Create Profile → Lock → Blueprint → Enforce