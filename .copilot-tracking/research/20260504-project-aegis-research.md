<!-- markdownlint-disable-file -->

# Task Research Notes: Project Aegis - AI Agentic Security Hardening Solution

## Research Executed

### File Analysis

- `.github/agents/task-researcher.agent.md`
  - Research specialist agent definition; tools include fetch, githubRepo, codebase, search, usages
- `.github/instructions/task-implementation.instructions.md`
  - Implementation standards: progressive tracking in `.copilot-tracking/plans/`, `.copilot-tracking/details/`, `.copilot-tracking/changes/`; plan-driven development with checklist completion tracking
- `.copilot-tracking/research/20260504-project-aegis-research.md-backuo`
  - Prior research session findings preserved as backup; comprehensive technology stack analysis, API design, and project directory structure already researched

### Code Search Results

- No existing source code found — greenfield project
- Workspace contains only GitHub agent definitions and instruction files
- All research conducted from authoritative external sources and technology documentation

### External Research

- #fetch:https://www.open-scap.org/
  - OpenSCAP is the de-facto open-source SCAP framework; supports OVAL, XCCDF, ARF, XCCDF-Tailoring; `oscap` CLI generates ARF (Assessment Results Format) XML and HTML compliance reports; natively evaluates CIS/STIG/SRG content bundles
- #fetch:https://www.cisecurity.org/cis-benchmarks
  - CIS Benchmarks published as XCCDF + OVAL bundles (CIS-CAT compatible); Level 1 (minimal impact) and Level 2 (high security) profiles; cover OS (RHEL, SLES, Ubuntu), hypervisors (VMware ESXi), network devices (Aruba), and cloud platforms
- #fetch:https://public.cyber.mil/stigs/
  - DISA STIGs published as XCCDF bundles with OVAL evaluation content; SRGs are parent product-family documents; STIG Viewer 2.x/3.x used for human review; SCAP content distributed as ZIP archives with benchmark XML files
- #fetch:https://milvus.io/docs
  - Milvus 2.4 is a cloud-native vector database; standalone deployment via Docker Compose with etcd + MinIO dependencies; pymilvus SDK for Python; supports cosine/L2/IP similarity; collection schema with vector + scalar fields; used for semantic retrieval of policy rule context and remediation patterns
- #fetch:https://ollama.com/
  - Ollama runs quantized LLMs locally (Llama 3.1, CodeLlama, Mistral, DeepSeek-Coder); exposes OpenAI-compatible REST API at `http://localhost:11434/v1`; supports GPU acceleration (NVIDIA CUDA, AMD ROCm, Apple Metal); ideal for air-gapped HPE Private Cloud environments; model pull: `ollama pull codellama:34b`
- #fetch:https://fastapi.tiangolo.com/
  - FastAPI 0.111+ with Python 3.12; native async/await; OpenAPI/Swagger auto-docs; WebSocket support for streaming LLM token generation; Pydantic v2 for request/response validation; dependency injection for RBAC and DB sessions
- #fetch:https://docs.celeryq.dev/
  - Celery 5.x distributed task queue; Redis or RabbitMQ broker; task chaining (`chain`, `chord`, `group`) for evaluate → remediate → rollback pipelines; result backend for task status tracking; beat scheduler for periodic compliance scans
- #fetch:https://www.ansible.com/
  - Ansible agentless SSH automation; 7000+ modules covering OS (RHEL, SLES), network (Aruba AOS-CX, Juniper), VMware ESXi, iLO via HTTPS modules; idempotent playbooks; `check_mode: true` for dry-run; suitable for remediation and rollback playbook generation
- #fetch:https://docs.paramiko.org/
  - Paramiko 3.x Python SSH library; `SSHClient` for command execution; `SFTPClient` for file transfer; supports RSA/Ed25519 key auth and password auth; used for direct SSH connectivity to VMs, servers, Linux OS endpoints
- #fetch:https://react.dev/
  - React 18 with concurrent features; hooks-based component model; Suspense for async data loading; ideal for HITL code review/editor, compliance dashboard, enforcement console
- #fetch:https://microsoft.github.io/monaco-editor/
  - Monaco Editor (VS Code engine) embeds in React via `@monaco-editor/react`; syntax highlighting for Python, YAML, Shell, JSON; diff editor for showing LLM-generated vs. human-edited code; IntelliSense and code folding; core of the HITL rule implementation review and editing interface

### Project Conventions

- Standards referenced: Greenfield project — conventions to be established during implementation
- Instructions followed: `.github/instructions/task-implementation.instructions.md` — progressive tracking in `.copilot-tracking/plans/` and `.copilot-tracking/changes/`

## Key Discoveries

### Project Structure

