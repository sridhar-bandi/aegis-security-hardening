<!-- markdownlint-disable-file -->

# Task Details: Project Aegis - AI Agentic Security Hardening Solution

## Research Reference

**Source Research**: #file:../research/20260504-project-aegis-research.md

---

## Phase 1: Project Scaffold & Infrastructure

### Task 1.1: Create Monorepo Directory Structure

Create the full project directory skeleton for the monorepo: `backend/aegis/` (FastAPI + Celery), `frontend/src/` (React + Vite + TypeScript), migrations, tests, and all subdirectories as defined in the research directory structure.

- **Files**:
  - `backend/aegis/__init__.py` — Package init
  - `backend/aegis/main.py` — FastAPI app entry point (placeholder)
  - `backend/aegis/config.py` — Pydantic BaseSettings placeholder
  - `backend/aegis/database.py` — SQLAlchemy async engine placeholder
  - `backend/aegis/worker.py` — Celery app definition placeholder
  - `backend/aegis/api/__init__.py`, `backend/aegis/api/v1/__init__.py` — API package inits
  - `backend/aegis/models/__init__.py` — Models package init
  - `backend/aegis/schemas/__init__.py` — Schemas package init
  - `backend/aegis/services/__init__.py` — Services package init
  - `backend/aegis/services/policy_parser/__init__.py` — Policy parser package init
  - `backend/aegis/services/llm/__init__.py` — LLM service package init
  - `backend/aegis/services/connectors/__init__.py` — Connectors package init
  - `backend/aegis/services/enforcement/__init__.py` — Enforcement package init
  - `backend/aegis/services/reporting/__init__.py` — Reporting package init
  - `backend/aegis/tasks/__init__.py` — Tasks package init
  - `backend/migrations/` — Alembic migrations directory
  - `backend/tests/__init__.py` — Tests package init
  - `backend/requirements.txt` — All Python dependencies (exact versions from research)
  - `backend/Dockerfile` — Python 3.12 slim image with requirements install
  - `frontend/src/components/PolicyManager/.gitkeep`
  - `frontend/src/components/SolutionTypeBuilder/.gitkeep`
  - `frontend/src/components/HardeningProfileEditor/.gitkeep`
  - `frontend/src/components/InstanceManager/.gitkeep`
  - `frontend/src/components/ComplianceDashboard/.gitkeep`
  - `frontend/src/components/EnforcementConsole/.gitkeep`
  - `frontend/src/components/UserManagement/.gitkeep`
  - `frontend/src/pages/.gitkeep`
  - `frontend/src/services/.gitkeep`
  - `frontend/src/hooks/.gitkeep`
  - `frontend/src/types/.gitkeep`
  - `frontend/package.json` — All npm dependencies (exact versions from research)
  - `frontend/tsconfig.json` — TypeScript config targeting ES2020
  - `frontend/vite.config.ts` — Vite config with React plugin and API proxy
  - `frontend/tailwind.config.js` — Tailwind CSS configuration
  - `frontend/index.html` — Vite HTML entry point
  - `frontend/Dockerfile` — Node 20 slim + nginx for production build
  - `README.md` — Project overview and getting started guide
  - `.env.example` — All environment variables with placeholder values
- **Success**:
  - `tree backend/aegis` shows full directory hierarchy
  - `pip install -r backend/requirements.txt` completes without errors
  - All `__init__.py` files exist; Python can import `aegis` package
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 248-330) — Project directory structure
  - #file:../research/20260504-project-aegis-research.md (Lines 331-395) — Python and npm dependencies
- **Dependencies**:
  - None — this is the foundational task

### Task 1.2: Docker Compose Infrastructure

Create `docker-compose.yml` for all infrastructure services: PostgreSQL 16, Redis 7, etcd, MinIO, MilvusDB 2.4, Ollama, aegis-api, aegis-worker, aegis-ui. Create `docker-compose.dev.yml` for development overrides (hot-reload volumes).

