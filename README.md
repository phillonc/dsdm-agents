# DSDM Agents

AI-powered agents implementing the Dynamic Systems Development Method (DSDM) framework using the Claude Agent SDK.

## Overview

DSDM Agents provides a set of specialized AI agents for each phase of the DSDM methodology:

| Phase | Agent | Description |
|-------|-------|-------------|
| **Feasibility** | FeasibilityAgent | Assesses project viability and DSDM suitability |
| **Business Study** | BusinessStudyAgent | Defines requirements using MoSCoW prioritization |
| **Functional Model** | FunctionalModelAgent | Creates and refines prototypes iteratively |
| **Design & Build** | DesignBuildAgent | Develops production-ready code with testing |
| **Implementation** | ImplementationAgent | Deploys system to production |

Each agent has specialized tools and can operate in **Manual**, **Automated**, or **Hybrid** mode.

## Getting Started

### Prerequisites

- Python 3.10+
- Anthropic API key

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
from src.orchestrator import DSDMOrchestrator, DSDMPhase
from src.agents import AgentMode

# Create orchestrator
orchestrator = DSDMOrchestrator()

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

## Integrations

### Confluence Integration

Enable Confluence integration to create and manage DSDM documentation directly in Confluence.

1. Add Confluence credentials to `.env`:
```
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
```

2. Get an API token from [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

3. Enable in your code:
```python
from src.tools import create_dsdm_tool_registry

registry = create_dsdm_tool_registry(include_confluence=True)
```

**Available Confluence Tools:**
- `confluence_get_page` - Retrieve page content
- `confluence_create_page` - Create new pages
- `confluence_update_page` - Update existing pages
- `confluence_search` - Search using CQL
- `confluence_get_space` - Get space info
- `confluence_add_comment` - Add comments to pages
- `confluence_create_dsdm_doc` - Create DSDM-formatted documentation (feasibility reports, business requirements, etc.)

### Jira Integration

Enable Jira integration to manage project tasks, user stories, and sprints.

1. Add Jira credentials to `.env`:
```
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
```

2. Get an API token from [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

3. Enable in your code:
```python
from src.tools import create_dsdm_tool_registry

registry = create_dsdm_tool_registry(include_jira=True)
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

### Enable Both Integrations

```python
from src.tools import create_dsdm_tool_registry

# Enable both Confluence and Jira
registry = create_dsdm_tool_registry(
    include_confluence=True,
    include_jira=True
)
```

## Adding Custom Tools

You can extend agents with custom tools:

```python
from src.tools import Tool, create_dsdm_tool_registry

# Get the default registry (optionally with integrations)
registry = create_dsdm_tool_registry(include_jira=True)

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
│   ├── agents/              # DSDM phase agents
│   │   ├── base_agent.py
│   │   ├── feasibility_agent.py
│   │   ├── business_study_agent.py
│   │   ├── functional_model_agent.py
│   │   ├── design_build_agent.py
│   │   └── implementation_agent.py
│   ├── tools/               # Tool definitions
│   │   ├── tool_registry.py
│   │   ├── dsdm_tools.py
│   │   └── integrations/    # External integrations
│   │       ├── confluence_tools.py
│   │       └── jira_tools.py
│   └── orchestrator/        # Workflow management
│       └── dsdm_orchestrator.py
├── examples/                # Usage examples
├── main.py                  # CLI entry point
├── requirements.txt
└── .env.example
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

## License

MIT