**Greenfield full-stack AI Agentic application.** Two discrete operational stages with a shared backend:

**Development Stage** (one-time per Solution Type — e.g., PCAI-Small, PCE-Standard):
1. Security Officer uploads policy (OVAL/XCCDF/XML/English text)
2. User creates Solution Type with a representative config JSON (no real IPs needed)
3. User selects which components/services to harden from the config hierarchy
4. AEGIS triggers LLM to generate `evaluate()`, `remediate()`, `rollback()` Python functions for each policy rule × component type pair
5. HITL interface: Security Officer reviews code in Monaco Editor, comments on issues, re-triggers LLM regeneration with comments as context, or hand-edits directly, then approves
6. Approved rule implementations saved as a named **Hardening Profile** (reusable across instances)

**Enforcement Stage** (repeated per Solution Instance — real deployments with actual IPs/credentials):
1. User selects a saved Hardening Profile (from Development Stage)
2. User uploads Solution Instance config JSON (actual endpoints, credentials, network topology)
3. Operations available:
   - **Evaluate** (read-only): Run `evaluate()` functions against real endpoints → compliance report
   - **Impact Assessment**: Analyze network topology to map service communication channels and identify TLS/protocol dependencies
   - **Remediation Dry-Run**: For each rule being remediated, score risk and detect breaking channels
   - **Remediate**: Execute `remediate()` functions with pre-state capture for rollback
   - **Rollback**: Execute `rollback()` using captured pre-remediation state

### Solution Instance Hierarchy

```
Solution Instance (PCAI-Small / PCE-Standard / etc.)
├── RACK-0
│   ├── PDU-00, PDU-01               (SNMP / HTTPS)
│   ├── Switch-00, Switch-01, Switch-02 (SSH via Netmiko / AOS-CX REST)
│   ├── Server-00
│   │   ├── iLO-000                  (HTTPS/Redfish — HPE iLO 5/6)
│   │   ├── SRController-000         (HTTPS/Redfish — HPE Smart Array MR/SR)
│   │   ├── BIOS-000                 (HTTPS/Redfish via iLO)
│   │   ├── hypervisor-000           (SSH + HTTPS — VMware ESXi / KVM)
│   │   ├── VM-000                   (SSH — RHEL/SLES/Ubuntu)
│   │   └── VM-001
│   ├── Server-01 [mirror of Server-00]
│   └── Alletra-10k-00               (HTTPS REST — HPE Alletra Storage API)
└── RACK-1 [mirror of RACK-0]
```

**Additional Solution Services (cross-rack, software-defined):**
- StepCA (certificate authority — HTTPS REST)
- HashiCorp Vault (secrets management — HTTPS REST, `hvac` Python SDK)
- Kubernetes cluster (HTTPS — `kubernetes-client` Python SDK)
- Morpheus (HPE cloud management — HTTPS REST)
- NVIDIA GPU nodes (for PCAI — SSH + DCGM API)

### Core Data Models

**Policy Rule (normalized across OVAL/XCCDF/text):**
```python
class PolicyRule:
    rule_id: str                    # e.g., "CIS-RHEL9-1.1.1" or "STIG-ESXI-V-001"
    title: str
    description: str
    rationale: str
    severity: Literal["critical","high","medium","low","informational"]
    category: str                   # "filesystem","network","authentication","audit"
    target_component_types: List[str]  # ["OS-RHEL","OS-SLES","Hypervisor-ESXi"]
    check_content: str              # OVAL check description or text
    fix_text: str                   # Remediation guidance text
    evaluation_code: Optional[str]  # LLM-generated Python function
    remediation_code: Optional[str]
    rollback_code: Optional[str]
    code_status: Literal["pending","generated","reviewed","approved","rejected"]
    risk_score: float               # 0.0-10.0 for dry-run
    hitl_comments: List[HITLComment]
    milvus_embedding_id: Optional[str]
```

**Solution Instance Config JSON Schema:**
```json
{
  "solution_type": "PCAI-Small",
  "solution_instance_id": "pcai-prod-001",
  "racks": [
    {
      "rack_id": "RACK-0",
      "components": [
        {
          "component_id": "iLO-000",
          "component_type": "iLO",
          "hostname": "ilo-server-00.internal",
          "ip_address": "10.0.1.10",
          "port": 443,
          "protocol": "HTTPS-Redfish",
          "auth": {
            "type": "basic",
            "username": "Administrator",
            "password_ref": "vault://secret/ilo-000-pass"
          },
          "firmware_version": "3.2.0"
        },
        {
          "component_id": "VM-000",
          "component_type": "VM-RHEL",
          "hostname": "vm-000.internal",
          "ip_address": "10.0.1.100",
          "port": 22,
          "protocol": "SSH",
          "auth": {
            "type": "key",
            "username": "svcaccount",
            "private_key_ref": "vault://secret/vm-000-key"
          },
          "os": "RHEL9"
        }
      ]
    }
  ],
  "services": [
    {
      "service_id": "stepca-01",
      "service_type": "StepCA",
      "ip_address": "10.0.2.50",
      "port": 8443,
      "protocol": "HTTPS",
      "auth": { "type": "token", "token_ref": "vault://secret/stepca-token" }
    }
  ],
  "network_topology": {
    "communication_channels": [
      {
        "source": "kubernetes-node-00",
        "target": "vault-service",
        "protocol": "HTTPS",
        "tls_versions": ["TLS1.2","TLS1.3"],
        "cipher_suites": ["TLS_AES_256_GCM_SHA384"],
        "port": 8200
      }
    ]
  }
}
```

