<!-- markdownlint-disable-file -->

# Changes: Project Aegis - AI Agentic Security Hardening Solution

## Added

### Phase 1 — Scaffold & Infrastructure
- `docker-compose.yml` — Full production stack: postgres, redis, etcd, minio, milvus, ollama, aegis-api, aegis-worker, aegis-ui
- `docker-compose.dev.yml` — Dev overrides with hot-reload volumes
- `.env.example` — Template for all environment variables
- `backend/Dockerfile` — Python 3.12-slim with lxml/paramiko/openssh deps
- `frontend/Dockerfile` — Node 20 builder + nginx:alpine production image
- `frontend/nginx.conf` — Nginx proxy config with WebSocket upgrade support
- All `__init__.py` package markers for backend subpackages

### Phase 2 — Backend Foundation
- `backend/aegis/__init__.py` — Version string `0.1.0`
- `backend/aegis/config.py` — Pydantic BaseSettings with all env vars
- `backend/aegis/database.py` — Async SQLAlchemy engine + session factory
- `backend/aegis/worker.py` — Celery application definition
- `backend/aegis/main.py` — FastAPI app with lifespan, CORS, all routers registered
- `backend/requirements.txt` — All Python deps pinned
- `backend/alembic.ini` — Alembic config
- `backend/migrations/env.py` — Async Alembic env with asyncpg
- `backend/migrations/script.py.mako` — Migration template
- `backend/migrations/versions/001_initial_schema.py` — Initial migration creating all 12 tables
- `backend/aegis/models/user.py` — User ORM model
- `backend/aegis/models/workspace.py` — Workspace + WorkspaceMember ORM models
- `backend/aegis/models/policy.py` — Policy + PolicyRule ORM models
- `backend/aegis/models/solution_type.py` — SolutionType ORM model
- `backend/aegis/models/hardening_profile.py` — HardeningProfile + ProfileRule + HITLComment ORM models
- `backend/aegis/models/solution_instance.py` — SolutionInstance ORM model
- `backend/aegis/models/enforcement_job.py` — EnforcementJob ORM model
- `backend/aegis/models/compliance_report.py` — ComplianceReport ORM model
- `backend/aegis/models/__init__.py` — Imports all models for Alembic
- `backend/aegis/schemas/auth.py` — LoginRequest, TokenResponse, TokenPayload
- `backend/aegis/schemas/user.py` — UserCreate, UserResponse, UserRoleUpdate
- `backend/aegis/schemas/workspace.py` — WorkspaceCreate, WorkspaceResponse, WorkspaceMemberAdd
- `backend/aegis/schemas/policy.py` — PolicyResponse, PolicyRuleResponse, PolicyImportRequest
- `backend/aegis/schemas/solution_type.py` — SolutionTypeCreate, SolutionTypeResponse, ComponentSelectionUpdate, ComponentTreeNode
- `backend/aegis/schemas/profile.py` — HardeningProfileCreate/Response, ProfileRuleResponse, ProfileRuleCodeUpdate, HITLCommentCreate/Response, CodeGenRequest
- `backend/aegis/schemas/instance.py` — SolutionInstanceCreate/Response, EnforcementJobResponse, ComplianceReportResponse, DryRunReport, ImpactAssessmentReport, EnforcementRequest
- `backend/aegis/services/rbac.py` — JWT auth, RBAC dependencies, workspace access checks, WebSocket token validation

### Phase 3 — Policy Parsers
- `backend/aegis/services/policy_parser/base.py` — PolicyRuleData dataclass + PolicyParseError
- `backend/aegis/services/policy_parser/oval_parser.py` — OVAL 5.x XML parser using lxml
- `backend/aegis/services/policy_parser/xccdf_parser.py` — XCCDF 1.2 XML parser using lxml
- `backend/aegis/services/policy_parser/text_parser.py` — LLM-assisted English text policy parser

### Phase 4 — LLM & Vector Store
- `backend/aegis/services/llm/client.py` — AegisLLMClient using openai AsyncOpenAI → Ollama; embed via httpx
- `backend/aegis/services/llm/milvus_store.py` — MilvusRuleStore for policy rule embeddings with IVF_FLAT index
- `backend/aegis/services/llm/prompts.py` — Prompt templates for evaluate/remediate/rollback code generation
- `backend/aegis/services/llm/code_generator.py` — CodeGenerator with few-shot RAG from Milvus + streaming support
- `backend/aegis/tasks/codegen_tasks.py` — Celery `generate_profile_codes` task with Redis pub/sub progress events

