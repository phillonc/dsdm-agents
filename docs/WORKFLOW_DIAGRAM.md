# DSDM Agents Workflow Diagram

## Complete Workflow Overview

```
                                    ┌─────────────────────────────────────┐
                                    │           USER INPUT                │
                                    │   (Project Description/Task)        │
                                    └─────────────────┬───────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      DSDM ORCHESTRATOR                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  Tool Registry: create_dsdm_tool_registry(include_jira=True, include_confluence=True)   │   │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                              │
                                              ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                    PHASE 1: FEASIBILITY                                        ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Agent: FeasibilityAgent                                                                       ┃
┃  Mode: AUTOMATED                                                                               ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                                    TOOLS                                                 │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────────┐  ┌──────────────────────┐         │  ┃
┃  │  │ analyze_requirements│  │assess_technical_feasib. │  │   identify_risks     │         │  ┃
┃  │  └─────────────────────┘  └─────────────────────────┘  └──────────────────────┘         │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────────┐  ┌──────────────────────┐         │  ┃
┃  │  │    project_init     │  │      file_write         │  │   directory_create   │         │  ┃
┃  │  └─────────────────────┘  └─────────────────────────┘  └──────────────────────┘         │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────────────── JIRA/CONFLUENCE ──────────────────────────────────┐ │  ┃
┃  │  │ jira_create_issue │ jira_transition_issue │ jira_add_comment │ jira_enable_conf... │ │  ┃
┃  │  │ sync_work_item_status │ confluence_create_page │ confluence_create_dsdm_doc        │ │  ┃
┃  │  └────────────────────────────────────────────────────────────────────────────────────┘ │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  Output: FEASIBILITY_REPORT.md → generated/<project>/docs/                                     ┃
┃  Decision: GO / NO-GO                                                                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              │
                                              │ if GO
                                              ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                   PHASE 2: BUSINESS STUDY                                      ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Agent: BusinessStudyAgent                                                                     ┃
┃  Mode: AUTOMATED                                                                               ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                                    TOOLS                                                 │  ┃
┃  │  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────────┐      │  ┃
┃  │  │analyze_business_proc. │  │ identify_stakeholders │  │prioritize_requirements  │      │  ┃
┃  │  └───────────────────────┘  └───────────────────────┘  └─────────────────────────┘      │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────────┐      │  ┃
┃  │  │  define_architecture  │  │  create_timebox_plan  │  │    update_risk_log      │      │  ┃
┃  │  └───────────────────────┘  └───────────────────────┘  └─────────────────────────┘      │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────────────── JIRA/CONFLUENCE ──────────────────────────────────┐ │  ┃
┃  │  │ jira_create_issue │ jira_create_user_story │ jira_transition_issue │ jira_add_comm │ │  ┃
┃  │  │ jira_bulk_create_requirements │ sync_work_item_status │ confluence_create_page     │ │  ┃
┃  │  │ confluence_update_page │ confluence_create_dsdm_doc                                 │ │  ┃
┃  │  └────────────────────────────────────────────────────────────────────────────────────┘ │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  Output: BUSINESS_STUDY.md → generated/<project>/docs/                                         ┃
┃  MoSCoW: Must Have | Should Have | Could Have | Won't Have                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              │
                                              ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                    PHASE 3: PRD / TRD                                          ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃                                                                                                ┃
┃  ┌────────────────────────────────────┐    ┌────────────────────────────────────┐              ┃
┃  │      ProductManagerAgent           │    │         DevLeadAgent               │              ┃
┃  │      (Creates PRD)                 │───▶│         (Creates TRD)              │              ┃
┃  └────────────────────────────────────┘    └────────────────────────────────────┘              ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                                    TOOLS                                                 │  ┃
┃  │  ┌───────────────────────────────────────┐  ┌────────────────────────────────────────┐   │  ┃
┃  │  │ generate_product_requirements_document│  │generate_technical_requirements_document│   │  ┃
┃  │  └───────────────────────────────────────┘  └────────────────────────────────────────┘   │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  Output: PRODUCT_REQUIREMENTS.md, TECHNICAL_REQUIREMENTS.md → generated/<project>/docs/        ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                           APPROVAL GATE                                                  │  ┃
┃  │            Dev Lead & Test Lead must approve before Jira/Confluence sync                 │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                              │                                                 ┃
┃                                              ▼                                                 ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                      SYNC TO JIRA & CONFLUENCE                                           │  ┃
┃  │   • PRD → Confluence (Business Requirements Doc)                                         │  ┃
┃  │   • TRD → Confluence (Technical Design Doc)                                              │  ┃
┃  │   • Requirements → Jira Issues (with MoSCoW priorities)                                  │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              │
                                              ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                 PHASE 4: FUNCTIONAL MODEL                                      ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Agent: FunctionalModelAgent                                                                   ┃
┃  Mode: AUTOMATED                                                                               ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                                    TOOLS                                                 │  ┃
┃  │  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────────┐      │  ┃
┃  │  │   create_prototype    │  │ generate_code_scaffold│  │ collect_user_feedback   │      │  ┃
┃  │  └───────────────────────┘  └───────────────────────┘  └─────────────────────────┘      │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────────┐      │  ┃
┃  │  │  refine_requirements  │  │  run_functional_tests │  │   document_iteration    │      │  ┃
┃  │  └───────────────────────┘  └───────────────────────┘  └─────────────────────────┘      │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────────────── JIRA/CONFLUENCE ──────────────────────────────────┐ │  ┃
┃  │  │ jira_transition_issue │ jira_update_issue │ jira_add_comment │ sync_work_item_stat │ │  ┃
┃  │  │ confluence_update_page │ confluence_add_comment                                     │ │  ┃
┃  │  └────────────────────────────────────────────────────────────────────────────────────┘ │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                              ITERATION LOOP                                              │  ┃
┃  │       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │  ┃
┃  │       │   Build     │────▶│  Demo to    │────▶│   Gather    │────▶│   Refine    │───┐   │  ┃
┃  │       │  Prototype  │     │ Stakeholders│     │  Feedback   │     │Requirements │   │   │  ┃
┃  │       └─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘   │   │  ┃
┃  │              ▲                                                           │          │   │  ┃
┃  │              └───────────────────────────────────────────────────────────┘          │   │  ┃
┃  │                                         Repeat until satisfied                      │   │  ┃
┃  └─────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  Output: FUNCTIONAL_MODEL_REPORT.md, prototypes/ → generated/<project>/                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              │
                                              ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                  PHASE 5: DESIGN & BUILD                                       ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Agent: DesignBuildAgent (or Specialized Team)                                                 ┃
┃  Mode: HYBRID                                                                                  ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                          SPECIALIZED TEAM (Optional)                                     │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  ┃
┃  │  │  Dev Lead   │  │  Frontend   │  │  Backend    │  │ Automation  │  │    NFR      │    │  ┃
┃  │  │   Agent     │─▶│  Developer  │─▶│  Developer  │─▶│   Tester    │─▶│   Tester    │──┐ │  ┃
┃  │  │  (HYBRID)   │  │ (AUTOMATED) │  │ (AUTOMATED) │  │ (AUTOMATED) │  │  (HYBRID)   │  │ │  ┃
┃  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │  ┃
┃  │                                                                                       │ │  ┃
┃  │                                                           ┌─────────────┐             │ │  ┃
┃  │                                                           │     Pen     │◀────────────┘ │  ┃
┃  │                                                           │   Tester    │               │  ┃
┃  │                                                           │  (MANUAL)   │               │  ┃
┃  │                                                           └─────────────┘               │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                                    TOOLS                                                 │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐              │  ┃
┃  │  │create_technical_des.│  │    generate_code    │  │     write_file      │              │  ┃
┃  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘              │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐              │  ┃
┃  │  │     run_tests       │  │    review_code      │  │create_documentation │              │  ┃
┃  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘              │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────────────────────────────────────┐       │  ┃
┃  │  │   security_check    │  │  generate_technical_requirements_document (TRD)     │       │  ┃
┃  │  └─────────────────────┘  └─────────────────────────────────────────────────────┘       │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────────────── JIRA/CONFLUENCE ──────────────────────────────────┐ │  ┃
┃  │  │ jira_transition_issue │ jira_update_issue │ jira_add_comment │ jira_search         │ │  ┃
┃  │  │ sync_work_item_status │ confluence_update_page │ confluence_add_comment            │ │  ┃
┃  │  └────────────────────────────────────────────────────────────────────────────────────┘ │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  Output: src/, tests/, docs/ → generated/<project>/                                            ┃
┃  Requires: All tests passed                                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              │
                                              │ if tests passed
                                              ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                  PHASE 6: IMPLEMENTATION                                       ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Agent: ImplementationAgent                                                                    ┃
┃  Mode: MANUAL (requires approval for deployments)                                              ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                                    TOOLS                                                 │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐              │  ┃
┃  │  │create_deployment_pl.│  │  setup_environment  │  │   deploy_system     │              │  ┃
┃  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘              │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐              │  ┃
┃  │  │  run_smoke_tests    │  │   create_rollback   │  │  execute_rollback   │              │  ┃
┃  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘              │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐              │  ┃
┃  │  │create_training_mat. │  │notify_stakeholders  │  │generate_handover_d. │              │  ┃
┃  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘              │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌───────────────────────────────── JIRA/CONFLUENCE ──────────────────────────────────┐ │  ┃
┃  │  │ jira_transition_issue │ jira_update_issue │ jira_add_comment │ jira_search         │ │  ┃
┃  │  │ sync_work_item_status │ confluence_update_page │ confluence_add_comment            │ │  ┃
┃  │  │ confluence_create_dsdm_doc                                                         │ │  ┃
┃  │  └────────────────────────────────────────────────────────────────────────────────────┘ │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                           DEPLOYMENT WORKFLOW                                            │  ┃
┃  │                                                                                          │  ┃
┃  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │  ┃
┃  │  │ Create  │──▶│ Setup   │──▶│ Deploy  │──▶│ Smoke   │──▶│ Verify  │──▶│Handover │     │  ┃
┃  │  │  Plan   │   │   Env   │   │ System  │   │  Tests  │   │   &     │   │   to    │     │  ┃
┃  │  │         │   │         │   │         │   │         │   │ Monitor │   │   Ops   │     │  ┃
┃  │  └─────────┘   └─────────┘   └─────────┘   └────┬────┘   └─────────┘   └─────────┘     │  ┃
┃  │                                                 │                                       │  ┃
┃  │                                                 ▼ if failed                             │  ┃
┃  │                                          ┌─────────────┐                                │  ┃
┃  │                                          │  ROLLBACK   │                                │  ┃
┃  │                                          └─────────────┘                                │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                                                ┃
┃  Output: DEPLOYMENT_PLAN.md, TRAINING_MATERIALS.md, HANDOVER_DOCS.md → generated/<project>/    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                              │
                                              ▼
                               ┌──────────────────────────────┐
                               │     SYSTEM DEPLOYED          │
                               │     Documentation Complete   │
                               │     Stakeholders Notified    │
                               └──────────────────────────────┘
```