**LLM Code Generation Prompt Pattern:**
```python
RULE_CODE_GEN_PROMPT = """
You are a security hardening expert for HPE Private Cloud solutions.
Generate Python 3.12 code for the following security rule.

Rule ID: {rule_id}
Rule Title: {rule_title}
Rule Description: {rule_description}
Fix Guidance: {fix_text}
Target Component Type: {component_type}    # e.g., "iLO", "VM-RHEL9", "ArubaSwitch-AOSCX"
Communication Protocol: {protocol}         # e.g., "SSH", "HTTPS-Redfish", "HTTPS-REST"

Similar rules from knowledge base (for reference):
{retrieved_context}

Generate exactly three Python functions with these exact signatures:

def evaluate(connection: BaseConnector) -> ComplianceResult:
    \"\"\"READ-ONLY check. Return PASS/FAIL/ERROR with evidence text.\"\"\"
    ...

def remediate(connection: BaseConnector) -> RemediationResult:
    \"\"\"Apply fix. MUST capture pre-state into result.saved_state for rollback.\"\"\"
    ...

def rollback(connection: BaseConnector, saved_state: dict) -> RollbackResult:
    \"\"\"Restore pre-remediation state using saved_state from remediate().\"\"\"
    ...

Use paramiko.SSHClient for SSH connections.
Use requests.Session for HTTPS/REST/Redfish connections.
Include full error handling with try/except blocks.
Log all operations using Python logging module.
Return structured result objects — do NOT raise unhandled exceptions.
"""
```

### Complete Technology Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Backend API | FastAPI | 0.111+ | Async, OpenAPI auto-docs, WebSocket for LLM streaming, Pydantic v2 |
| Task Queue | Celery + Redis | 5.x + 7.x | Async enforce jobs, task chaining evaluate→remediate→rollback |
| LLM Runtime | Ollama + CodeLlama/Llama3 | latest | Air-gapped private cloud; OpenAI-compatible API; local GPU |
| LLM Orchestration | LangChain | 0.2+ | Prompt templates, retrieval chain, output parsing |
| Vector Store | MilvusDB | 2.4 | Per-requirements spec; semantic retrieval of policy rule context |
| Relational DB | PostgreSQL | 16 | Workspace/user/policy/instance metadata; RBAC |
| ORM + Migrations | SQLAlchemy + Alembic | 2.x | Async ORM; schema versioning |
| Frontend | React + TypeScript | 18 + 5.x | SPA; type-safe; HITL editor; compliance dashboard |
| Code Editor | Monaco Editor | latest | Embedded VS Code editor for rule code review/edit/diff |
| State Management | React Query (TanStack) | v5 | Server-state caching, mutation tracking, WebSocket sync |
| Charts | Recharts | 2.x | RED/Orange/Green compliance gauges and bar charts |
| Topology Graph | React Flow | 11.x | Interactive service dependency graph visualization |
| SSH Automation | Paramiko | 3.x | Direct SSH to VMs, servers, Linux OS endpoints |
| Network Devices | Netmiko | 4.x | Multi-vendor SSH (Aruba AOS-CX, AOS-S, Juniper) |
| BMC/BIOS/Storage | python-redfish / requests | latest | HPE iLO 5/6 Redfish API; BIOS; SRController; Alletra |
| Kubernetes Client | kubernetes-client | 29.x | k8s API server security configuration |
| Vault Client | hvac | 2.x | HashiCorp Vault secret retrieval for credentials |
| Policy Engine | OpenSCAP (oscap) | 1.3+ | Native OVAL/XCCDF evaluation, ARF report generation |
| Graph Analysis | NetworkX | 3.x | Service dependency graph for impact assessment |
| XML Parsing | lxml | 5.x | OVAL and XCCDF policy file parsing |
| Auth | JWT + OAuth2 + bcrypt | — | RBAC: Admin, Security Officer, Auditor, User |
| Containerization | Docker Compose | v2 | Local dev + production deployment |