- **Files**:
  - `docker-compose.yml` — Full production-ready compose file with all services, volumes, health checks, and environment variable references
  - `docker-compose.dev.yml` — Development overrides: volume mounts for hot-reload, debug ports
  - `.env.example` — Template with `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, `MINIO_USER`, `MINIO_PASSWORD`, `MILVUS_HOST`, `OLLAMA_BASE_URL`, `VITE_API_URL`
- **Success**:
  - `docker compose config` validates without errors
  - `docker compose up -d postgres redis` starts both containers successfully
  - PostgreSQL responds to `pg_isready` health check
  - Redis responds to `redis-cli ping`
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 332-395) — Docker Compose YAML with all services and volumes
- **Dependencies**:
  - Task 1.1 (Dockerfile files must exist for build context references)

---

## Phase 2: Backend Foundation

### Task 2.1: FastAPI Application Core

Implement the FastAPI application entry point, configuration management, and database connection pool. `config.py` reads all settings from environment variables using Pydantic BaseSettings. `database.py` creates the async SQLAlchemy engine and session factory. `main.py` creates the FastAPI app, registers all routers, configures CORS, and includes startup/shutdown lifespan events for DB and MilvusDB initialization.

- **Files**:
  - `backend/aegis/config.py` — Pydantic BaseSettings: `DATABASE_URL`, `REDIS_URL`, `MILVUS_HOST`, `MILVUS_PORT`, `OLLAMA_BASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALGORITHM="HS256"`, `CORS_ORIGINS`
  - `backend/aegis/database.py` — `create_async_engine`, `AsyncSessionLocal`, `Base = declarative_base()`, `get_db()` dependency
  - `backend/aegis/main.py` — FastAPI app with `lifespan` context manager; register routers under `/api/v1/`; CORS middleware with configurable origins; include WebSocket routes
- **Success**:
  - `uvicorn aegis.main:app --reload` starts without import errors
  - `GET /docs` returns Swagger UI
  - `GET /health` returns `{"status": "ok"}`
  - DB session dependency injected correctly in router tests
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 37-50) — FastAPI version and async patterns
  - #file:../research/20260504-project-aegis-research.md (Lines 248-265) — Directory structure for api/v1/ routers
- **Dependencies**:
  - Task 1.1 (project scaffold), Task 1.2 (PostgreSQL running for DB connection)

### Task 2.2: SQLAlchemy ORM Models

Implement all 11 SQLAlchemy async ORM models with proper relationships, foreign keys, and indexes. All models inherit from `Base` defined in `database.py`. Use UUID primary keys, `created_at`/`updated_at` timestamps.

- **Files**:
  - `backend/aegis/models/user.py` — `User`: id (UUID), email (unique), username, hashed_password, role (enum: admin/security_officer/auditor/user), is_active, created_at
  - `backend/aegis/models/workspace.py` — `Workspace`: id, name, description, owner_id (FK→User), created_at; `WorkspaceMember`: workspace_id + user_id + role (composite PK)
  - `backend/aegis/models/policy.py` — `Policy`: id, workspace_id (FK), name, description, standard (CIS/STIG/SRG/Custom), format (OVAL/XCCDF/text), file_path, created_by (FK→User), created_at
  - `backend/aegis/models/policy_rule.py` — `PolicyRule`: id, policy_id (FK), rule_id (external), title, description, rationale, severity (enum), category, target_component_types (JSON array), check_content, fix_text, milvus_embedding_id, created_at
  - `backend/aegis/models/solution_type.py` — `SolutionType`: id, workspace_id (FK), name, description, config_json (JSON), component_selection (JSON array of selected component_ids), created_by (FK→User), created_at
  - `backend/aegis/models/hardening_profile.py` — `HardeningProfile`: id, name, solution_type_id (FK), policy_id (FK), status (enum: draft/generating/ready), created_by (FK→User), created_at
  - `backend/aegis/models/profile_rule.py` — `ProfileRule`: id, profile_id (FK), policy_rule_id (FK), component_type, evaluation_code, remediation_code, rollback_code, code_status (enum: pending/generated/reviewed/approved/rejected), risk_score (float), saved_state (JSON), created_at, updated_at
  - `backend/aegis/models/hitl_comment.py` — `HITLComment`: id, profile_rule_id (FK), author_id (FK→User), comment_text, comment_type (enum: review/approval/rejection), created_at
  - `backend/aegis/models/solution_instance.py` — `SolutionInstance`: id, workspace_id (FK), name, solution_type_id (FK), profile_id (FK), config_json (JSON), owner_id (FK→User), created_at
  - `backend/aegis/models/enforcement_job.py` — `EnforcementJob`: id, instance_id (FK), job_type (enum: evaluate/remediate/rollback/dry_run/impact_assessment), status (enum: pending/running/completed/failed), celery_task_id, result_summary (JSON), created_by (FK→User), created_at, completed_at
  - `backend/aegis/models/compliance_report.py` — `ComplianceReport`: id, instance_id (FK), job_id (FK), report_type (enum: arf/html), file_path, summary (JSON: total_rules, passed, failed, error), created_at
  - `backend/aegis/models/__init__.py` — Import all models for Alembic auto-detection
- **Success**:
  - All 11 model files import without errors
  - `Base.metadata.tables` contains all table names
  - SQLAlchemy relationships (one-to-many, many-to-many) resolve without circular import errors
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 82-116) — PolicyRule data model with all fields
  - #file:../research/20260504-project-aegis-research.md (Lines 248-265) — models/ directory listing
- **Dependencies**:
  - Task 2.1 (database.py Base and async engine)

### Task 2.3: Alembic Migrations

Initialize Alembic and create the initial migration that creates all tables. Configure `alembic.ini` and `migrations/env.py` to use the async SQLAlchemy engine and `DATABASE_URL` from environment.

- **Files**:
  - `backend/alembic.ini` — Standard Alembic config pointing to `migrations/`
  - `backend/migrations/env.py` — Async Alembic env using `asyncpg`; import `Base` from `aegis.models`; use `DATABASE_URL` from `aegis.config.settings`
  - `backend/migrations/versions/001_initial_schema.py` — Auto-generated migration: creates all 11 tables with correct columns, FKs, indexes, and enums
- **Success**:
  - `alembic upgrade head` runs without errors against running PostgreSQL
  - `psql` confirms all tables exist: users, workspaces, workspace_members, policies, policy_rules, solution_types, hardening_profiles, profile_rules, hitl_comments, solution_instances, enforcement_jobs, compliance_reports
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 248-265) — migrations/ directory
- **Dependencies**:
  - Task 2.2 (all ORM models must exist for autogenerate)

### Task 2.4: Pydantic v2 Request/Response Schemas

Implement all Pydantic v2 schemas for request validation and response serialization. Schemas must not expose hashed_password or internal fields. Use `model_config = ConfigDict(from_attributes=True)` for ORM mode.

- **Files**:
  - `backend/aegis/schemas/auth.py` — `LoginRequest`, `TokenResponse`, `TokenPayload`
  - `backend/aegis/schemas/user.py` — `UserCreate`, `UserResponse`, `UserRoleUpdate`
  - `backend/aegis/schemas/workspace.py` — `WorkspaceCreate`, `WorkspaceResponse`, `WorkspaceMemberAdd`
  - `backend/aegis/schemas/policy.py` — `PolicyResponse`, `PolicyRuleResponse`, `PolicyImportRequest` (GitHub/SharePoint/Confluence)
  - `backend/aegis/schemas/solution_type.py` — `SolutionTypeCreate`, `SolutionTypeResponse`, `ComponentSelectionUpdate`, `ComponentTreeNode` (recursive for hierarchy)
  - `backend/aegis/schemas/profile.py` — `HardeningProfileCreate`, `HardeningProfileResponse`, `ProfileRuleResponse`, `ProfileRuleCodeUpdate`, `HITLCommentCreate`, `CodeGenRequest`
  - `backend/aegis/schemas/instance.py` — `SolutionInstanceCreate`, `SolutionInstanceResponse`, `EnforcementJobResponse`, `ComplianceReportResponse`, `DryRunReport`, `ImpactAssessmentReport`, `EnforcementRequest`
- **Success**:
  - All schemas import without errors
  - Pydantic validation catches missing required fields and wrong types
  - `UserResponse` does not include `hashed_password`
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 118-175) — REST API endpoint signatures (inform response shapes)
  - #file:../research/20260504-project-aegis-research.md (Lines 82-116) — PolicyRule and Solution Instance JSON schemas
- **Dependencies**:
  - Task 2.2 (schemas reference ORM model field names)

### Task 2.5: JWT Authentication & RBAC Middleware

Implement JWT-based authentication with bcrypt password hashing, token creation/validation, and a FastAPI dependency `require_role(*roles)` that enforces RBAC on all protected endpoints. Implement workspace membership scope checks.

- **Files**:
  - `backend/aegis/services/rbac.py` — `create_access_token()`, `decode_token()`, `get_current_user()` dependency, `require_role(*roles)` factory dependency, `check_workspace_access()` for instance scope enforcement
- **Success**:
  - `POST /api/v1/auth/login` with valid credentials returns JWT access token
  - Protected endpoint with `Depends(require_role("admin"))` returns 403 for non-admin token
  - Expired token returns 401
  - Workspace member check blocks non-member access to instances
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 178-215) — RBAC role matrix defining which roles access which operations
- **Dependencies**:
  - Task 2.1 (database session), Task 2.2 (User model), Task 2.4 (token schemas)

---

## Phase 3: Policy Parsing Service

### Task 3.1: OVAL XML Parser

Implement `oval_parser.py` to parse OVAL 5.x XML files using `lxml`. Extract definition elements: `@id`, `<title>`, `<description>`, `<affected>`, `<criteria>`, `<tests>`. Map to normalized `PolicyRule` objects. Handle both standalone OVAL files and OVAL embedded in XCCDF data streams.

- **Files**:
  - `backend/aegis/services/policy_parser/oval_parser.py` — `OVALParser` class with `parse(file_path: str) -> List[PolicyRuleData]`; uses lxml XPath with OVAL 5 namespace `{http://oval.mitre.org/XMLSchema/oval-definitions-5}`; extracts id, title, description, check_content (from criteria/test refs), severity from class attribute; maps `vulnerability→critical`, `patch→high`, `compliance→medium`
- **Success**:
  - Parse a sample CIS RHEL9 OVAL file → returns list of `PolicyRuleData` with correct `rule_id`, `title`, `severity`, `check_content`
  - Handles malformed XML with `lxml.etree.XMLSyntaxError` caught and re-raised as `PolicyParseError`
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 57-65) — OVAL/XCCDF formats and CIS Benchmark bundle structure
  - #file:../research/20260504-project-aegis-research.md (Lines 216-225) — Security standards table (OVAL for CIS + STIG)
- **Dependencies**:
  - Task 1.1 (requirements.txt includes lxml==5.2.2)

### Task 3.2: XCCDF XML Parser

Implement `xccdf_parser.py` to parse XCCDF 1.2 XML files (both standalone benchmarks and data stream collections). Extract `<Rule>` elements: id, title, description, rationale, severity, `<check>`, `<fixtext>`. Also extract `<Profile>` elements for CIS Level 1/Level 2 profile mapping.

- **Files**:
  - `backend/aegis/services/policy_parser/xccdf_parser.py` — `XCCDFParser` class with `parse(file_path: str) -> List[PolicyRuleData]` and `get_profiles(file_path: str) -> List[ProfileInfo]`; XCCDF 1.2 namespace `{http://checklists.nist.gov/xccdf/1.2}`; extracts all `<Rule>` elements with selected=True; maps severity: `high→high`, `medium→medium`, `low→low`; extracts `<fix>` or `<fixtext>` as fix_text; extracts `<check-content>` or OVAL reference as check_content
