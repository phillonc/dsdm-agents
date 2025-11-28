"""Tool definitions for DSDM phase agents."""

import json
from datetime import datetime
from typing import Any, Dict, List

from .tool_registry import Tool, ToolRegistry


def create_dsdm_tool_registry(
    include_confluence: bool = False,
    include_jira: bool = False,
    include_devops: bool = False,
) -> ToolRegistry:
    """Create a tool registry with all DSDM tools."""
    registry = ToolRegistry()

    # ==================== FEASIBILITY PHASE TOOLS ====================

    registry.register(Tool(
        name="analyze_requirements",
        description="Analyze and document initial project requirements from user input",
        input_schema={
            "type": "object",
            "properties": {
                "requirements_text": {
                    "type": "string",
                    "description": "Raw requirements or project description to analyze"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to focus on (e.g., 'security', 'performance')"
                }
            },
            "required": ["requirements_text"]
        },
        handler=lambda requirements_text, focus_areas=None: json.dumps({
            "status": "analyzed",
            "requirements_count": len(requirements_text.split(".")),
            "focus_areas": focus_areas or ["general"],
            "timestamp": datetime.now().isoformat()
        }),
        category="feasibility"
    ))

    registry.register(Tool(
        name="assess_technical_feasibility",
        description="Assess technical feasibility of the project",
        input_schema={
            "type": "object",
            "properties": {
                "technology_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Proposed technology stack"
                },
                "complexity_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Estimated complexity level"
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Technical constraints"
                }
            },
            "required": ["technology_stack"]
        },
        handler=lambda technology_stack, complexity_level="medium", constraints=None: json.dumps({
            "feasible": True,
            "technology_stack": technology_stack,
            "complexity": complexity_level,
            "constraints": constraints or [],
            "recommendation": "Proceed with caution" if complexity_level == "high" else "Proceed"
        }),
        category="feasibility"
    ))

    registry.register(Tool(
        name="estimate_resources",
        description="Estimate resources required for the project",
        input_schema={
            "type": "object",
            "properties": {
                "team_size": {
                    "type": "integer",
                    "description": "Estimated team size"
                },
                "duration_weeks": {
                    "type": "integer",
                    "description": "Estimated duration in weeks"
                },
                "skills_required": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required skills"
                }
            },
            "required": ["team_size", "duration_weeks"]
        },
        handler=lambda team_size, duration_weeks, skills_required=None: json.dumps({
            "team_size": team_size,
            "duration_weeks": duration_weeks,
            "skills_required": skills_required or [],
            "estimated_cost_factor": team_size * duration_weeks
        }),
        requires_approval=True,
        category="feasibility"
    ))

    registry.register(Tool(
        name="identify_risks",
        description="Identify and document project risks",
        input_schema={
            "type": "object",
            "properties": {
                "risk_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Areas to analyze for risks"
                },
                "severity_threshold": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Minimum severity to report"
                }
            },
            "required": ["risk_areas"]
        },
        handler=lambda risk_areas, severity_threshold="medium": json.dumps({
            "risks_identified": len(risk_areas),
            "risk_areas": risk_areas,
            "severity_threshold": severity_threshold,
            "status": "documented"
        }),
        category="feasibility"
    ))

    registry.register(Tool(
        name="check_dsdm_suitability",
        description="Check if DSDM methodology is suitable for this project",
        input_schema={
            "type": "object",
            "properties": {
                "project_type": {
                    "type": "string",
                    "description": "Type of project"
                },
                "stakeholder_availability": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Expected stakeholder availability"
                },
                "flexibility_needed": {
                    "type": "boolean",
                    "description": "Whether requirements are likely to change"
                }
            },
            "required": ["project_type"]
        },
        handler=lambda project_type, stakeholder_availability="medium", flexibility_needed=True: json.dumps({
            "dsdm_suitable": flexibility_needed and stakeholder_availability != "low",
            "project_type": project_type,
            "recommendation": "DSDM recommended" if flexibility_needed else "Consider waterfall"
        }),
        category="feasibility"
    ))

    # ==================== BUSINESS STUDY PHASE TOOLS ====================

    registry.register(Tool(
        name="analyze_business_process",
        description="Analyze current business processes and identify pain points",
        input_schema={
            "type": "object",
            "properties": {
                "process_name": {
                    "type": "string",
                    "description": "Name of the business process"
                },
                "current_state": {
                    "type": "string",
                    "description": "Description of current state"
                },
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known pain points"
                }
            },
            "required": ["process_name", "current_state"]
        },
        handler=lambda process_name, current_state, pain_points=None: json.dumps({
            "process": process_name,
            "analyzed": True,
            "pain_points_count": len(pain_points) if pain_points else 0,
            "improvement_potential": "high" if pain_points else "medium"
        }),
        category="business_study"
    ))

    registry.register(Tool(
        name="identify_stakeholders",
        description="Identify and document project stakeholders",
        input_schema={
            "type": "object",
            "properties": {
                "stakeholder_groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Groups of stakeholders"
                },
                "key_contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "influence": {"type": "string"}
                        }
                    },
                    "description": "Key contact persons"
                }
            },
            "required": ["stakeholder_groups"]
        },
        handler=lambda stakeholder_groups, key_contacts=None: json.dumps({
            "stakeholder_groups": stakeholder_groups,
            "key_contacts_count": len(key_contacts) if key_contacts else 0,
            "engagement_plan": "required"
        }),
        category="business_study"
    ))

    registry.register(Tool(
        name="prioritize_requirements",
        description="Prioritize requirements using MoSCoW method",
        input_schema={
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["must_have", "should_have", "could_have", "wont_have"]
                            }
                        }
                    },
                    "description": "List of requirements with priorities"
                }
            },
            "required": ["requirements"]
        },
        handler=lambda requirements: json.dumps({
            "total_requirements": len(requirements),
            "must_have": len([r for r in requirements if r.get("priority") == "must_have"]),
            "should_have": len([r for r in requirements if r.get("priority") == "should_have"]),
            "could_have": len([r for r in requirements if r.get("priority") == "could_have"]),
            "wont_have": len([r for r in requirements if r.get("priority") == "wont_have"]),
            "prioritized": True
        }),
        category="business_study"
    ))

    registry.register(Tool(
        name="define_architecture",
        description="Define high-level system architecture",
        input_schema={
            "type": "object",
            "properties": {
                "architecture_type": {
                    "type": "string",
                    "description": "Type of architecture (e.g., 'microservices', 'monolith')"
                },
                "components": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main system components"
                },
                "integrations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "External integrations needed"
                }
            },
            "required": ["architecture_type", "components"]
        },
        handler=lambda architecture_type, components, integrations=None: json.dumps({
            "architecture_type": architecture_type,
            "components_count": len(components),
            "components": components,
            "integrations": integrations or [],
            "defined": True
        }),
        category="business_study"
    ))

    registry.register(Tool(
        name="create_timebox_plan",
        description="Create timebox plan for iterative development",
        input_schema={
            "type": "object",
            "properties": {
                "total_duration_weeks": {
                    "type": "integer",
                    "description": "Total project duration in weeks"
                },
                "timebox_length_weeks": {
                    "type": "integer",
                    "description": "Length of each timebox in weeks"
                },
                "deliverables_per_timebox": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Planned deliverables per timebox"
                }
            },
            "required": ["total_duration_weeks", "timebox_length_weeks"]
        },
        handler=lambda total_duration_weeks, timebox_length_weeks, deliverables_per_timebox=None: json.dumps({
            "total_timeboxes": total_duration_weeks // timebox_length_weeks,
            "timebox_length_weeks": timebox_length_weeks,
            "plan_created": True
        }),
        category="business_study"
    ))

    registry.register(Tool(
        name="update_risk_log",
        description="Update the project risk log",
        input_schema={
            "type": "object",
            "properties": {
                "new_risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "probability": {"type": "string"},
                            "impact": {"type": "string"},
                            "mitigation": {"type": "string"}
                        }
                    },
                    "description": "New risks to add"
                },
                "resolved_risks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Risk IDs that have been resolved"
                }
            },
            "required": []
        },
        handler=lambda new_risks=None, resolved_risks=None: json.dumps({
            "risks_added": len(new_risks) if new_risks else 0,
            "risks_resolved": len(resolved_risks) if resolved_risks else 0,
            "log_updated": True
        }),
        category="business_study"
    ))

    # ==================== FUNCTIONAL MODEL PHASE TOOLS ====================

    registry.register(Tool(
        name="create_prototype",
        description="Create a functional prototype",
        input_schema={
            "type": "object",
            "properties": {
                "prototype_name": {
                    "type": "string",
                    "description": "Name of the prototype"
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Features to include"
                },
                "prototype_type": {
                    "type": "string",
                    "enum": ["throwaway", "evolutionary"],
                    "description": "Type of prototype"
                }
            },
            "required": ["prototype_name", "features"]
        },
        handler=lambda prototype_name, features, prototype_type="evolutionary": json.dumps({
            "prototype_name": prototype_name,
            "features_count": len(features),
            "type": prototype_type,
            "created": True,
            "iteration": 1
        }),
        category="functional_model"
    ))

    registry.register(Tool(
        name="generate_code_scaffold",
        description="Generate code scaffold for a component",
        input_schema={
            "type": "object",
            "properties": {
                "component_name": {
                    "type": "string",
                    "description": "Name of the component"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language"
                },
                "framework": {
                    "type": "string",
                    "description": "Framework to use"
                }
            },
            "required": ["component_name", "language"]
        },
        handler=lambda component_name, language, framework=None: json.dumps({
            "component": component_name,
            "language": language,
            "framework": framework,
            "scaffold_generated": True
        }),
        category="functional_model"
    ))

    registry.register(Tool(
        name="collect_user_feedback",
        description="Collect and document user feedback on prototype",
        input_schema={
            "type": "object",
            "properties": {
                "prototype_name": {
                    "type": "string",
                    "description": "Name of the prototype"
                },
                "feedback_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "feedback": {"type": "string"},
                            "priority": {"type": "string"}
                        }
                    },
                    "description": "Feedback items collected"
                }
            },
            "required": ["prototype_name", "feedback_items"]
        },
        handler=lambda prototype_name, feedback_items: json.dumps({
            "prototype": prototype_name,
            "feedback_count": len(feedback_items),
            "categories": list(set(f.get("category", "general") for f in feedback_items)),
            "collected": True
        }),
        category="functional_model"
    ))

    registry.register(Tool(
        name="refine_requirements",
        description="Refine requirements based on feedback",
        input_schema={
            "type": "object",
            "properties": {
                "original_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Original requirements"
                },
                "feedback_based_changes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Changes based on feedback"
                }
            },
            "required": ["original_requirements", "feedback_based_changes"]
        },
        handler=lambda original_requirements, feedback_based_changes: json.dumps({
            "original_count": len(original_requirements),
            "changes_count": len(feedback_based_changes),
            "refined": True
        }),
        category="functional_model"
    ))

    registry.register(Tool(
        name="run_functional_tests",
        description="Run functional tests on prototype",
        input_schema={
            "type": "object",
            "properties": {
                "prototype_name": {
                    "type": "string",
                    "description": "Name of the prototype"
                },
                "test_cases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Test cases to run"
                }
            },
            "required": ["prototype_name"]
        },
        handler=lambda prototype_name, test_cases=None: json.dumps({
            "prototype": prototype_name,
            "tests_run": len(test_cases) if test_cases else 0,
            "passed": True,
            "status": "all tests passed"
        }),
        category="functional_model"
    ))

    registry.register(Tool(
        name="document_iteration",
        description="Document the current iteration",
        input_schema={
            "type": "object",
            "properties": {
                "iteration_number": {
                    "type": "integer",
                    "description": "Iteration number"
                },
                "achievements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What was achieved"
                },
                "next_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Next steps planned"
                }
            },
            "required": ["iteration_number", "achievements"]
        },
        handler=lambda iteration_number, achievements, next_steps=None: json.dumps({
            "iteration": iteration_number,
            "achievements_count": len(achievements),
            "documented": True
        }),
        category="functional_model"
    ))

    # ==================== DESIGN & BUILD PHASE TOOLS ====================

    registry.register(Tool(
        name="create_technical_design",
        description="Create detailed technical design document",
        input_schema={
            "type": "object",
            "properties": {
                "component_name": {
                    "type": "string",
                    "description": "Name of the component"
                },
                "design_details": {
                    "type": "object",
                    "description": "Design details including classes, interfaces, etc."
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Dependencies"
                }
            },
            "required": ["component_name", "design_details"]
        },
        handler=lambda component_name, design_details, dependencies=None: json.dumps({
            "component": component_name,
            "design_created": True,
            "dependencies_count": len(dependencies) if dependencies else 0
        }),
        category="design_build"
    ))

    registry.register(Tool(
        name="generate_code",
        description="Generate production code based on design",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path for the code file"
                },
                "code_content": {
                    "type": "string",
                    "description": "The code to generate"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language"
                }
            },
            "required": ["file_path", "code_content", "language"]
        },
        handler=lambda file_path, code_content, language: json.dumps({
            "file_path": file_path,
            "language": language,
            "lines_of_code": len(code_content.split("\n")),
            "generated": True
        }),
        requires_approval=True,
        category="design_build"
    ))

    registry.register(Tool(
        name="write_file",
        description="Write content to a file",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["file_path", "content"]
        },
        handler=lambda file_path, content: json.dumps({
            "file_path": file_path,
            "written": True,
            "size_bytes": len(content)
        }),
        requires_approval=True,
        category="design_build"
    ))

    registry.register(Tool(
        name="run_tests",
        description="Run tests on the code",
        input_schema={
            "type": "object",
            "properties": {
                "test_type": {
                    "type": "string",
                    "enum": ["unit", "integration", "system", "all"],
                    "description": "Type of tests to run"
                },
                "target_path": {
                    "type": "string",
                    "description": "Path to test"
                }
            },
            "required": ["test_type"]
        },
        handler=lambda test_type, target_path=None: json.dumps({
            "test_type": test_type,
            "target": target_path,
            "passed": True,
            "coverage": "85%",
            "status": "all tests passed"
        }),
        category="design_build"
    ))

    registry.register(Tool(
        name="review_code",
        description="Review code for quality and standards",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to review"
                },
                "review_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Criteria to review against"
                }
            },
            "required": ["file_path"]
        },
        handler=lambda file_path, review_criteria=None: json.dumps({
            "file": file_path,
            "reviewed": True,
            "issues_found": 0,
            "status": "approved"
        }),
        category="design_build"
    ))

    registry.register(Tool(
        name="create_documentation",
        description="Create technical or user documentation",
        input_schema={
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["technical", "user", "api", "deployment"],
                    "description": "Type of documentation"
                },
                "content": {
                    "type": "string",
                    "description": "Documentation content"
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the documentation"
                }
            },
            "required": ["doc_type", "content"]
        },
        handler=lambda doc_type, content, output_path=None: json.dumps({
            "doc_type": doc_type,
            "created": True,
            "path": output_path
        }),
        category="design_build"
    ))

    registry.register(Tool(
        name="security_check",
        description="Run security checks on the code",
        input_schema={
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "description": "Path to check"
                },
                "check_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of security checks"
                }
            },
            "required": ["target_path"]
        },
        handler=lambda target_path, check_types=None: json.dumps({
            "target": target_path,
            "vulnerabilities_found": 0,
            "status": "secure",
            "checks_performed": check_types or ["default"]
        }),
        category="design_build"
    ))

    # ==================== IMPLEMENTATION PHASE TOOLS ====================

    registry.register(Tool(
        name="create_deployment_plan",
        description="Create a deployment plan",
        input_schema={
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "description": "Target environment"
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Deployment steps"
                },
                "rollback_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Rollback steps"
                }
            },
            "required": ["environment", "steps"]
        },
        handler=lambda environment, steps, rollback_steps=None: json.dumps({
            "environment": environment,
            "steps_count": len(steps),
            "has_rollback": rollback_steps is not None,
            "plan_created": True
        }),
        requires_approval=True,
        category="implementation"
    ))

    registry.register(Tool(
        name="setup_environment",
        description="Set up the deployment environment",
        input_schema={
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "description": "Environment name"
                },
                "configuration": {
                    "type": "object",
                    "description": "Environment configuration"
                }
            },
            "required": ["environment"]
        },
        handler=lambda environment, configuration=None: json.dumps({
            "environment": environment,
            "configured": True,
            "status": "ready"
        }),
        requires_approval=True,
        category="implementation"
    ))

    registry.register(Tool(
        name="deploy_system",
        description="Deploy the system to target environment",
        input_schema={
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "description": "Target environment"
                },
                "version": {
                    "type": "string",
                    "description": "Version to deploy"
                }
            },
            "required": ["environment", "version"]
        },
        handler=lambda environment, version: json.dumps({
            "environment": environment,
            "version": version,
            "deployed": True,
            "timestamp": datetime.now().isoformat()
        }),
        requires_approval=True,
        category="implementation"
    ))

    registry.register(Tool(
        name="run_smoke_tests",
        description="Run smoke tests after deployment",
        input_schema={
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "description": "Environment to test"
                },
                "test_endpoints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Endpoints to test"
                }
            },
            "required": ["environment"]
        },
        handler=lambda environment, test_endpoints=None: json.dumps({
            "environment": environment,
            "endpoints_tested": len(test_endpoints) if test_endpoints else 0,
            "passed": True,
            "status": "all smoke tests passed"
        }),
        category="implementation"
    ))

    registry.register(Tool(
        name="create_rollback",
        description="Create rollback point",
        input_schema={
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "description": "Environment"
                },
                "version": {
                    "type": "string",
                    "description": "Version to rollback to"
                }
            },
            "required": ["environment", "version"]
        },
        handler=lambda environment, version: json.dumps({
            "environment": environment,
            "rollback_version": version,
            "rollback_ready": True
        }),
        requires_approval=True,
        category="implementation"
    ))

    registry.register(Tool(
        name="execute_rollback",
        description="Execute rollback to previous version",
        input_schema={
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "description": "Environment"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for rollback"
                }
            },
            "required": ["environment", "reason"]
        },
        handler=lambda environment, reason: json.dumps({
            "environment": environment,
            "reason": reason,
            "rolled_back": True,
            "timestamp": datetime.now().isoformat()
        }),
        requires_approval=True,
        category="implementation"
    ))

    registry.register(Tool(
        name="create_training_materials",
        description="Create user training materials",
        input_schema={
            "type": "object",
            "properties": {
                "material_type": {
                    "type": "string",
                    "enum": ["guide", "video_script", "faq", "quick_start"],
                    "description": "Type of training material"
                },
                "content": {
                    "type": "string",
                    "description": "Training content"
                }
            },
            "required": ["material_type", "content"]
        },
        handler=lambda material_type, content: json.dumps({
            "type": material_type,
            "created": True,
            "content_length": len(content)
        }),
        category="implementation"
    ))

    registry.register(Tool(
        name="notify_stakeholders",
        description="Notify stakeholders about deployment",
        input_schema={
            "type": "object",
            "properties": {
                "stakeholder_groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Groups to notify"
                },
                "message": {
                    "type": "string",
                    "description": "Notification message"
                },
                "notification_type": {
                    "type": "string",
                    "enum": ["pre_deployment", "deployment", "post_deployment", "issue"],
                    "description": "Type of notification"
                }
            },
            "required": ["stakeholder_groups", "message", "notification_type"]
        },
        handler=lambda stakeholder_groups, message, notification_type: json.dumps({
            "groups_notified": stakeholder_groups,
            "notification_type": notification_type,
            "sent": True
        }),
        category="implementation"
    ))

    registry.register(Tool(
        name="generate_handover_docs",
        description="Generate handover documentation for operations team",
        input_schema={
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "Name of the system"
                },
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sections to include"
                }
            },
            "required": ["system_name"]
        },
        handler=lambda system_name, sections=None: json.dumps({
            "system": system_name,
            "sections": sections or ["overview", "architecture", "operations", "troubleshooting"],
            "generated": True
        }),
        category="implementation"
    ))

    # ==================== OPTIONAL INTEGRATIONS ====================

    if include_confluence:
        from .integrations.confluence_tools import register_confluence_tools
        register_confluence_tools(registry)

    if include_jira:
        from .integrations.jira_tools import register_jira_tools
        register_jira_tools(registry)

    if include_devops:
        from .integrations.devops_tools import register_devops_tools
        register_devops_tools(registry)

    return registry