### Complete REST API Endpoints

```
Authentication:
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  POST   /api/v1/auth/logout

Users & RBAC:
  GET    /api/v1/users
  POST   /api/v1/users
  GET    /api/v1/users/{user_id}
  PUT    /api/v1/users/{user_id}/roles
  DELETE /api/v1/users/{user_id}

Workspaces:
  POST   /api/v1/workspaces
  GET    /api/v1/workspaces
  GET    /api/v1/workspaces/{workspace_id}
  PUT    /api/v1/workspaces/{workspace_id}
  DELETE /api/v1/workspaces/{workspace_id}
  POST   /api/v1/workspaces/{workspace_id}/members
  DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}

Policies (Security Officer):
  POST   /api/v1/policies/upload              # multipart/form-data: OVAL/XCCDF/XML/text
  POST   /api/v1/policies/import/github       # Import from GitHub repo
  POST   /api/v1/policies/import/sharepoint   # Import from SharePoint/OneDrive
  POST   /api/v1/policies/import/confluence   # Import from Confluence
  GET    /api/v1/policies
  GET    /api/v1/policies/{policy_id}
  GET    /api/v1/policies/{policy_id}/rules
  GET    /api/v1/policies/{policy_id}/rules/{rule_id}
  DELETE /api/v1/policies/{policy_id}

Solution Types (Development Stage — per solution type):
  POST   /api/v1/solution-types
  GET    /api/v1/solution-types
  GET    /api/v1/solution-types/{type_id}
  POST   /api/v1/solution-types/{type_id}/config        # Upload representative config JSON
  GET    /api/v1/solution-types/{type_id}/components    # Hierarchical component tree
  PUT    /api/v1/solution-types/{type_id}/components/selection  # Select components to harden
  DELETE /api/v1/solution-types/{type_id}

Hardening Profiles (Development Stage output):
  POST   /api/v1/profiles                               # Create profile for type + policy
  GET    /api/v1/profiles
  GET    /api/v1/profiles/{profile_id}
  POST   /api/v1/profiles/{profile_id}/generate         # Trigger LLM code gen (all rules)
  GET    /api/v1/profiles/{profile_id}/rules
  GET    /api/v1/profiles/{profile_id}/rules/{rule_id}
  PUT    /api/v1/profiles/{profile_id}/rules/{rule_id}/code          # HITL manual edit
  POST   /api/v1/profiles/{profile_id}/rules/{rule_id}/regenerate    # Re-gen with comments
  POST   /api/v1/profiles/{profile_id}/rules/{rule_id}/approve
  POST   /api/v1/profiles/{profile_id}/rules/{rule_id}/reject
  POST   /api/v1/profiles/{profile_id}/rules/{rule_id}/comment
  DELETE /api/v1/profiles/{profile_id}

Solution Instances (Enforcement Stage):
  POST   /api/v1/instances
  GET    /api/v1/instances
  GET    /api/v1/instances/{instance_id}
  POST   /api/v1/instances/{instance_id}/config         # Upload instance config JSON
  DELETE /api/v1/instances/{instance_id}

  # Enforcement Operations (async — return job_id; track via WebSocket):
  POST   /api/v1/instances/{instance_id}/evaluate
  POST   /api/v1/instances/{instance_id}/remediate
  POST   /api/v1/instances/{instance_id}/remediate/dry-run
  POST   /api/v1/instances/{instance_id}/rollback
  POST   /api/v1/instances/{instance_id}/impact-assessment

  # Jobs & Reports:
  GET    /api/v1/instances/{instance_id}/jobs
  GET    /api/v1/instances/{instance_id}/jobs/{job_id}
  GET    /api/v1/instances/{instance_id}/reports
  GET    /api/v1/instances/{instance_id}/reports/{report_id}
  GET    /api/v1/instances/{instance_id}/reports/{report_id}/download  # ARF XML download

WebSocket (real-time streaming):
  WS     /ws/profiles/{profile_id}/generate            # Stream LLM code gen progress per rule
  WS     /ws/instances/{instance_id}/jobs/{job_id}     # Stream enforcement job progress
```

### RBAC Role Matrix