- **Success**:
  - Parse a DISA STIG XCCDF bundle → returns all rules with correct severity mapping
  - Parse a CIS Benchmark with profiles → `get_profiles()` returns Level 1 and Level 2 profile names with rule selections
  - Handles XCCDF data stream (DS) files by locating the `<Benchmark>` component inside the data stream
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 57-65) — CIS XCCDF + OVAL bundle structure and DISA STIG format
  - #file:../research/20260504-project-aegis-research.md (Lines 216-225) — Standards supported table
- **Dependencies**:
  - Task 3.1 (shares lxml patterns; OVAL parser may be called for embedded OVAL)

### Task 3.3: English/Text Policy Parser (LLM-Assisted)

Implement `text_parser.py` to convert plain English text or JSON-structured policy rules into normalized `PolicyRuleData` objects using the LLM. Prompt the LLM to extract: rule_id, title, description, rationale, severity, check_content, fix_text, target_component_types.

- **Files**:
  - `backend/aegis/services/policy_parser/text_parser.py` — `TextPolicyParser` class with `parse(text: str) -> List[PolicyRuleData]`; sends structured extraction prompt to Ollama client; parses JSON response from LLM; validates required fields; assigns generated rule_ids if not present (format: `CUSTOM-{hash}`)
- **Success**:
  - Given a paragraph describing a TLS hardening requirement → returns `PolicyRuleData` with severity "high", fix_text, and target_component_types inferred from text
  - Invalid LLM JSON response handled gracefully with retry (max 2 retries)
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 216-225) — Text/English policy format
  - #file:../research/20260504-project-aegis-research.md (Lines 230-250) — LLM code generation pipeline (same Ollama client)
- **Dependencies**:
  - Task 4.1 (LLM client must exist before text parser can call it)

---

## Phase 4: LLM & Vector Store Service

### Task 4.1: Ollama LLM Client

Implement the Ollama LLM client using the `openai` Python SDK (OpenAI-compatible API) pointing to `OLLAMA_BASE_URL`. Wrap with LangChain for prompt template management and chain construction. Support both standard completion and streaming (for WebSocket token delivery).

- **Files**:
  - `backend/aegis/services/llm/client.py` — `AegisLLMClient` class: `__init__` creates `openai.AsyncOpenAI(base_url=settings.OLLAMA_BASE_URL+"/v1", api_key="ollama")`; `generate(prompt, stream=False) -> str`; `stream_generate(prompt) -> AsyncIterator[str]` for WebSocket streaming; configurable `model` (default: `codellama:34b`), `temperature=0.1` for deterministic code gen, `max_tokens=4096`
- **Success**:
  - `await client.generate("Write a Python hello world")` returns a valid Python string
  - `stream_generate()` yields tokens incrementally
  - Connection failure raises `LLMConnectionError` with clear message
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 43-50) — Ollama OpenAI-compatible API at `/v1`; CodeLlama 34B recommendation
- **Dependencies**:
  - Task 2.1 (config.py provides `OLLAMA_BASE_URL`)

### Task 4.2: MilvusDB Vector Store

Implement `milvus_store.py` to manage the MilvusDB collection for policy rule embeddings. On startup: connect to MilvusDB, create collection `policy_rules` if not exists (schema: `rule_id` varchar, `policy_id` varchar, `embedding` float vector dim=768, `metadata` varchar JSON). Implement `embed_rule()`, `search_similar_rules()`, `upsert_rule()`.

- **Files**:
  - `backend/aegis/services/llm/milvus_store.py` — `MilvusRuleStore` class: `connect()` using `pymilvus.connections.connect(host=settings.MILVUS_HOST)`; `create_collection()` with schema; `embed_text(text: str) -> List[float]` using Ollama embedding endpoint (`/api/embeddings`, model: `nomic-embed-text`); `upsert_rule(rule_id, policy_id, text, metadata)` embeds and inserts; `search_similar(query_text: str, top_k=5) -> List[SimilarRule]` returns top-K rules with their stored code as few-shot examples
- **Success**:
  - `store.upsert_rule(...)` inserts without error; `search_similar("disable telnet")` returns ≥1 result
  - Collection exists in MilvusDB after `connect()` is called
  - Embedding dimension matches collection schema (768 for nomic-embed-text)
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 43-50) — MilvusDB 2.4 pymilvus SDK; collection schema; cosine similarity
- **Dependencies**:
  - Task 4.1 (uses Ollama embedding endpoint via same base URL)

### Task 4.3: LLM Code Generator & Prompt Templates

Implement `code_generator.py` as the orchestration layer for LLM-driven rule code generation. For each `(policy_rule, component_type)` pair: retrieve similar rules from MilvusDB, build the structured prompt, call LLM, validate generated Python via `ast.parse()`, and return the three functions. Implement `prompts.py` with component-type-specific prompt templates.

- **Files**:
  - `backend/aegis/services/llm/prompts.py` — `RULE_CODE_GEN_PROMPT` template (as defined in research); component-type-specific system prompts for SSH (Paramiko), Redfish (iLO/BIOS), Netmiko (Aruba), Kubernetes, REST; `build_prompt(rule, component_type, protocol, retrieved_context) -> str`
  - `backend/aegis/services/llm/code_generator.py` — `CodeGenerator` class: `generate_rule_code(profile_rule_id, rule, component_type) -> GeneratedCode`; calls `MilvusRuleStore.search_similar()`; builds prompt via `prompts.build_prompt()`; calls `LLMClient.generate()`; validates with `ast.parse()`; on syntax error: retry once with error feedback in prompt; extracts the three function bodies from LLM response using regex; returns `GeneratedCode(evaluate_code, remediate_code, rollback_code)`
- **Success**:
  - Given a TLS version rule for a VM-RHEL9 target → returns valid Python with `evaluate()`, `remediate()`, `rollback()` functions
  - `ast.parse()` succeeds on all three generated functions
  - On LLM returning invalid Python: retries once with syntax error appended to prompt
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 141-175) — Full LLM code generation prompt pattern with exact signatures
  - #file:../research/20260504-project-aegis-research.md (Lines 230-250) — LLM pipeline flow (retrieve → prompt → generate → validate → store)
- **Dependencies**:
  - Task 4.1 (LLM client), Task 4.2 (MilvusDB store for retrieval)

### Task 4.4: Celery Code Generation Tasks

Implement Celery tasks for async LLM code generation. The main task `generate_profile_codes` iterates all `pending` ProfileRules in a HardeningProfile and generates code for each one, publishing progress events to Redis pub/sub for WebSocket consumption.

- **Files**:
  - `backend/aegis/tasks/codegen_tasks.py` — `generate_profile_codes(profile_id: str)` Celery task: loads all ProfileRules with status "pending"; for each rule calls `CodeGenerator.generate_rule_code()`; updates ProfileRule in DB with generated code and status "generated"; publishes `{"type":"progress","rule_id":..., "status":"generated"}` to Redis channel `profile:{profile_id}:codegen`; on completion publishes `{"type":"complete"}`
- **Success**:
  - `generate_profile_codes.delay(profile_id)` enqueues task; Celery worker processes it
  - All ProfileRules in profile have status updated to "generated" after task completes
  - Redis pub/sub channel receives progress events per rule
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 51-56) — Celery task chaining and Redis broker
- **Dependencies**:
  - Task 4.3 (CodeGenerator), Task 2.2 (ProfileRule model), Task 2.1 (worker.py Celery app)

---

## Phase 5: Connector Library

