# AEGIS — AI Agentic Security Hardening

AEGIS is an AI-driven security hardening platform for HPE Private Cloud solutions (PCE, PCAI). It ingests industry-standard security policies (OVAL, XCCDF), uses an LLM to generate evaluate/remediate/rollback code for each rule, and then executes enforcement operations against live infrastructure endpoints — all through a browser-based UI with real-time progress updates.

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
| **Policy Import** | Upload OVAL, XCCDF, or plain-text policy files; rules are parsed and stored per workspace |
| **AI Code Generation** | LLM generates `evaluate`, `remediate`, and `rollback` Python snippets for each policy rule using RAG (Milvus vector store) |
| **Hardening Profiles** | Compose a profile from selected policy rules; approve, edit, or regenerate the AI-produced code |
| **Solution Types** | Define target infrastructure types (server, switch, Kubernetes cluster, etc.) with their connector configuration schema |
| **Instance Manager** | Register live infrastructure instances and associate them with a hardening profile |
| **Enforcement Console** | Run evaluate, dry-run, remediate, or rollback against an instance; stream real-time status via WebSocket |
| **Compliance Dashboard** | Aggregated pass/fail compliance reports per instance |
| **User Management** | Full RBAC with four roles; workspace-scoped access control |
| **Vault Integration** | Credential references in endpoint configs resolved at runtime from HashiCorp Vault |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, React Router |
| Backend API | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (async), Alembic |
| Database | PostgreSQL 16 |
| Task Queue | Celery 5, Redis 7 |
| Vector Store | Milvus 2.4 (backed by etcd + MinIO) |
| LLM | OpenAI-compatible API **or** Ollama (local) |
| Embeddings | OpenAI `text-embedding-3-small`, HuggingFace, or Ollama `nomic-embed-text` |
| Auth | JWT (HS256) via `python-jose`, bcrypt passwords |
| Connectors | Paramiko (SSH), Netmiko, `kubernetes` Python client, Redfish/pyVmomi, hvac (Vault) |
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

---

## API Overview

All API routes are prefixed with `/api/v1`. Authentication uses OAuth2 Bearer tokens obtained from `POST /api/v1/auth/login`.

| Router | Prefix | Description |
|---|---|---|
| Auth | `/api/v1/auth` | Login, token refresh, register |
| Users | `/api/v1/users` | User CRUD, role assignment |
| Workspaces | `/api/v1/workspaces` | Workspace and member management |
| Policies | `/api/v1/policies` | Upload and browse security policies (OVAL/XCCDF/text) |
| Solution Types | `/api/v1/solution-types` | Define infrastructure target types |
| Profiles | `/api/v1/profiles` | Hardening profile CRUD; trigger LLM code generation |
| Instances | `/api/v1/instances` | Register instances; trigger enforcement jobs |
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
│   │   │   ├── connectors/   # SSH, Netmiko, K8s, Redfish, Vault
│   │   │   ├── enforcement/  # Evaluator, remediator, rollback, dry-run
│   │   │   ├── llm/          # LLM client, code generator, Milvus store
│   │   │   ├── policy_parser/# OVAL, XCCDF, text parsers
│   │   │   ├── reporting/    # Compliance report generation
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
│       ├── context/          # AuthContext (JWT state)
│       ├── pages/            # Top-level page components
│       └── types/            # TypeScript type definitions
├── projects/
│   └── PCAI/scid/            # HPE PCAI infrastructure layout definitions
├── docker-compose.yml        # Production stack
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