| Operation | Admin | Security Officer | Auditor | User |
|-----------|:-----:|:----------------:|:-------:|:----:|
| Create/manage policies | ✓ | ✓ | | |
| Import policies (GitHub/SharePoint/Confluence) | ✓ | ✓ | | |
| Create solution types | ✓ | | | ✓ |
| Upload representative config | ✓ | ✓ | | ✓ |
| Select components to harden | ✓ | ✓ | | ✓ |
| Generate rule code (LLM) | ✓ | ✓ | | |
| HITL review / edit / approve rules | ✓ | ✓ | | |
| Create / manage hardening profiles | ✓ | ✓ | | |
| Create solution instances | ✓ | | | ✓ |
| Upload instance config | ✓ | | | ✓ |
| Run evaluation | ✓ | ✓ | ✓ | |
| Run impact assessment | ✓ | ✓ | ✓ | |
| Run remediation dry-run | ✓ | ✓ | | |
| Run remediation | ✓ | ✓ | | |
| Run rollback | ✓ | ✓ | | |
| Manage workspaces / members | ✓ | | | |
| Manage users / roles | ✓ | | | |
| View reports | ✓ | ✓ | ✓ | ✓ |

### Connector Abstraction Pattern

```python
# backend/aegis/services/connectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int

class BaseConnector(ABC):
    def __init__(self, component_config: dict):
        self.config = component_config

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def execute(self, command: str) -> CommandResult: ...

    @abstractmethod
    def get_config(self, path: str) -> Any: ...

    @abstractmethod
    def set_config(self, path: str, value: Any) -> None: ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
```

**Connector Implementations:**

| Connector Class | Target | Protocol | Library |
|----------------|--------|----------|---------|
| `SSHConnector` | Linux VMs/Servers, Hypervisor KVM | SSH | Paramiko |
| `RedfishConnector` | iLO BMC, BIOS, SRController | HTTPS/Redfish | requests |
| `NetmikoConnector` | Aruba AOS-CX/S, Juniper | SSH | Netmiko |
| `KubernetesConnector` | k8s API server | HTTPS | kubernetes-client |
| `VaultConnector` | HashiCorp Vault | HTTPS | hvac |
| `StepCAConnector` | StepCA | HTTPS REST | requests |
| `AlletraConnector` | HPE Alletra 10k Storage | HTTPS REST | requests |
| `MorpheusConnector` | HPE Morpheus | HTTPS REST | requests |
| `PDUConnector` | HPE/APC PDU | SNMP/HTTPS | pysnmp/requests |
| `ESXiConnector` | VMware ESXi Hypervisor | SSH + HTTPS | Paramiko + pyVmomi |

### Endpoint Connectivity Requirements

| Component Type | Protocol | Library | Authentication |
|---------------|----------|---------|----------------|
| Linux VMs / Servers | SSH | Paramiko 3.x | Key or password |
| iLO BMC (5/6) | HTTPS/Redfish | requests | Basic auth or session token |
| BIOS (UEFI) | HTTPS/Redfish via iLO | requests | iLO credentials |
| SRController (MR/SR) | HTTPS/Redfish | requests | iLO credentials |
| VMware ESXi | SSH + HTTPS | Paramiko + pyVmomi | SSH key + vSphere session |
| Aruba Switch (AOS-CX) | SSH + REST | Netmiko + requests | SSH credentials + API token |
| Alletra 10k Storage | HTTPS REST | requests | API token |
| HPE PDU | SNMP v3 / HTTPS | pysnmp / requests | SNMP community / basic auth |
| Kubernetes | HTTPS | kubernetes-client | Kubeconfig / service account token |
| StepCA | HTTPS REST | requests | Admin token |
| HashiCorp Vault | HTTPS REST | hvac | AppRole / token |
| Morpheus | HTTPS REST | requests | API token |
| NVIDIA GPU nodes | SSH + DCGM REST | Paramiko + requests | SSH key |

### Security Hardening Standards Supported

| Standard | Format | Parser | Scope |
|----------|--------|--------|-------|
| CIS Benchmarks | XCCDF + OVAL | `xccdf_parser.py` + `oval_parser.py` | OS, hypervisor, network, cloud |
| DISA STIG | XCCDF + OVAL | `xccdf_parser.py` + `oval_parser.py` | OS, network, firmware |
| DISA SRG | XCCDF (no OVAL) | `xccdf_parser.py` | Policy-level guidance |
| Custom / English text | Plain text / JSON | `text_parser.py` (LLM-assisted) | HPE-specific rules |

### LLM Code Generation Pipeline

```
Policy Rule (OVAL/XCCDF/text)
    → Policy Parser → Normalized PolicyRule object
    → MilvusDB semantic search: retrieve top-K similar rules with approved code
    → Prompt Construction: rule + retrieved context + component type + protocol
    → Ollama (CodeLlama 34B or Llama3 70B) → streaming token output via WebSocket
    → Python AST syntax validation
    → Store in HardeningProfile (status: "generated")
    → HITL Review (Monaco Editor):
        - Approve → status: "approved" → ready for enforcement
        - Comment → re-generate with comments as additional context
        - Manual edit + save → status: "reviewed" → approve
    → Approved code stored locally in DB and vector store (as future reference examples)
```

