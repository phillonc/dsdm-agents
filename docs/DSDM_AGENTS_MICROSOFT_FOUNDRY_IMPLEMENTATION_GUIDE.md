# DSDM Agents: Microsoft Foundry Implementation Guide

Version 1.0 | 5 November 2026  
Repository: https://github.com/phillonc/dsdm-agents  
Status: Implementation instructions, not evidence of deployment.

## 1. Architecture and scope

**Recommendation:** Host the existing Python DSDM orchestrator as a Microsoft Foundry Hosted Agent. Keep `src/agents/`, `src/orchestrator/`, role definitions and human approvals authoritative. Expose selected `src/tools/` capabilities through a secured remote MCP gateway or Foundry Toolbox. Move delivery-room state and generated artifacts into durable storage.

```text
User / DSDM Console / CI
           |
Authenticated Foundry Hosted Agent (Python orchestrator)
           |
DSDM phase agents + specialist Dev / QA / Security roles
           |
Restricted MCP tools -> GitHub / test workers / optional Atlassian
           |
Durable project state + artifacts + approvals
           |
Foundry tracing / Azure Monitor / evaluations
```

Microsoft Agent Framework is optional, not a prerequisite for hosting existing Python code. Validate `pi.dev` compatibility separately before using its TypeScript runtime in hosted compute.

## 2. Verified repository mapping

| Existing path | Function | Foundry mapping |
|---|---|---|
| `main.py` | CLI, phases, rooms, GUI, diagnostics | Local operator interface |
| `src/agents/` | DSDM and specialist agents | Preserve agent implementations |
| `src/orchestrator/` | Phase orchestration | Hosted adapter invokes it |
| `src/rooms/` | Delivery-room state | Durable persistence adapter |
| `src/tools/` | Tool registry | Restricted MCP bridge |
| `src/gui/` | Browser console | Optional separately hosted UI |
| `pi/` | Alternative agent runtime | Compatibility assessment |
| `.github/agents/` | Role instructions | Version-controlled role mapping |
| `.github/prompts/` | Task prompts | Version-controlled instructions |
| `tests/` | Regression suite | CI evidence |
| `generated/` | Local artifacts | Durable artifact store in production |

## 3. Step-by-step implementation

### Step 1 — Establish a tested baseline

Prerequisites: Git, Python 3.10+ for the local framework, Azure subscription, Azure CLI, Azure Developer CLI, VS Code and Microsoft Foundry Toolkit. The hosted runtime may have a different Python requirement.

```bash
git clone https://github.com/phillonc/dsdm-agents.git
cd dsdm-agents
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --list-phases
python main.py --list-tools
python main.py --generate-agents
python -m pytest tests/ -q
```

Record exact outputs, versions and failures. Never commit `.env`.

**Acceptance:** A reproducible baseline and verified agent/tool inventory.

### Step 2 — Provision Microsoft Foundry

1. Visit https://ai.azure.com/ and create or select a Foundry resource and project in a supported region.
2. Configure Microsoft Entra identities and least-privilege Foundry roles.
3. Deploy a supported model; record the **deployment name**.
4. Enable Application Insights and cost/budget alerts.
5. Copy the **project endpoint** from the portal. Do not infer it from the resource name.
6. Verify access from your developer identity.

**Acceptance:** Project, model deployment and authenticated access confirmed.

### Step 3 — Test the Python SDK connection

```bash
az login
pip install --upgrade azure-ai-projects azure-identity
export FOUNDRY_PROJECT_ENDPOINT='https://YOUR-RESOURCE.services.ai.azure.com/api/projects/YOUR-PROJECT'
export FOUNDRY_MODEL_DEPLOYMENT='YOUR-MODEL-DEPLOYMENT'
```

