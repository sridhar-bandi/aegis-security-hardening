---
mode: agent
model: Claude Sonnet 4
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Project Aegis - AI Agentic Security Hardening Solution

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260504-project-aegis-changes.md` in #file:../changes/ if it does not exist, with sections: `## Added`, `## Modified`, `## Removed`.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260504-project-aegis-plan.instructions.md task-by-task
You WILL read the full task details from #file:../details/20260504-project-aegis-details.md before implementing each task
You WILL follow ALL project standards and conventions established during implementation

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:false} is true, you WILL stop after each Task for user review.

### Step 3: Implementation Order

Implement phases in dependency order:
1. **Phase 1** — Project scaffold and Docker Compose infrastructure (no dependencies)
2. **Phase 2** — Backend foundation: FastAPI core, ORM models, migrations, schemas, RBAC (depends on Phase 1)
3. **Phase 3** — Policy parsers: OVAL, XCCDF, text/LLM (depends on Phase 2 for lxml and DB models; Task 3.3 depends on Phase 4 Task 4.1)
4. **Phase 4** — LLM service: Ollama client, MilvusDB store, code generator, Celery tasks (depends on Phase 2; Task 3.3 can be completed after Task 4.1)
5. **Phase 5** — Connector library: BaseConnector, SSH, Redfish, Netmiko, Kubernetes, Vault, REST (depends on Phase 1 for installed packages)
6. **Phase 6** — Enforcement engine: evaluator, remediator, rollback, impact assessment, dry-run, Celery tasks (depends on Phases 2, 4, 5)
7. **Phase 7** — Reporting: ARF generator, HTML/summary generator (depends on Phase 6 for ComplianceResult types)
8. **Phase 8** — REST API layer: all routers and WebSocket handlers (depends on Phases 2-7)
9. **Phase 9** — React frontend: all components and pages (depends on Phase 8 API being available)

### Step 4: Key Implementation Standards

- All Python code must be **Python 3.12** with full type hints
- All FastAPI endpoints must be **async**; use `AsyncSession` from SQLAlchemy for DB operations
- All Celery tasks must update `EnforcementJob.status` in DB and publish to Redis pub/sub
- Generated code execution uses `exec()` in a sandboxed namespace — NEVER use `eval()`; always import `BaseConnector` and result types into the exec namespace
- Credentials referenced as `vault://secret/...` MUST be resolved via `VaultConnector` before being passed to other connectors — never log or store plaintext credentials
- WebSocket auth: validate JWT from `?token=` query param on connect; close with 4001 if invalid
- RBAC: every protected endpoint must use `Depends(require_role(...))` — no unprotected write endpoints
- Frontend TypeScript: zero `any` types; all API responses must have corresponding TypeScript interfaces in `src/types/index.ts`
- Monaco Editor: Python syntax mode for `evaluate`/`remediate`/`rollback` tabs; diff mode for LLM-generated vs. edited comparison

### Step 5: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260504-project-aegis-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to:
   - .copilot-tracking/plans/20260504-project-aegis-plan.instructions.md
   - .copilot-tracking/details/20260504-project-aegis-details.md
   - .copilot-tracking/research/20260504-project-aegis-research.md

   You WILL recommend cleaning these files up after the implementation is complete.

3. **MANDATORY**: You WILL attempt to delete `.copilot-tracking/prompts/implement-project-aegis.prompt.md`

## Success Criteria

- [ ] Changes tracking file created at `.copilot-tracking/changes/20260504-project-aegis-changes.md`
- [ ] All 29 plan tasks implemented with working code
- [ ] All detailed specifications from details file satisfied
- [ ] Docker Compose starts cleanly: `docker compose up -d` brings all services healthy
- [ ] `uvicorn aegis.main:app --reload` starts without import errors; `/docs` returns Swagger UI
- [ ] `alembic upgrade head` creates all 12 database tables
- [ ] `npm run dev` starts Vite dev server without TypeScript errors
- [ ] Policy upload → LLM code generation → HITL approval workflow end-to-end functional
- [ ] Evaluate/remediate/rollback enforcement operations execute via Celery tasks with WebSocket progress
- [ ] OpenSCAP ARF XML report generated and downloadable
- [ ] RBAC enforced on all protected endpoints
