# DSDM Agents

AI-powered agents implementing the Dynamic Systems Development Method (DSDM) framework using the Claude Agent SDK.

## Overview

DSDM Agents provides a set of specialized AI agents for each phase of the DSDM methodology, plus a DevOps agent based on the Development Principles.

### DSDM Phase Agents

| Phase | Agent | Description |
|-------|-------|-------------|
| **Feasibility** | FeasibilityAgent | Assesses project viability and DSDM suitability |
| **Business Study** | BusinessStudyAgent | Defines requirements using MoSCoW prioritization |
| **Functional Model** | FunctionalModelAgent | Creates and refines prototypes iteratively |
| **Design & Build** | DesignBuildAgent | Develops production-ready code with testing |
| **Implementation** | ImplementationAgent | Deploys system to production |
| **DevOps** | DevOpsAgent | Enables development principles through DevOps practices |

### Design & Build Specialized Agents

The Design & Build phase can be broken down into specialized roles for more granular control:

| Role | Agent | Mode | Description |
|------|-------|------|-------------|
| **Dev Lead** | DevLeadAgent | Hybrid | Architecture, ADRs, code review, team coordination |
| **Frontend Developer** | FrontendDeveloperAgent | Automated | UI/UX, components, accessibility, responsive design |
| **Backend Developer** | BackendDeveloperAgent | Automated | APIs, business logic, databases, integrations |
| **Automation Tester** | AutomationTesterAgent | Automated | Unit/integration/E2E tests, CI/CD, coverage |
| **NFR Tester** | NFRTesterAgent | Hybrid | Performance, scalability, reliability, accessibility |
| **Penetration Tester** | PenTesterAgent | Manual | Security scans, vulnerability assessment, OWASP |

Each agent has specialized tools and can operate in **Manual**, **Automated**, or **Hybrid** mode.

## Getting Started

### Prerequisites

- Python 3.10+
- Anthropic API key (or Ollama for local LLM)

### Installation

1. Clone the repository:
```bash
cd dsdm-agents
```

2. Create and activate the virtual environment:
```bash
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your API key:
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Usage

### Interactive Mode

Launch the interactive menu to explore phases and configure agents:

```bash
python main.py --interactive
```

This opens a menu where you can:
- Run specific phases
- Run the full DSDM workflow
- Access the Design & Build team (specialized roles)
- Configure agent modes (Manual/Automated/Hybrid)
- View available tools for each phase

### Command Line

**Run a specific phase:**
```bash
python main.py --phase feasibility --input "Build a customer feedback system"
```

**Run the full workflow:**
```bash
python main.py --workflow --input "Build an inventory management system"
```

**Set agent mode:**
```bash
python main.py --phase design_build --mode manual --input "Implement user authentication"
```

**List all phases:**
```bash
python main.py --list-phases
```

**List all tools:**
```bash
python main.py --list-tools
```

### Programmatic Usage

```python
from src.orchestrator import DSDMOrchestrator, DSDMPhase, DesignBuildRole
from src.agents import AgentMode

# Create orchestrator with all integrations
orchestrator = DSDMOrchestrator(
    include_devops=True,
    include_confluence=True,
    include_jira=True
)

