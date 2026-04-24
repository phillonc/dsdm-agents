# PRD: Living Project Memory Graph

## 1. Product Summary

Living Project Memory Graph gives every DSDM project a persistent, queryable knowledge graph connecting requirements, stakeholders, decisions, risks, architecture, code files, tests, defects, deployments, and outcomes.

Agents use this shared memory before planning or acting, and update it after producing artifacts. The result is a cumulative project brain instead of isolated prompt responses.

## 2. Problem Statement

AI agents lose value when context is scattered across generated docs, code files, chat history, and tool calls. Users must repeatedly restate requirements, constraints, and decisions. Agents can accidentally contradict earlier work or ignore hidden dependencies.

A living memory graph solves this by making project knowledge explicit, linked, and reusable.

## 3. Target Users

- Founders building products with AI agents
- Product managers managing evolving requirements
- Technical leads maintaining architectural consistency
- QA and security teams needing traceability
- Consultants creating long-running client delivery artifacts

## 4. Goals

- Persist structured project knowledge across all phases.
- Link requirements to decisions, risks, code, tests, deployments, and outcomes.
- Let agents query memory before acting.
- Let agents update memory after work is completed.
- Support impact analysis when requirements change.

## 5. Non-Goals

- Building a full enterprise knowledge graph UI in MVP.
- Replacing source control or issue tracking.
- Automatically trusting every generated fact without provenance.

## 6. Core User Stories

### Must Have

1. As a user, I can initialize project memory for a generated project.
2. As an agent, I can save requirements, decisions, risks, artifacts, and relationships.
3. As an agent, I can query memory for relevant context before execution.
4. As a user, I can ask what a requirement depends on.
5. As a user, I can ask what will be affected if a requirement changes.

### Should Have

1. As a user, I can view a memory summary as Markdown.
2. As a user, I can see confidence/provenance for memory items.
3. As an agent, I can detect contradictions between new and existing knowledge.
4. As a user, I can export memory to JSON.

### Could Have

1. Graph visualization.
2. Vector search over generated artifacts.
3. Integration with Jira and Confluence.
4. Semantic deduplication.

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| LPMG-PRD-FR-001 | Create project memory store under generated/<project>/memory/ | Must |
| LPMG-PRD-FR-002 | Store typed nodes: requirement, decision, risk, artifact, code_file, test, deployment, stakeholder | Must |
| LPMG-PRD-FR-003 | Store typed relationships: depends_on, implements, tests, mitigates, supersedes, blocks, owned_by | Must |
| LPMG-PRD-FR-004 | Provide memory query tool for agents | Must |
| LPMG-PRD-FR-005 | Provide memory update tool for agents | Must |
| LPMG-PRD-FR-006 | Support impact analysis for changed requirements | Must |
| LPMG-PRD-FR-007 | Generate Markdown memory summary | Should |
| LPMG-PRD-FR-008 | Track provenance for memory nodes | Should |
| LPMG-PRD-FR-009 | Detect conflicting facts or decisions | Should |

## 8. Acceptance Criteria

- Given a project memory store exists, when an agent adds a requirement, then the requirement has ID, title, description, source, priority, and timestamp.
- Given code implements a requirement, when the memory graph is queried, then the implementation link is returned.
- Given a requirement changes, when impact analysis runs, then affected decisions, files, tests, and risks are listed.
- Given an agent starts a task, when memory is enabled, then relevant memory context is included in the agent prompt.

## 9. Metrics

- 80% of generated phase outputs create or update memory nodes.
- 90% of requirements have at least one downstream relationship by design/build phase.
- 50% reduction in repeated context passed manually by users.
- Impact analysis returns useful dependencies in under 5 seconds for normal projects.

## 10. Risks

- Memory quality can degrade if agents store vague or duplicate information.
- Large projects may need indexing beyond JSON.
- Incorrect links could mislead future agents.

## 11. Release Plan

### MVP

- JSON graph store.
- Memory tools.
- Node and edge schema.
- Markdown export.
- Basic impact analysis.

### V2

- SQLite or graph database backend.
- Vector search.
- Conflict detection.
- Graph visualization.
- Jira/Confluence synchronization.

## 12. Open Questions

- Should memory be local-only or optionally synced to external systems?
- Should memory updates require approval in manual mode?
- Should each agent have private memory plus shared project memory?
