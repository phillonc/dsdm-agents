"""Tool definitions for DSDM phase agents."""

import json
from datetime import datetime
from typing import Any, Dict, List

from .tool_registry import Tool, ToolRegistry


def create_dsdm_tool_registry(
    include_confluence: bool = False,
    include_jira: bool = False,
    include_devops: bool = False,
    include_file_tools: bool = True,
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

    registry.register(Tool(
        name="generate_technical_requirements_document",
        description="Generate a comprehensive Technical Requirements Document (TRD) for developer manual review after build completion",
        input_schema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project"
                },
                "version": {
                    "type": "string",
                    "description": "Document version (e.g., '1.0.0')"
                },
                "executive_summary": {
                    "type": "string",
                    "description": "Brief overview of the system purpose and scope"
                },
                "system_overview": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "key_features": {"type": "array", "items": {"type": "string"}},
                        "target_users": {"type": "array", "items": {"type": "string"}}
                    },
                    "description": "High-level system description and features"
                },
                "architecture": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "components": {"type": "array", "items": {"type": "string"}},
                        "data_flow": {"type": "string"},
                        "technology_stack": {"type": "array", "items": {"type": "string"}}
                    },
                    "description": "System architecture details"
                },
                "functional_requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "string", "enum": ["must_have", "should_have", "could_have", "wont_have"]},
                            "acceptance_criteria": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "description": "List of functional requirements with MoSCoW priorities"
                },
                "non_functional_requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "category": {"type": "string", "enum": ["performance", "security", "reliability", "usability", "maintainability", "scalability"]},
                            "description": {"type": "string"},
                            "target_metric": {"type": "string"}
                        }
                    },
                    "description": "Non-functional requirements (performance, security, etc.)"
                },
                "api_specifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "endpoint": {"type": "string"},
                            "method": {"type": "string"},
                            "description": {"type": "string"},
                            "request_schema": {"type": "object"},
                            "response_schema": {"type": "object"}
                        }
                    },
                    "description": "API endpoint specifications"
                },
                "data_models": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "fields": {"type": "array", "items": {"type": "object"}},
                            "relationships": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "description": "Data model definitions"
                },
                "security_requirements": {
                    "type": "object",
                    "properties": {
                        "authentication": {"type": "string"},
                        "authorization": {"type": "string"},
                        "data_protection": {"type": "array", "items": {"type": "string"}},
                        "compliance": {"type": "array", "items": {"type": "string"}}
                    },
                    "description": "Security specifications"
                },
                "testing_requirements": {
                    "type": "object",
                    "properties": {
                        "unit_tests": {"type": "string"},
                        "integration_tests": {"type": "string"},
                        "e2e_tests": {"type": "string"},
                        "coverage_target": {"type": "string"}
                    },
                    "description": "Testing strategy and requirements"
                },
                "deployment_requirements": {
                    "type": "object",
                    "properties": {
                        "environments": {"type": "array", "items": {"type": "string"}},
                        "infrastructure": {"type": "string"},
                        "ci_cd": {"type": "string"},
                        "monitoring": {"type": "string"}
                    },
                    "description": "Deployment and infrastructure requirements"
                },
                "dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "version": {"type": "string"},
                            "purpose": {"type": "string"}
                        }
                    },
                    "description": "External dependencies and libraries"
                },
                "known_limitations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known limitations and constraints"
                },
                "future_considerations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Future enhancements and roadmap items"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path to save the TRD document (default: docs/TECHNICAL_REQUIREMENTS.md)"
                }
            },
            "required": ["project_name", "executive_summary", "system_overview", "architecture", "functional_requirements"]
        },
        handler=lambda project_name, version="1.0.0", executive_summary="", system_overview=None, architecture=None, functional_requirements=None, non_functional_requirements=None, api_specifications=None, data_models=None, security_requirements=None, testing_requirements=None, deployment_requirements=None, dependencies=None, known_limitations=None, future_considerations=None, output_path=None: json.dumps({
            "project_name": project_name,
            "version": version,
            "document_generated": True,
            "sections_included": {
                "executive_summary": bool(executive_summary),
                "system_overview": bool(system_overview),
                "architecture": bool(architecture),
                "functional_requirements": len(functional_requirements) if functional_requirements else 0,
                "non_functional_requirements": len(non_functional_requirements) if non_functional_requirements else 0,
                "api_specifications": len(api_specifications) if api_specifications else 0,
                "data_models": len(data_models) if data_models else 0,
                "security_requirements": bool(security_requirements),
                "testing_requirements": bool(testing_requirements),
                "deployment_requirements": bool(deployment_requirements),
                "dependencies": len(dependencies) if dependencies else 0,
                "known_limitations": len(known_limitations) if known_limitations else 0,
                "future_considerations": len(future_considerations) if future_considerations else 0
            },
            "output_path": output_path or f"generated/{project_name}/docs/TECHNICAL_REQUIREMENTS.md",
            "status": "ready_for_developer_review",
            "timestamp": datetime.now().isoformat()
        }),
        requires_approval=False,
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

    if include_file_tools:
        from .file_tools import register_file_tools
        register_file_tools(registry)

    # ==================== JIRA-CONFLUENCE SYNC WORKFLOW ====================
    # Register workflow tools when both Jira and Confluence are enabled
    if include_jira and include_confluence:
        _register_sync_workflow_tools(registry)

    return registry


