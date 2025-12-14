# Technical Requirements Document (TRD)

## DSDM Agents - AI-Powered Software Development Framework

**Version:** 1.0.0
**Date:** December 2025
**Status:** Draft for Review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Technical Specifications](#6-technical-specifications)
7. [Integration Requirements](#7-integration-requirements)
8. [Security Requirements](#8-security-requirements)
9. [Data Requirements](#9-data-requirements)
10. [Deployment Requirements](#10-deployment-requirements)
11. [Testing Requirements](#11-testing-requirements)
12. [Appendices](#12-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This Technical Requirements Document defines the technical specifications, architecture, and requirements for the DSDM Agents system - an AI-powered software development framework that implements the Dynamic Systems Development Method (DSDM) methodology using autonomous AI agents.

### 1.2 Scope

The system provides:
- **5 DSDM Phase Agents**: Feasibility, Business Study, Functional Model, Design & Build, Implementation
- **7 Specialized Development Agents**: DevOps, Dev Lead, Frontend Developer, Backend Developer, Automation Tester, NFR Tester, Penetration Tester
- **Multi-Provider LLM Support**: Anthropic Claude, OpenAI GPT, Google Gemini, Ollama (local)
- **Tool Integrations**: Jira, Confluence, File Operations, DevOps Tools

### 1.3 Intended Audience

- Software Architects
- Development Team Leads
- DevOps Engineers
- Project Managers
- Quality Assurance Teams

---

## 2. System Overview

### 2.1 System Description

DSDM Agents is a Python-based framework that orchestrates AI agents to assist in software development following DSDM principles. Each agent specializes in a specific phase or role, using tools to analyze requirements, generate code, run tests, and manage deployments.

### 2.2 Key Features

| Feature | Description |
|---------|-------------|
| **Phase-Based Workflow** | Sequential execution through DSDM phases with handoff between agents |
| **MoSCoW Prioritization** | Built-in support for Must/Should/Could/Won't requirement classification |
| **Code Generation** | Agents can write production-quality code to disk |
| **Tool Extensibility** | Pluggable tool system for custom integrations |
| **Multi-Provider LLM** | Switch between AI providers without code changes |
| **Interactive & Automated Modes** | Run manually, automated, or hybrid |

### 2.3 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Systems                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  Jira    │  │Confluence│  │  GitHub  │  │   LLM Providers      │ │
│  │  API     │  │   API    │  │   API    │  │ (Anthropic/OpenAI/   │ │
│  │          │  │          │  │          │  │  Gemini/Ollama)      │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘ │
│       │             │             │                    │             │
└───────┼─────────────┼─────────────┼────────────────────┼─────────────┘
        │             │             │                    │
        ▼             ▼             ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DSDM Agents System                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                     Orchestrator Layer                          ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   ││
│  │  │ Phase Manager │  │ Agent Factory │  │ Workflow Engine   │   ││
│  │  └───────────────┘  └───────────────┘  └───────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                       Agent Layer                                ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐││
│  │  │Feasibility│ │ Business │ │Functional│ │ Design & │ │Implement│││
│  │  │  Agent   │ │  Study   │ │  Model   │ │  Build   │ │  Agent ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐││
│  │  │ DevOps   │ │ Dev Lead │ │ Frontend │ │ Backend  │ │ Testers│││
│  │  │  Agent   │ │  Agent   │ │Developer │ │Developer │ │ Agents ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                        Tool Layer                                ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐││
│  │  │  DSDM    │ │   File   │ │   Jira   │ │Confluence│ │ DevOps │││
│  │  │  Tools   │ │   Tools  │ │  Tools   │ │  Tools   │ │ Tools  ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                        LLM Layer                                 ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐││
│  │  │ Anthropic│ │  OpenAI  │ │  Gemini  │ │       Ollama         │││
│  │  │  Client  │ │  Client  │ │  Client  │ │      Client          ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Generated Output                                │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  generated/                                                      ││
│  │  └── <project_name>/                                             ││
│  │      ├── src/                    # Application source code       ││
│  │      ├── tests/                  # Test suites                   ││
│  │      ├── docs/                   # Generated documentation       ││
│  │      ├── config/                 # Configuration files           ││
│  │      └── infrastructure/         # IaC and deployment files      ││
│  └──────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture

### 3.1 Component Architecture

#### 3.1.1 Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Orchestrator** | `src/orchestrator/` | Manages workflow execution, phase transitions, agent coordination |
| **Base Agent** | `src/agents/base_agent.py` | Abstract base class for all agents with LLM integration |
| **Phase Agents** | `src/agents/*_agent.py` | DSDM phase-specific agents |
| **Tool Registry** | `src/tools/tool_registry.py` | Central registry for tool management |
| **LLM Providers** | `src/llm/providers.py` | Multi-provider LLM abstraction |
| **File Tools** | `src/tools/file_tools.py` | File system operations for code generation |

#### 3.1.2 Agent Hierarchy

```
BaseAgent (Abstract)
├── FeasibilityAgent
├── BusinessStudyAgent
├── FunctionalModelAgent
├── DesignBuildAgent
├── ImplementationAgent
├── DevOpsAgent
├── DevLeadAgent
├── FrontendDeveloperAgent
├── BackendDeveloperAgent
├── AutomationTesterAgent
├── NFRTesterAgent
└── PenTesterAgent
```

### 3.2 Data Flow

```
User Input → Orchestrator → Phase Agent → LLM Client → Tool Execution → Output
                 ↑                              ↓
                 └────────── Tool Results ──────┘
```

### 3.3 Directory Structure

```
dsdm-agents/
├── main.py                      # CLI entry point
├── src/
│   ├── agents/                  # Agent implementations
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Base agent class
│   │   ├── feasibility_agent.py
│   │   ├── business_study_agent.py
│   │   ├── functional_model_agent.py
│   │   ├── design_build_agent.py
│   │   ├── implementation_agent.py
│   │   ├── devops_agent.py
│   │   ├── dev_lead_agent.py
│   │   ├── frontend_developer_agent.py
│   │   ├── backend_developer_agent.py
│   │   ├── automation_tester_agent.py
│   │   ├── nfr_tester_agent.py
│   │   └── pen_tester_agent.py
│   ├── orchestrator/            # Workflow orchestration
│   │   ├── __init__.py
│   │   └── dsdm_orchestrator.py
│   ├── tools/                   # Tool implementations
│   │   ├── __init__.py
│   │   ├── tool_registry.py
│   │   ├── dsdm_tools.py
│   │   ├── file_tools.py
│   │   └── integrations/
│   │       ├── jira_tools.py
│   │       ├── confluence_tools.py
│   │       └── devops_tools.py
│   ├── llm/                     # LLM provider abstraction
│   │   ├── __init__.py
│   │   └── providers.py
│   └── utils/                   # Utility modules
│       ├── __init__.py
│       └── output_formatter.py
├── generated/                   # Agent-generated code output
│   └── <project_name>/
│       ├── src/
│       ├── tests/
│       └── docs/
├── docs/                        # Project documentation
├── examples/                    # Example requirements files
└── tests/                       # Framework tests
```

---

## 4. Functional Requirements

### 4.1 Agent Requirements

#### FR-001: Phase Agent Execution
- **Priority**: Must Have
- **Description**: System shall execute DSDM phase agents in sequence: Feasibility → Business Study → Functional Model → Design & Build → Implementation
- **Acceptance Criteria**:
  - Each phase agent receives input from previous phase
  - Phase results are persisted for handoff
  - Failed phases halt workflow with clear error message

#### FR-002: Specialized Agent Invocation
- **Priority**: Must Have
- **Description**: Design & Build phase shall support invoking specialized agents (Dev Lead, Frontend, Backend, Testers)
- **Acceptance Criteria**:
  - Dev Lead coordinates other specialized agents
  - Agents can be run individually or as a team
  - Results from each agent are aggregated

#### FR-003: Tool Execution
- **Priority**: Must Have
- **Description**: Agents shall execute tools based on LLM decisions
- **Acceptance Criteria**:
  - Tools are registered with name, schema, and handler
  - Tool calls include input validation
  - Tool results returned to LLM for next decision

#### FR-004: Code Generation
- **Priority**: Must Have
- **Description**: Development agents shall write code files to disk
- **Acceptance Criteria**:
  - Files written to `generated/<project>/` directory
  - Parent directories created automatically
  - Overwrite protection with explicit flag

### 4.2 Workflow Requirements

#### FR-005: Interactive Mode
- **Priority**: Must Have
- **Description**: System shall provide interactive menu for phase selection
- **Acceptance Criteria**:
  - User can select individual phases
  - User can run full workflow
  - Progress displayed in terminal

#### FR-006: Automated Mode
- **Priority**: Must Have
- **Description**: System shall run workflows non-interactively
- **Acceptance Criteria**:
  - CLI arguments specify phase and input
  - No user prompts during execution
  - Exit codes indicate success/failure

#### FR-007: Hybrid Mode
- **Priority**: Should Have
- **Description**: System shall support approval-required tools
- **Acceptance Criteria**:
  - Tools marked `requires_approval=True` prompt user
  - Approval callback customizable
  - Non-approved tools skipped with message

### 4.3 Integration Requirements

#### FR-008: Jira Integration
- **Priority**: Should Have
- **Description**: System shall create/update Jira issues and sprints
- **Acceptance Criteria**:
  - Create issues with summary, description, type
  - Assign issues to sprints
  - Update issue status

#### FR-009: Confluence Integration
- **Priority**: Should Have
- **Description**: System shall create/update Confluence pages
- **Acceptance Criteria**:
  - Create pages with markdown content
  - Convert markdown to storage format
  - Update existing pages by ID

#### FR-010: LLM Provider Switching
- **Priority**: Must Have
- **Description**: System shall support multiple LLM providers
- **Acceptance Criteria**:
  - Switch provider via environment variable
  - Each provider uses appropriate API format
  - Tool calling works across all providers

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NFR-001 | Agent response time | < 60 seconds per iteration | Should Have |
| NFR-002 | Tool execution time | < 10 seconds per tool | Should Have |
| NFR-003 | Max iterations | 15 per agent (configurable) | Must Have |
| NFR-004 | Memory usage | < 500MB per agent | Could Have |

### 5.2 Reliability

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NFR-005 | Error recovery | Graceful handling of LLM failures | Must Have |
| NFR-006 | State persistence | No data loss on interruption | Should Have |
| NFR-007 | Timeout handling | Configurable per provider | Must Have |

### 5.3 Usability

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NFR-008 | CLI help | --help shows all options | Must Have |
| NFR-009 | Output formatting | Rich terminal output | Should Have |
| NFR-010 | Progress indication | Show phase/iteration progress | Should Have |

### 5.4 Maintainability

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NFR-011 | Code documentation | Docstrings on all public methods | Should Have |
| NFR-012 | Type hints | Full typing coverage | Should Have |
| NFR-013 | Modular design | Single responsibility per module | Must Have |

---

## 6. Technical Specifications

### 6.1 Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Language** | Python | >= 3.10 |
| **LLM Client (Anthropic)** | anthropic | >= 0.45.0 |
| **LLM Client (OpenAI)** | openai | >= 1.0.0 (optional) |
| **LLM Client (Gemini)** | google-generativeai | >= 0.8.0 (optional) |
| **Environment** | python-dotenv | >= 1.0.0 |
| **Data Validation** | pydantic | >= 2.0.0 |
| **Terminal UI** | rich | >= 13.0.0 |
| **HTTP** | requests | >= 2.31.0 |

### 6.2 LLM Provider Configuration

#### Anthropic (Default)
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_TIMEOUT=120
```

#### OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_ORG_ID=org-... (optional)
```

#### Google Gemini
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

#### Ollama (Local/Cloud)
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=kimi-k2-thinking:cloud
OLLAMA_CODE_MODEL=codellama
```

### 6.3 Agent Configuration

```python
@dataclass
class AgentConfig:
    name: str                           # Display name
    description: str                    # Purpose description
    phase: str                          # DSDM phase
    system_prompt: str                  # LLM system prompt
    tools: List[str]                    # Available tool names
    mode: AgentMode = AUTOMATED         # Execution mode
    model: Optional[str] = None         # Override default model
    max_tokens: int = 4096              # Response length limit
    max_iterations: int = 10            # Loop limit
    llm_provider: Optional[LLMProvider] = None  # Override provider
```

### 6.4 Tool Schema

```python
@dataclass
class Tool:
    name: str                           # Unique identifier
    description: str                    # For LLM understanding
    input_schema: Dict[str, Any]        # JSON Schema for parameters
    handler: Callable[..., str]         # Execution function
    requires_approval: bool = False     # Hybrid mode flag
    category: str = "general"           # Grouping category
```

---

## 7. Integration Requirements

### 7.1 Jira Integration

#### Configuration
```env
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_DEFAULT_PROJECT=PROJ
```

#### Available Tools
| Tool | Description |
|------|-------------|
| `jira_create_issue` | Create new Jira issue |
| `jira_update_issue` | Update existing issue (auto-syncs to Confluence if enabled) |
| `jira_get_issue` | Retrieve issue details |
| `jira_search_issues` | JQL search |
| `jira_add_comment` | Add comment to issue |
| `jira_transition_issue` | Change issue status (auto-syncs to Confluence if enabled) |
| `jira_create_sprint` | Create new sprint |
| `jira_add_to_sprint` | Add issues to sprint |
| `jira_enable_confluence_sync` | Enable automatic Confluence sync |
| `jira_disable_confluence_sync` | Disable automatic Confluence sync |
| `jira_sync_to_confluence` | Manually sync issue to Confluence |
| `jira_set_confluence_page_mapping` | Map issue to specific Confluence page |

### 7.2 Confluence Integration

#### Configuration
```env
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
CONFLUENCE_DEFAULT_SPACE=SPACE
```

#### Available Tools
| Tool | Description |
|------|-------------|
| `confluence_create_page` | Create new page |
| `confluence_update_page` | Update existing page |
| `confluence_get_page` | Retrieve page content |
| `confluence_search` | CQL search |
| `confluence_add_attachment` | Upload attachment |

### 7.3 Jira-Confluence Sync Integration

When both Jira and Confluence integrations are enabled, the system supports automatic synchronization of work item status changes to Confluence documentation.

#### Configuration
Enable sync programmatically:
```python
orchestrator = DSDMOrchestrator(include_jira=True, include_confluence=True)

# Setup automatic sync
orchestrator.tool_registry.execute(
    "setup_jira_confluence_sync",
    confluence_space_key="PROJ",
    create_status_page=True
)
```

#### Sync Behavior
| Trigger | Action |
|---------|--------|
| `jira_transition_issue` | Logs status change to Confluence status page |
| `jira_update_issue` | Logs field update to Confluence status page |
| Manual `jira_sync_to_confluence` | Syncs current issue state on demand |

#### Workflow Tools
| Tool | Description |
|------|-------------|
| `setup_jira_confluence_sync` | Enable sync and optionally create status log page |
| `sync_work_item_status` | Sync with DSDM phase context |
| `get_sync_status` | Get current sync configuration |

#### Work Item Status Log Page
When sync is enabled, a "Work Item Status Log" page is created/updated in Confluence with:
- Timestamp of each status change
- Issue key and summary
- Current status
- Update type (transition, field_update, manual_sync)

#### Page Mapping
Map specific Jira issues to dedicated Confluence pages:
```python
# Map issue to its design document
orchestrator.tool_registry.execute(
    "jira_set_confluence_page_mapping",
    issue_key="PROJ-123",
    page_id="12345678"
)
```

When mapped, status updates for that issue will be added to the specific page instead of the general status log.

### 7.4 File System Integration

#### Output Structure
```
generated/
└── <project_name>/
    ├── src/                    # Source code
    │   ├── components/         # UI components
    │   ├── services/           # Business logic
    │   ├── models/             # Data models
    │   └── utils/              # Utilities
    ├── tests/                  # Test suites
    │   ├── unit/
    │   ├── integration/
    │   └── e2e/
    ├── docs/                   # Documentation
    │   ├── api/
    │   ├── architecture/
    │   └── user-guides/
    ├── config/                 # Configuration
    └── infrastructure/         # IaC files
        ├── docker/
        ├── kubernetes/
        └── terraform/
```

#### Available Tools
| Tool | Description |
|------|-------------|
| `file_write` | Write content to file |
| `file_read` | Read file content |
| `file_append` | Append to file |
| `file_delete` | Delete file |
| `file_copy` | Copy file |
| `directory_create` | Create directory |
| `directory_list` | List directory contents |

---

## 8. Security Requirements

### 8.1 API Key Management

| ID | Requirement | Implementation |
|----|-------------|----------------|
| SEC-001 | API keys stored in environment | `.env` file, not in code |
| SEC-002 | No key logging | Keys masked in any output |
| SEC-003 | Key validation | Verify keys before LLM calls |

### 8.2 Generated Code Security

| ID | Requirement | Implementation |
|----|-------------|----------------|
| SEC-004 | Input validation | Agents generate validation code |
| SEC-005 | SQL injection prevention | Parameterized queries |
| SEC-006 | XSS prevention | Output encoding |
| SEC-007 | Secret detection | No hardcoded secrets |

### 8.3 File System Security

| ID | Requirement | Implementation |
|----|-------------|----------------|
| SEC-008 | Output sandboxing | Files only in `generated/` |
| SEC-009 | Path traversal prevention | Validate relative paths |
| SEC-010 | Overwrite protection | Explicit `overwrite=True` required |

---

## 9. Data Requirements

### 9.1 Input Data

| Data Type | Format | Source |
|-----------|--------|--------|
| Requirements | Markdown | User input or file |
| Context | JSON/Dict | Previous phase output |
| Configuration | Environment variables | `.env` file |

### 9.2 Output Data

| Data Type | Format | Destination |
|-----------|--------|-------------|
| Generated Code | Various (py, ts, etc.) | `generated/<project>/` |
| Documentation | Markdown | `generated/<project>/docs/` |
| Agent Results | `AgentResult` dataclass | In-memory, optional persistence |
| Tool History | JSON | Agent `tool_call_history` |

### 9.3 Data Retention

- Generated code: Persisted until manually deleted
- Agent state: Session-only (not persisted)
- Tool history: Session-only
- LLM responses: Not stored

---

## 10. Deployment Requirements

### 10.1 Development Environment

```bash
# Prerequisites
- Python 3.10+
- pip or uv package manager
- Git

# Setup
git clone <repository>
cd dsdm-agents
python -m venv env
source env/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
```

### 10.2 Production Considerations

| Aspect | Recommendation |
|--------|----------------|
| **Containerization** | Docker support for consistent environments |
| **Secrets Management** | Use vault or cloud secrets manager |
| **Logging** | Structured logging for observability |
| **Monitoring** | Track LLM API usage and costs |

### 10.3 CI/CD Requirements

- Run linting on all Python files
- Execute unit tests before merge
- Validate tool schemas
- Check for security vulnerabilities

---

## 11. Testing Requirements

### 11.1 Test Categories

| Category | Scope | Tools |
|----------|-------|-------|
| **Unit Tests** | Individual functions, tools | pytest |
| **Integration Tests** | Agent + LLM interaction | pytest, mocking |
| **End-to-End Tests** | Full workflow execution | pytest |
| **Security Tests** | Vulnerability scanning | bandit, safety |

### 11.2 Test Coverage Targets

| Component | Target Coverage |
|-----------|-----------------|
| Tool handlers | 90% |
| Agent logic | 80% |
| Orchestrator | 80% |
| LLM clients | 70% (with mocking) |

### 11.3 Test Data

- Example requirements in `examples/`
- Mock LLM responses for deterministic testing
- Sample tool inputs/outputs

---

## 12. Appendices

### Appendix A: DSDM Phase Descriptions

| Phase | Purpose | Key Deliverables |
|-------|---------|------------------|
| **Feasibility** | Determine if project is viable | Feasibility Report, Risk Assessment |
| **Business Study** | Understand business needs | Prioritized Requirements, Architecture |
| **Functional Model** | Create working prototype | Functional Prototype, User Feedback |
| **Design & Build** | Build production system | Tested Code, Documentation |
| **Implementation** | Deploy to production | Deployed System, Training Materials |

### Appendix B: MoSCoW Prioritization

| Priority | Definition | Typical Allocation |
|----------|------------|-------------------|
| **Must Have** | Critical for success | 60% of effort |
| **Should Have** | Important but not critical | 20% of effort |
| **Could Have** | Desirable if time permits | 20% of effort |
| **Won't Have** | Out of scope this release | 0% |

### Appendix C: Agent Tools by Phase

#### Feasibility Phase
- `analyze_requirements`
- `assess_technical_feasibility`
- `estimate_resources`
- `identify_risks`
- `check_dsdm_suitability`

#### Business Study Phase
- `analyze_business_process`
- `identify_stakeholders`
- `prioritize_requirements`
- `define_architecture`
- `create_timebox_plan`
- `update_risk_log`

#### Functional Model Phase
- `create_prototype`
- `generate_code_scaffold`
- `collect_user_feedback`
- `refine_requirements`
- `run_functional_tests`
- `document_iteration`

#### Design & Build Phase
- `create_technical_design`
- `generate_code`
- `file_write` / `file_read`
- `directory_create` / `directory_list`
- `run_tests`
- `review_code`
- `security_check`
- `create_documentation`

#### Implementation Phase
- `create_deployment_plan`
- `setup_environment`
- `deploy_system`
- `run_smoke_tests`
- `create_rollback`
- `execute_rollback`
- `create_training_materials`
- `notify_stakeholders`
- `generate_handover_docs`

### Appendix D: Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `MAX_ITERATIONS` | Agent hit iteration limit | Increase `max_iterations` or simplify task |
| `UNKNOWN_TOOL` | Tool not registered | Check tool name spelling |
| `TOOL_DENIED` | Tool requires approval | Run in HYBRID mode with callback |
| `PROVIDER_ERROR` | LLM API failure | Check API key and connectivity |
| `PHASE_DISABLED` | Phase not in config | Enable phase in orchestrator |

### Appendix E: Glossary

| Term | Definition |
|------|------------|
| **DSDM** | Dynamic Systems Development Method - Agile project delivery framework |
| **MoSCoW** | Prioritization technique: Must/Should/Could/Won't have |
| **Timebox** | Fixed time period for iterative development |
| **Agent** | AI-powered component that performs specific tasks |
| **Tool** | Function that agents can invoke to perform actions |
| **Orchestrator** | Component that manages workflow and agent coordination |
| **LLM** | Large Language Model - AI that powers agent reasoning |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | Dec 2025 | DSDM Agents Team | Initial release |

---

*This document is subject to review and approval before implementation begins.*
