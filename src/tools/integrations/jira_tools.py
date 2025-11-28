"""Jira integration tools for DSDM agents."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from ..tool_registry import Tool, ToolRegistry


class JiraClient:
    """Client for Jira API interactions."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.base_url = base_url or os.environ.get("JIRA_BASE_URL", "").rstrip("/")
        self.username = username or os.environ.get("JIRA_USERNAME", "")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN", "")
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Get or create authenticated session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = (self.username, self.api_token)
            self._session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json",
            })
        return self._session

    @property
    def is_configured(self) -> bool:
        """Check if Jira is properly configured."""
        return bool(self.base_url and self.username and self.api_token)

    def _api_url(self, endpoint: str) -> str:
        """Build API URL."""
        return f"{self.base_url}/rest/api/3/{endpoint.lstrip('/')}"

    def get_issue(self, issue_key: str, fields: str = "*all") -> Dict[str, Any]:
        """Get issue details."""
        response = self.session.get(
            self._api_url(f"issue/{issue_key}"),
            params={"fields": fields}
        )
        response.raise_for_status()
        return response.json()

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new issue."""
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": issue_type}
            }
        }

        if priority:
            payload["fields"]["priority"] = {"name": priority}
        if labels:
            payload["fields"]["labels"] = labels
        if assignee:
            payload["fields"]["assignee"] = {"accountId": assignee}
        if custom_fields:
            payload["fields"].update(custom_fields)

        response = self.session.post(self._api_url("issue"), json=payload)
        response.raise_for_status()
        return response.json()

    def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any],
    ) -> None:
        """Update an existing issue."""
        payload = {"fields": fields}
        response = self.session.put(self._api_url(f"issue/{issue_key}"), json=payload)
        response.raise_for_status()

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Transition an issue to a new status."""
        payload = {"transition": {"id": transition_id}}
        response = self.session.post(
            self._api_url(f"issue/{issue_key}/transitions"),
            json=payload
        )
        response.raise_for_status()

    def get_transitions(self, issue_key: str) -> Dict[str, Any]:
        """Get available transitions for an issue."""
        response = self.session.get(self._api_url(f"issue/{issue_key}/transitions"))
        response.raise_for_status()
        return response.json()

    def search_issues(self, jql: str, fields: str = "summary,status,priority,assignee", max_results: int = 50) -> Dict[str, Any]:
        """Search issues using JQL."""
        payload = {
            "jql": jql,
            "fields": fields.split(","),
            "maxResults": max_results
        }
        response = self.session.post(self._api_url("search"), json=payload)
        response.raise_for_status()
        return response.json()

    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }
                ]
            }
        }
        response = self.session.post(
            self._api_url(f"issue/{issue_key}/comment"),
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_project(self, project_key: str) -> Dict[str, Any]:
        """Get project details."""
        response = self.session.get(self._api_url(f"project/{project_key}"))
        response.raise_for_status()
        return response.json()

    def create_sprint(
        self,
        board_id: int,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new sprint."""
        payload = {
            "name": name,
            "originBoardId": board_id,
        }
        if start_date:
            payload["startDate"] = start_date
        if end_date:
            payload["endDate"] = end_date
        if goal:
            payload["goal"] = goal

        response = self.session.post(
            f"{self.base_url}/rest/agile/1.0/sprint",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_board_sprints(self, board_id: int, state: str = "active,future") -> Dict[str, Any]:
        """Get sprints for a board."""
        response = self.session.get(
            f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint",
            params={"state": state}
        )
        response.raise_for_status()
        return response.json()

    def move_issues_to_sprint(self, sprint_id: int, issue_keys: List[str]) -> None:
        """Move issues to a sprint."""
        payload = {"issues": issue_keys}
        response = self.session.post(
            f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
            json=payload
        )
        response.raise_for_status()


# Global client instance
_jira_client: Optional[JiraClient] = None


def get_jira_client() -> JiraClient:
    """Get or create global Jira client."""
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client


def register_jira_tools(registry: ToolRegistry) -> None:
    """Register Jira tools with the registry."""

    # Get Issue
    registry.register(Tool(
        name="jira_get_issue",
        description="Get details of a Jira issue by its key (e.g., PROJ-123)",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key (e.g., PROJ-123)"
                }
            },
            "required": ["issue_key"]
        },
        handler=_handle_get_issue,
        category="jira"
    ))

    # Create Issue
    registry.register(Tool(
        name="jira_create_issue",
        description="Create a new Jira issue (task, bug, story, etc.)",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "The Jira project key (e.g., PROJ)"
                },
                "summary": {
                    "type": "string",
                    "description": "Issue summary/title"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the issue"
                },
                "issue_type": {
                    "type": "string",
                    "enum": ["Task", "Bug", "Story", "Epic", "Sub-task"],
                    "description": "Type of issue (default: Task)"
                },
                "priority": {
                    "type": "string",
                    "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                    "description": "Issue priority"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to add to the issue"
                }
            },
            "required": ["project_key", "summary", "description"]
        },
        handler=_handle_create_issue,
        requires_approval=True,
        category="jira"
    ))

    # Update Issue
    registry.register(Tool(
        name="jira_update_issue",
        description="Update an existing Jira issue",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key to update"
                },
                "summary": {
                    "type": "string",
                    "description": "New summary (optional)"
                },
                "description": {
                    "type": "string",
                    "description": "New description (optional)"
                },
                "priority": {
                    "type": "string",
                    "description": "New priority (optional)"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New labels (optional)"
                }
            },
            "required": ["issue_key"]
        },
        handler=_handle_update_issue,
        requires_approval=True,
        category="jira"
    ))

    # Search Issues
    registry.register(Tool(
        name="jira_search",
        description="Search Jira issues using JQL (Jira Query Language)",
        input_schema={
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query string (e.g., 'project=PROJ AND status=Open')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default 50)"
                }
            },
            "required": ["jql"]
        },
        handler=_handle_search,
        category="jira"
    ))

    # Transition Issue
    registry.register(Tool(
        name="jira_transition_issue",
        description="Transition a Jira issue to a new status (e.g., To Do -> In Progress)",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key"
                },
                "transition_name": {
                    "type": "string",
                    "description": "Name of the transition (e.g., 'Start Progress', 'Done')"
                }
            },
            "required": ["issue_key", "transition_name"]
        },
        handler=_handle_transition_issue,
        requires_approval=True,
        category="jira"
    ))

    # Add Comment
    registry.register(Tool(
        name="jira_add_comment",
        description="Add a comment to a Jira issue",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment text"
                }
            },
            "required": ["issue_key", "comment"]
        },
        handler=_handle_add_comment,
        category="jira"
    ))

    # Get Project
    registry.register(Tool(
        name="jira_get_project",
        description="Get Jira project details",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "The Jira project key"
                }
            },
            "required": ["project_key"]
        },
        handler=_handle_get_project,
        category="jira"
    ))

    # Create DSDM User Story
    registry.register(Tool(
        name="jira_create_user_story",
        description="Create a DSDM-formatted user story with MoSCoW priority",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "The Jira project key"
                },
                "as_a": {
                    "type": "string",
                    "description": "User role (As a...)"
                },
                "i_want": {
                    "type": "string",
                    "description": "What the user wants (I want to...)"
                },
                "so_that": {
                    "type": "string",
                    "description": "Business value (So that...)"
                },
                "moscow_priority": {
                    "type": "string",
                    "enum": ["Must Have", "Should Have", "Could Have", "Won't Have"],
                    "description": "MoSCoW priority level"
                },
                "acceptance_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of acceptance criteria"
                }
            },
            "required": ["project_key", "as_a", "i_want", "so_that", "moscow_priority"]
        },
        handler=_handle_create_user_story,
        requires_approval=True,
        category="jira"
    ))

    # Create Timebox/Sprint
    registry.register(Tool(
        name="jira_create_timebox",
        description="Create a DSDM timebox (sprint) for iterative development",
        input_schema={
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "integer",
                    "description": "The Jira board ID"
                },
                "name": {
                    "type": "string",
                    "description": "Timebox name (e.g., 'Timebox 1 - Core Features')"
                },
                "goal": {
                    "type": "string",
                    "description": "Timebox goal/objective"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD format)"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD format)"
                }
            },
            "required": ["board_id", "name"]
        },
        handler=_handle_create_timebox,
        requires_approval=True,
        category="jira"
    ))

    # Bulk Create Requirements
    registry.register(Tool(
        name="jira_bulk_create_requirements",
        description="Bulk create Jira issues from a list of requirements",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "The Jira project key"
                },
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "string"},
                            "issue_type": {"type": "string"}
                        },
                        "required": ["summary"]
                    },
                    "description": "List of requirements to create"
                }
            },
            "required": ["project_key", "requirements"]
        },
        handler=_handle_bulk_create,
        requires_approval=True,
        category="jira"
    ))


def _handle_get_issue(issue_key: str) -> str:
    """Handle get issue request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured. Set JIRA_BASE_URL, JIRA_USERNAME, and JIRA_API_TOKEN"})

    try:
        issue = client.get_issue(issue_key)
        fields = issue.get("fields", {})
        return json.dumps({
            "key": issue["key"],
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", ""),
            "issue_type": fields.get("issuetype", {}).get("name", ""),
            "assignee": fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned",
            "labels": fields.get("labels", []),
            "url": f"{client.base_url}/browse/{issue['key']}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_create_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: Optional[str] = None,
    labels: Optional[List[str]] = None
) -> str:
    """Handle create issue request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        issue = client.create_issue(
            project_key=project_key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            priority=priority,
            labels=labels
        )
        return json.dumps({
            "success": True,
            "key": issue["key"],
            "id": issue["id"],
            "url": f"{client.base_url}/browse/{issue['key']}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_update_issue(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    labels: Optional[List[str]] = None
) -> str:
    """Handle update issue request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    fields = {}
    if summary:
        fields["summary"] = summary
    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}]
                }
            ]
        }
    if priority:
        fields["priority"] = {"name": priority}
    if labels is not None:
        fields["labels"] = labels

    if not fields:
        return json.dumps({"error": "No fields to update"})

    try:
        client.update_issue(issue_key, fields)
        return json.dumps({
            "success": True,
            "key": issue_key,
            "updated_fields": list(fields.keys())
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_search(jql: str, max_results: int = 50) -> str:
    """Handle search request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        results = client.search_issues(jql, max_results=max_results)
        issues = []
        for issue in results.get("issues", []):
            fields = issue.get("fields", {})
            issues.append({
                "key": issue["key"],
                "summary": fields.get("summary", ""),
                "status": fields.get("status", {}).get("name", ""),
                "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned"
            })
        return json.dumps({
            "total": results.get("total", len(issues)),
            "issues": issues
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_transition_issue(issue_key: str, transition_name: str) -> str:
    """Handle transition issue request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        # Get available transitions
        transitions = client.get_transitions(issue_key)
        transition_id = None
        for t in transitions.get("transitions", []):
            if t["name"].lower() == transition_name.lower():
                transition_id = t["id"]
                break

        if not transition_id:
            available = [t["name"] for t in transitions.get("transitions", [])]
            return json.dumps({
                "error": f"Transition '{transition_name}' not found",
                "available_transitions": available
            })

        client.transition_issue(issue_key, transition_id)
        return json.dumps({
            "success": True,
            "key": issue_key,
            "transition": transition_name
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_add_comment(issue_key: str, comment: str) -> str:
    """Handle add comment request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        result = client.add_comment(issue_key, comment)
        return json.dumps({
            "success": True,
            "comment_id": result["id"],
            "issue_key": issue_key
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_get_project(project_key: str) -> str:
    """Handle get project request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        project = client.get_project(project_key)
        return json.dumps({
            "key": project["key"],
            "name": project["name"],
            "project_type": project.get("projectTypeKey", ""),
            "lead": project.get("lead", {}).get("displayName", ""),
            "url": f"{client.base_url}/browse/{project['key']}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_create_user_story(
    project_key: str,
    as_a: str,
    i_want: str,
    so_that: str,
    moscow_priority: str,
    acceptance_criteria: Optional[List[str]] = None
) -> str:
    """Handle create user story request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    # Build user story format
    summary = f"As a {as_a}, I want to {i_want}"
    description_parts = [
        f"**As a** {as_a}",
        f"**I want to** {i_want}",
        f"**So that** {so_that}",
        "",
        f"**MoSCoW Priority:** {moscow_priority}",
    ]

    if acceptance_criteria:
        description_parts.append("")
        description_parts.append("**Acceptance Criteria:**")
        for i, criterion in enumerate(acceptance_criteria, 1):
            description_parts.append(f"{i}. {criterion}")

    description = "\n".join(description_parts)

    # Map MoSCoW to Jira priority
    priority_map = {
        "Must Have": "Highest",
        "Should Have": "High",
        "Could Have": "Medium",
        "Won't Have": "Low"
    }

    try:
        issue = client.create_issue(
            project_key=project_key,
            summary=summary[:255],  # Jira summary limit
            description=description,
            issue_type="Story",
            priority=priority_map.get(moscow_priority, "Medium"),
            labels=[moscow_priority.lower().replace(" ", "-"), "dsdm"]
        )
        return json.dumps({
            "success": True,
            "key": issue["key"],
            "moscow_priority": moscow_priority,
            "url": f"{client.base_url}/browse/{issue['key']}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_create_timebox(
    board_id: int,
    name: str,
    goal: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """Handle create timebox/sprint request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        sprint = client.create_sprint(
            board_id=board_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            goal=goal
        )
        return json.dumps({
            "success": True,
            "sprint_id": sprint["id"],
            "name": sprint["name"],
            "state": sprint.get("state", "future")
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_bulk_create(
    project_key: str,
    requirements: List[Dict[str, Any]]
) -> str:
    """Handle bulk create requirements request."""
    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    created = []
    errors = []

    for req in requirements:
        try:
            issue = client.create_issue(
                project_key=project_key,
                summary=req.get("summary", "Untitled"),
                description=req.get("description", ""),
                issue_type=req.get("issue_type", "Task"),
                priority=req.get("priority"),
                labels=req.get("labels")
            )
            created.append({
                "key": issue["key"],
                "summary": req.get("summary")
            })
        except requests.RequestException as e:
            errors.append({
                "summary": req.get("summary"),
                "error": str(e)
            })

    return json.dumps({
        "success": len(errors) == 0,
        "created_count": len(created),
        "created": created,
        "errors": errors
    })