Create and run a temporary smoke-test script:

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
agent = project.agents.create_version(
    agent_name="dsdm-connectivity-smoke",
    definition=PromptAgentDefinition(
        model=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],
        instructions="Reply briefly. Do not call external tools.",
    ),
)
print(agent.name, agent.version)
```

This confirms prompt-agent creation, not the hosted DSDM integration. Remove the smoke-test agent afterwards.

**Acceptance:** A versioned agent is visible in Foundry.

### Step 4 — Map DSDM roles and permissions

| Role | Responsibility | Approval gate |
|---|---|---|
| Feasibility | Feasibility and risks | Go/no-go |
| Product Manager | PRD and MoSCoW | Scope approval |
| Business Study | Requirements | Requirements approval |
| Functional Model | Prototype and feedback | User validation |
| Dev Lead | Architecture and TRD | Design review |
| Frontend / Backend | Implement features | Code review |
| Automation Tester | Unit, integration, E2E | Tests pass |
| NFR Tester | Performance and accessibility | NFR review |
| Pen Tester | Security verification | Security review |
| DevOps / Implementation | Build and deploy | Release approval |
| Change Control | Scope changes | Change approval |

For every role define model deployment, instructions, permitted tools, input/output contract, approver and artifact destination. Start with `src/agents/role_definitions.py` and `.github/agents/`. Not all roles are standalone CLI `--phase` values.

**Acceptance:** Role-to-tool and approval matrix reviewed.

### Step 5 — Create a Hosted Agent adapter

1. In VS Code Foundry Toolkit, choose **Create Agent** and **Create in code with full control**.
2. Scaffold a Python Hosted Agent using the **Responses** protocol unless your client requires Invocations.
3. Keep the generated hosting wrapper; adapt it to call `src/orchestrator/` and `src/rooms/`.
4. Accept `project_id`, `run_id`, `task`, `phase`, `execution_mode`.
5. Return `run_id`, `status`, `phase`, `artifact_uris`, `blockers`, `approvals_required`, `next_action`.
6. Add authentication, input validation, correlation IDs, idempotency and structured errors.
7. Run a read-only feasibility phase locally before enabling writes.

Do not assume existing local subprocesses, filesystem persistence or `pi.dev` work unchanged in hosted compute. Run builds and tests in a separate isolated worker.

**Acceptance:** The adapter executes one DSDM phase with expected artifacts and gates.

### Step 6 — Connect tools using MCP

1. Inventory the tool registry and `.github/copilot/mcp-config.json`.
2. Categorise tools as read-only, artifact-write, Git-write, test-execution, deployment or external publishing.
3. Expose approved tools through a remote HTTPS MCP server or Foundry Toolbox.
4. Authenticate using supported Entra managed identity, project connections or OAuth.
5. Set a **nonempty `allowed_tools` list per role**. Empty or omitted lists can expose every server tool.
6. Require explicit human approval for commits, publishing and deployments.
7. Test permitted and denied tool calls and record evidence.

**Acceptance:** Every tool invocation is scoped, authenticated and auditable.

### Step 7 — Externalise delivery-room state

Current room state and artifacts are project-local, including `generated/<project>/room_state.json`. Hosted compute may be ephemeral.

1. Store artifacts in Azure Blob Storage or an approved durable store.
2. Store mutable state and approval decisions in a transactional store.
3. Track project/run/phase/agent IDs, revision, approver, decision, artifact URI and correlation ID.
4. Enforce project isolation, encryption, retention and concurrency control.
5. Test restart on a different worker and prevent duplicate actions.

**Acceptance:** A run resumes without losing or duplicating state.

### Step 8 — Preserve manual, hybrid and automated modes

- **Manual:** Approve privileged tool calls before execution.
- **Hybrid:** Automate only explicitly approved low-risk operations.
- **Automated:** Confine operations to an approved sandbox and tool allowlist.

Bind approvals to exact actions and arguments. Handle rejection, expiry and retries. Never infer permission to deploy production from an automated mode setting.

**Acceptance:** Rejected actions never execute and approved actions execute at most once.

### Step 9 — Add monitoring, evaluation and budgets

1. Enable Foundry tracing and Application Insights.
2. Capture run/phase IDs, model usage, latency, tool calls, errors, approvals and artifact references.
3. Build evaluation cases for feasibility, PRD, TRD, implementation, QA, security and handoffs.
4. Set maximum steps, token budgets, concurrency limits and timeout thresholds.
5. Redact secrets and sensitive content from telemetry.

**Acceptance:** An operator can trace every artifact to the agent, tool, decision and run that produced it.

### Step 10 — Deploy the development Hosted Agent

1. Package the adapter and necessary Python modules using the Foundry Toolkit or Azure Developer CLI workflow.
2. Verify Python runtime and dependency compatibility.
3. Exclude `.env`, credentials, local generated artifacts and unrelated demos.
4. Grant the hosted managed identity only required access.
5. Deploy a version and wait for its active state.
6. Invoke a read-only feasibility run.
7. Verify telemetry, tool restrictions, persistence and output.

Microsoft documents both Toolkit/`azd` and source-code ZIP deployment. Follow the current official deployment quickstart for exact commands.

**Acceptance:** A deployed read-only phase produces a traceable artifact.

### Step 11 — Run a complete sandbox vertical slice

Use a dedicated sandbox repository and task: **Build a minimal task-management API with one endpoint and tests**.

| Test ID | Scenario | Acceptance |
|---|---|---|
| T01 | Feasibility | Report and decision recorded |
| T02 | PRD | MoSCoW scope approved |
| T03 | TRD | Design and test strategy approved |
| T04 | Code | Changes limited to authorised feature branch |
| T05 | QA | Tests executed, failures block progression |
| T06 | Security | Disallowed tools denied and logged |
| T07 | Approval | Rejection blocks deployment; approval resumes once |
| T08 | Recovery | Worker restart resumes without duplication |
| T09 | Traceability | Artifacts linked to run, agent and decision |
| T10 | Rollback | Previous approved state can be restored |

```gherkin
Feature: Controlled DSDM release
  Scenario: Deployment requires approval
    Given all required tests have passed
    And the Implementation agent requests production deployment
    When no authorised approver has approved the action
    Then the deployment tool must not execute
    And the run must remain pending approval

  Scenario: Role permissions are enforced
    Given the Feasibility agent has read-only tools
    When it requests a Git write tool
    Then the request must be denied
    And the denial must be recorded