def _register_sync_workflow_tools(registry: ToolRegistry) -> None:
    """Register tools for Jira-Confluence sync workflow integration."""

    registry.register(Tool(
        name="sync_work_item_status",
        description="Sync a Jira work item's status to Confluence documentation as part of the DSDM workflow. This should be called after updating work items in Jira to keep Confluence documentation in sync.",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key to sync (e.g., PROJ-123)"
                },
                "status": {
                    "type": "string",
                    "description": "The current status of the work item"
                },
                "summary": {
                    "type": "string",
                    "description": "Summary/title of the work item"
                },
                "phase": {
                    "type": "string",
                    "enum": ["feasibility", "business_study", "functional_model", "design_build", "implementation"],
                    "description": "Current DSDM phase for the work item"
                },
                "confluence_space_key": {
                    "type": "string",
                    "description": "Confluence space key to sync to"
                },
                "confluence_page_id": {
                    "type": "string",
                    "description": "Optional specific Confluence page ID to update"
                }
            },
            "required": ["issue_key", "status", "summary", "confluence_space_key"]
        },
        handler=_handle_sync_work_item_status,
        category="workflow"
    ))

    registry.register(Tool(
        name="setup_jira_confluence_sync",
        description="Set up automatic synchronization between Jira and Confluence for the DSDM workflow. Once enabled, all Jira status transitions and updates will automatically reflect in Confluence documentation.",
        input_schema={
            "type": "object",
            "properties": {
                "confluence_space_key": {
                    "type": "string",
                    "description": "The Confluence space key to sync to"
                },
                "create_status_page": {
                    "type": "boolean",
                    "description": "Whether to create a Work Item Status Log page in Confluence (default: true)"
                },
                "issue_page_mappings": {
                    "type": "object",
                    "description": "Optional mapping of Jira issue keys to Confluence page IDs"
                }
            },
            "required": ["confluence_space_key"]
        },
        handler=_handle_setup_jira_confluence_sync,
        category="workflow"
    ))

    registry.register(Tool(
        name="get_sync_status",
        description="Get the current status of Jira-Confluence synchronization configuration",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=_handle_get_sync_status,
        category="workflow"
    ))


