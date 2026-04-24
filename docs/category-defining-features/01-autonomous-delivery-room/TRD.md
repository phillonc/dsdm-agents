# TRD: Autonomous Delivery Room

## 1. Technical Summary

Autonomous Delivery Room introduces a project-level orchestration layer above existing DSDM phase agents and Design & Build role agents. It persists room state, assigns role ownership, coordinates handoffs, records blockers and decisions, and exposes CLI commands for creation, status, execution, and export.

## 2. Current Architecture Fit

The repository already includes:

- `DSDMOrchestrator` for phase and role execution.
- `BaseAgent` with progress callbacks, workflow modes, tool execution, and tool history.
- DSDM phase agents.
- Design & Build specialist agents.
- Project output under `generated/<project>/`.

Autonomous Delivery Room should sit above the orchestrator and use existing agents rather than replace them.

## 3. Proposed Components

```text
src/
├── rooms/
│   ├── __init__.py
│   ├── delivery_room.py
│   ├── room_state.py
│   ├── room_templates.py
│   ├── room_events.py
│   ├── room_health.py
│   └── room_exporter.py
├── orchestrator/
│   └── dsdm_orchestrator.py
└── tools/
    └── room_tools.py
```

## 4. Data Models

### DeliveryRoomState

```python
@dataclass
class DeliveryRoomState:
    project_name: str
    mission: str
    template: str
    status: str
    active_phase: str | None
    agents: list[RoomAgentAssignment]
    decisions: list[RoomDecision]
    blockers: list[RoomBlocker]
    handoffs: list[RoomHandoff]
    artifacts: list[RoomArtifact]
    created_at: str
    updated_at: str
```

### RoomAgentAssignment

```python
@dataclass
class RoomAgentAssignment:
    role: str
    agent_name: str
    phase: str
    responsibilities: list[str]
    status: str
    current_task: str | None = None
```

### RoomDecision

```python
@dataclass
class RoomDecision:
    id: str
    title: str
    owner_agent: str
    context: str
    decision: str
    consequences: list[str]
    created_at: str
```

### RoomBlocker

```python
@dataclass
class RoomBlocker:
    id: str
    title: str
    owner_agent: str
    severity: str
    status: str
    suggested_resolution: str
    created_at: str
```

### RoomHandoff

```python
@dataclass
class RoomHandoff:
    from_agent: str
    to_agent: str
    artifact_refs: list[str]
    summary: str
    acceptance_gate: str
```

## 5. Persistence

MVP persistence should use JSON for machine state and Markdown for human review.

```text
generated/<project>/
├── room_state.json
└── docs/
    └── DELIVERY_ROOM.md
```

A later version can migrate to SQLite or a graph database.

## 6. CLI Commands

Add commands to `main.py`:

```bash
python main.py --room-create --input "Build a customer support platform"
python main.py --room-status --project customer-support-platform
python main.py --room-run --project customer-support-platform
python main.py --room-export --project customer-support-platform
```

## 7. Room Templates

Initial templates:

- `mvp`
- `platform`
- `migration`
- `enterprise`
- `compliance`

Each template defines required agents, recommended workflow modes, risk focus, quality gates, and default output artifacts.

## 8. Execution Flow

1. User starts room.
2. System derives project name and mission.
3. Room template selected or inferred.
4. Agents are assigned.
5. Kickoff plan is generated.
6. Feasibility runs.
7. Business Study consumes feasibility output.
8. Functional Model consumes business study output.
9. Design & Build team consumes PRD/TRD/prototype outputs.
10. Implementation consumes release package.
11. Room summary and state are updated after each step.

## 9. Integration Points

### BaseAgent

Use `progress_callback` to stream room events.

### DSDMOrchestrator

Add optional `room_context` parameter to phase and role runs.

### Tool Registry

Add room tools:

- `room_create`
- `room_get_status`
- `room_add_decision`
- `room_add_blocker`
- `room_add_handoff`
- `room_export`

## 10. Acceptance Tests

- Creating a room produces `room_state.json`.
- Running room status returns project mission, agents, blockers, decisions, and next action.
- Running a phase appends handoff metadata.
- Exporting creates `DELIVERY_ROOM.md`.
- Failed phase creates blocker entry.

## 11. Security and Safety

- Human approval remains required for deployment, destructive file operations, and sensitive tools in manual/hybrid mode.
- Room state must not store secrets.
- Tool input/output logs should redact API keys and tokens.

## 12. Implementation Phases

### Phase 1

- Data models.
- JSON persistence.
- Room creation.
- Room status.
- Markdown export.

### Phase 2

- Orchestrator integration.
- Handoff generation.
- Blocker capture.
- Health scoring.

### Phase 3

- Multi-agent discussion.
- Jira/Confluence sync.
- UI dashboard.
