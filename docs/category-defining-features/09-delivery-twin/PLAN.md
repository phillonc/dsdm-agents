# Plan: Delivery Twin

## 1. Vision

Delivery Twin creates a live digital model of a project's delivery state. It represents scope, agents, requirements, architecture, code, tests, risks, blockers, environments, deployment status, quality gates, and release readiness.

Users can ask strategic questions such as:

- What is the weakest part of this project?
- What is blocking release?
- Which Must-have requirement is most at risk?
- What should we do next for maximum impact?

## 2. Strategic Purpose

Delivery Twin turns DSDM Agents into an AI operating system for software delivery. It goes beyond generated documents by maintaining a constantly updated model of project health and next-best actions.

## 3. MVP Scope

- Delivery state model.
- Health scoring.
- Risk and blocker aggregation.
- Readiness summary.
- Next-best-action recommendation.
- Markdown dashboard export.

## 4. Future Scope

- Visual dashboard.
- CI/CD and GitHub integration.
- Jira and Confluence sync.
- Predictive delivery forecasting.
- Simulation of descoping and capacity changes.

## 5. Proposed Components

```text
src/
├── twin/
│   ├── __init__.py
│   ├── delivery_twin.py
│   ├── twin_models.py
│   ├── twin_store.py
│   ├── twin_health.py
│   ├── twin_recommendations.py
│   ├── twin_forecast.py
│   └── twin_exporter.py
└── tools/
    └── delivery_twin_tools.py
```

## 6. Relationship to Features 1, 2, and 3

Delivery Twin should aggregate from:

- Autonomous Delivery Room: agents, blockers, decisions, handoffs.
- Living Project Memory Graph: requirements, risks, decisions, artifacts, dependencies.
- MoSCoW-to-Code Traceability Engine: implementation, test, and release readiness evidence.

It should not duplicate these stores permanently. It should act as a projection and scoring layer.

## 7. Data Model

```python
@dataclass
class DeliveryTwinState:
    project_name: str
    scope_health: float
    delivery_health: float
    quality_health: float
    release_health: float
    risk_health: float
    active_blockers: list[str]
    weak_points: list[str]
    next_best_actions: list[str]
    readiness_status: str
    updated_at: str
```

## 8. Health Dimensions

| Dimension | Signals |
|---|---|
| Scope health | MoSCoW completeness, open questions, change volatility |
| Delivery health | phase progress, handoff quality, blockers, timebox risk |
| Quality health | test coverage, failing tests, NFR status, code review gaps |
| Release health | deployment evidence, environment readiness, rollback plan |
| Risk health | open risks, severity, mitigation status |

## 9. Tool Interface

- `twin_build`
- `twin_refresh`
- `twin_get_health`
- `twin_get_weak_points`
- `twin_recommend_next_actions`
- `twin_export_dashboard`

## 10. CLI Commands

```bash
python main.py --twin-refresh --project my-project
python main.py --twin-health --project my-project
python main.py --twin-next-actions --project my-project
python main.py --twin-export --project my-project
```

## 11. Output Artifacts

```text
generated/<project>/docs/
└── DELIVERY_TWIN_DASHBOARD.md

generated/<project>/twin/
└── twin_state.json
```

## 12. Recommendation Engine

MVP recommendation rules:

- If Must-have requirement lacks code link, recommend design/build work.
- If Must-have requirement lacks passing tests, recommend automation testing.
- If deployment evidence missing, recommend implementation readiness work.
- If high severity risks have no mitigation, recommend feasibility/business review.
- If blockers exist for more than one phase, recommend delivery room escalation.

## 13. Implementation Roadmap

### Phase 1

- Add twin state model.
- Read from room, memory, and traceability JSON stores.
- Compute basic health scores.
- Export Markdown dashboard.

### Phase 2

- Add recommendation engine.
- Add CLI commands.
- Add agent/tool integration.

### Phase 3

- Add predictive forecasting.
- Add visual dashboard.
- Add CI/CD and issue tracker ingestion.

## 14. Risks

- Health scores may appear overly authoritative.
- Missing source data can create misleading conclusions.
- Duplicating state across modules can create inconsistency.

## 15. Guardrails

- Show confidence level for each score.
- Show missing data explicitly.
- Treat twin as decision support, not absolute truth.

## 16. Success Metrics

- Delivery twin identifies at least one useful next action for active projects.
- Release readiness summaries align with traceability evidence.
- Users can understand project health in under two minutes.
