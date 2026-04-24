# TRD: Living Project Memory Graph

## 1. Technical Summary

Living Project Memory Graph introduces a persistent project knowledge layer that stores typed nodes and relationships across the DSDM lifecycle. Agents use memory tools to retrieve relevant context, update project facts, and perform impact analysis.

## 2. Architecture Fit

This feature should integrate with:

- `BaseAgent.run()` to inject relevant memory context.
- `ToolRegistry` to expose memory tools.
- `generated/<project>/` output structure.
- Existing phase and role agents to store phase artifacts and links.

## 3. Proposed Components

```text
src/
├── memory/
│   ├── __init__.py
│   ├── graph_store.py
│   ├── graph_models.py
│   ├── graph_query.py
│   ├── impact_analysis.py
│   ├── memory_exporter.py
│   └── memory_context.py
└── tools/
    └── memory_tools.py
```

## 4. Data Storage

MVP storage:

```text
generated/<project>/memory/
├── graph.json
├── index.json
└── MEMORY_SUMMARY.md
```

Future storage options:

- SQLite for reliability and query performance.
- DuckDB for analytical queries.
- Neo4j or KuzuDB for graph-native workloads.
- Vector index for semantic retrieval.

## 5. Core Data Models

### MemoryNode

```python
@dataclass
class MemoryNode:
    id: str
    type: str
    title: str
    description: str
    properties: dict[str, Any]
    source: str
    confidence: float
    created_at: str
    updated_at: str
```

### MemoryEdge

```python
@dataclass
class MemoryEdge:
    id: str
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any]
    created_at: str
```

### MemoryGraph

```python
@dataclass
class MemoryGraph:
    project_name: str
    nodes: list[MemoryNode]
    edges: list[MemoryEdge]
    version: str
    updated_at: str
```

## 6. Node Types

- `requirement`
- `user_story`
- `acceptance_criteria`
- `stakeholder`
- `decision`
- `risk`
- `assumption`
- `artifact`
- `code_file`
- `test`
- `deployment`
- `metric`
- `blocker`

## 7. Edge Types

- `depends_on`
- `implements`
- `tests`
- `validates`
- `mitigates`
- `blocks`
- `owned_by`
- `supersedes`
- `derived_from`
- `documented_in`
- `deployed_by`

## 8. Tool Interface

Add tools:

- `memory_init`
- `memory_add_node`
- `memory_add_edge`
- `memory_query`
- `memory_get_context`
- `memory_impact_analysis`
- `memory_export_markdown`

Example schema:

```python
Tool(
    name="memory_query",
    description="Query project memory by node type, keywords, and relationship depth",
    input_schema={
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "query": {"type": "string"},
            "node_types": {"type": "array", "items": {"type": "string"}},
            "depth": {"type": "integer", "default": 1}
        },
        "required": ["project_name", "query"]
    },
    handler=memory_query_handler,
    requires_approval=False,
    category="memory"
)
```

## 9. Agent Context Injection

Add optional memory support to agent execution:

```python
result = agent.run(
    user_input,
    context={
        "project_name": project_name,
        "memory_context": memory_context
    }
)
```

`memory_get_context` should return a concise context pack:

- Relevant requirements.
- Active decisions.
- Constraints.
- Risks.
- Related files/tests.
- Open blockers.

## 10. Impact Analysis Algorithm

MVP algorithm:

1. Locate changed requirement node.
2. Traverse outgoing and incoming edges to configured depth.
3. Group affected nodes by type.
4. Rank by relationship type and distance.
5. Return recommended agent actions.

Example output:

```json
{
  "requirement": "REQ-001",
  "affected_decisions": ["ADR-003"],
  "affected_files": ["src/api/auth.py"],
  "affected_tests": ["tests/test_auth.py"],
  "risks": ["RISK-002"],
  "recommended_agents": ["BackendDeveloperAgent", "AutomationTesterAgent"]
}
```

## 11. Validation

- Validate graph schema on load.
- Prevent orphaned edges unless explicitly allowed.
- Generate stable IDs.
- Deduplicate nodes by type/title/source where possible.

## 12. Tests

- Unit tests for node creation.
- Unit tests for edge creation.
- Unit tests for graph persistence.
- Unit tests for impact traversal.
- Integration test: requirement to code to test trace.

## 13. Security and Privacy

- Do not store secrets.
- Redact tokens from artifact text.
- Mark memory nodes with provenance and confidence.
- Allow users to inspect memory before agent reuse.

## 14. Implementation Plan

### Phase 1

- Implement graph models.
- Implement JSON graph store.
- Implement memory tools.
- Implement Markdown export.

### Phase 2

- Inject memory context into orchestrator phase runs.
- Add impact analysis.
- Add deduplication and validation.

### Phase 3

- Add vector search.
- Add graph visualization.
- Add external sync.
