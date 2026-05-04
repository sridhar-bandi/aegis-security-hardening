---
applyTo: ".copilot-tracking/changes/20260504-project-aegis-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Project Aegis - AI Agentic Security Hardening Solution

## Overview

Build AEGIS, a full-stack AI Agentic security hardening application for HPE Private Cloud solutions (PCE, PCAI), with a Development Stage (LLM code generation + HITL review) and an Enforcement Stage (evaluate/remediate/rollback on real endpoints).

## Objectives

- Deliver a production-ready monorepo application: `backend/` (FastAPI + Celery + Python 3.12) + `frontend/` (React 18 + TypeScript + Vite)
- Implement LLM-driven (Ollama + CodeLlama) generation of `evaluate()`, `remediate()`, `rollback()` Python functions for each policy rule x component type pair
- Provide a HITL Monaco Editor interface for Security Officers to review, comment, regenerate, edit, and approve generated code
- Support CIS Benchmarks, DISA STIG, SRG, and custom English-text policies in OVAL/XCCDF/text formats
- Execute enforcement operations (evaluate, remediate, rollback) against real HPE Private Cloud endpoints (iLO, OS VMs, Aruba switches, Kubernetes, Vault, Alletra storage)
- Implement Remediation Impact Assessment (NetworkX topology graph) and Dry-Run (breaking change detection) before any remediation
- Generate OpenSCAP-compatible ARF XML compliance reports with RED/Orange/Green hierarchy dashboard
- Enforce RBAC (Admin, Security Officer, Auditor, User) and workspace-scoped access control

## Research Summary

### Project Files

- `.github/instructions/task-implementation.instructions.md` — Implementation tracking and progressive changes file standards
- `.copilot-tracking/research/20260504-project-aegis-research.md` — Comprehensive technology stack, API design, directory structure, and implementation patterns

### External References

- #file:../research/20260504-project-aegis-research.md — Full research findings: technology stack decisions, REST API endpoints, RBAC matrix, connector abstractions, LLM pipeline, dry-run algorithm, ARF reporting

### Standards References

- #file:../../.github/instructions/task-implementation.instructions.md — Progressive tracking in `.copilot-tracking/changes/`; plan-driven development with checklist completion

## Implementation Checklist

### [x] Phase 1: Project Scaffold & Infrastructure

- [x] Task 1.1: Create Monorepo Directory Structure
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 13-65)

- [x] Task 1.2: Docker Compose Infrastructure
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 66-85)

### [x] Phase 2: Backend Foundation

- [x] Task 2.1: FastAPI Application Core
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 88-106)

- [x] Task 2.2: SQLAlchemy ORM Models
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 107-133)

- [x] Task 2.3: Alembic Migrations
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 134-149)

- [x] Task 2.4: Pydantic v2 Request/Response Schemas
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 150-171)

- [x] Task 2.5: JWT Authentication & RBAC Middleware
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 172-189)

### [x] Phase 3: Policy Parsing Service

- [x] Task 3.1: OVAL XML Parser
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 192-206)

- [x] Task 3.2: XCCDF XML Parser
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 207-222)

- [x] Task 3.3: English/Text Policy Parser (LLM-Assisted)
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 223-239)

### [x] Phase 4: LLM & Vector Store Service

- [x] Task 4.1: Ollama LLM Client
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 242-256)

- [x] Task 4.2: MilvusDB Vector Store
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 257-271)

- [x] Task 4.3: LLM Code Generator & Prompt Templates
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 272-288)

- [x] Task 4.4: Celery Code Generation Tasks
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 289-305)

### [x] Phase 5: Connector Library

- [x] Task 5.1: BaseConnector Abstract Class & Result Types
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 308-322)

- [x] Task 5.2: SSH & Redfish Connectors
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 323-338)

- [x] Task 5.3: Network, Kubernetes, Vault & REST Connectors
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 339-359)

### [x] Phase 6: Enforcement Engine

- [x] Task 6.1: Evaluator Service
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 362-376)

- [x] Task 6.2: Remediator Service
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 377-391)

- [x] Task 6.3: Rollback Service
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 392-406)

- [x] Task 6.4: Impact Assessment Service
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 407-421)

- [x] Task 6.5: Remediation Dry-Run Engine
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 422-436)

- [x] Task 6.6: Celery Enforcement Tasks
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 437-452)

### [x] Phase 7: Reporting

- [x] Task 7.1: OpenSCAP ARF XML Report Generator
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 455-469)

- [x] Task 7.2: Compliance Summary & HTML Report Generator
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 470-486)

### [x] Phase 8: REST API Layer

- [x] Task 8.1: Auth, Users & Workspaces Routers
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 489-507)

- [x] Task 8.2: Policies, Solution Types & Hardening Profiles Routers
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 508-526)

- [x] Task 8.3: Solution Instances & Enforcement Routers
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 527-542)

- [x] Task 8.4: WebSocket Handlers
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 543-559)

### [x] Phase 9: React Frontend

- [x] Task 9.1: Frontend Project Setup
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 562-585)

- [x] Task 9.2: Authentication Pages & Layout
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 586-603)

- [x] Task 9.3: Policy Manager Component
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 604-621)

- [x] Task 9.4: Solution Type Builder Component
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 622-641)

- [x] Task 9.5: Hardening Profile Editor (HITL Interface)
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 642-664)

- [x] Task 9.6: Instance Manager & Compliance Dashboard
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 665-688)

- [x] Task 9.7: Enforcement Console, Impact Assessment, Dry-Run & User Management
  - Details: .copilot-tracking/details/20260504-project-aegis-details.md (Lines 689-733)

## Dependencies

- Python 3.12, Node.js 20, Docker, Docker Compose v2
- PostgreSQL 16, Redis 7, MilvusDB 2.4, Ollama (CodeLlama 34B / Llama3 70B)
- Python packages: fastapi, celery, sqlalchemy, alembic, asyncpg, paramiko, netmiko, requests, kubernetes, hvac, pymilvus, openai, langchain, lxml, networkx, pydantic-settings, aiofiles
- npm packages: react 18, typescript, @monaco-editor/react, reactflow, recharts, @tanstack/react-query, axios, tailwindcss, react-router-dom, lucide-react

## Success Criteria

- Policy upload (OVAL/XCCDF) → rules parsed and displayed with severity, category, and target component types
- LLM generates `evaluate()`/`remediate()`/`rollback()` Python functions per rule per component type; code passes `ast.parse()` validation
- HITL: Monaco Editor renders Python code; Security Officer can comment, regenerate, hand-edit, and approve; WebSocket streams token progress in real time
- Solution instance config JSON upload → hierarchical component tree displayed; Evaluation runs against real endpoints via correct connector (SSH/Redfish/Netmiko/k8s)
- Impact assessment builds NetworkX topology graph from `network_topology.communication_channels`; dry-run detects TLS/protocol/permission breaking changes before execution
- Rollback restores pre-remediation state from `saved_state` captured in `remediate()`
- Compliance report: OpenSCAP ARF XML downloadable; HTML report with RED/Orange/Green hierarchy dashboard (Rack → Server → Component)
- RBAC enforced: Security Officer manages policies/code, Auditor runs evaluation only, User manages instances, Admin does everything
- Workspace scope: only owner and collaborators can access solution instances