---

## Cross-Cutting: DevOps Agent

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                    DEVOPS AGENT                                                ┃
┃                        (Available throughout all phases)                                       ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Mode: HYBRID                                                                                  ┃
┃  Based on: 14 Development Principles                                                           ┃
┃                                                                                                ┃
┃  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  ┃
┃  │                              TOOL CATEGORIES (28 tools)                                  │  ┃
┃  │                                                                                          │  ┃
┃  │  Testing & Quality          CI/CD & Automation        Infrastructure                    │  ┃
┃  │  ─────────────────          ──────────────────        ──────────────                    │  ┃
┃  │  • run_tests                • run_ci_pipeline         • provision_infrastructure        │  ┃
┃  │  • check_coverage           • deploy_to_environment   • validate_terraform              │  ┃
┃  │  • run_linter               • rollback_deployment     • manage_containers               │  ┃
┃  │  • run_security_scan        • automate_task           • scale_service                   │  ┃
┃  │  • check_code_quality                                                                   │  ┃
┃  │                                                                                          │  ┃
┃  │  Monitoring & Health        NFRs & Dependencies       Documentation                     │  ┃
┃  │  ───────────────────        ────────────────────      ─────────────                     │  ┃
┃  │  • health_check             • analyze_dependencies    • create_adr                      │  ┃
┃  │  • setup_monitoring         • run_performance_test    • generate_docs                   │  ┃
┃  │  • check_service_status     • check_accessibility     • track_decision                  │  ┃
┃  │  • run_chaos_test           • validate_nfr                                              │  ┃
┃  │                                                                                          │  ┃
┃  │  Task Management            Backup & Recovery                                           │  ┃
┃  │  ───────────────            ─────────────────                                           │  ┃
┃  │  • check_incomplete_tasks   • backup_database                                           │  ┃
┃  │  • track_toil               • test_restore                                              │  ┃
┃  └──────────────────────────────────────────────────────────────────────────────────────────┘  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Jira/Confluence Sync Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              JIRA/CONFLUENCE SYNC WORKFLOW                                      │
│                                                                                                 │
│  ┌──────────────────────┐                                                                       │
│  │  Agent performs      │                                                                       │
│  │  status change       │                                                                       │
│  └──────────┬───────────┘                                                                       │
│             │                                                                                   │
│             ▼                                                                                   │
│  ┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────────────┐    │
│  │ jira_transition_     │────────▶│ Automatic sync       │────────▶│ Confluence page      │    │
│  │ issue / update_issue │         │ triggered            │         │ updated              │    │
│  └──────────────────────┘         └──────────────────────┘         └──────────────────────┘    │
│                                                                                                 │
│                                   OR                                                            │
│                                                                                                 │
│  ┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────────────┐    │
│  │ sync_work_item_      │────────▶│ Manual sync with     │────────▶│ Status Log page      │    │
│  │ status               │         │ DSDM phase context   │         │ updated              │    │
│  └──────────────────────┘         └──────────────────────┘         └──────────────────────┘    │
│                                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              STATUS LOG PAGE (Confluence)                                │  │
│  │  ┌───────────────┬─────────────┬────────────────┬────────────┬─────────────────┐        │  │
│  │  │   Timestamp   │  Issue Key  │    Summary     │   Status   │   Update Type   │        │  │
│  │  ├───────────────┼─────────────┼────────────────┼────────────┼─────────────────┤        │  │
│  │  │ 2025-01-15    │  PROJ-123   │ User Auth      │ In Progress│ transition      │        │  │
│  │  │ 2025-01-16    │  PROJ-124   │ Dashboard API  │ Code Review│ field_update    │        │  │
│  │  │ 2025-01-17    │  PROJ-123   │ User Auth      │ Done       │ transition      │        │  │
│  │  └───────────────┴─────────────┴────────────────┴────────────┴─────────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Modes Summary

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AGENT MODES                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  EXECUTION MODES (Tool Approval)                                                                │
│  ═══════════════════════════════                                                                │
│                                                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                                       │
│  │  AUTOMATED  │     │   HYBRID    │     │   MANUAL    │                                       │
│  │─────────────│     │─────────────│     │─────────────│                                       │
│  │ All tools   │     │ Some tools  │     │ All tools   │                                       │
│  │ run without │     │ auto-run,   │     │ require     │                                       │
│  │ approval    │     │ critical    │     │ approval    │                                       │
│  │             │     │ need approve│     │             │                                       │
│  └─────────────┘     └─────────────┘     └─────────────┘                                       │
│                                                                                                 │
│  Default by Phase:                                                                              │
│  • Feasibility      → AUTOMATED                                                                 │
│  • Business Study   → AUTOMATED                                                                 │
│  • Functional Model → AUTOMATED                                                                 │
│  • Design & Build   → HYBRID                                                                    │
│  • Implementation   → MANUAL                                                                    │
│                                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  WORKFLOW MODES (Agent Interaction Style)                                                       │
│  ════════════════════════════════════════                                                       │
│                                                                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐                           │
│  │ AGENT_WRITES_CODE │  │AGENT_PROVIDES_TIPS│  │ MANUAL_WITH_TIPS  │                           │
│  │───────────────────│  │───────────────────│  │───────────────────│                           │
│  │ Agent writes code │  │ Agent provides    │  │ Developer writes  │                           │
│  │ autonomously      │  │ guidance only     │  │ code, agent       │                           │
│  │ using tools       │  │ (no code writing) │  │ advises           │                           │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘                           │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Output Structure