### Task 5.1: BaseConnector Abstract Class & Result Types

Implement the abstract `BaseConnector` interface and all result dataclasses (`ComplianceResult`, `RemediationResult`, `RollbackResult`, `CommandResult`). This forms the typed contract that all generated `evaluate()`/`remediate()`/`rollback()` functions depend on.

- **Files**:
  - `backend/aegis/services/connectors/base.py` — `BaseConnector` ABC (as defined in research) with `connect()`, `disconnect()`, `execute()`, `get_config()`, `set_config()`, `__enter__`/`__exit__`; `CommandResult` dataclass; `ComplianceResult` dataclass: `status: Literal["pass","fail","error"]`, `evidence: str`, `component_id: str`, `rule_id: str`; `RemediationResult` dataclass: `success: bool`, `saved_state: dict`, `message: str`; `RollbackResult` dataclass: `success: bool`, `message: str`; `ConnectorFactory.get_connector(component_config: dict) -> BaseConnector` dispatcher by `protocol` field
- **Success**:
  - All dataclasses instantiate correctly
  - `ConnectorFactory.get_connector({"protocol":"SSH",...})` returns `SSHConnector` instance
  - Abstract methods raise `NotImplementedError` if not implemented
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 168-205) — BaseConnector abstract class definition and all connector types table
- **Dependencies**:
  - Task 1.1 (packages installed)

### Task 5.2: SSH & Redfish Connectors

Implement `SSHConnector` (Paramiko) for Linux VMs/servers and `RedfishConnector` (requests) for HPE iLO BMC, BIOS, and SRController.

- **Files**:
  - `backend/aegis/services/connectors/ssh_connector.py` — `SSHConnector(BaseConnector)`: `connect()` creates `paramiko.SSHClient()` with `AutoAddPolicy`, supports key-based and password auth from `component_config.auth`; `execute(command)` runs `exec_command()` with 30s timeout; `get_config(path)` reads remote file via SFTP; `set_config(path, content)` writes remote file via SFTP; `disconnect()` closes client
  - `backend/aegis/services/connectors/redfish_connector.py` — `RedfishConnector(BaseConnector)`: `connect()` creates `requests.Session` with basic auth and `verify=False` (for self-signed iLO certs); `execute(command)` not applicable → raises `NotImplementedError`; `get_config(path)` does `GET {base_url}{path}` Redfish URI; `set_config(path, value)` does `PATCH {base_url}{path}` with JSON body; `get_redfish_resource(uri)` and `patch_redfish_resource(uri, payload)` as convenience methods
- **Success**:
  - `SSHConnector` with mock SSH server: `execute("whoami")` returns `CommandResult(stdout="root", exit_code=0)`
  - `RedfishConnector.get_config("/redfish/v1/Systems/1")` returns JSON dict from mock Redfish endpoint
  - `with SSHConnector(config) as conn:` properly calls `connect()` and `disconnect()`
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 197-215) — Connector implementations table with libraries and auth types
- **Dependencies**:
  - Task 5.1 (BaseConnector abstract class)

### Task 5.3: Network, Kubernetes, Vault & REST Connectors

Implement remaining connectors: `NetmikoConnector` (Aruba/Juniper switches), `KubernetesConnector` (k8s API), `VaultConnector` (credential retrieval), `RESTConnector` (generic HTTPS for Alletra, StepCA, Morpheus).

- **Files**:
  - `backend/aegis/services/connectors/netmiko_connector.py` — `NetmikoConnector(BaseConnector)`: uses `netmiko.ConnectHandler` with `device_type` mapped from `component_config.component_type` (e.g., `aruba_osapi` for AOS-CX); `execute(command)` sends command and returns output; `get_config("running")` retrieves running config; `set_config(path, commands)` sends config commands list
  - `backend/aegis/services/connectors/kubernetes_connector.py` — `KubernetesConnector(BaseConnector)`: loads kubeconfig from `component_config.auth.kubeconfig_ref` (retrieved via VaultConnector); creates `kubernetes.client.CoreV1Api`, `RbacAuthorizationV1Api`, `PolicyV1Api`; `get_config(resource_type)` queries k8s API; `set_config(resource_type, manifest)` applies manifest via `kubernetes.utils.create_from_dict()`
  - `backend/aegis/services/connectors/vault_connector.py` — `VaultConnector`: not a `BaseConnector` subclass but a helper; `get_secret(vault_path: str) -> str` authenticates via AppRole and retrieves secret; called by `ConnectorFactory` to resolve `vault://` credential refs before creating target connectors
  - `backend/aegis/services/connectors/rest_connector.py` — `RESTConnector(BaseConnector)`: generic HTTPS REST connector; `connect()` creates `requests.Session` with token/bearer auth from config; `get_config(path)` → `GET {base_url}{path}`; `set_config(path, value)` → `PATCH/PUT {base_url}{path}`; `execute(command)` → POST to action endpoint; supports Alletra, StepCA, Morpheus, and any HTTPS REST endpoint
- **Success**:
  - `ConnectorFactory.get_connector({"protocol":"SSH",...})` dispatches to `SSHConnector`
  - `ConnectorFactory.get_connector({"protocol":"HTTPS-Redfish",...})` dispatches to `RedfishConnector`
  - `ConnectorFactory.get_connector({"protocol":"netmiko-aruba",...})` dispatches to `NetmikoConnector`
  - `VaultConnector.get_secret("vault://secret/ilo-000-pass")` returns credential string
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 197-215) — Full connector table with protocols and libraries
- **Dependencies**:
  - Task 5.1, Task 5.2 (base patterns established)

---

## Phase 6: Enforcement Engine

### Task 6.1: Evaluator Service

Implement `evaluator.py` to orchestrate evaluation of a HardeningProfile against a SolutionInstance. For each selected component in the instance config, find matching ProfileRules by component_type, dynamically execute the `evaluate()` function using the appropriate connector, and collect `ComplianceResult` objects.

- **Files**:
  - `backend/aegis/services/enforcement/evaluator.py` — `Evaluator` class: `run_evaluation(instance_id: str, profile_id: str, rule_ids: List[str] = None) -> List[ComplianceResult]`; loads SolutionInstance config JSON; for each component: creates connector via `ConnectorFactory`; finds all applicable ProfileRules by component_type; for each rule: dynamically loads and executes `evaluate(connection)` function using `exec()` in sandboxed namespace with `BaseConnector` and result types imported; catches all exceptions and returns `ComplianceResult(status="error")`; publishes per-component progress to Redis pub/sub
- **Success**:
  - Given a mock SSHConnector, `evaluator.run_evaluation()` returns `ComplianceResult` list with status for each rule × component
  - Exception in a single rule does not abort the entire evaluation
  - Progress events published to Redis channel during evaluation
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 230-250) — Enforcement stage: evaluation is read-only; runs evaluate() functions per component
- **Dependencies**:
  - Task 5.1-5.3 (ConnectorFactory), Task 2.2 (ProfileRule and SolutionInstance models)

### Task 6.2: Remediator Service

Implement `remediator.py` to execute remediation. Before execution, MUST capture pre-state by running `remediate()` with state capture and saving `saved_state` to `ProfileRule.saved_state` in the DB. Supports partial remediation (subset of rules).

- **Files**:
  - `backend/aegis/services/enforcement/remediator.py` — `Remediator` class: `run_remediation(instance_id, profile_id, rule_ids=None) -> List[RemediationResult]`; only executes ProfileRules with status "approved"; creates connector; executes `remediate(connection)` function dynamically; saves `result.saved_state` to `ProfileRule.saved_state` in DB; records `RemediationResult` per rule; publishes progress to Redis pub/sub; if `RemediationResult.success is False`, logs error and continues (does not abort batch)
