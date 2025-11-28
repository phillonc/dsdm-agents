#!/usr/bin/env python3
"""Example of adding custom tools to DSDM agents."""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.tools.tool_registry import Tool, ToolRegistry
from src.tools.dsdm_tools import create_dsdm_tool_registry
from src.agents.feasibility_agent import FeasibilityAgent
from src.agents.base_agent import AgentMode


def create_custom_tools() -> ToolRegistry:
    """Create a tool registry with custom tools added."""

    # Start with the default DSDM tools
    registry = create_dsdm_tool_registry()

    # Add custom tools

    # Example 1: Database connectivity check tool
    registry.register(Tool(
        name="check_database_connectivity",
        description="Check if we can connect to a specified database type",
        input_schema={
            "type": "object",
            "properties": {
                "database_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "mongodb", "sqlite"],
                    "description": "Type of database to check"
                },
                "connection_string": {
                    "type": "string",
                    "description": "Connection string (for validation only)"
                }
            },
            "required": ["database_type"]
        },
        handler=lambda database_type, connection_string=None: json.dumps({
            "database_type": database_type,
            "connectable": True,  # In reality, this would test the connection
            "latency_ms": 15,
            "checked_at": datetime.now().isoformat()
        }),
        category="feasibility"
    ))

    # Example 2: API availability check tool
    registry.register(Tool(
        name="check_api_availability",
        description="Check if required external APIs are available",
        input_schema={
            "type": "object",
            "properties": {
                "api_endpoints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of API endpoints to check"
                }
            },
            "required": ["api_endpoints"]
        },
        handler=lambda api_endpoints: json.dumps({
            "endpoints_checked": len(api_endpoints),
            "all_available": True,
            "details": {ep: {"status": "available", "response_time_ms": 100} for ep in api_endpoints}
        }),
        category="feasibility"
    ))

    # Example 3: Cost estimation tool
    registry.register(Tool(
        name="estimate_cloud_costs",
        description="Estimate cloud infrastructure costs for the project",
        input_schema={
            "type": "object",
            "properties": {
                "cloud_provider": {
                    "type": "string",
                    "enum": ["aws", "gcp", "azure"],
                    "description": "Cloud provider"
                },
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Services needed (e.g., 'compute', 'database', 'storage')"
                },
                "scale": {
                    "type": "string",
                    "enum": ["small", "medium", "large"],
                    "description": "Expected scale"
                }
            },
            "required": ["cloud_provider", "services"]
        },
        handler=lambda cloud_provider, services, scale="medium": json.dumps({
            "provider": cloud_provider,
            "monthly_estimate_usd": len(services) * {"small": 100, "medium": 500, "large": 2000}[scale],
            "services": services,
            "scale": scale,
            "confidence": "medium"
        }),
        requires_approval=True,  # Cost estimates might need review
        category="feasibility"
    ))

    # Example 4: Team skill assessment tool
    registry.register(Tool(
        name="assess_team_skills",
        description="Assess if the team has required skills for the project",
        input_schema={
            "type": "object",
            "properties": {
                "required_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills required for the project"
                },
                "team_size": {
                    "type": "integer",
                    "description": "Current team size"
                }
            },
            "required": ["required_skills", "team_size"]
        },
        handler=lambda required_skills, team_size: json.dumps({
            "skills_assessed": required_skills,
            "team_size": team_size,
            "skill_coverage": 0.8,  # 80% coverage
            "gaps": ["DevOps", "Security"] if "security" in [s.lower() for s in required_skills] else [],
            "training_recommended": True
        }),
        category="business_study"
    ))

    return registry


def main():
    """Demonstrate custom tools usage."""
    load_dotenv()

    print("DSDM Agents - Custom Tools Example")
    print("=" * 60)

    # Create registry with custom tools
    custom_registry = create_custom_tools()

    # List all tools in the registry
    print("\nAll registered tools:")
    for tool in custom_registry.get_all():
        print(f"  - {tool.name} ({tool.category})")

    # Create a Feasibility agent with custom tools
    # First, update the agent's tool list to include custom tools
    agent = FeasibilityAgent(
        tool_registry=custom_registry,
        mode=AgentMode.AUTOMATED
    )

    # Add custom tools to the agent's config
    agent.config.tools.extend([
        "check_database_connectivity",
        "check_api_availability",
        "estimate_cloud_costs",
    ])

    print(f"\nFeasibility Agent tools: {agent.config.tools}")

    # Run the agent with a project that could use custom tools
    print("\n" + "=" * 60)
    print("Running Feasibility with custom tools...")
    print("=" * 60)

    project = """
    Build a real-time analytics dashboard that:
    - Connects to PostgreSQL and MongoDB databases
    - Integrates with Stripe and SendGrid APIs
    - Deploys on AWS
    - Requires frontend (React), backend (Python), and DevOps skills
    """

    result = agent.run(project)

    print(f"\nResult: {'Success' if result.success else 'Failed'}")
    print(f"Tool calls made: {len(result.tool_calls)}")
    for tc in result.tool_calls:
        print(f"  - {tc['tool']}: {tc['result'][:100]}...")


if __name__ == "__main__":
    main()
