---
applyTo: ".github/agents/**"
description: Catalogue of DSDM tools registered in src/tools/. Reference this when an agent needs to know which tool name to call.
---

# DSDM Tools Catalogue

This file lists every tool registered in `src/tools/`. Agents call them via the Python tool registry (`src/tools/tool_registry.py`) at runtime; from the Copilot CLI side they appear as named functions invokable by the orchestrator.

When you (the agent) need a capability, prefer the **named tool** over a raw shell invocation — the named tool already handles output paths, validation, and Jira/Confluence sync.

## Feasibility tools (`src/tools/dsdm_tools.py`)

| Tool | Purpose |
|------|---------|
| `analyze_requirements` | Extract functional / non-functional requirements, entities, ambiguities |
| `assess_technical_feasibility` | Score technology maturity, constraint risks, give recommendations |
| `identify_risks` | Categorised risks with mitigations + severity |

## Product Management tools

| Tool | Purpose |
|------|---------|
| `generate_product_requirements_document` | Structured PRD generator |

## Business Study tools

| Tool | Purpose |
|------|---------|
| `analyze_business_process` | Walk current process, find pain points |
| `identify_stakeholders` | Map stakeholders + influence |
| `prioritize_requirements` | Apply MoSCoW |
| `define_architecture` | High-level architecture |
| `create_timebox_plan` | Initial timeboxes |
| `update_risk_log` | Refresh risks |

## Functional Model tools

| Tool | Purpose |
|------|---------|
| `create_prototype` | Generate a prototype |
| `generate_code_scaffold` | Bootstrap code skeleton |
| `collect_user_feedback` | Capture stakeholder feedback |
| `refine_requirements` | Update requirements from feedback |
| `run_functional_tests` | Execute prototype tests |
| `document_iteration` | Log iteration outcomes |

## Design & Build tools

| Tool | Purpose |
|------|---------|
| `create_technical_design` | Detailed technical design |
| `generate_code` | Generate production code |
| `write_file` | Legacy file writer (prefer `file_write`) |
| `run_tests` | Execute test suite |
| `review_code` | Code review pass |
| `create_documentation` | Build docs |
| `security_check` | Security audit on generated code |
| `generate_technical_requirements_document` | Build the TRD |

## Implementation tools

| Tool | Purpose |
|------|---------|
| `create_deployment_plan` | Deployment plan doc |
| `setup_environment` | Prep target env |
| `deploy_system` | Execute deployment (require approval) |
| `run_smoke_tests` | Post-deploy smoke tests |
| `create_rollback` | Rollback plan |
| `execute_rollback` | Run rollback (require approval) |
| `create_training_materials` | User training |
| `notify_stakeholders` | Comms |
| `generate_handover_docs` | Ops handover |

## DevOps tools (`src/tools/integrations/devops_tools.py`)

| Tool | Purpose |
|------|---------|
| `run_tests` | pytest 9.0.1 |
| `check_coverage` | pytest-cov 4.1.0 |
| `run_linter` | ruff 0.1.7 / pylint / flake8 |
| `run_security_scan` | bandit / safety / pip-audit |
| `check_code_quality` | Aggregate quality report |
| `run_ci_pipeline` | Trigger CI |
| `deploy_to_environment` | Targeted deploy |
| `rollback_deployment` | Revert |
| `automate_task` | Toil-elimination wrapper |
| `provision_infrastructure` | Terraform 1.5.7 |
| `validate_terraform` | `terraform validate` |
| `manage_containers` | Docker 28.5.1 |
| `scale_service` | Horizontal scale |
| `health_check` | Service health probe |
| `setup_monitoring` | Add metrics/alerts |
| `check_service_status` | Status query |
| `run_chaos_test` | Failure injection (require approval) |
| `analyze_dependencies` | Dep graph + vulnerabilities |
| `run_performance_test` | locust 2.42.6 |
| `check_accessibility` | pa11y 9.0.1 |
| `validate_nfr` | NFR compliance check |
| `create_adr` | Write an ADR |
| `generate_docs` | Doc generation |
| `track_decision` | Log a decision |
| `check_incomplete_tasks` | WIP audit |
| `track_toil` | Toil register |
| `backup_database` | Backup |
| `test_restore` | DR drill |

## File / project tools (`src/tools/file_tools.py`)

All paths are placed under `generated/` automatically.

| Tool | Purpose |
|------|---------|
| `project_init` | Bootstrap a new `generated/<project>/` skeleton |
| `project_list` | List existing projects |
| `project_get` | Fetch project metadata |
| `file_write` | Write a file (use this — not `write_file`) |
| `file_read` | Read a file |
| `file_append` | Append to a file |
| `file_delete` | Delete a file |
| `file_copy` | Copy a file |
| `directory_create` | Create directory |
| `directory_list` | List directory |

## Atlassian integration

### Jira (`src/tools/integrations/jira_tools.py`)
- `jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_search`
- `jira_transition_issue`, `jira_add_comment`, `jira_get_project`
- `jira_create_user_story`, `jira_create_timebox`, `jira_bulk_create_requirements`
- `jira_enable_confluence_sync`, `jira_disable_confluence_sync`, `jira_sync_to_confluence`, `jira_set_confluence_page_mapping`

### Confluence (`src/tools/integrations/confluence_tools.py`)
- `confluence_get_page`, `confluence_create_page`, `confluence_update_page`
- `confluence_search`, `confluence_get_space`, `confluence_add_comment`
- `confluence_create_dsdm_doc`

### Sync helpers (`src/tools/dsdm_tools.py`)
- `sync_work_item_status`, `setup_jira_confluence_sync`, `get_sync_status`

## Tool registration

Every tool above is wired in `src/tools/tool_registry.py` via `register_tool(...)`. To add a new tool, register it there and reference its name in the relevant agent's prompt body.