- **Success**:
  - `saved_state` persisted to DB after `remediate()` executes
  - Failed rule remediation logged but remaining rules continue
  - Only "approved" ProfileRules are eligible for remediation
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 252-258) — Remediation must capture pre-state; rollback depends on saved_state
- **Dependencies**:
  - Task 6.1 (same orchestration pattern), Task 5.1-5.3 (connectors)

### Task 6.3: Rollback Service

Implement `rollback.py` to restore pre-remediation state. Loads `saved_state` from `ProfileRule.saved_state` in DB and passes it to the dynamically executed `rollback(connection, saved_state)` function.

- **Files**:
  - `backend/aegis/services/enforcement/rollback.py` — `RollbackEngine` class: `run_rollback(instance_id, profile_id, rule_ids=None) -> List[RollbackResult]`; for each rule: loads `saved_state` from DB; creates connector; executes `rollback(connection, saved_state)` dynamically; if `saved_state` is None/empty, skips rule and logs "no remediation state found — rollback skipped"; publishes progress to Redis
- **Success**:
  - Rule with valid `saved_state` in DB → `rollback()` executes successfully
  - Rule with no `saved_state` → skipped gracefully with log message, not an error
  - After successful rollback, `ProfileRule.saved_state` is cleared (set to None)
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 252-258) — Rollback must use saved_state from remediate()
- **Dependencies**:
  - Task 6.2 (saved_state must be stored by Remediator first)

### Task 6.4: Impact Assessment Service

Implement `impact_assessment.py` using NetworkX to build a directed service communication graph from the `network_topology.communication_channels` section of the instance config JSON. Generate a table of all service communication channels with protocol, TLS version, cipher suite, and port data.

- **Files**:
  - `backend/aegis/services/enforcement/impact_assessment.py` — `ImpactAssessor` class: `build_topology_graph(instance_config: dict) -> nx.DiGraph`; adds nodes for each service/component; adds edges for each channel with attributes: `protocol`, `tls_versions`, `cipher_suites`, `port`; `assess(instance_id: str) -> ImpactAssessmentReport`; loads instance config from DB; builds graph; generates `communication_channels` table: `[{source, target, protocol, tls_versions, cipher_suites, port, risk_score}]`; stores result in DB via `EnforcementJob.result_summary`
- **Success**:
  - Given instance config with 3 communication channels → returns `ImpactAssessmentReport.communication_channels` with 3 entries
  - NetworkX graph has correct node and edge count
  - Report persisted to `EnforcementJob.result_summary`
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 254-272) — NetworkX impact assessment code pattern and ServiceCommunicationChannel model
- **Dependencies**:
  - Task 2.2 (SolutionInstance, EnforcementJob models)

### Task 6.5: Remediation Dry-Run Engine

Implement `dry_run.py` using the impact assessment graph plus per-rule `risk_score` and `affected_protocols` metadata to detect breaking changes before actual remediation.

- **Files**:
  - `backend/aegis/services/enforcement/dry_run.py` — `DryRunEngine` class: `run_dry_run(instance_id, profile_id, rule_ids=None) -> DryRunReport`; loads ImpactAssessmentReport (or runs impact assessment if not cached); for each ProfileRule in scope: retrieves `risk_score` and infers `affected_protocols` from LLM metadata or rule category; queries topology graph for channels using `affected_protocols`; checks compatibility: if rule disables TLS1.1 and a channel only supports TLS1.1 → `break_risk=critical`; aggregates into `DryRunReport.safe_rules[]`, `DryRunReport.risky_rules[]`, `DryRunReport.breaking_rules[]` with `{rule_id, risk_score, impacted_channels, break_risk, explanation}`
- **Success**:
  - Rule that disables TLS 1.1 + channel that only uses TLS 1.1 → appears in `breaking_rules` with `break_risk="critical"`
  - Rule with no matching channels → appears in `safe_rules`
  - Dry-run does NOT modify any target systems
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 272-292) — Dry-run algorithm step-by-step
- **Dependencies**:
  - Task 6.4 (ImpactAssessor for topology graph), Task 6.1 (same orchestration base)

### Task 6.6: Celery Enforcement Tasks

Wrap all enforcement operations as Celery tasks. Each task updates the `EnforcementJob` status in DB and publishes progress to Redis pub/sub.

- **Files**:
  - `backend/aegis/tasks/enforcement_tasks.py` — `run_evaluate_task(job_id, instance_id, profile_id, rule_ids)`, `run_remediate_task(job_id, ...)`, `run_rollback_task(job_id, ...)`, `run_dry_run_task(job_id, ...)`, `run_impact_assessment_task(job_id, ...)` Celery tasks; each: sets `EnforcementJob.status="running"`; calls corresponding service; saves result to `EnforcementJob.result_summary`; sets `EnforcementJob.status="completed"` or `"failed"`; publishes final event to Redis pub/sub channel `instance:{instance_id}:job:{job_id}`
- **Success**:
  - `run_evaluate_task.delay(...)` enqueues; Celery worker processes; EnforcementJob status transitions pending→running→completed
  - Redis channel receives `{"type":"complete","job_id":...}` on completion
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 51-56) — Celery task chaining and Redis pub/sub patterns
- **Dependencies**:
  - Tasks 6.1-6.5 (all enforcement services)

---

## Phase 7: Reporting

### Task 7.1: OpenSCAP ARF XML Report Generator

Implement `arf_generator.py` to produce OpenSCAP-compatible ARF (Assessment Results Format) XML from a list of `ComplianceResult` objects. ARF is the industry-standard format used by STIG Viewer and OpenSCAP tools.

- **Files**:
  - `backend/aegis/services/reporting/arf_generator.py` — `ARFGenerator` class: `generate(results: List[ComplianceResult], instance_id: str, profile_id: str) -> str` (returns ARF XML string); constructs `<arf:asset-report-collection>` with `<arf:reports>` containing `<xccdf:TestResult>` elements per component; each rule result as `<xccdf:rule-result idref="{rule_id}" result="{pass|fail|error}">` with `<xccdf:check-content-ref>`; saves XML to file in `reports/` directory; stores file path in `ComplianceReport` DB record; use `lxml.etree` to build the XML tree
- **Success**:
  - `arf_generator.generate(results, ...)` returns valid XML string
  - Output validates against XCCDF 1.2 namespace declarations
  - File saved to configured reports directory and path stored in DB
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 293-305) — OpenSCAP ARF format; `<arf:asset-report-collection>` structure
- **Dependencies**:
  - Task 6.1 (ComplianceResult objects produced by Evaluator), Task 2.2 (ComplianceReport model)

### Task 7.2: Compliance Summary & HTML Report Generator

Implement `html_generator.py` to produce an HTML compliance report and a JSON compliance summary (for the React dashboard). The summary includes per-component and aggregate counts: total_rules, passed, failed, error, pass_rate.

- **Files**:
  - `backend/aegis/services/reporting/html_generator.py` — `HTMLReportGenerator` class: `generate_summary(results: List[ComplianceResult]) -> ComplianceSummary`; groups results by component_id, severity, and rack; computes `{total, passed, failed, error, critical_failed, high_failed, medium_failed}` per group; `generate_html(results, instance_config) -> str` produces styled HTML with per-component tables using embedded CSS; saves to reports directory; `get_hierarchy_compliance(results, instance_config) -> HierarchyComplianceTree` returns nested dict matching rack→server→component structure with RED/Orange/Green status per node
- **Success**:
  - `generate_summary(results)` returns correct totals when given mix of pass/fail results
  - `get_hierarchy_compliance()` returns tree with correct hierarchy matching instance config rack structure
  - HTML output contains a table with all rule results
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 293-310) — Reporting scope: per-component, per-rack, per-instance, aggregate RED/Orange/Green
- **Dependencies**:
  - Task 7.1 (ComplianceResult types), Task 2.2 (ComplianceReport model)