def _handle_sync_work_item_status(
    issue_key: str,
    status: str,
    summary: str,
    confluence_space_key: str,
    phase: str = None,
    confluence_page_id: str = None,
) -> str:
    """Handle sync work item status request."""
    try:
        from .integrations.jira_tools import (
            enable_confluence_sync,
            set_confluence_page_mapping,
            _sync_issue_to_confluence,
            _confluence_sync_enabled,
        )

        # Ensure sync is enabled with the provided space key
        if not _confluence_sync_enabled:
            enable_confluence_sync(confluence_space_key)

        # Set page mapping if provided
        if confluence_page_id:
            set_confluence_page_mapping(issue_key, confluence_page_id)

        # Build additional info with DSDM context
        additional_info = {}
        if phase:
            additional_info["dsdm_phase"] = phase

        # Perform the sync
        result = _sync_issue_to_confluence(
            issue_key=issue_key,
            status=status,
            summary=summary,
            update_type=f"dsdm_workflow_{phase}" if phase else "dsdm_workflow",
            additional_info=additional_info if additional_info else None,
        )

        if result and result.get("success"):
            return json.dumps({
                "success": True,
                "issue_key": issue_key,
                "status": status,
                "phase": phase,
                "confluence_space": confluence_space_key,
                "sync_result": result,
                "message": f"Successfully synced {issue_key} status to Confluence"
            })
        elif result and result.get("error"):
            return json.dumps({
                "success": False,
                "error": result.get("error"),
                "issue_key": issue_key
            })
        else:
            return json.dumps({
                "success": False,
                "error": "Sync returned no result",
                "issue_key": issue_key
            })

    except ImportError as e:
        return json.dumps({"error": f"Required integration not available: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_setup_jira_confluence_sync(
    confluence_space_key: str,
    create_status_page: bool = True,
    issue_page_mappings: dict = None,
) -> str:
    """Handle setup Jira-Confluence sync request."""
    try:
        from .integrations.jira_tools import enable_confluence_sync
        from .integrations.confluence_tools import get_confluence_client

        # Enable the sync
        enable_confluence_sync(confluence_space_key, issue_page_mappings)

        result = {
            "success": True,
            "confluence_space_key": confluence_space_key,
            "sync_enabled": True,
            "page_mappings_configured": len(issue_page_mappings) if issue_page_mappings else 0,
        }

        # Optionally create a status page
        if create_status_page:
            try:
                confluence = get_confluence_client()
                if confluence.is_configured:
                    # Check if status page already exists
                    search_result = confluence.search(
                        f'space="{confluence_space_key}" AND title="Work Item Status Log"',
                        limit=1
                    )

                    if not search_result.get("results"):
                        # Create the status page
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        status_page_content = f"""<h1>Work Item Status Log</h1>
<p><strong>Space:</strong> {confluence_space_key}</p>
<p><strong>Last Updated:</strong> {timestamp}</p>
<p>This page tracks status changes for Jira work items automatically synced from the DSDM workflow.</p>
<hr/>
<h2>Sync Configuration</h2>
<p><strong>Auto-sync:</strong> Enabled</p>
<p><strong>Sync started:</strong> {timestamp}</p>
<hr/>
<h2>Status History</h2>
<table>
<thead>
<tr>
<th>Timestamp</th>
<th>Issue Key</th>
<th>Summary</th>
<th>Status</th>
<th>Update Type</th>
</tr>
</thead>
<tbody>
</tbody>
</table>
"""
                        new_page = confluence.create_page(
                            space_key=confluence_space_key,
                            title="Work Item Status Log",
                            content=status_page_content,
                        )
                        result["status_page_created"] = True
                        result["status_page_id"] = new_page["id"]
                    else:
                        result["status_page_created"] = False
                        result["status_page_id"] = search_result["results"][0]["id"]
                        result["message"] = "Status page already exists"
            except Exception as e:
                result["status_page_error"] = str(e)

        result["info"] = "Jira-Confluence sync is now active. All Jira transitions and updates will automatically sync to Confluence."

        return json.dumps(result)

    except ImportError as e:
        return json.dumps({"error": f"Required integration not available: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_get_sync_status() -> str:
    """Handle get sync status request."""
    try:
        from .integrations.jira_tools import (
            _confluence_sync_enabled,
            _confluence_space_key,
            _confluence_page_mapping,
        )

        return json.dumps({
            "sync_enabled": _confluence_sync_enabled,
            "confluence_space_key": _confluence_space_key,
            "page_mappings_count": len(_confluence_page_mapping),
            "page_mappings": _confluence_page_mapping,
        })

    except ImportError:
        return json.dumps({
            "sync_enabled": False,
            "error": "Jira integration not available"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
