# AEGIS — AI Agentic Security Hardening

AEGIS is an AI-driven security hardening platform for HPE Private Cloud solutions (PCE, PCAI). It ingests industry-standard security policies (OVAL, XCCDF, JSON), uses an LLM to generate evaluate/remediate/rollback code for each rule, and then executes enforcement operations against live infrastructure endpoints — all through a browser-based UI with real-time progress updates.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Development Setup](#development-setup)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [RBAC Roles](#rbac-roles)
- [Supported Connectors](#supported-connectors)
- [LLM Configuration](#llm-configuration)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [CIS Ubuntu Test Target](#cis-ubuntu-test-target)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript + TailwindCSS)                         │
│  Port 3000 (prod) / 5173 (dev)                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────────────┐
│  FastAPI  (aegis-api)  — Port 8000                                  │
│  • Auth (JWT/OAuth2)  • Policies  • Profiles  • Instances           │
│  • Solution Types     • Users     • Workspaces                      │
└────────┬──────────────────────────────────────┬─────────────────────┘
         │ SQLAlchemy (asyncpg)                  │ Celery tasks
┌────────▼────────┐                   ┌──────────▼──────────────────┐
│  PostgreSQL 16  │                   │  Celery Worker (aegis-worker)│
│  (primary DB)   │                   │  • Code generation (LLM)    │
└─────────────────┘                   │  • Evaluate / Remediate     │
                                      │  • Rollback / Dry-run       │
┌─────────────────┐                   └──────────┬────────┬──────────┘
│  Redis 7        │◄──────────────────────────────┘        │
│  (broker/cache  │   pub/sub (WebSocket relay)             │
│   + pub/sub)    │                                         │
└─────────────────┘                              ┌──────────▼──────────┐
                                                 │  Target Endpoints   │
┌──────────────────────────────────────┐         │  SSH / Netmiko      │
│  Milvus (vector store)               │         │  Kubernetes API     │
│  ├─ etcd  (metadata)                 │         │  Redfish (iLO/BMC)  │
│  └─ MinIO (object storage)           │         │  HashiCorp Vault    │
└──────────────────────────────────────┘         └─────────────────────┘
```

---

## Key Features

| Feature | Description |
|---|---|
| **Policy Import** | Upload OVAL, XCCDF, JSON, or plain-text policy files; rules are parsed and stored per workspace |
| **AI Code Generation** | LLM generates `evaluate`, `remediate`, and `rollback` Python snippets for each policy rule using RAG (Milvus vector store) |
| **Policy Profiles** | Create standard (all rules) or tailored (selected rules) profiles from a policy; customize rule selection, promote to locked state for deployment |
| **Rule Review Workflow** | Approve, reject, or import implementation code for individual rules; view code status across the profile |
| **Implementation Editor** | Full-featured code editor (Monaco) for reviewing and editing generated evaluate/remediate/rollback code per rule |
| **Hardening Blueprints** | Compose multi-component blueprints using locked profiles; map components to profiles for deployment |
| **Solution Types** | Define target infrastructure types (server, switch, Kubernetes cluster, etc.) with their connector configuration schema |
| **Instance Manager** | Register live infrastructure instances and associate them with a hardening blueprint |
| **Enforcement Console** | Run evaluate, dry-run, remediate, or rollback against an instance; stream real-time status via WebSocket |
| **Compliance Dashboard** | Aggregated pass/fail compliance reports per instance |
| **ARF Report Generation** | Generate OpenSCAP-compatible Asset Reporting Format (ARF 1.1) XML reports for compliance auditing |
| **HTML Reports** | Rendered HTML compliance reports for human-readable review |
| **Impact Assessment** | NetworkX-based communication channel analysis between components; TLS risk scoring and remediation impact modeling |
| **User Management** | Full RBAC with four roles; workspace-scoped access control |
| **Vault Integration** | Credential references in endpoint configs resolved at runtime from HashiCorp Vault |
| **Nautobot Golden Config** | Alternative data-driven evaluation method — LLM generates intended device configuration (CLI/JSON) and pushes to Nautobot for continuous drift monitoring |
| **Solution Type Upload** | Import solution type definitions from JSON files describing racks, servers, VMs, and network topology |

> **Note:** The Nautobot Golden Config integration and the live enforcement mode (evaluate/remediate/rollback against real infrastructure) are not yet fully tested in production environments. Use with caution and validate in a staging setup first.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, React Router, React Query, Recharts, ReactFlow |
| Backend API | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (async), Alembic, LangChain |
| Database | PostgreSQL 16 |
| Task Queue | Celery 5, Redis 7 |
| Vector Store | Milvus 2.4 (backed by etcd + MinIO) |
| LLM | OpenAI-compatible API **or** Ollama (local) |
| Embeddings | OpenAI `text-embedding-3-small`, HuggingFace (`sentence-transformers`), or Ollama `nomic-embed-text` |
| Graph Analysis | NetworkX (impact assessment / channel risk scoring) |
| Auth | JWT (HS256) via `python-jose`, bcrypt passwords |
| Connectors | Paramiko (SSH), Netmiko, `kubernetes` Python client, Redfish/pyVmomi, hvac (Vault), Nautobot REST |
| Container | Docker, Docker Compose |

---

## Prerequisites

- **Docker** ≥ 24 and **Docker Compose** ≥ 2
- An **OpenAI-compatible LLM endpoint** (e.g., Azure OpenAI, vLLM, Ollama) _or_ a local [Ollama](https://ollama.ai) instance

---

## Quick Start (Docker Compose)

```bash
# 1. Clone the repository
git clone <repo-url>
cd Aegis-SecurityHardening

# 2. Configure environment variables
cp .env.example .env
# Edit .env — set strong passwords and your LLM endpoint (see below)

# 3. Start all services
docker compose up -d

# 4. Apply database migrations
docker compose exec aegis-api alembic upgrade head

# 5. Open the UI
#    http://localhost:3000
```

> The API docs (Swagger UI) are available at **http://localhost:8000/docs**.

---

## Development Setup

The `docker-compose.dev.yml` overlay enables hot-reload for both the API and the frontend dev server.

```bash
# Start infrastructure services + hot-reload API/UI
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Backend runs with uvicorn --reload on :8000
# Frontend Vite dev server runs on :5173
# debugpy port exposed on :5678
```

### Local backend (without Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Run API
uvicorn aegis.main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A aegis.worker.celery_app worker --loglevel=info
```

### Local frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `.env.example` to `.env` and set the following values:

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL password | _(required)_ |
| `REDIS_PASSWORD` | Redis password | _(required)_ |
| `MINIO_USER` | MinIO root user | `aegisadmin` |
| `MINIO_PASSWORD` | MinIO root password | _(required)_ |
| `SECRET_KEY` | JWT signing secret (≥ 32 chars) | _(required)_ |
| `OPENAI_API_BASE` | OpenAI-compatible base URL (leave blank for Ollama) | `""` |
| `OPENAI_API_KEY` | API key for the LLM endpoint | `ollama` |
| `OPENAI_MODEL` | Chat model name | `""` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `EMBEDDING_PROVIDER` | `openai` \| `ollama` \| `huggingface` | `ollama` |
| `OLLAMA_MODEL` | Ollama model (when not using OpenAI) | `codellama:34b` |
| `OLLAMA_EMBED_MODEL` | Ollama embedding model | `nomic-embed-text` |
| `VITE_API_URL` | Backend URL used by the frontend dev server | `http://localhost:8000` |
| `NAUTOBOT_URL` | Nautobot instance base URL (optional) | `""` |
| `NAUTOBOT_API_TOKEN` | Nautobot REST API token (optional) | `""` |
| `NAUTOBOT_VERIFY_SSL` | Verify SSL for Nautobot connections | `true` |
| `NAUTOBOT_GOLDEN_CONFIG_REPO` | Git repo URL for Nautobot intended configs (optional) | `""` |
| `OLLAMA_BASE_URL` | Base URL for the local Ollama service | `http://localhost:11434` |
| `HUGGINGFACE_EMBEDDING_MODEL` | HuggingFace embedding model name (when `EMBEDDING_PROVIDER=huggingface`) | `all-MiniLM-L6-v2` |
| `DATABASE_URL` | Full PostgreSQL connection URI (for local dev without Docker) | `postgresql+asyncpg://aegis:aegis@localhost/aegis` |
| `REDIS_URL` | Full Redis connection URI (for local dev without Docker) | `redis://:redis@localhost:6379/0` |
| `MILVUS_HOST` | MilvusDB hostname | `localhost` |
| `MILVUS_PORT` | MilvusDB port | `19530` |
| `CORS_ORIGINS` | JSON array of allowed CORS origins | `["http://localhost:3000","http://localhost:5173"]` |
| `REPORTS_DIR` | Directory for generated compliance reports | `/tmp/aegis_reports` |

---

## API Overview

All API routes are prefixed with `/api/v1`. Authentication uses OAuth2 Bearer tokens obtained from `POST /api/v1/auth/login`.

| Router | Prefix | Description |
|---|---|---|
| Auth | `/api/v1/auth` | Login, token refresh, register |
| Users | `/api/v1/users` | User CRUD, role assignment |
| Workspaces | `/api/v1/workspaces` | Workspace and member management |
| Policies | `/api/v1/policies` | Upload and browse security policies; list/review policy rules |
| Profiles | `/api/v1/profiles` | Policy profile CRUD (standard/tailored); promote, lock, version |
| Solution Types | `/api/v1/solution-types` | Define infrastructure target types |
| Blueprints | `/api/v1/blueprints` | Hardening blueprints with component-to-profile mapping; rule code review |
| Instances | `/api/v1/instances` | Register instances; trigger enforcement jobs; push golden config to Nautobot |
| WebSocket | `/ws/{channel}` | Real-time job progress (codegen, enforcement) |

Full interactive documentation: **http://localhost:8000/docs**

---

## RBAC Roles

| Role | Capabilities |
|---|---|
| `admin` | Full access — user management, all workspaces |
| `security_officer` | Create/edit policies, profiles, instances; trigger enforcement |
| `auditor` | Read-only access to compliance reports and instance state |
| `user` | View dashboards within assigned workspaces |

---

## Supported Connectors

AEGIS connects to target infrastructure using pluggable connectors selected by the `component_type` field on a Solution Instance:

| Connector | `component_type` | Protocol / Library |
|---|---|---|
| SSH | `ssh` | Paramiko |
| Network Device | `netmiko` | Netmiko |
| Kubernetes | `kubernetes` | `kubernetes` Python client |
| Redfish (iLO/BMC) | `redfish` | REST via `requests` |
| HashiCorp Vault | `vault` | `hvac` (credential resolver) |
| Nautobot | `nautobot` | REST API via `requests` (Golden Config push) |

The connector factory also supports automatic mapping via component name prefixes:

| Prefix | Resolved Connector |
|---|---|
| `VM`, `Server`, `Linux` | SSH |
| `iLO`, `BIOS`, `Redfish`, `SRController` | Redfish |
| `Aruba`, `Switch` | Netmiko |
| `Kubernetes`, `K8s` | Kubernetes |
| `Vault` | Vault |

Credential references in endpoint configs follow the `vault://secret/path#key` syntax and are resolved at evaluation time.

---

## LLM Configuration

AEGIS supports two LLM backends:

### Ollama (default — local)

Pull a code-capable model and start Ollama, then set in `.env`:

```
OLLAMA_MODEL=codellama:34b
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBEDDING_PROVIDER=ollama
```

### OpenAI-compatible endpoint

Set in `.env`:

```
OPENAI_API_BASE=https://your-endpoint/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_PROVIDER=openai
```

The code generator uses RAG: similar previously-approved rules are retrieved from Milvus and injected as few-shot examples into the prompt.

---

## Project Structure

```
Aegis-SecurityHardening/
├── backend/
│   ├── aegis/
│   │   ├── api/v1/           # FastAPI routers
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── connectors/   # SSH, Netmiko, K8s, Redfish, Vault, Nautobot + factory
│   │   │   ├── enforcement/  # Evaluator, remediator, rollback, dry-run, impact assessor
│   │   │   ├── llm/          # LLM client, code generator, Milvus store, prompt templates
│   │   │   ├── policy_parser/# OVAL, XCCDF, JSON, text parsers
│   │   │   ├── reporting/    # ARF XML generator, HTML reports
│   │   │   └── rbac.py       # JWT auth + role-based access control
│   │   ├── tasks/            # Celery tasks (codegen, enforcement)
│   │   ├── config.py         # Pydantic settings
│   │   ├── database.py       # Async SQLAlchemy engine
│   │   ├── main.py           # FastAPI app entry point
│   │   └── worker.py         # Celery app definition
│   ├── migrations/           # Alembic migration scripts
│   └── tests/                # pytest test suite
├── frontend/
│   └── src/
│       ├── api/              # Axios client + endpoint definitions
│       ├── components/       # Feature UI components
│       ├── context/          # AuthContext, WorkspaceContext
│       ├── pages/            # Top-level page components
│       │   ├── LoginPage                 # Authentication / login form
│       │   ├── DashboardPage             # Compliance overview with Recharts
│       │   ├── PolicyManagerPage         # Policy import, profiles, rule overview
│       │   ├── PolicyImplementationEditorPage  # Monaco code editor for rule review
│       │   ├── SolutionTypeBuilderPage   # Solution type definition + JSON upload
│       │   ├── HardeningBlueprintManagerPage   # Blueprint creation with profile mapping
│       │   ├── HardeningBlueprintEditorPage    # Blueprint rule code review
│       │   ├── InstanceManagerPage       # Instance registration
│       │   ├── EnforcementConsolePage    # Enforcement execution + Nautobot push
│       │   └── UserManagementPage
│       └── types/            # TypeScript type definitions
├── projects/
│   ├── cis-ubuntu-target/    # Simulated Ubuntu 22.04 for CIS benchmark testing
│   ├── PCAI/scid/            # HPE PCAI infrastructure layout definitions
│   ├── sample-policies/      # Sample CIS/HPE policy JSON files + seed script
│   └── sample-solution-type-upload.json  # Example solution type import file
├── scripts/
│   └── restart-docker.ps1    # Helper script to restart Docker services
├── docker-compose.yml        # Production stack (includes CIS Ubuntu test target)
├── docker-compose.dev.yml    # Development overrides (hot-reload)
└── .env.example              # Environment variable template
```

---

## Running Tests

```bash
cd backend

# Install test dependencies (if running locally)
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test module
pytest tests/test_enforcement.py
```

Test configuration is in `backend/pytest.ini`. Async tests use `pytest-asyncio`.

Available test modules:

| Test File | Coverage Area |
|---|---|
| `test_rbac.py` | JWT auth, role-based access, workspace scoping |
| `test_enforcement.py` | Evaluate, remediate, rollback, dry-run pipelines |
| `test_policy_parsers.py` | OVAL, XCCDF, JSON, and text policy parsing |
| `test_connector_factory.py` | Connector dispatch by component_type |
| `test_nautobot_connector.py` | Nautobot Golden Config integration |
| `test_golden_config_gen.py` | LLM-driven golden config generation |

---

## CIS Ubuntu Test Target

The Docker Compose stack includes a **simulated Ubuntu 22.04 target** (`cis-ubuntu-target`) for end-to-end testing of the CIS benchmark hardening pipeline without touching real infrastructure.

### How it works

- A lightweight container exposes SSH on port **2222** (mapped from container port 22)
- A JSON state file (`/aegis-state/state.json`) simulates system configuration
- Mock shell commands (`findmnt`, `dpkg`, `sysctl`, `systemctl`, `sshd`, `apparmor_status`) read/write from the state file
- Aegis can safely run `evaluate` → `remediate` → `rollback` against this target

### Credentials

| Field | Value |
|---|---|
| Host | `cis-ubuntu-target` (Docker network) or `localhost:2222` (host) |
| Username | `aegis-test` |
| Password | `aegistest123` |

### Seeding the test instance

After starting the stack, register the test target in Aegis:

```bash
cd projects/cis-ubuntu-target/seed
pip install requests
python seed_instance.py --password <admin-password>
```

This creates a solution instance and associates it with the 10-rule CIS Ubuntu 22.04 hardening profile included in `hardening_profile.json`.

---

## Troubleshooting

| Issue | Resolution |
|---|---|
| `alembic upgrade head` fails with connection error | Ensure PostgreSQL is healthy: `docker compose ps postgres` |
| Milvus fails to start | Check that etcd and MinIO are healthy first; Milvus depends on both |
| LLM code generation returns empty | Verify `OPENAI_API_BASE` and `OPENAI_API_KEY` (or Ollama is running on `OLLAMA_BASE_URL`) |
| Frontend can't reach API | Set `VITE_API_URL=http://localhost:8000` in `.env` and restart the dev server |
| WebSocket disconnects immediately | Confirm Redis is running and `REDIS_URL` is correct |
| `cis-ubuntu-target` SSH refused | Wait for healthcheck to pass: `docker compose ps cis-ubuntu-target` |
