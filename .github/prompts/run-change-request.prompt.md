---
mode: agent
description: Arbitrate a mid-timebox scope-change request — what it costs in MoSCoW terms, what gets traded out, and whether it needs stakeholder approval.
---

# Task: Scope change request

Invoke the `change-control` agent to arbitrate the request below.

## Inputs you need from the user
- **Project slug**: which `generated/<slug>/` this applies to
- **Change description**: what's being requested and why
- **Requested priority**: what MoSCoW bucket the requester thinks this belongs in
- **Source**: who raised it (stakeholder name/role, or "internal" if raised by the team)

## Steps
1. Read the current requirements list — `generated/<slug>/docs/BUSINESS_STUDY.md`
   (or `PRODUCT_REQUIREMENTS.md` if Business Study hasn't run yet).
2. Invoke `change-control` agent with the change description and current state.
3. It must produce an explicit trade: *"add X at priority P by moving Y
   (currently priority P) out to the next timebox"* — never a bare addition.
4. If the trade would displace an existing **Must Have**, the agent stops
   and asks for explicit stakeholder approval before proceeding.
5. Confirm `generated/<slug>/docs/CHANGE_LOG.md` has a new entry.
6. Confirm the risk log was updated if the change carries new/retired risk.

## Output
- The trade-off statement (what's in, what's out, at what priority)
- Updated MoSCoW counts (Must / Should / Could / Won't)
- Decision record reference
- Whether this needs stakeholder sign-off (and why, if so)

## Equivalent programmatic invocation
```python
from src.agents.change_control_agent import ChangeControlAgent
from src.tools.dsdm_tools import create_dsdm_tool_registry
from src.agents.base_agent import AgentMode

agent = ChangeControlAgent(
    tool_registry=create_dsdm_tool_registry(include_jira=True),
    mode=AgentMode.HYBRID,
)
result = agent.run(
    "Change request for customer-feedback-portal: add CSV+PDF combined "
    "export (currently only CSV, Should-have). Requested priority: Must "
    "Have, per exec ask. Source: VP Customer Success."
)
```

## Stop condition
After the trade-off is logged (and stakeholder approval is either captured
or explicitly requested), post a one-paragraph summary and stop.
