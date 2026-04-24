# Plan: Product-to-Platform Strategy Agent

## 1. Vision

Product-to-Platform Strategy Agent helps users evolve a single product idea into a scalable platform and eventually an ecosystem. It analyzes customer, retailer/provider, supplier/partner, developer, data, API, and marketplace opportunities.

The agent encourages platform thinking from the earliest DSDM phases.

## 2. Strategic Purpose

Many products fail to become category-defining because they remain single-purpose tools. This agent helps identify expansion paths, network effects, partner loops, ecosystem moats, and monetization layers.

## 3. Core Jobs

- Identify whether a product has platform potential.
- Map the customer-provider-supplier triangle.
- Identify network effects and ecosystem loops.
- Recommend APIs, plugin points, partner capabilities, and marketplace models.
- Produce a platform evolution roadmap.

## 4. MVP Scope

- New strategy agent class.
- Platform potential assessment.
- Ecosystem actor map.
- Platform roadmap output.
- Integration with Feasibility and Business Study phases.

## 5. Future Scope

- Marketplace economics simulator.
- Partner onboarding model.
- Developer ecosystem strategy.
- Trust and safety model.
- API monetization advisor.

## 6. Proposed Components

```text
src/
├── agents/
│   └── platform_strategy_agent.py
├── strategy/
│   ├── platform_models.py
│   ├── ecosystem_mapper.py
│   ├── network_effects.py
│   └── platform_roadmap.py
└── tools/
    └── platform_strategy_tools.py
```

## 7. Agent Responsibilities

| Responsibility | Description |
|---|---|
| Platform potential scoring | Determine whether the idea can become a platform |
| Ecosystem actor mapping | Identify customers, providers, suppliers, partners, developers, regulators |
| Network effect analysis | Identify direct, indirect, data, social, and marketplace effects |
| API surface recommendation | Recommend public/internal APIs and extension points |
| Monetization mapping | Recommend subscription, transaction, usage, data, partner, and marketplace revenue models |
| Roadmap planning | Define product → platform → ecosystem stages |

## 8. Platform Scoring Dimensions

- Multi-sided participation potential.
- Repeat usage frequency.
- Supply-side scalability.
- Data feedback loops.
- API/plugin potential.
- Trust and safety requirements.
- Monetization diversity.
- Switching costs.
- Ecosystem defensibility.

## 9. Output Artifacts

```text
generated/<project>/docs/strategy/
├── PLATFORM_POTENTIAL_ASSESSMENT.md
├── ECOSYSTEM_ACTOR_MAP.md
├── NETWORK_EFFECTS_MODEL.md
├── PLATFORM_ROADMAP.md
└── MONETIZATION_STRATEGY.md
```

## 10. Tool Interface

- `platform_assess_potential`
- `platform_map_actors`
- `platform_identify_network_effects`
- `platform_recommend_api_surface`
- `platform_generate_roadmap`
- `platform_monetization_map`

## 11. CLI Examples

```bash
python main.py --phase platform_strategy --input "Build a booking app for local cleaners"
python main.py --workflow --include-platform-strategy --input "Build a food delivery app for small towns"
```

## 12. Integration Plan

### Feasibility

Add platform potential as an optional feasibility dimension.

### Business Study

Convert stakeholder analysis into ecosystem actor mapping.

### Design & Build

Feed API/plugin strategy into architecture decisions.

### Implementation

Feed platform roadmap into phased releases.

## 13. Implementation Roadmap

### Phase 1

- Add `PlatformStrategyAgent`.
- Add scoring models.
- Add actor map and roadmap tools.
- Add generated strategy artifacts.

### Phase 2

- Add marketplace/platform skill pack integration.
- Add business model and monetization tools.
- Add ecosystem risk scoring.

### Phase 3

- Add simulations for liquidity, supply growth, and network effects.
- Add platform dashboard.

## 14. Risks

- Platform recommendations may be too ambitious for MVP users.
- Some products should remain focused products, not platforms.
- Over-platforming can delay delivery.

## 15. Guardrails

- Always recommend MVP-first path.
- Separate immediate product needs from long-term platform opportunities.
- Use MoSCoW prioritization for platform features.

## 16. Success Metrics

- 80% of strategy outputs include clear product, platform, and ecosystem stages.
- Users can identify at least three new platform opportunities per product idea.
- Platform roadmap feeds actionable requirements into Business Study.
