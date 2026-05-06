# Changes Record: Policy-Level Hardening Implementation

## Added

- `backend/migrations/versions/006_policy_profiles_and_rule_review.py` — Alembic migration adding code_source/reviewed_by/reviewed_at/imported_filename to policy_rules, creating policy_profiles table, and replacing component_policy_map with component_profile_map on hardening_blueprints
- `backend/aegis/models/policy_profile.py` — New PolicyProfile ORM model with relationships to Policy, Workspace, and self-referential parent_version
- `backend/aegis/schemas/profile.py` — Pydantic schemas for PolicyProfile (Create, Update, Response with computed rule_count/approved_count)
- `backend/aegis/api/v1/profiles.py` — Full profiles router: CRUD, promote (lock), new-version, workspace-level listing with status filter
- `frontend/src/pages/PolicyImplementationEditorPage.tsx` — Monaco-based HITL review page with sidebar rule list, 3-tab editor, approve/reject/import/save actions, WebSocket streaming for code gen

## Modified

- `backend/aegis/models/policy.py` — Added code_source, imported_filename, reviewed_by, reviewed_at columns to PolicyRule; added profiles relationship to Policy
- `backend/aegis/models/hardening_blueprint.py` — Removed policy_id column and policy relationship; replaced component_policy_map with component_profile_map
- `backend/aegis/models/__init__.py` — Registered PolicyProfile import and __all__ export
- `backend/aegis/schemas/policy.py` — Extended PolicyRuleResponse with new fields; added PolicyRuleCodeUpdate, PolicyRuleRejectRequest schemas
- `backend/aegis/schemas/blueprint.py` — HardeningBlueprintCreate/Response now uses component_profile_map instead of component_policy_map
- `backend/aegis/api/v1/policies.py` — Added 4 rule-level endpoints: PATCH code, POST approve, POST reject, POST import
- `backend/aegis/api/v1/blueprints.py` — create_blueprint validates locked profiles and inherits approved code from PolicyRules
- `backend/aegis/main.py` — Registered profiles router
- `frontend/src/types/index.ts` — Extended PolicyRule with code/review fields; added PolicyProfile interface; updated HardeningBlueprint to component_profile_map
- `frontend/src/api/endpoints.ts` — Added rule review APIs (updateCode, approve, reject, import); profile CRUD + promote + newVersion + listLocked; updated createBlueprint signature
- `frontend/src/App.tsx` — Added route for PolicyImplementationEditorPage
- `frontend/src/pages/PolicyManagerPage.tsx` — Added profiles section with ProfileCard grid, CreateProfileModal, "Review Implementation" button, code_status column in rules table
- `frontend/src/pages/HardeningBlueprintManagerPage.tsx` — Replaced policy dropdowns with locked profile dropdowns; added findBestProfile auto-matcher; blueprint tiles show profile names

## Removed

- `hardening_blueprints.policy_id` column (migrated away)
- `hardening_blueprints.component_policy_map` column (replaced by component_profile_map)