---

## Phase 8: REST API Layer

### Task 8.1: Auth, Users & Workspaces Routers

Implement the FastAPI routers for authentication, user management, and workspace management. All endpoints use Pydantic schemas for validation. Protected endpoints use `require_role()` dependency.

- **Files**:
  - `backend/aegis/api/v1/auth.py` — `POST /api/v1/auth/login`: validates credentials, returns JWT; `POST /api/v1/auth/refresh`: refreshes token; `POST /api/v1/auth/logout`: blacklists token in Redis
  - `backend/aegis/api/v1/users.py` — Admin-only CRUD; `GET/POST /users`, `GET/PUT/DELETE /users/{id}`; `PUT /users/{id}/roles`
  - `backend/aegis/api/v1/workspaces.py` — `POST/GET /workspaces`; `GET/PUT/DELETE /workspaces/{id}`; `POST /workspaces/{id}/members`; `DELETE /workspaces/{id}/members/{user_id}`; workspace owner or Admin can manage members
- **Success**:
  - `POST /login` with correct credentials → 200 with `access_token`
  - `POST /login` with wrong password → 401
  - `GET /users` without admin token → 403
  - `POST /workspaces/{id}/members` by non-owner → 403
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 118-145) — Auth, Users, Workspaces endpoint definitions
  - #file:../research/20260504-project-aegis-research.md (Lines 178-215) — RBAC role matrix
- **Dependencies**:
  - Task 2.5 (JWT auth + RBAC), Task 2.4 (schemas), Task 2.2 (User, Workspace models)

### Task 8.2: Policies, Solution Types & Hardening Profiles Routers

Implement the core Development Stage API routers. Policy upload supports `multipart/form-data` with auto-detection of OVAL/XCCDF/text format. Profile generation triggers Celery `generate_profile_codes` task. HITL endpoints handle code edit, comment, approve, reject, and regenerate.

- **Files**:
  - `backend/aegis/api/v1/policies.py` — `POST /policies/upload`: accepts file, detects format (OVAL/XCCDF/text), calls parser, stores rules in DB, embeds in MilvusDB; `POST /policies/import/github`: fetches file from GitHub raw URL using token; `POST /policies/import/sharepoint` and `/confluence`: similar HTTP fetch with auth; `GET /policies`, `GET /policies/{id}`, `GET /policies/{id}/rules`, `DELETE /policies/{id}`
  - `backend/aegis/api/v1/solution_types.py` — `POST /solution-types`, `GET /solution-types`, `GET /solution-types/{id}`; `POST /solution-types/{id}/config`: parses uploaded JSON, stores config_json, returns component tree; `GET /solution-types/{id}/components`: returns hierarchical component tree from config_json; `PUT /solution-types/{id}/components/selection`: saves selected component_ids
  - `backend/aegis/api/v1/profiles.py` — `POST /profiles`: creates HardeningProfile record and generates ProfileRule stubs (one per rule × selected component_type); `GET /profiles`, `GET /profiles/{id}`; `POST /profiles/{id}/generate`: enqueues Celery `generate_profile_codes` task, returns job_id; `GET /profiles/{id}/rules`: paginated list of ProfileRules with code_status filter; `PUT /profiles/{id}/rules/{rule_id}/code`: HITL manual code edit, sets status="reviewed"; `POST /profiles/{id}/rules/{rule_id}/regenerate`: re-generates with additional context from latest HITL comment; `POST /profiles/{id}/rules/{rule_id}/approve/reject/comment`
- **Success**:
  - Upload CIS RHEL9 XCCDF file → rules stored in DB and MilvusDB within 5s
  - `POST /profiles/{id}/generate` → Celery task enqueued, returns `{"job_id":"...","status":"pending"}`
  - HITL approve endpoint sets ProfileRule.code_status to "approved"
  - Policy import from GitHub fetches and parses file correctly
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 118-175) — Full endpoint listing for policies, solution types, profiles
  - #file:../research/20260504-project-aegis-research.md (Lines 230-250) — LLM pipeline triggered by profile generate endpoint
- **Dependencies**:
  - Task 3.1-3.3 (policy parsers), Task 4.4 (codegen tasks), Task 8.1 (auth middleware)

### Task 8.3: Solution Instances & Enforcement Routers

Implement the Enforcement Stage API. All enforcement operations are async: create `EnforcementJob` in DB, enqueue Celery task, return `job_id`. Report download serves ARF XML and HTML files.

- **Files**:
  - `backend/aegis/api/v1/instances.py` — `POST/GET /instances`; `GET/DELETE /instances/{id}`; `POST /instances/{id}/config`: validates and stores instance config JSON; validates all `vault://` credential refs resolve; `POST /instances/{id}/evaluate`: creates EnforcementJob, enqueues `run_evaluate_task`, returns job_id; `POST /instances/{id}/remediate`: same pattern with `run_remediate_task`; `POST /instances/{id}/remediate/dry-run`: same with `run_dry_run_task`; `POST /instances/{id}/rollback`: same with `run_rollback_task`; `POST /instances/{id}/impact-assessment`: same with `run_impact_assessment_task`; `GET /instances/{id}/jobs`, `GET /instances/{id}/jobs/{job_id}`; `GET /instances/{id}/reports`, `GET /instances/{id}/reports/{report_id}`; `GET /instances/{id}/reports/{report_id}/download`: returns `FileResponse` with correct Content-Type (application/xml for ARF, text/html for HTML)
- **Success**:
  - `POST /instances/{id}/evaluate` → 202 response with `{"job_id":"...", "status":"pending"}`
  - `GET /instances/{id}/jobs/{job_id}` shows status transitions: pending→running→completed
  - `GET /instances/{id}/reports/{id}/download` returns ARF XML file with correct Content-Type
  - Non-member user gets 403 on all instance endpoints (workspace scope enforcement)
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 150-175) — Enforcement endpoint definitions and async job pattern
- **Dependencies**:
  - Task 6.6 (Celery enforcement tasks), Task 7.1-7.2 (report generators), Task 8.1 (auth)

### Task 8.4: WebSocket Handlers

Implement WebSocket endpoints for real-time streaming: LLM code generation progress (token streaming) and enforcement job progress (status events). Use Redis pub/sub as the message bus between Celery workers and WebSocket connections.

- **Files**:
  - `backend/aegis/api/v1/websockets.py` — `WS /ws/profiles/{profile_id}/generate`: authenticates via `token` query param; subscribes to Redis pub/sub channel `profile:{profile_id}:codegen`; forwards all messages to WebSocket client until `{"type":"complete"}` received; `WS /ws/instances/{instance_id}/jobs/{job_id}`: authenticates; subscribes to `instance:{instance_id}:job:{job_id}`; forwards progress events; closes on `{"type":"complete"}` or `{"type":"error"}`
- **Success**:
  - WebSocket connection to `/ws/profiles/{id}/generate` during active code generation receives per-rule progress events in real time
  - Connection with invalid/expired JWT token query param → 401 close
  - WebSocket closes cleanly after `{"type":"complete"}` event
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 175-180) — WebSocket endpoint definitions; streaming LLM + enforcement progress
- **Dependencies**:
  - Task 4.4, Task 6.6 (both publish to Redis); Task 2.5 (JWT auth for WS token validation)

---

## Phase 9: React Frontend

### Task 9.1: Frontend Project Setup

Initialize React 18 + Vite + TypeScript project with Tailwind CSS, React Router, React Query (TanStack v5), and all required dependencies from the research package.json. Configure Vite proxy for API calls during development.