### Remediation Safety Pipeline

**Impact Assessment (prerequisite for dry-run and remediation):**
```python
# NetworkX directed graph: nodes = services, edges = communication channels
G = nx.DiGraph()
for channel in topology["communication_channels"]:
    G.add_edge(channel["source"], channel["target"],
               protocol=channel["protocol"],
               tls_versions=channel["tls_versions"],
               cipher_suites=channel["cipher_suites"],
               port=channel["port"])

# For a given rule affecting TLS configuration:
affected_edges = [(u, v, d) for u, v, d in G.edges(data=True)
                  if "TLS1.1" in d.get("tls_versions", [])]
# → Impacted channel table: source, target, protocol, risk_score
```

**Dry-Run Algorithm:**
```
For each rule selected for remediation:
1. Retrieve rule.risk_score and rule.affected_protocols/settings
2. Query impact assessment graph: find all communication channels using affected settings
3. For each channel: check post-hardening compatibility
   - If rule disables TLS 1.1 and channel uses TLS 1.1 only → BREAK (high risk)
   - If rule disables IPMI and service depends on IPMI → BREAK (critical)
4. Aggregate: List[{rule_id, risk_score, impacted_channels, break_risk, explanation}]
5. Return dry-run report: safe_rules[], risky_rules[], breaking_rules[]
6. UI shows RED/Orange/Green per rule before user confirms actual remediation
```

### Reporting

- **OpenSCAP ARF XML**: `<arf:asset-report-collection>` with XCCDF results per component; downloadable from API
- **HTML Report**: OpenSCAP-generated `report.html` with per-rule PASS/FAIL table
- **Graphical Dashboard**: React + Recharts — RED (Failed/Critical), Orange (Failed/Medium), Green (Passed) compliance gauge per hierarchy layer (Rack → Server → Component)
- **Report scope**: per-component, per-rack, per-solution-instance, and aggregate views

### Project Directory Structure