```

**Acceptance:** T01–T10 have observed test evidence, not assumed completion.

### Step 12 — Production hardening

1. Review identity, networking, data residency, secrets and RBAC.
2. Pin dependencies, agent versions and model deployments.
3. Add adversarial prompt/tool tests and security scans.
4. Configure alerting, backup, recovery drills and rollback.
5. Separate development, staging and production.
6. Run a controlled pilot before enabling broader autonomy.
7. Consider separately hosted roles only where isolation, scale or governance justifies them.

**Acceptance:** Signed-off pilot with security, cost, reliability and rollback evidence.

## 4. Proposed new files and folders

These are **proposed**, not yet created in GitHub:

```text
dsdm-agents/
├── src/foundry/
│   ├── __init__.py
│   ├── hosted_adapter.py
│   ├── contracts.py
│   ├── identity.py
│   ├── durable_state.py
│   └── telemetry.py
├── infra/foundry/
├── tests/
│   ├── test_foundry_contracts.py
│   ├── test_foundry_approvals.py
│   └── test_foundry_resume.py
└── docs/
    └── DSDM_AGENTS_MICROSOFT_FOUNDRY_IMPLEMENTATION_GUIDE.md
```

Use only files required by the chosen Foundry deployment template. Do not create a competing orchestrator or duplicate role definitions.

## 5. Delivery plan and risks

| Stage | Deliverable | Dependency |
|---|---|---|
| P1 | Baseline, project, model, identity | Azure access |
| P2 | Read-only hosted adapter | P1 |
| P3 | MCP and approvals | P2 |
| P4 | Durable state and recovery | P3 |
| P5 | End-to-end vertical slice | P4 |
| P6 | Monitoring, staging, pilot | P5 |

**R1 Runtime incompatibility:** Test hosted Python and `pi.dev` separately.  
**R2 Overprivileged tools:** Explicit allowlists, isolated workers and approvals.  
**R3 State loss:** Durable storage, revisions and idempotency.  
**R4 Agent drift:** Run `--generate-agents` and source-controlled checks.  
**R5 Cost overrun:** Budget caps, timeouts and usage alerts.  
**R6 Platform changes:** Verify region, SDK, hosting and RBAC documentation before implementation.

## 6. References

Official Microsoft documentation, consulted 5 November 2026:

- [Microsoft Foundry overview](https://learn.microsoft.com/en-us/azure/foundry/)
- [Agent Service overview](https://learn.microsoft.com/en-gb/azure/ai-foundry/agents/overview?view=foundry-classic)
- [Agent runtime components and Python SDK](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components)
- [MCP tool connections](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/model-context-protocol)
- [Hosted Agent quickstart](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-deploy-own-code)
- [Hosted source-code deployment](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code)
- [Foundry environment setup](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/environment-setup?view=foundry)

## 7. Completion checklist

- [ ] Local baseline verified
- [ ] Foundry project and model configured
- [ ] Role matrix approved
- [ ] Hosted adapter deployed
- [ ] MCP permissions and approvals verified
- [ ] Durable room state tested
- [ ] Monitoring and evaluations enabled
- [ ] T01–T10 passed with evidence
- [ ] Security and rollback approved
- [ ] Pilot signed off

**Next action:** Complete P1 and record the baseline results before changing agent implementations.