- **Files**:
  - `frontend/package.json` — All dependencies from research including `@monaco-editor/react`, `reactflow`, `recharts`, `@radix-ui/react-dialog`, `lucide-react`, `axios`, `tailwindcss`
  - `frontend/vite.config.ts` — Vite config with React plugin; dev proxy: `/api` → `http://localhost:8000`, `/ws` → `ws://localhost:8000`
  - `frontend/tailwind.config.js` — Content paths for all `src/**/*.tsx` files
  - `frontend/src/main.tsx` — React root: `QueryClientProvider` wrapping `RouterProvider`
  - `frontend/src/App.tsx` — React Router routes: `/login`, `/dashboard`, `/policies`, `/solution-types`, `/profiles/:id`, `/instances`, `/instances/:id`, `/users`
  - `frontend/src/types/index.ts` — All TypeScript interfaces: `User`, `Workspace`, `Policy`, `PolicyRule`, `SolutionType`, `HardeningProfile`, `ProfileRule`, `HITLComment`, `SolutionInstance`, `EnforcementJob`, `ComplianceReport`, `DryRunReport`, `ImpactAssessmentReport`
  - `frontend/src/services/api.ts` — Axios instance with base URL, JWT auth interceptor (attach Bearer token), 401 interceptor (redirect to login), and typed API functions for all endpoints
  - `frontend/src/hooks/useWebSocket.ts` — Custom hook: `useWebSocket(url)` manages WebSocket lifecycle, reconnection, and message queue; returns `{messages, isConnected}`
  - `frontend/src/services/auth.ts` — `login()`, `logout()`, `getToken()`, `getCurrentUser()` using localStorage for token storage
- **Success**:
  - `npm run dev` starts Vite dev server at `localhost:3000` without errors
  - TypeScript compilation completes with zero type errors
  - Navigating to `/login` renders login form
  - `api.ts` Axios interceptor attaches `Authorization: Bearer {token}` to all requests
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 376-395) — Frontend npm dependencies and package.json
- **Dependencies**:
  - Task 1.1 (frontend/ directory structure exists)

### Task 9.2: Authentication Pages & Layout

Implement login page, protected route wrapper, main navigation layout, and dashboard home page.

- **Files**:
  - `frontend/src/pages/LoginPage.tsx` — Login form with email/password; calls `auth.login()`; on success stores JWT and redirects to `/dashboard`; shows error message on 401
  - `frontend/src/components/Layout.tsx` — Top navigation bar with AEGIS branding, current user display, role badge, navigation links (Policies, Solution Types, Profiles, Instances, Users), logout button
  - `frontend/src/components/ProtectedRoute.tsx` — Wrapper that checks `getToken()`; redirects to `/login` if not authenticated; checks role for admin-only routes
  - `frontend/src/pages/DashboardPage.tsx` — Overview cards: total policies, total profiles, total instances, recent enforcement jobs; uses React Query to fetch summary data
- **Success**:
  - Login with valid credentials → JWT stored, redirected to `/dashboard`
  - Navigating to protected route without JWT → redirected to `/login`
  - Layout renders nav links appropriate for current user's role (Auditor does not see Remediate button)
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 178-215) — RBAC role matrix determines which UI elements each role sees
- **Dependencies**:
  - Task 9.1 (project setup, auth service, API service)

### Task 9.3: Policy Manager Component

Implement the PolicyManager feature: upload OVAL/XCCDF/text files, import from GitHub/SharePoint/Confluence, list policies, view policy rules with severity badges, and delete policies.

- **Files**:
  - `frontend/src/components/PolicyManager/PolicyList.tsx` — Table of policies with columns: name, standard (CIS/STIG/SRG/Custom), format, rule count, created date, actions (view, delete); uses React Query `useQuery`
  - `frontend/src/components/PolicyManager/PolicyUpload.tsx` — Drag-and-drop file upload area + import source buttons (GitHub, SharePoint, Confluence); GitHub import shows modal for repo URL + file path + token; calls appropriate API endpoint; shows upload progress
  - `frontend/src/components/PolicyManager/PolicyRuleList.tsx` — Filterable/sortable table of rules for a selected policy; columns: rule_id, title, severity (color-coded badge), category, target_component_types; click to view full rule details in slide-over panel
  - `frontend/src/pages/PoliciesPage.tsx` — Composes PolicyUpload + PolicyList + PolicyRuleList; Security Officer and Admin roles can upload/delete; all roles can view
- **Success**:
  - Upload a XCCDF file → progress indicator → policy appears in list with correct rule count
  - Rule list shows severity badges: Critical=red, High=orange, Medium=yellow, Low=blue
  - GitHub import modal sends `POST /policies/import/github` with correct payload
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 118-140) — Policy API endpoints and import sources
- **Dependencies**:
  - Task 9.1-9.2 (layout, auth), Task 8.2 (policies router must exist)

### Task 9.4: Solution Type Builder Component

Implement the SolutionTypeBuilder: create solution type, upload representative config JSON, display hierarchical component tree with checkboxes for component selection, and save selection.

- **Files**:
  - `frontend/src/components/SolutionTypeBuilder/SolutionTypeForm.tsx` — Create form: name, description; `POST /solution-types`
  - `frontend/src/components/SolutionTypeBuilder/ConfigUpload.tsx` — File upload for representative JSON config; calls `POST /solution-types/{id}/config`; on success shows component tree
  - `frontend/src/components/SolutionTypeBuilder/ComponentTree.tsx` — Recursive tree component rendering `RACK → Server → [iLO, BIOS, SRController, hypervisor, VMs]` hierarchy with expand/collapse; checkbox per component with indeterminate state for partial parent selection; shows component type badge
  - `frontend/src/components/SolutionTypeBuilder/SolutionTypeList.tsx` — Cards for each solution type showing name, component count, selected count, associated profiles
  - `frontend/src/pages/SolutionTypesPage.tsx` — Composes above components; `PUT /solution-types/{id}/components/selection` on Save Selection
- **Success**:
  - Upload representative JSON → hierarchical tree renders matching RACK-0→Server-00→iLO-000 structure
  - Checking a Server checkbox selects all child components (iLO, BIOS, hypervisor, VMs)
  - Save Selection button calls API with selected component_ids array
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 73-95) — Solution instance hierarchy structure used for component tree
  - #file:../research/20260504-project-aegis-research.md (Lines 142-155) — Solution type and component selection API endpoints
- **Dependencies**:
  - Task 9.1-9.2, Task 8.2 (solution types router)

### Task 9.5: Hardening Profile Editor (HITL Interface)

Implement the core HITL Monaco Editor interface. This is the primary Development Stage UI: lists rules by status, displays LLM-generated code in Monaco Editor, shows comment threads, supports manual editing, code diff view, approve/reject/comment/regenerate actions, and WebSocket-driven real-time generation progress.

- **Files**:
  - `frontend/src/components/HardeningProfileEditor/RuleList.tsx` — Left panel: filterable list of ProfileRules grouped by code_status (pending/generated/reviewed/approved/rejected); status badges; click to select rule for editing; shows overall profile completion percentage
  - `frontend/src/components/HardeningProfileEditor/RuleCodeEditor.tsx` — Right panel: Monaco Editor tabs for `evaluate`, `remediate`, `rollback` function code; Python syntax highlighting; read-only by default; Edit button enables editing; Save button calls `PUT /profiles/{id}/rules/{rule_id}/code`; `@monaco-editor/react` with `language="python"`, `theme="vs-dark"`, `height="400px"`
  - `frontend/src/components/HardeningProfileEditor/DiffViewer.tsx` — Monaco diff editor showing original LLM-generated code vs. current (edited) code; toggled by Diff button
  - `frontend/src/components/HardeningProfileEditor/CommentThread.tsx` — Comment list per rule with author, timestamp, comment text; Add Comment form; comment type selector (review/approval); Regenerate with Comments button triggers `POST /profiles/{id}/rules/{rule_id}/regenerate` with latest comment
  - `frontend/src/components/HardeningProfileEditor/GenerationProgress.tsx` — WebSocket-driven progress panel: uses `useWebSocket` hook; shows per-rule generation status as it streams; overall progress bar
  - `frontend/src/pages/ProfileEditorPage.tsx` — Full page layout: profile header (name, policy, solution type, status); Generate All button; RuleList + RuleCodeEditor side-by-side; GenerationProgress overlay during generation