### Phase 5 — Connector Library
- `backend/aegis/services/connectors/base.py` — BaseConnector ABC + ConnectorResult dataclass
- `backend/aegis/services/connectors/ssh_connector.py` — Paramiko SSH connector with SFTP support
- `backend/aegis/services/connectors/redfish_connector.py` — HPE iLO/BIOS Redfish connector
- `backend/aegis/services/connectors/netmiko_connector.py` — Aruba AOS-CX/AOS-S Netmiko connector
- `backend/aegis/services/connectors/kubernetes_connector.py` — K8s connector (in-cluster + kubeconfig)
- `backend/aegis/services/connectors/vault_connector.py` — HashiCorp Vault connector with vault:// ref resolution
- `backend/aegis/services/connectors/factory.py` — ConnectorFactory dispatching by component_type

### Phase 6 — Enforcement Engine
- `backend/aegis/services/enforcement/evaluator.py` — Evaluator: runs eval code in sandboxed exec()
- `backend/aegis/services/enforcement/remediator.py` — Remediator: runs remediation code + persists saved_state
- `backend/aegis/services/enforcement/rollback.py` — RollbackEngine: restores saved_state via rollback code
- `backend/aegis/services/enforcement/impact_assessor.py` — ImpactAssessor using NetworkX DiGraph for TLS/cipher risk
- `backend/aegis/services/enforcement/dry_run.py` — DryRunEngine: composite risk scoring (none/low/medium/high/critical)
- `backend/aegis/tasks/enforcement_tasks.py` — Celery tasks for evaluate/remediate/rollback/dry-run with Redis pub/sub

### Phase 7 — Reporting
- `backend/aegis/services/reporting/arf_generator.py` — OpenSCAP ARF 1.1 XML report generator using lxml
- `backend/aegis/services/reporting/html_report.py` — HTML compliance report with RED/Orange/Green scoring

### Phase 8 — REST API Layer
- `backend/aegis/api/v1/auth.py` — POST /auth/login, POST /auth/register
- `backend/aegis/api/v1/users.py` — GET /users/me, GET /users, PATCH /users/{id}/role, DELETE /users/{id}
- `backend/aegis/api/v1/workspaces.py` — CRUD workspaces + member management
- `backend/aegis/api/v1/policies.py` — Policy upload (OVAL/XCCDF/text), list, rules, delete
- `backend/aegis/api/v1/solution_types.py` — CRUD solution types + component selection update
- `backend/aegis/api/v1/profiles.py` — Profile CRUD, rule code update, approve/reject, HITL comments, code gen trigger
- `backend/aegis/api/v1/instances.py` — Instance CRUD + evaluate/remediate/rollback/dry-run enforcement endpoints
- `backend/aegis/api/v1/websockets.py` — WebSocket handlers for codegen and enforcement real-time progress

### Phase 9 — React Frontend
- `frontend/package.json` — React 18 + TS + Vite + Monaco + Recharts + ReactFlow + TanStack Query
- `frontend/vite.config.ts` — Vite config with API + WebSocket proxy
- `frontend/tsconfig.json` + `frontend/tsconfig.node.json` — TypeScript config (strict mode)
- `frontend/tailwind.config.js` + `frontend/postcss.config.js` — Tailwind CSS setup
- `frontend/index.html` — HTML entry point
- `frontend/src/index.css` — Tailwind base styles
- `frontend/src/main.tsx` — React entry + QueryClientProvider
- `frontend/src/types/index.ts` — Full TypeScript interfaces for all entities (zero `any`)
- `frontend/src/api/client.ts` — Axios client with JWT interceptors
- `frontend/src/api/endpoints.ts` — All API call functions typed against entity interfaces
- `frontend/src/context/AuthContext.tsx` — JWT auth context + useAuth hook
- `frontend/src/App.tsx` — React Router v6 routes with ProtectedRoute
- `frontend/src/components/Layout.tsx` — App shell with nav, user info, logout
- `frontend/src/pages/LoginPage.tsx` — Login form
- `frontend/src/pages/DashboardPage.tsx` — Compliance dashboard with Recharts PieChart
- `frontend/src/pages/PolicyManagerPage.tsx` — Policy upload + rule browse table
- `frontend/src/pages/SolutionTypeBuilderPage.tsx` — Component selection grid
- `frontend/src/pages/HardeningProfileEditorPage.tsx` — Monaco Editor HITL + WebSocket streaming
- `frontend/src/pages/InstanceManagerPage.tsx` — Instance CRUD
- `frontend/src/pages/EnforcementConsolePage.tsx` — Enforcement actions + WebSocket log + job history
- `frontend/src/pages/UserManagementPage.tsx` — User role management (admin only)

## Modified

- `.copilot-tracking/plans/20260504-project-aegis-plan.instructions.md` — Marked all 29 tasks [x] completed

## Removed

(none)