# Run a single phase
result = orchestrator.run_phase(
    DSDMPhase.FEASIBILITY,
    "Build a real-time analytics dashboard"
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")

# Change agent mode
orchestrator.set_agent_mode(DSDMPhase.DESIGN_BUILD, AgentMode.MANUAL)

# Run full workflow
results = orchestrator.run_workflow(
    "Build an e-commerce platform",
    start_phase=DSDMPhase.FEASIBILITY,
    end_phase=DSDMPhase.FUNCTIONAL_MODEL
)
```

### Using Design & Build Specialized Agents

```python
from src.orchestrator import DSDMOrchestrator, DesignBuildRole
from src.agents import AgentMode

orchestrator = DSDMOrchestrator()

# Run a specific role
result = orchestrator.run_design_build_role(
    DesignBuildRole.BACKEND_DEV,
    "Implement REST API for user authentication"
)

# Run the full Design & Build team in sequence
results = orchestrator.run_design_build_team(
    "Build a payment processing module"
)

# Run specific roles only
results = orchestrator.run_design_build_team(
    "Implement checkout flow",
    roles=[
        DesignBuildRole.DEV_LEAD,
        DesignBuildRole.FRONTEND_DEV,
        DesignBuildRole.BACKEND_DEV,
        DesignBuildRole.AUTOMATION_TESTER
    ]
)

# Configure role mode
orchestrator.set_role_mode(DesignBuildRole.PEN_TESTER, AgentMode.MANUAL)
```

## Agent Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **AUTOMATED** | All tools run without approval | Development, prototyping |
| **MANUAL** | Every tool requires user approval | Production deployments, sensitive operations |
| **HYBRID** | Some tools auto-run, critical ones need approval | Balanced workflow |

Default modes by phase:
- Feasibility → Automated
- Business Study → Automated
- Functional Model → Automated
- Design & Build → Hybrid
- Implementation → Manual
- DevOps → Hybrid

Default modes for Design & Build roles:
- Dev Lead → Hybrid
- Frontend Developer → Automated
- Backend Developer → Automated
- Automation Tester → Automated
- NFR Tester → Hybrid
- Penetration Tester → Manual

## DevOps Agent

The DevOps agent is based on the 14 Development Principles:

| # | Principle | Tools |
|---|-----------|-------|
| 1 | Decision Making should be distributed | `create_adr`, `track_decision` |
| 2 | If it's not tested, it's broken | `run_tests`, `check_coverage` |
| 3 | Transparency dispels myth | `run_linter`, `check_code_quality`, `generate_docs` |
| 4 | Mean Time To Innocence (MTTI) | `health_check`, `setup_monitoring`, `check_service_status` |
| 5 | No Dead Cats over the fence | `run_ci_pipeline`, `deploy_to_environment` |
| 6 | Friends would not let friends build data centres | `provision_infrastructure`, `scale_service` |
| 7 | Non Functional Requirements are first class citizens | `run_performance_test`, `check_accessibility`, `validate_nfr` |
| 8 | Cattle not Pets | `validate_terraform`, `manage_containers` |
| 9 | Keep the Hostage | `backup_database`, `test_restore` |
| 10 | Elimination of Toil | `automate_task`, `track_toil` |
| 11 | Failure is Normal | `rollback_deployment`, `run_chaos_test` |
| 12 | Dependencies create latency as a service | `analyze_dependencies` |
| 13 | Focus on differentiating code | Use managed services |
| 14 | Stop Starting and Start Stopping | `check_incomplete_tasks` |

## Integrations

### Confluence Integration

Enable Confluence integration to create and manage DSDM documentation directly in Confluence.

1. Add Confluence credentials to `.env`:
```
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
CONFLUENCE_DEFAULT_SPACE=your-space-key
```

2. Get an API token from [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

3. Enable in your code:
```python
orchestrator = DSDMOrchestrator(include_confluence=True)
```

**Available Confluence Tools:**
- `confluence_get_page` - Retrieve page content
- `confluence_create_page` - Create new pages
- `confluence_update_page` - Update existing pages
- `confluence_search` - Search using CQL
- `confluence_get_space` - Get space info
- `confluence_add_comment` - Add comments to pages
- `confluence_create_dsdm_doc` - Create DSDM-formatted documentation

### Jira Integration

Enable Jira integration to manage project tasks, user stories, and sprints.

1. Add Jira credentials to `.env`:
```
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_DEFAULT_PROJECT=your-project-key
```

2. Get an API token from [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

3. Enable in your code:
```python
orchestrator = DSDMOrchestrator(include_jira=True)
```

**Available Jira Tools:**
- `jira_get_issue` - Get issue details
- `jira_create_issue` - Create tasks, bugs, stories
- `jira_update_issue` - Update existing issues
- `jira_search` - Search using JQL
- `jira_transition_issue` - Change issue status
- `jira_add_comment` - Add comments
- `jira_get_project` - Get project info
- `jira_create_user_story` - Create DSDM-formatted user stories with MoSCoW priority
- `jira_create_timebox` - Create sprints/timeboxes
- `jira_bulk_create_requirements` - Bulk create requirements

### LLM Provider Configuration

DSDM Agents supports multiple LLM providers. Configure your preferred provider in `.env`:

| Provider | Description | Model Examples |
|----------|-------------|----------------|
| **Anthropic** | Claude models (default) | claude-sonnet-4-20250514, claude-opus-4-20250514 |
| **OpenAI** | GPT models | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| **Gemini** | Google AI models | gemini-2.0-flash-exp, gemini-1.5-pro |
| **Ollama** | Local LLM | llama3.2, codellama, mistral |

#### Anthropic (Default)
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

#### OpenAI
```bash
pip install openai
```
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_ORG_ID=  # Optional
```

#### Google Gemini
```bash
pip install google-generativeai
```
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp
```

#### Ollama (Local LLM)

1. Install [Ollama](https://ollama.ai/)

2. Pull a model:
```bash
ollama pull llama3.2
ollama pull codellama  # For code-specific tasks
```

3. Configure in `.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_CODE_MODEL=codellama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=120
```

#### Programmatic Provider Selection

```python
from src.llm import LLMProvider, create_llm_client
from src.agents import AgentConfig, AgentMode

# Create agent with specific provider
config = AgentConfig(
    name="My Agent",
    description="Custom agent",
    phase="design_build",
    system_prompt="You are a helpful assistant.",
    llm_provider=LLMProvider.OPENAI,  # Use OpenAI for this agent
    model="gpt-4o",
)

# Or create a client directly
client = create_llm_client(LLMProvider.GEMINI)
```

### Enable All Integrations

```python
orchestrator = DSDMOrchestrator(
    include_devops=True,
    include_confluence=True,
    include_jira=True
)
```

## Adding Custom Tools

You can extend agents with custom tools:

```python
from src.tools import Tool, create_dsdm_tool_registry

# Get the default registry (optionally with integrations)
registry = create_dsdm_tool_registry(
    include_jira=True,
    include_devops=True
)

# Add a custom tool
registry.register(Tool(
    name="my_custom_tool",
    description="Description of what the tool does",
    input_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "First parameter"},
            "param2": {"type": "integer", "description": "Second parameter"}
        },
        "required": ["param1"]
    },
    handler=lambda param1, param2=0: f"Result: {param1}, {param2}",
    requires_approval=False,  # Set True for manual approval
    category="feasibility"    # Phase category
))
```

See [examples/custom_tools_example.py](examples/custom_tools_example.py) for more details.

## Project Structure

```
dsdm-agents/
├── src/
│   ├── agents/                    # DSDM phase agents
│   │   ├── base_agent.py
│   │   ├── feasibility_agent.py
│   │   ├── business_study_agent.py
│   │   ├── functional_model_agent.py
│   │   ├── design_build_agent.py
│   │   ├── implementation_agent.py
│   │   ├── devops_agent.py
│   │   ├── dev_lead_agent.py           # Design & Build specialized
│   │   ├── frontend_developer_agent.py
│   │   ├── backend_developer_agent.py
│   │   ├── automation_tester_agent.py
│   │   ├── nfr_tester_agent.py
│   │   └── pen_tester_agent.py
│   ├── tools/                     # Tool definitions
│   │   ├── tool_registry.py
│   │   ├── dsdm_tools.py
│   │   └── integrations/          # External integrations
│   │       ├── confluence_tools.py
│   │       ├── jira_tools.py
│   │       └── devops_tools.py
│   ├── orchestrator/              # Workflow management
│   │   └── dsdm_orchestrator.py
│   └── docs/                      # Documentation
│       └── development-principles.md
├── examples/                      # Usage examples
├── main.py                        # CLI entry point
├── requirements.txt
├── .env.example
└── README.md
```

## DSDM Methodology

DSDM (Dynamic Systems Development Method) is an agile framework based on 8 principles:

1. Focus on the business need
2. Deliver on time
3. Collaborate
4. Never compromise quality
5. Build incrementally from firm foundations
6. Develop iteratively
7. Communicate continuously and clearly
8. Demonstrate control

Key practices used by these agents:
- **MoSCoW Prioritization**: Must have, Should have, Could have, Won't have
- **Timeboxing**: Fixed time periods for delivery
- **Iterative Development**: Continuous refinement through feedback
- **Prototyping**: Early validation through working models

## Available Tools by Phase

### Feasibility Phase
- `analyze_requirements` - Parse and structure requirements
- `assess_technical_feasibility` - Evaluate technical viability
- `estimate_resources` - Estimate team and budget needs
- `identify_risks` - Document project risks
- `check_dsdm_suitability` - Verify DSDM fit

### Business Study Phase
- `analyze_business_process` - Map current processes
- `identify_stakeholders` - Document stakeholders
- `prioritize_requirements` - MoSCoW prioritization
- `define_architecture` - High-level system design
- `create_timebox_plan` - Plan iterations
- `update_risk_log` - Maintain risk register

### Functional Model Phase
- `create_prototype` - Build functional prototypes
- `generate_code_scaffold` - Create code structure
- `collect_user_feedback` - Gather stakeholder input
- `refine_requirements` - Update based on feedback
- `run_functional_tests` - Validate functionality
- `document_iteration` - Record progress

### Design & Build Phase
- `create_technical_design` - Detailed designs
- `generate_code` - Write production code
- `write_file` - Create files
- `run_tests` - Execute test suites
- `review_code` - Quality checks
- `create_documentation` - Technical docs
- `security_check` - Security scanning

### Implementation Phase
- `create_deployment_plan` - Plan go-live
- `setup_environment` - Configure infrastructure
- `deploy_system` - Deploy to production
- `run_smoke_tests` - Verify deployment
- `create_rollback` - Prepare rollback
- `execute_rollback` - Revert if needed
- `create_training_materials` - User guides
- `notify_stakeholders` - Communication
- `generate_handover_docs` - Operations handover

### DevOps Tools (28 tools)
**Testing & Quality:** `run_tests`, `check_coverage`, `run_linter`, `run_security_scan`, `check_code_quality`

**CI/CD & Automation:** `run_ci_pipeline`, `deploy_to_environment`, `rollback_deployment`, `automate_task`

**Infrastructure:** `provision_infrastructure`, `validate_terraform`, `manage_containers`, `scale_service`

**Monitoring & Health:** `health_check`, `setup_monitoring`, `check_service_status`, `run_chaos_test`

**NFRs & Dependencies:** `analyze_dependencies`, `run_performance_test`, `check_accessibility`, `validate_nfr`

**Documentation & Decisions:** `create_adr`, `generate_docs`, `track_decision`

**Task Management:** `check_incomplete_tasks`, `track_toil`

**Backup & Recovery:** `backup_database`, `test_restore`

## License

MIT
