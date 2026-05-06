---
applyTo: ".copilot-tracking/changes/20260506-policy-level-hardening-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Policy-Level Hardening Implementation

## Overview

Implement policy-level rule hardening (LLM code generation + HITL review + script import), tailored profiles with versioning/locking, and update Blueprint creation to use locked profiles instead of raw policies.

## Objectives

- Enable HITL review workflow (approve/reject/edit/import) directly on PolicyRule records
- Support importing external scripts/tools as rule implementations
- Add PolicyProfile model for creating standard or tailored (subset) profiles from policies
- Implement profile versioning and READ_ONLY locking upon promotion
- Replace Blueprint's `component_policy_map` with `component_profile_map` referencing locked profiles
- Build Policy Implementation Editor page with Monaco Editor for reviewing rule code
- Build Profile management UI for creating/promoting/versioning profiles

## Research Summary

### Project Files

- `backend/aegis/models/policy.py` — PolicyRule model to extend with review/import fields
- `backend/aegis/models/hardening_blueprint.py` — HardeningBlueprint to replace component_policy_map
- `backend/aegis/api/v1/policies.py` — Existing router to extend with rule review endpoints
- `backend/aegis/api/v1/blueprints.py` — Blueprint creation to update for profile-based mapping
- `backend/aegis/tasks/codegen_tasks.py` — Existing code gen pipeline (no changes needed)
- `frontend/src/pages/HardeningBlueprintEditorPage.tsx` — Pattern for Monaco-based HITL review UI
- `frontend/src/pages/PolicyManagerPage.tsx` — Page to extend with profile management
- `frontend/src/pages/HardeningBlueprintManagerPage.tsx` — Page to update for profile-based mapping

### External References

- #file:../research/20260506-policy-level-hardening-research.md — Complete research with data models, API specs, and code examples

### Standards References

- `backend/aegis/api/v1/blueprints.py` — Existing HITL review pattern (approve/reject/update)
- `frontend/src/pages/HardeningBlueprintEditorPage.tsx` — Existing Monaco Editor integration pattern

## Implementation Checklist

### [x] Phase 1: Database & Model Changes

- [x] Task 1.1: Create Alembic migration 006 (extend policy_rules + create policy_profiles + update hardening_blueprints)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 11-74)

- [x] Task 1.2: Update PolicyRule model with review/import tracking fields
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 76-102)

- [x] Task 1.3: Create PolicyProfile ORM model
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 104-163)

- [x] Task 1.4: Update HardeningBlueprint model (remove policy_id + component_policy_map, add component_profile_map)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 165-183)

- [x] Task 1.5: Update models/__init__.py and add relationships
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 185-198)

### [x] Phase 2: Backend API — Policy Rule Review Endpoints

- [x] Task 2.1: Add PATCH /policies/{policy_id}/rules/{rule_id}/code endpoint
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 202-227)

- [x] Task 2.2: Add POST /policies/{policy_id}/rules/{rule_id}/approve endpoint
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 229-240)

- [x] Task 2.3: Add POST /policies/{policy_id}/rules/{rule_id}/reject endpoint
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 242-258)

- [x] Task 2.4: Add POST /policies/{policy_id}/rules/{rule_id}/import endpoint
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 260-275)

- [x] Task 2.5: Update PolicyRuleResponse schema with new fields
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 277-295)

### [x] Phase 3: Backend API — Profile CRUD & Lifecycle

- [x] Task 3.1: Create Pydantic schemas for profiles (PolicyProfileCreate, PolicyProfileResponse, PolicyProfileUpdate)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 299-344)

- [x] Task 3.2: Create profiles router with POST /policies/{policy_id}/profiles and GET /policies/{policy_id}/profiles
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 346-370)

- [x] Task 3.3: Add GET /profiles/{profile_id}, PATCH /profiles/{profile_id}, DELETE /profiles/{profile_id}
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 372-384)

- [x] Task 3.4: Add POST /profiles/{profile_id}/promote (lock profile)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 386-400)

- [x] Task 3.5: Add POST /profiles/{profile_id}/new-version (create draft from locked)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 402-416)

- [x] Task 3.6: Register profiles router in main.py
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 418-430)

### [x] Phase 4: Backend API — Blueprint Update

- [x] Task 4.1: Update HardeningBlueprintCreate schema to use component_profile_map
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 434-444)

- [x] Task 4.2: Update create_blueprint endpoint to validate locked profiles and create BlueprintRules from PolicyRules
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 446-459)

- [x] Task 4.3: Update HardeningBlueprintResponse schema
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 461-471)

### [x] Phase 5: Frontend — Types & API Layer

- [x] Task 5.1: Extend PolicyRule type with code/review fields
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 475-484)

- [x] Task 5.2: Add PolicyProfile type
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 486-496)

- [x] Task 5.3: Update HardeningBlueprint type (component_profile_map replaces component_policy_map)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 498-508)

- [x] Task 5.4: Add API endpoint functions for rule review (updatePolicyRuleCode, approvePolicyRule, rejectPolicyRule, importPolicyRuleCode)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 510-522)

- [x] Task 5.5: Add API endpoint functions for profiles (createProfile, listProfiles, getProfile, updateProfile, deleteProfile, promoteProfile, newProfileVersion)
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 524-540)

- [x] Task 5.6: Update createBlueprint API function to use component_profile_map
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 542-552)

### [x] Phase 6: Frontend — Policy Implementation Editor Page

- [x] Task 6.1: Create PolicyImplementationEditorPage component with route /policies/:policyId/implementation
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 556-582)

- [x] Task 6.2: Add route registration in App.tsx
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 584-594)

### [x] Phase 7: Frontend — Profile Management UI

- [x] Task 7.1: Add profile list and management section to PolicyManagerPage
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 598-617)

- [x] Task 7.2: Create Profile Creation modal with rule selection for tailored profiles
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 619-634)

### [x] Phase 8: Frontend — Blueprint Manager Update

- [x] Task 8.1: Update HardeningBlueprintManagerPage to use locked profiles in component mapping
  - Details: .copilot-tracking/details/20260506-policy-level-hardening-details.md (Lines 638-670)

## Dependencies

- PostgreSQL database (running via docker-compose)
- Alembic migration tooling
- Existing LLM code generation pipeline (Celery + CodeGenerator)
- Monaco Editor (@monaco-editor/react)
- TanStack React Query
- FastAPI + SQLAlchemy async + Pydantic v2

## Success Criteria

- Policy-level HITL review: users can approve/reject/edit/import rule code directly on PolicyRules
- Profile creation: standard (all rules) and tailored (selected subset) profiles can be created
- Profile promotion: only succeeds when all included PolicyRules have code_status=approved
- Profile locking: locked profiles are READ_ONLY; new-version creates draft copy
- Blueprint creation: maps components to locked profiles; inherits code from PolicyRules
- End-to-end workflow: Policy → Code Gen → Review → Profile → Lock → Blueprint → Enforce