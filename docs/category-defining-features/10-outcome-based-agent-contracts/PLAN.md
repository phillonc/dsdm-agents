# Plan: Outcome-Based Agent Contracts

## 1. Vision

Outcome-Based Agent Contracts let users define the desired business or technical outcome instead of prescribing tasks. Agents then decompose the outcome into requirements, hypotheses, metrics, implementation work, tests, deployment evidence, and monitoring.

Examples:

- Reduce checkout abandonment by 15%.
- Improve API latency below 200ms.
- Deliver an MVP in 10 working days with Must-have scope only.
- Make onboarding WCAG AA accessible.
- Increase marketplace supplier activation by 20%.

## 2. Strategic Purpose

This feature shifts DSDM Agents from task automation to outcome automation. It connects delivery to measurable value and supports DSDM's focus on business need.

## 3. MVP Scope

- Outcome contract model.
- Outcome decomposition into requirements and metrics.
- Agent assignment by outcome type.
- Success criteria and evidence plan.
- Contract status reporting.

## 4. Future Scope

- Experiment design.
- Production metric ingestion.
- Automated hypothesis tracking.
- Contract-based release gates.
- Outcome marketplace templates.

## 5. Proposed Components

```text
src/
├── outcomes/
│   ├── __init__.py
│   ├── outcome_contract.py
│   ├── outcome_models.py
│   ├── outcome_decomposer.py
│   ├── outcome_metrics.py
│   ├── outcome_evidence.py
│   └── outcome_exporter.py
└── tools/
    └── outcome_tools.py
```

## 6. Outcome Contract Model

```python
@dataclass
class OutcomeContract:
    id: str
    project_name: str
    title: str
    outcome_statement: str
    baseline: str | None
    target: str
    metric: str
    deadline: str | None
    owner: str | None
    confidence: float
    status: str
    assumptions: list[str]
    requirements: list[str]
    evidence: list[str]
    created_at: str
    updated_at: str
```

## 7. Contract Types

- Business growth
- Cost reduction
- Conversion improvement
- Performance improvement
- Reliability improvement
- Accessibility compliance
- Security hardening
- MVP delivery
- Migration success
- Operational efficiency

## 8. Tool Interface

- `outcome_create_contract`
- `outcome_decompose`
- `outcome_define_metrics`
- `outcome_generate_evidence_plan`
- `outcome_assign_agents`
- `outcome_status`
- `outcome_export`

## 9. Output Artifacts

```text
generated/<project>/outcomes/
├── contracts.json
└── evidence.json

generated/<project>/docs/outcomes/
├── OUTCOME_CONTRACT_<id>.md
└── OUTCOME_STATUS.md
```

## 10. Agent Flow

1. User defines an outcome.
2. Outcome Decomposer clarifies metric, baseline, target, and constraints.
3. Business Study Agent converts outcome into MoSCoW requirements.
4. Dev Lead maps architecture and technical approach.
5. Relevant developer agents implement changes.
6. Tester agents define verification evidence.
7. DevOps/Implementation agents define monitoring and release evidence.
8. Delivery Twin reports whether outcome is on track.

## 11. CLI Commands

```bash
python main.py --outcome-create --project shop-app --input "Reduce checkout abandonment by 15%"
python main.py --outcome-status --project shop-app
python main.py --outcome-export --project shop-app
```

## 12. Success Criteria Pattern

Every outcome contract should include:

- Outcome statement.
- Baseline or known unknown.
- Target value.
- Metric definition.
- Measurement method.
- Time horizon.
- Assumptions.
- Required changes.
- Evidence required.
- Agent ownership.

## 13. Implementation Roadmap

### Phase 1

- Add contract models.
- Add JSON persistence.
- Add outcome decomposition tool.
- Add Markdown export.

### Phase 2

- Link outcome contracts to MoSCoW requirements.
- Link outcome evidence to traceability.
- Add contract status reporting.

### Phase 3

- Add production metric integrations.
- Add experiment tracking.
- Add outcome-based release gates.

## 14. Risks

- Outcomes may be vague or not measurable.
- Users may not know the baseline.
- Agents may overpromise business impact.

## 15. Guardrails

- Require measurable target or mark as exploratory.
- Separate delivery evidence from real-world outcome evidence.
- Show assumptions and confidence clearly.
- Avoid claiming outcome achieved without measurement.

## 16. Success Metrics

- 90% of outcome contracts include measurable targets or explicit unknown baseline.
- Each contract generates requirements and evidence plan.
- Users can see whether delivery work maps to business value.
