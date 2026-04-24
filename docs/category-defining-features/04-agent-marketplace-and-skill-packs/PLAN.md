# Plan: Agent Marketplace and Skill Packs

## 1. Vision

Agent Marketplace and Skill Packs transform DSDM Agents from a fixed framework into an extensible platform. Users can install, create, share, and compose domain-specific agent packs for industries, delivery patterns, technologies, compliance regimes, and product categories.

Examples:

- Startup MVP Pack
- Marketplace Platform Pack
- SaaS Billing Pack
- Healthcare Compliance Pack
- FinTech Security Pack
- Accessibility Pack
- AI Safety Pack
- Enterprise Migration Pack

## 2. Strategic Purpose

This feature creates an ecosystem layer. Instead of one repository containing all agent logic, DSDM Agents becomes a platform where new capabilities can be added through packaged skills.

## 3. Scope

### MVP Scope

- Local skill pack format.
- Skill pack discovery from `packs/` folder.
- Pack metadata.
- Pack-defined prompts, tools, checklists, templates, and agent overrides.
- CLI commands to list and activate packs.

### Future Scope

- Remote marketplace registry.
- Pack publishing workflow.
- Versioning and compatibility checks.
- Community ratings and trust levels.
- Paid/private packs.

## 4. Proposed Repository Structure

```text
packs/
├── startup-mvp/
│   ├── pack.yaml
│   ├── prompts/
│   ├── tools/
│   ├── templates/
│   ├── checklists/
│   └── examples/
├── marketplace-platform/
└── accessibility/
```

## 5. Pack Manifest

```yaml
name: marketplace-platform
version: 0.1.0
description: Skill pack for two-sided and multi-sided platform products
author: dsdm-agents
compatibility:
  min_dsdm_agents_version: 0.1.0
agents:
  - ProductStrategyAgent
  - PlatformEconomicsAgent
  - TrustSafetyAgent
prompts:
  business_study: prompts/business_study.md
  design_build: prompts/design_build.md
templates:
  prd: templates/platform_prd.md
  trd: templates/platform_trd.md
checklists:
  launch: checklists/launch.md
  trust_safety: checklists/trust_safety.md
tools:
  - tools/network_effects.py
```

## 6. Functional Plan

| Capability | Description | Priority |
|---|---|---|
| Pack discovery | Load available packs from local folder | Must |
| Pack validation | Validate manifest and required files | Must |
| Pack activation | Activate one or more packs for a project | Must |
| Prompt extension | Add pack-specific prompt fragments to agents | Must |
| Template extension | Use pack-specific PRD/TRD/checklist templates | Should |
| Tool extension | Register pack-provided tools | Should |
| Pack compatibility | Check framework version compatibility | Should |
| Pack publishing | Publish pack to registry | Could |

## 7. Technical Components

```text
src/
├── packs/
│   ├── __init__.py
│   ├── pack_manifest.py
│   ├── pack_loader.py
│   ├── pack_registry.py
│   ├── pack_validator.py
│   └── pack_context.py
└── tools/
    └── pack_tools.py
```

## 8. CLI Commands

```bash
python main.py --pack-list
python main.py --pack-info marketplace-platform
python main.py --pack-activate marketplace-platform --project my-project
python main.py --workflow --pack marketplace-platform --input "Build a services marketplace"
```

## 9. Integration Points

- `AgentConfig.system_prompt`: append active pack prompt fragments.
- `ToolRegistry`: register pack tools.
- `DSDMOrchestrator`: accept `active_packs` parameter.
- `generated/<project>/`: persist active pack configuration.

## 10. Implementation Roadmap

### Phase 1: Local Pack Foundation

- Add pack manifest model.
- Add loader and validator.
- Add CLI list/info commands.
- Add sample `startup-mvp` and `marketplace-platform` packs.

### Phase 2: Agent Integration

- Inject pack prompts into agents.
- Register pack-specific tools.
- Use pack templates for PRD/TRD output.

### Phase 3: Marketplace Preparation

- Add versioning.
- Add signing/trust metadata.
- Add remote registry abstraction.
- Add pack publishing commands.

## 11. Risks

- Poor-quality packs could reduce output quality.
- Tool execution from packs creates security risk.
- Pack conflicts need resolution rules.

## 12. Safety Requirements

- Pack tools should default to requiring approval.
- Remote packs must not execute code without explicit trust.
- Pack manifests should declare permissions.

## 13. Success Metrics

- Users can activate a pack in under one minute.
- At least three sample packs produce visibly different outputs.
- Pack prompts reduce manual customization for domain projects.