```
Aegis-SecurityHardening/
├── backend/
│   ├── aegis/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI app entry point
│   │   ├── config.py                     # Pydantic BaseSettings
│   │   ├── database.py                   # SQLAlchemy async engine + session factory
│   │   ├── worker.py                     # Celery app definition
│   │   │
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── workspaces.py
│   │   │   ├── policies.py
│   │   │   ├── solution_types.py
│   │   │   ├── profiles.py               # Hardening profiles (Dev Stage)
│   │   │   ├── instances.py              # Solution instances + enforcement (Enforcement Stage)
│   │   │   └── websockets.py             # WS: LLM streaming + enforcement progress
│   │   │
│   │   ├── models/                       # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── workspace.py
│   │   │   ├── policy.py
│   │   │   ├── policy_rule.py
│   │   │   ├── solution_type.py
│   │   │   ├── hardening_profile.py
│   │   │   ├── profile_rule.py           # Rule code per profile
│   │   │   ├── hitl_comment.py
│   │   │   ├── solution_instance.py
│   │   │   ├── enforcement_job.py
│   │   │   └── compliance_report.py
│   │   │
│   │   ├── schemas/                      # Pydantic v2 request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── workspace.py
│   │   │   ├── policy.py
│   │   │   ├── solution_type.py
│   │   │   ├── profile.py
│   │   │   └── instance.py
│   │   │
│   │   ├── services/
│   │   │   ├── policy_parser/
│   │   │   │   ├── oval_parser.py        # OVAL XML → PolicyRule list (lxml)
│   │   │   │   ├── xccdf_parser.py       # XCCDF XML → PolicyRule list (lxml)
│   │   │   │   └── text_parser.py        # English/JSON text → PolicyRule via LLM
│   │   │   │
│   │   │   ├── llm/
│   │   │   │   ├── client.py             # Ollama OpenAI-compat client + LangChain
│   │   │   │   ├── code_generator.py     # LLM code gen orchestration
│   │   │   │   ├── prompts.py            # Prompt templates per component type
│   │   │   │   └── milvus_store.py       # pymilvus: embed + retrieve policy context
│   │   │   │
│   │   │   ├── connectors/
│   │   │   │   ├── base.py               # Abstract BaseConnector
│   │   │   │   ├── ssh_connector.py      # Paramiko SSH
│   │   │   │   ├── redfish_connector.py  # HPE iLO/BIOS/SRController Redfish
│   │   │   │   ├── netmiko_connector.py  # Aruba/Juniper network switches
│   │   │   │   ├── kubernetes_connector.py
│   │   │   │   ├── vault_connector.py    # hvac: credential retrieval
│   │   │   │   └── rest_connector.py     # Generic HTTPS REST (Alletra, StepCA, etc.)
│   │   │   │
│   │   │   ├── enforcement/
│   │   │   │   ├── evaluator.py          # Execute evaluate() functions
│   │   │   │   ├── remediator.py         # Execute remediate() + pre-state capture
│   │   │   │   ├── rollback.py           # Execute rollback() from saved state
│   │   │   │   ├── dry_run.py            # Risk scoring + breaking change detection
│   │   │   │   └── impact_assessment.py  # NetworkX topology graph + channel analysis
│   │   │   │
│   │   │   ├── reporting/
│   │   │   │   ├── arf_generator.py      # OpenSCAP ARF XML report generation
│   │   │   │   └── html_generator.py     # HTML compliance report
│   │   │   │
│   │   │   └── rbac.py                   # FastAPI dependency: role enforcement
│   │   │
│   │   └── tasks/
│   │       ├── enforcement_tasks.py      # Celery tasks: evaluate/remediate/rollback
│   │       └── codegen_tasks.py          # Celery tasks: LLM code generation
│   │
│   ├── migrations/                       # Alembic migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PolicyManager/            # Upload, import, view, manage policies
│   │   │   ├── SolutionTypeBuilder/      # Create solution type; component selection UI
│   │   │   ├── HardeningProfileEditor/   # HITL code review/edit interface
│   │   │   │   ├── RuleList.tsx
│   │   │   │   ├── RuleCodeEditor.tsx    # Monaco Editor: eval/remediate/rollback code
│   │   │   │   ├── DiffViewer.tsx        # Monaco diff: LLM-generated vs. edited
│   │   │   │   └── CommentThread.tsx     # HITL comment → re-gen workflow
│   │   │   ├── InstanceManager/          # Upload instance config; manage instances
│   │   │   ├── ComplianceDashboard/      # RED/Orange/Green hierarchy visualization
│   │   │   │   ├── HierarchyTree.tsx     # Rack → Server → Component tree
│   │   │   │   ├── ComplianceGauge.tsx   # Recharts gauge per layer
│   │   │   │   └── ReportDownload.tsx    # ARF XML + HTML download
│   │   │   ├── EnforcementConsole/       # Run eval/remediate/rollback
│   │   │   │   ├── ImpactAssessmentTable.tsx
│   │   │   │   ├── DryRunResults.tsx     # Risk table: safe/risky/breaking rules
│   │   │   │   └── TopologyGraph.tsx     # React Flow: service dependency visualization
│   │   │   └── UserManagement/
│   │   ├── pages/
│   │   ├── services/                     # Axios API client services
│   │   ├── hooks/                        # Custom React hooks (useWebSocket, useQuery)
│   │   └── types/                        # TypeScript type definitions
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

### Infrastructure Configuration

**Docker Compose (local dev + production):**
```yaml
version: '3.9'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: aegis
      POSTGRES_USER: aegis
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}

  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"

  minio:
    image: minio/minio:RELEASE.2024-01-01T00-00-00Z
    command: server /data --console-address :9001
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}

  milvus:
    image: milvusdb/milvus:v2.4.0
    command: milvus run standalone
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    depends_on: [etcd, minio]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama_models:/root/.ollama]
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: all, capabilities: [gpu]}]

  aegis-api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://aegis:${POSTGRES_PASSWORD}@postgres/aegis
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      MILVUS_HOST: milvus
      OLLAMA_BASE_URL: http://ollama:11434
      SECRET_KEY: ${SECRET_KEY}
    depends_on: [postgres, redis, milvus, ollama]

  aegis-worker:
    build: ./backend
    command: celery -A aegis.worker worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql+asyncpg://aegis:${POSTGRES_PASSWORD}@postgres/aegis
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on: [redis, postgres]

  aegis-ui:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      VITE_API_URL: http://localhost:8000

volumes:
  postgres_data:
  milvus_data:
  ollama_models:
```

**Python Dependencies (`requirements.txt`):**
```
# Web framework
fastapi==0.111.0
uvicorn[standard]==0.30.0
websockets==12.0

# Database
sqlalchemy[asyncio]==2.0.31
alembic==1.13.2
asyncpg==0.29.0
psycopg2-binary==2.9.9

# Task queue
celery==5.4.0
redis==5.0.7

# LLM and vector store
openai==1.35.0          # OpenAI-compatible client for Ollama
langchain==0.2.6
langchain-community==0.2.6
pymilvus==2.4.3

# Security and auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# Endpoint connectors
paramiko==3.4.0
netmiko==4.4.0
requests==2.32.3
kubernetes==30.1.0
hvac==2.3.0
pyVmomi==8.0.2

# Policy parsing
lxml==5.2.2

# Network analysis
networkx==3.3

