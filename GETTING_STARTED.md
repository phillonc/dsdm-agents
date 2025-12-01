# Getting Started with DSDM Agents

This guide walks you through setting up and using DSDM Agents to manage your software development projects using the Dynamic Systems Development Method.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Your First Run](#your-first-run)
5. [Feeding Requirements](#feeding-requirements)
6. [Using the Interactive Menu](#using-the-interactive-menu)
7. [Working with Specialized Agents](#working-with-specialized-agents)
8. [Integration Setup](#integration-setup)
9. [Example Workflows](#example-workflows)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher** installed
- **An API key for your chosen LLM provider**:
  - Anthropic (default): [console.anthropic.com](https://console.anthropic.com)
  - OpenAI: [platform.openai.com](https://platform.openai.com/api-keys)
  - Google Gemini: [aistudio.google.com](https://aistudio.google.com/app/apikey)
  - Ollama: No API key needed (local)
- **Git** for cloning the repository

Optional:
- **Ollama** for local LLM support
- **Atlassian account** for Jira/Confluence integration

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/dsdm-agents.git
cd dsdm-agents
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv env
```

### Step 3: Activate the Virtual Environment

**On macOS/Linux:**
```bash
source env/bin/activate
```

**On Windows:**
```bash
env\Scripts\activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

For optional LLM providers, install additional packages:

```bash
# For OpenAI
pip install openai

# For Google Gemini
pip install google-generativeai
```

---

## Configuration

### Step 1: Create Environment File

```bash
cp .env.example .env
```

### Step 2: Configure LLM Provider

Edit the `.env` file to configure your preferred LLM provider:

#### Option A: Anthropic (Default)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

#### Option B: OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_ORG_ID=  # Optional organization ID
```

#### Option C: Google Gemini

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp
```

#### Option D: Ollama (Local LLM)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_CODE_MODEL=codellama
```

### Step 3: (Optional) Configure Integrations

For Jira integration:
```env
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_DEFAULT_PROJECT=YOUR_PROJECT_KEY
```

For Confluence integration:
```env
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
CONFLUENCE_DEFAULT_SPACE=your-space-key
```

---

## Your First Run

### Option 1: Interactive Mode (Recommended for Beginners)

Launch the interactive menu:

```bash
python main.py --interactive
```

You'll see a menu like this:

```
DSDM Agent Orchestrator

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Phase               ┃ Agent               ┃ Mode      ┃ Status     ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Feasibility         │ Feasibility Agent   │ automated │ [+] Enabled │
│ Business Study      │ Business Study Agent│ automated │ [+] Enabled │
│ Functional Model    │ Functional Model    │ automated │ [+] Enabled │
│ Design Build        │ Design & Build Agent│ hybrid    │ [+] Enabled │
│ Implementation      │ Implementation Agent│ manual    │ [+] Enabled │
└─────────────────────┴─────────────────────┴───────────┴────────────┘

Options:
1. Run specific phase
2. Run full workflow
3. Design & Build team
4. Configure modes
5. View tools
6. Exit
```

### Option 2: Command Line

Run a specific phase directly:

```bash
python main.py --phase feasibility --input "Build a customer feedback portal"
```

---

## Feeding Requirements

You can provide your project requirements in several ways:

### Method 1: Command Line Input

Pass requirements directly via the `--input` flag:

```bash
python main.py --phase feasibility --input "Build an e-commerce platform with user authentication, product catalog, shopping cart, and payment processing"
```

### Method 2: Interactive Prompt

When running interactively, you'll be prompted to enter your requirements:

```bash
python main.py --interactive
```

Select option `1` (Run specific phase), choose a phase, then enter your requirements when prompted:

```
Enter your task/requirement: Build a real-time analytics dashboard for monitoring sales data
```

### Method 3: Requirements File (Markdown)

Create a requirements file (e.g., `requirements.md`):

```markdown
# Project: Customer Feedback Portal

## Overview
Build a web-based customer feedback system for collecting and analyzing user feedback.

## Requirements

### Must Have
- User registration and login
- Feedback submission form
- Admin dashboard for viewing feedback
- Email notifications for new feedback

### Should Have
- Feedback categorization
- Search and filter functionality
- Export to CSV

### Could Have
- Sentiment analysis
- Charts and visualizations
- API for third-party integration

### Won't Have (this release)
- Mobile app
- Multi-language support
```

Then pipe it to the agent:

```bash
cat requirements.md | python main.py --phase feasibility --input -
```

Or read it programmatically:

```python
from src.orchestrator import DSDMOrchestrator, DSDMPhase

# Read requirements from file
with open('requirements.md', 'r') as f:
    requirements = f.read()

# Create orchestrator and run
orchestrator = DSDMOrchestrator()
result = orchestrator.run_phase(DSDMPhase.FEASIBILITY, requirements)

print(result.output)
```

### Method 4: Python Script

Create a script to process your requirements:

```python
#!/usr/bin/env python3
"""run_project.py - Run DSDM workflow with requirements file."""

import sys
from pathlib import Path
from src.orchestrator import DSDMOrchestrator, DSDMPhase

def main():
    # Check for requirements file argument
    if len(sys.argv) < 2:
        print("Usage: python run_project.py <requirements.md>")
        sys.exit(1)

    requirements_file = Path(sys.argv[1])

    if not requirements_file.exists():
        print(f"Error: File not found: {requirements_file}")
        sys.exit(1)

    # Read requirements
    requirements = requirements_file.read_text()
    print(f"Loaded requirements from: {requirements_file}")
    print(f"Content length: {len(requirements)} characters\n")

    # Create orchestrator with integrations
    orchestrator = DSDMOrchestrator(
        include_devops=True,
        include_jira=False,  # Set True if configured
        include_confluence=False,  # Set True if configured
    )

    # Run the full DSDM workflow
    print("Starting DSDM Workflow...\n")
    results = orchestrator.run_workflow(requirements)

    # Print summary
    print("\n" + "="*50)
    print("WORKFLOW SUMMARY")
    print("="*50)

    for phase, result in results.items():
        status = "[+]" if result.success else "[x]"
        print(f"{status} {phase.value}: {'Success' if result.success else 'Failed'}")

    return 0 if all(r.success for r in results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
```

Run it:

```bash
python run_project.py requirements.md
```

---

## Using the Interactive Menu

### Main Menu Options

1. **Run specific phase** - Execute a single DSDM phase
2. **Run full workflow** - Run all phases in sequence
3. **Design & Build team** - Access specialized development roles
4. **Configure modes** - Change agent modes (Manual/Automated/Hybrid)
5. **View tools** - See available tools for each phase
6. **Exit** - Close the application

### Running a Specific Phase

1. Select option `1` from the main menu
2. Choose a phase (e.g., `1` for Feasibility)
3. Enter your requirements when prompted
4. Review the agent's output

Example session:

```
Select option: 1

Available phases:
  1. Feasibility
  2. Business Study
  3. Functional Model
  4. Design Build
  5. Implementation

Select phase: 1

Enter your task/requirement: Assess the feasibility of building a mobile banking app with biometric authentication

╭─────────────────────── DSDM Phase ───────────────────────╮
│ Starting Feasibility Phase                                │
│ Agent: Feasibility Agent                                  │
│ Mode: automated                                           │
╰───────────────────────────────────────────────────────────╯

[Agent processes your request...]

╭─────────────────── Feasibility Result ───────────────────╮
│ [+] Success                                               │
│                                                           │
│ ## Feasibility Assessment                                 │
│                                                           │
│ ### Project Viability: HIGH                               │
│ ...                                                       │
╰───────────────────────────────────────────────────────────╯
```

### Configuring Agent Modes

Modes control how much human oversight is required:

| Mode | Description | When to Use |
|------|-------------|-------------|
| **automated** | All tools run without approval | Development, prototyping |
| **manual** | Every tool requires approval | Production, sensitive ops |
| **hybrid** | Critical tools need approval | Balanced workflow |

To change modes:

1. Select option `4` from the main menu
2. For each phase, choose a new mode or press Enter to keep current

---

## Working with Specialized Agents

The Design & Build phase includes specialized agents for different roles.

### Accessing the Design & Build Team

1. Select option `3` from the main menu
2. You'll see the specialized roles menu:

```
Design & Build Team

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Role                ┃ Agent               ┃ Mode      ┃ Status     ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Dev Lead            │ Dev Lead            │ hybrid    │ [+] Enabled │
│ Frontend Developer  │ Frontend Developer  │ automated │ [+] Enabled │
│ Backend Developer   │ Backend Developer   │ automated │ [+] Enabled │
│ Automation Tester   │ Automation Tester   │ automated │ [+] Enabled │
│ Nfr Tester          │ NFR Tester          │ hybrid    │ [+] Enabled │
│ Pen Tester          │ Penetration Tester  │ manual    │ [+] Enabled │
└─────────────────────┴─────────────────────┴───────────┴────────────┘

Options:
1. Run specific role
2. Run full team
3. Configure role modes
4. View role tools
5. Back to main menu
```

### Running the Full Team

Select option `2` to run all specialized agents in sequence:

```
Enter your development task/requirement: Implement user authentication with OAuth2 and JWT tokens

╭────────────────── Design & Build Team ───────────────────╮
│ Starting Design & Build Team                              │
│ Roles: Dev Lead → Frontend Developer → Backend Developer  │
│        → Automation Tester → Nfr Tester → Pen Tester     │
╰───────────────────────────────────────────────────────────╯
```

### Running a Specific Role

Select option `1` to run just one role:

```
Available roles:
  1. Dev Lead
  2. Frontend Developer
  3. Backend Developer
  4. Automation Tester
  5. Nfr Tester
  6. Pen Tester

Select role: 3

Enter your task/requirement: Create REST API endpoints for user CRUD operations
```

---

## Integration Setup

### Jira Integration

1. Get an API token from [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

2. Add to `.env`:
   ```
   JIRA_BASE_URL=https://your-domain.atlassian.net
   JIRA_USERNAME=your-email@example.com
   JIRA_API_TOKEN=your-token
   JIRA_DEFAULT_PROJECT=PROJ
   ```

3. Enable in code:
   ```python
   orchestrator = DSDMOrchestrator(include_jira=True)
   ```

4. Use Jira tools:
   - Create user stories with MoSCoW priorities
   - Track tasks and sprints
   - Search issues with JQL

### Confluence Integration

1. Get an API token (same as Jira)

2. Add to `.env`:
   ```
   CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
   CONFLUENCE_USERNAME=your-email@example.com
   CONFLUENCE_API_TOKEN=your-token
   CONFLUENCE_DEFAULT_SPACE=SPACE
   ```

3. Enable in code:
   ```python
   orchestrator = DSDMOrchestrator(include_confluence=True)
   ```

4. Use Confluence tools:
   - Create DSDM documentation
   - Update project pages
   - Search content

---

## Example Workflows

### Example 1: New Project Assessment

**requirements.md:**
```markdown
# Mobile Banking App

## Business Need
Create a mobile banking application allowing customers to manage accounts,
transfer funds, and pay bills from their smartphones.

## Key Features
- Account balance and transaction history
- Fund transfers (internal and external)
- Bill payments
- Biometric authentication (fingerprint/face)
- Push notifications for transactions

## Constraints
- Must comply with banking regulations
- 99.9% uptime requirement
- Response time < 2 seconds
```

**Run assessment:**
```bash
python main.py --phase feasibility --input "$(cat requirements.md)"
```

### Example 2: Full Development Workflow

```python
from src.orchestrator import DSDMOrchestrator, DSDMPhase

# Read requirements
with open('requirements.md', 'r') as f:
    requirements = f.read()

# Create orchestrator with all integrations
orchestrator = DSDMOrchestrator(
    include_devops=True,
    include_jira=True,
    include_confluence=True,
)

# Run phases 1-3 (up to Functional Model)
results = orchestrator.run_workflow(
    requirements,
    start_phase=DSDMPhase.FEASIBILITY,
    end_phase=DSDMPhase.FUNCTIONAL_MODEL
)

# Check results
for phase, result in results.items():
    print(f"{phase.value}: {'[+]' if result.success else '[x]'}")
```

### Example 3: Design & Build with Specific Roles

```python
from src.orchestrator import DSDMOrchestrator, DesignBuildRole

orchestrator = DSDMOrchestrator()

# Run only development roles (skip testers for now)
results = orchestrator.run_design_build_team(
    "Implement the shopping cart feature with add/remove/checkout",
    roles=[
        DesignBuildRole.DEV_LEAD,
        DesignBuildRole.FRONTEND_DEV,
        DesignBuildRole.BACKEND_DEV,
    ]
)
```

### Example 4: DevOps Pipeline

```python
from src.orchestrator import DSDMOrchestrator, DSDMPhase

orchestrator = DSDMOrchestrator(include_devops=True)

# Run DevOps agent for CI/CD setup
result = orchestrator.run_phase(
    DSDMPhase.DEVOPS,
    """
    Set up CI/CD pipeline for the project:
    - Run tests on every push
    - Check code coverage (minimum 80%)
    - Run security scans
    - Deploy to staging on merge to main
    - Deploy to production on release tag
    """
)
```

---

## Tips and Best Practices

1. **Start with Feasibility** - Always begin with the feasibility phase to validate your project idea

2. **Use MoSCoW Prioritization** - Structure your requirements with Must/Should/Could/Won't have

3. **Review in Hybrid Mode** - Use hybrid mode for critical phases to maintain human oversight

4. **Save Outputs** - Capture agent outputs for documentation and future reference

5. **Iterate** - DSDM is iterative - run phases multiple times as requirements evolve

6. **Use Specialized Agents** - For complex development, use the specialized Design & Build roles

7. **Integrate Early** - Set up Jira/Confluence integration to track work automatically

---

## Troubleshooting

### Common Issues

**"Provider not configured" or "API key not found"**
- Ensure `.env` file exists and contains the API key for your chosen provider
- Check `LLM_PROVIDER` is set correctly (anthropic, openai, gemini, ollama)
- Verify your API key at the provider's console:
  - Anthropic: console.anthropic.com
  - OpenAI: platform.openai.com
  - Gemini: aistudio.google.com

**"Module not found"**
- Activate the virtual environment: `source env/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`
- For OpenAI/Gemini, install optional packages:
  ```bash
  pip install openai  # For OpenAI
  pip install google-generativeai  # For Gemini
  ```

**"Connection refused" (Ollama)**
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_BASE_URL is correct (default: http://localhost:11434)
- Verify the model is pulled: `ollama list`

**"Connection refused" (Jira/Confluence)**
- Verify your base URL includes `https://`
- Check API token is correct and not expired
- Ensure you have access to the project/space

### Switching Providers

To switch between providers, simply update `.env`:

```env
# Change from Anthropic to OpenAI
LLM_PROVIDER=openai
```

Or specify per-agent in code:

```python
from src.llm import LLMProvider
from src.agents import AgentConfig

config = AgentConfig(
    name="My Agent",
    llm_provider=LLMProvider.GEMINI,
    model="gemini-2.0-flash-exp",
    ...
)
```

### Getting Help

- Check the [README.md](README.md) for detailed documentation
- Review the [examples/](examples/) directory for code samples
- Open an issue on GitHub for bugs or feature requests

---

## Next Steps

1. [x] Complete installation and configuration
2. [x] Run your first feasibility assessment
3. [ ] Try the full DSDM workflow with a sample project
4. [ ] Explore the Design & Build specialized agents
5. [ ] Set up Jira/Confluence integration
6. [ ] Customize agent modes for your workflow
7. [ ] Create your own requirements files

Happy developing with DSDM Agents!
