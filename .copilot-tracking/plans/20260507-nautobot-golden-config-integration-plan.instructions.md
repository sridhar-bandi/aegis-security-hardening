---
applyTo: ".copilot-tracking/changes/20260507-nautobot-golden-config-integration-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Nautobot Golden Configuration Integration for Policy Evaluation

## Overview

Add an alternative data-driven evaluation method that generates golden configuration (CLI/JSON) via LLM and pushes it to a Nautobot instance for continuous configuration drift monitoring, while keeping script-based evaluation/remediation/rollback as the default.

## Objectives

- Add `evaluation_method` enum to PolicyRule and BlueprintRule models (`script` default, `nautobot_golden_config` alternative)
- Store LLM-generated golden configuration data (CLI text or JSON) alongside existing code fields
- Create LLM prompt templates for generating intended device configuration instead of Python scripts
- Build a `NautobotConnector` service for pushing golden configs and triggering compliance jobs via Nautobot REST API
- Add Celery tasks for golden config generation and Nautobot push operations
- Provide API endpoints for generating golden configs and pushing to Nautobot
- Update frontend to allow users to select evaluation method and view/push golden configs

## Research Summary

### Project Files

- `backend/aegis/models/policy.py` — PolicyRule model to extend with evaluation_method and golden_config_data fields
- `backend/aegis/models/hardening_blueprint.py` — BlueprintRule model to extend similarly
- `backend/aegis/services/llm/code_generator.py` — CodeGenerator to extend with `generate_golden_config()` method
- `backend/aegis/services/llm/prompts.py` — Add new golden config prompt templates
- `backend/aegis/services/connectors/` — Add NautobotConnector
- `backend/aegis/tasks/codegen_tasks.py` — Extend with golden config generation task
- `backend/aegis/config.py` — Add Nautobot connection settings
- `backend/aegis/api/v1/policies.py` — Add golden config generation endpoint
- `backend/aegis/api/v1/instances.py` — Add Nautobot push endpoint
- `frontend/src/types/index.ts` — Extend types with new fields
- `frontend/src/api/endpoints.ts` — Add new API calls

### External References

- #file:../research/20260507-nautobot-golden-config-integration-research.md — Complete research with Nautobot API docs, architecture analysis, and implementation guidance
- Nautobot Golden Config REST API: `/api/plugins/golden-config/` endpoints
- Nautobot Core REST API: `/api/dcim/devices/` for config_context updates

### Standards References

- Existing `code_source` enum pattern in `backend/aegis/models/policy.py`
- Existing LLM prompt template pattern in `backend/aegis/services/llm/prompts.py`
- Existing connector pattern in `backend/aegis/services/connectors/base.py`
- Existing Celery task pattern in `backend/aegis/tasks/codegen_tasks.py`

## Implementation Checklist

### [ ] Phase 1: Database & Model Changes

- [ ] Task 1.1: Create Alembic migration 007 — add evaluation_method, golden_config_data, golden_config_format columns to policy_rules and blueprint_rules tables
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 11-72)

- [ ] Task 1.2: Update PolicyRule ORM model with new fields (evaluation_method, golden_config_data, golden_config_format)
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 74-109)

- [ ] Task 1.3: Update BlueprintRule ORM model with new fields (evaluation_method, golden_config_data, golden_config_format)
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 111-140)

### [ ] Phase 2: Configuration & Nautobot Connector

- [ ] Task 2.1: Add Nautobot settings to config.py (NAUTOBOT_URL, NAUTOBOT_API_TOKEN, NAUTOBOT_GOLDEN_CONFIG_REPO)
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 142-171)

- [ ] Task 2.2: Create NautobotConnector service class for REST API interaction
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 173-260)

### [ ] Phase 3: LLM Golden Config Generation

- [ ] Task 3.1: Add golden config prompt templates to prompts.py (GOLDEN_CONFIG_CLI_TEMPLATE, GOLDEN_CONFIG_JSON_TEMPLATE)
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 262-336)

- [ ] Task 3.2: Extend CodeGenerator with generate_golden_config() method
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 338-392)

### [ ] Phase 4: Celery Tasks & Backend Logic

- [ ] Task 4.1: Add Celery task for golden config generation (generate_golden_configs task)
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 394-456)

- [ ] Task 4.2: Add Celery task for pushing golden config to Nautobot (push_golden_config_to_nautobot task)
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 458-520)

### [ ] Phase 5: API Endpoints & Schemas

- [ ] Task 5.1: Add Pydantic schemas for golden config requests/responses
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 522-573)

- [ ] Task 5.2: Add API endpoint POST /policies/{id}/generate-golden-config
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 575-618)

- [ ] Task 5.3: Add API endpoint POST /instances/{id}/push-nautobot
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 620-668)

- [ ] Task 5.4: Add API endpoint PATCH /policies/{id}/rules/{rule_id}/evaluation-method for toggling evaluation method
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 670-705)

### [ ] Phase 6: Frontend Updates

- [ ] Task 6.1: Update TypeScript types (PolicyRule, BlueprintRule) with new fields
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 707-738)

- [ ] Task 6.2: Add API endpoint functions for golden config operations
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 740-770)

- [ ] Task 6.3: Add evaluation method toggle UI in PolicyManager component
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 772-815)

- [ ] Task 6.4: Add "Push to Nautobot" button in EnforcementConsole for instances with golden config
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 817-855)

### [ ] Phase 7: Testing & Documentation

- [ ] Task 7.1: Add unit tests for NautobotConnector
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 857-895)

- [ ] Task 7.2: Add unit tests for golden config generation prompt/flow
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 897-930)

- [ ] Task 7.3: Update .env.example with Nautobot configuration variables
  - Details: .copilot-tracking/details/20260507-nautobot-golden-config-integration-details.md (Lines 932-950)

## Dependencies

- `requests` (already in requirements.txt) — HTTP client for Nautobot API
- `gitpython` (new dependency) — Git repo operations for pushing intended configs
- Nautobot instance with Golden Config plugin (external dependency, not required for Aegis to function)
- Existing LLM infrastructure (Ollama/OpenAI) for generating golden configs
- Existing PostgreSQL + Alembic for schema migrations

## Success Criteria

- User can toggle evaluation method between "script" and "nautobot_golden_config" per PolicyRule
- LLM generates valid CLI or JSON intended configuration from policy check_content/fix_text
- Golden config data is stored in the database and visible in the frontend
- "Push to Nautobot" action successfully pushes config via Nautobot REST API (when Nautobot is configured)
- Script-based evaluation, remediation, and rollback remain fully functional as the default method
- Frontend clearly shows which evaluation method is active and provides appropriate controls
- Nautobot settings are optional — system works without Nautobot configured (graceful degradation)