# Utility
pydantic-settings==2.3.4
python-dotenv==1.0.1
aiofiles==23.2.1
```

**Frontend Dependencies (`package.json`):**
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "typescript": "^5.5.3",
    "@tanstack/react-query": "^5.50.0",
    "axios": "^1.7.2",
    "@monaco-editor/react": "^4.6.0",
    "react-flow-renderer": "^11.11.4",
    "recharts": "^2.12.7",
    "react-router-dom": "^6.25.0",
    "@radix-ui/react-dialog": "^1.1.1",
    "tailwindcss": "^3.4.6",
    "lucide-react": "^0.400.0"
  }
}
```

## Recommended Approach

**Full-Stack Python + React AI Agentic Architecture** — the single recommended implementation approach:

- **Backend**: FastAPI (async, WebSocket streaming, RBAC injection) + Celery (distributed enforcement tasks) + PostgreSQL (relational metadata) + Redis (task broker + caching)
- **LLM Runtime**: Ollama with CodeLlama 34B or Llama3 70B — mandatory for HPE air-gapped Private Cloud; OpenAI-compatible API allows future migration to hosted OpenAI with config-only change
- **Orchestration**: LangChain for retrieval-augmented code generation (RAG): MilvusDB stores policy rule embeddings; retrieval of top-K similar approved rules provides few-shot examples
- **Policy Engine**: OpenSCAP (`oscap` CLI) for native OVAL/XCCDF evaluation on Linux OS endpoints; Custom Python connector-based execution for non-Linux targets (iLO, switches, storage)
- **HITL Interface**: React 18 + Monaco Editor for professional in-browser code editing; WebSocket for real-time LLM token streaming; structured comment threads for Security Officer review workflow
- **Remediation Safety**: NetworkX graph for impact assessment topology; per-rule risk scoring; dry-run produces RED/Orange/Green risk table before any actual changes applied
- **Reporting**: OpenSCAP ARF XML (industry-standard, compatible with STIG Viewer) + React Recharts dashboard with hierarchical RED/Orange/Green compliance visualization

## Implementation Guidance

- **Objectives**: Build complete AEGIS application covering both Development Stage (LLM code gen + HITL review) and Enforcement Stage (evaluate/remediate/rollback on real HPE Private Cloud endpoints)
- **Key Tasks**:
  1. Project scaffold: monorepo `backend/` (FastAPI + Celery) + `frontend/` (React + Vite + TypeScript)
  2. Infrastructure: Docker Compose with PostgreSQL 16, Redis 7, MilvusDB 2.4, Ollama, etcd, MinIO
  3. Database: SQLAlchemy async ORM models + Alembic migrations for all entities
  4. Auth: JWT + OAuth2 + bcrypt; RBAC FastAPI dependency covering all 4 roles
  5. Policy parsers: `oval_parser.py` (lxml), `xccdf_parser.py` (lxml), `text_parser.py` (LLM-assisted)
  6. LLM service: Ollama client via LangChain; MilvusDB RAG retrieval; code gen prompts per component type
  7. Connector library: SSH (Paramiko), Redfish (requests), Netmiko (switches), kubernetes-client, hvac, REST
  8. Enforcement engine: evaluator, remediator (with pre-state capture), rollback, dry-run, impact assessment
  9. OpenSCAP ARF report generation + HTML dashboard
  10. Full REST API: all endpoints with RBAC enforcement
  11. WebSocket: streaming code gen progress + enforcement job progress
  12. React frontend: PolicyManager, SolutionTypeBuilder, HardeningProfileEditor (Monaco HITL), InstanceManager, ComplianceDashboard, EnforcementConsole
  13. Policy import integrations: GitHub, SharePoint/OneDrive, Confluence
- **Dependencies**: All Python packages in `requirements.txt` above; all npm packages in `package.json` above; Docker Compose infrastructure
- **Success Criteria**:
  - Policy upload (OVAL/XCCDF) → rules parsed and displayed with severity, category, description
  - LLM generates `evaluate()`/`remediate()`/`rollback()` Python code for each rule per component type
  - HITL: Security Officer can view code in Monaco Editor, add comments, trigger re-generation, hand-edit, and approve
  - Solution instance config JSON upload → hierarchical component tree displayed; Evaluation runs against real endpoints
  - Impact assessment generates service communication channel table with TLS/protocol details
  - Remediation dry-run identifies breaking changes with risk scores before execution
  - Rollback restores pre-remediation state using captured pre-state from `remediate()`
  - Compliance report generated in OpenSCAP ARF XML format with downloadable HTML report and RED/Orange/Green dashboard
  - RBAC enforced: Security Officer manages policies/code, Auditor runs evaluation only, User manages instances
  - Solution instance scope enforced: only owner and collaborators can access an instance