```
generated/
└── <project-name>/
    ├── docs/
    │   ├── FEASIBILITY_REPORT.md          ◀── Phase 1
    │   ├── BUSINESS_STUDY.md              ◀── Phase 2
    │   ├── PRODUCT_REQUIREMENTS.md        ◀── Phase 3 (PRD)
    │   ├── TECHNICAL_REQUIREMENTS.md      ◀── Phase 3 (TRD)
    │   ├── FUNCTIONAL_MODEL_REPORT.md     ◀── Phase 4
    │   ├── DEPLOYMENT_PLAN.md             ◀── Phase 6
    │   ├── TRAINING_MATERIALS.md          ◀── Phase 6
    │   ├── HANDOVER_DOCS.md               ◀── Phase 6
    │   ├── api/                           ◀── API documentation
    │   ├── architecture/                  ◀── ADRs
    │   │   └── decisions/
    │   └── user-guides/                   ◀── End-user docs
    │
    ├── src/                               ◀── Phase 5 (Production code)
    │   └── ...
    │
    ├── tests/                             ◀── Phase 5 (Test files)
    │   ├── unit/
    │   └── integration/
    │
    ├── prototypes/                        ◀── Phase 4 (Functional prototypes)
    │
    ├── config/                            ◀── Configuration files
    │
    ├── README.md
    ├── .gitignore
    └── pyproject.toml / package.json
```

---

## Quick Reference: CLI Commands

```bash
# Run full workflow
python main.py --workflow --input "Build a task management app"

# Run specific phase
python main.py --phase feasibility --input "Analyze e-commerce migration"
python main.py --phase design_build --input "Add notifications feature"

# Interactive mode
python main.py --interactive

# List phases and tools
python main.py --list-phases
python main.py --list-tools

# Set execution mode
python main.py --phase design_build --mode manual --input "Deploy to production"
```