- **Success**:
  - Monaco Editor renders Python code with syntax highlighting
  - Clicking Generate All → WebSocket connects → per-rule status updates appear in real time
  - Editing code in Monaco → Save → API call → rule status updated to "reviewed"
  - Add comment → Regenerate → new code appears in editor (WebSocket delivers token stream)
  - Approve button → rule status badge turns green
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 60-68) — Monaco Editor integration via `@monaco-editor/react`; Python/diff support
  - #file:../research/20260504-project-aegis-research.md (Lines 155-175) — HITL profile API endpoints (code, regenerate, approve, comment)
- **Dependencies**:
  - Task 9.1-9.2, Task 8.2 (profiles router), Task 8.4 (WebSocket endpoint)

### Task 9.6: Instance Manager & Compliance Dashboard

Implement instance creation, config upload, enforcement operation console, and the compliance dashboard with hierarchical RED/Orange/Green visualization.

- **Files**:
  - `frontend/src/components/InstanceManager/InstanceForm.tsx` — Create instance form: name, select workspace, select solution type, select hardening profile; `POST /instances`
  - `frontend/src/components/InstanceManager/ConfigUpload.tsx` — Upload actual instance config JSON (with real IPs/credentials); `POST /instances/{id}/config`; shows validation results
  - `frontend/src/components/InstanceManager/InstanceList.tsx` — Cards per instance with owner, creation date, last job status, quick action buttons (Evaluate, Remediate, Rollback)
  - `frontend/src/components/ComplianceDashboard/HierarchyTree.tsx` — Recursive tree rendering rack→server→component hierarchy; each node has RED/Orange/Green status badge based on compliance percentage (>90%=green, 50-90%=orange, <50%=red); expandable; click node to filter report table
  - `frontend/src/components/ComplianceDashboard/ComplianceGauge.tsx` — Recharts `RadialBarChart` or `PieChart` showing pass/fail/error as RED/Orange/Green segments; displayed per selected node
  - `frontend/src/components/ComplianceDashboard/ReportTable.tsx` — Filterable table of all rule results: rule_id, title, component, severity, status (PASS/FAIL/ERROR), evidence; sortable by severity and status
  - `frontend/src/components/ComplianceDashboard/ReportDownload.tsx` — Download buttons for ARF XML and HTML report; calls download endpoint
  - `frontend/src/pages/InstanceDetailPage.tsx` — Tab layout: Overview, Evaluate, Remediate, Reports; Evaluate tab has Run Evaluation button + WebSocket job progress + redirects to compliance report on completion
- **Success**:
  - Instance config upload → validation errors shown if Vault refs are invalid
  - Run Evaluation → WebSocket job progress displayed → on completion, hierarchy tree renders with GREEN/ORANGE/RED nodes
  - Recharts gauge shows correct pass percentage for selected node
  - Download ARF XML button triggers file download with `application/xml` content type
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 293-310) — RED/Orange/Green reporting and hierarchy compliance tree
  - #file:../research/20260504-project-aegis-research.md (Lines 67-74) — Recharts and React Flow for dashboard
- **Dependencies**:
  - Task 9.1-9.2, Task 8.3 (instances router), Task 8.4 (WebSocket)

### Task 9.7: Enforcement Console, Impact Assessment, Dry-Run & User Management

Implement the enforcement operations UI (impact assessment table, dry-run risk table, topology graph, remediation confirmation), and the admin user management page.

- **Files**:
  - `frontend/src/components/EnforcementConsole/ImpactAssessmentTable.tsx` — Table of communication channels: source, target, protocol, TLS versions, cipher suites, port; color-coded risk column; triggers `POST /instances/{id}/impact-assessment`
  - `frontend/src/components/EnforcementConsole/DryRunResults.tsx` — Three-section display: safe rules (green), risky rules (orange), breaking rules (red); each rule shows risk_score, impacted_channels list, explanation; Proceed to Remediate button disabled if breaking_rules exist (requires override checkbox)
  - `frontend/src/components/EnforcementConsole/TopologyGraph.tsx` — React Flow graph: nodes = services/components, edges = communication channels; edge color = risk level; click edge to see TLS/cipher details; zoom and pan support
  - `frontend/src/components/EnforcementConsole/RemediatePanel.tsx` — Rule selection checkboxes; Run Dry-Run first button; Confirm Remediation button with impact warning; WebSocket progress for active remediation job
  - `frontend/src/components/EnforcementConsole/RollbackPanel.tsx` — List of remediated rules with saved_state presence indicator; Select rules to rollback; Confirm Rollback with confirmation dialog
  - `frontend/src/components/UserManagement/UserList.tsx` — Admin-only table of users: username, email, role badge, status (active/inactive); Edit Role dropdown; Deactivate button
  - `frontend/src/components/UserManagement/CreateUserForm.tsx` — Admin-only form: email, username, password, role selector; `POST /users`
  - `frontend/src/pages/UsersPage.tsx` — Composes UserList + CreateUserForm; Admin-only route
- **Success**:
  - Impact assessment table displays after `POST /impact-assessment` job completes
  - Dry-run results clearly separate safe/risky/breaking rules with color coding
  - Proceed to Remediate disabled when breaking_rules list is non-empty (must acknowledge)
  - React Flow topology graph renders nodes and edges from impact assessment data
  - Admin user management: Create user → appears in list; Edit role → badge updates
- **Research References**:
  - #file:../research/20260504-project-aegis-research.md (Lines 272-292) — Dry-run algorithm and break risk categories
  - #file:../research/20260504-project-aegis-research.md (Lines 178-215) — RBAC role matrix for admin-only user management
- **Dependencies**:
  - Task 9.6 (shares InstanceDetailPage), Task 8.3 (enforcement router), Task 8.1 (user management router)

---

## Dependencies

- Python 3.12, Node.js 20, Docker, Docker Compose v2
- All Python packages in `backend/requirements.txt` (fastapi, celery, sqlalchemy, paramiko, netmiko, pymilvus, openai, langchain, lxml, networkx, etc.)
- All npm packages in `frontend/package.json` (react, @monaco-editor/react, reactflow, recharts, @tanstack/react-query, axios, tailwindcss, etc.)
- Local infrastructure: PostgreSQL 16, Redis 7, MilvusDB 2.4, Ollama with CodeLlama 34B model

## Success Criteria

- Policy upload (OVAL/XCCDF) → rules parsed and displayed with correct severity, category, and target component types
- LLM generates `evaluate()`/`remediate()`/`rollback()` Python functions for each rule per component type; code passes `ast.parse()` validation
- HITL: Monaco Editor renders code; Security Officer can comment, regenerate, hand-edit, and approve; WebSocket streams token progress in real time
- Solution instance config JSON upload → hierarchical component tree displayed; Evaluation runs against real endpoints via correct connector
- Impact assessment builds NetworkX topology graph from `network_topology.communication_channels`; dry-run detects TLS/protocol breaking changes
- Rollback restores pre-remediation state from `saved_state` captured during `remediate()`
- Compliance report: OpenSCAP ARF XML downloadable; HTML report with RED/Orange/Green hierarchy dashboard
- RBAC: Security Officer manages policies/code, Auditor runs evaluation only, User manages instances, Admin does everything
- Workspace scope: only owner and collaborators can access solution instances
