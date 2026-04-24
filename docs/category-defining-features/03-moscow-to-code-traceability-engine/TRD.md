# TRD: MoSCoW-to-Code Traceability Engine

## 1. Technical Summary

MoSCoW-to-Code Traceability Engine adds a requirement evidence layer that links prioritized requirements to stories, acceptance criteria, ADRs, source files, tests, test results, deployments, and release readiness.

This can be implemented as a focused traceability module and later integrated deeply with Living Project Memory Graph.

## 2. Architecture Fit

The repository already creates project artifacts under `generated/<project>/` and includes Business Study, Design & Build, Automation Tester, NFR Tester, DevOps, and Implementation agents. Traceability should connect these agent outputs.

## 3. Proposed Components

```text
src/
├── traceability/
│   ├── __init__.py
│   ├── trace_models.py
│   ├── trace_store.py
│   ├── trace_matrix.py
│   ├── readiness.py
│   ├── test_evidence.py
│   └── trace_exporter.py
└── tools/
    └── traceability_tools.py
```

## 4. Storage Layout

```text
generated/<project>/traceability/
├── requirements.json
├── links.json
├── test_evidence.json
├── TRACEABILITY_MATRIX.md
└── RELEASE_READINESS.md
```

## 5. Core Data Models

### TraceRequirement

```python
@dataclass
class TraceRequirement:
    id: str
    title: str
    description: str
    moscow_priority: str
    status: str
    source: str
    owner: str | None
    created_at: str
    updated_at: str
```

### TraceLink

```python
@dataclass
class TraceLink:
    id: str
    requirement_id: str
    target_type: str
    target_ref: str
    relationship: str
    confidence: float
    created_by: str
    created_at: str
```

### TestEvidence

```python
@dataclass
class TestEvidence:
    id: str
    requirement_id: str
    test_ref: str
    status: str
    last_run_at: str | None
    output_ref: str | None
```

### ReadinessReport

```python
@dataclass
class ReadinessReport:
    project_name: str
    must_total: int
    must_implemented: int
    must_tested: int
    must_passing: int
    blockers: list[str]
    recommendation: str
    generated_at: str
```

## 6. Tool Interface

Add tools:

- `trace_register_requirement`
- `trace_link_artifact`
- `trace_link_code`
- `trace_link_test`
- `trace_record_test_result`
- `trace_generate_matrix`
- `trace_release_readiness`
- `trace_export`

## 7. Trace Matrix Columns

| Column | Description |
|---|---|
| Requirement ID | Stable requirement identifier |
| Priority | Must, Should, Could, Won't |
| Status | Proposed, designed, implemented, tested, deployed, blocked |
| Story Links | Related stories |
| ADR Links | Related architecture decisions |
| Code Links | Source files implementing the requirement |
| Test Links | Unit/integration/e2e tests |
| Test Status | Passing, failing, missing, unknown |
| Release Evidence | Deployment or release notes |
| Gaps | Missing proof or blockers |

## 8. Readiness Algorithm

1. Load all requirements.
2. Filter Must-have requirements.
3. For each Must-have, check code links.
4. Check test links.
5. Check latest test evidence.
6. Identify blockers and missing evidence.
7. Generate recommendation:
   - `ready`
   - `ready_with_risk`
   - `not_ready`

## 9. Agent Integration

### BusinessStudyAgent

- Registers MoSCoW requirements.
- Links user stories and acceptance criteria.

### DevLeadAgent

- Links ADRs and architecture artifacts.

### FrontendDeveloperAgent / BackendDeveloperAgent

- Link created files to requirements.

### AutomationTesterAgent

- Link tests and store results.

### ImplementationAgent

- Link deployment evidence and release notes.

## 10. CLI Commands

```bash
python main.py --trace-matrix --project my-project
python main.py --trace-readiness --project my-project
python main.py --trace-export --project my-project
```

## 11. Tests

- Requirement registration test.
- Code link creation test.
- Test link creation test.
- Matrix generation test.
- Readiness report test.
- Missing Must-have evidence test.

## 12. Migration Path to Memory Graph

Traceability can either:

1. Remain a separate focused module, or
2. Use Living Project Memory Graph as the backing store.

Recommended approach:

- MVP: separate JSON store for speed.
- V2: memory graph becomes canonical store; traceability becomes a projection/report.

## 13. Security and Safety

- Do not expose private file contents unless requested.
- Do not store secrets in test evidence.
- Human approval can be required for changing requirement status in manual mode.

## 14. Implementation Plan

### Phase 1

- Data models.
- JSON store.
- Requirement registration.
- Artifact links.

### Phase 2

- Test evidence ingestion.
- Trace matrix generation.
- Readiness report.

### Phase 3

- Agent integration.
- CI/PR checks.
- Jira/GitHub integration.
