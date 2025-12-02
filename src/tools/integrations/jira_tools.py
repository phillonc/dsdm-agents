"""Jira integration tools for DSDM agents."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from ..tool_registry import Tool, ToolRegistry


# Forward declaration for Confluence sync
_confluence_sync_enabled: bool = False
_confluence_space_key: Optional[str] = None
_confluence_page_mapping: Dict[str, str] = {}  # Maps Jira issue key to Confluence page ID


def enable_confluence_sync(space_key: str, page_mapping: Optional[Dict[str, str]] = None) -> None:
    """Enable automatic Confluence sync when Jira issues are updated.

    Args:
        space_key: The Confluence space key to sync to
        page_mapping: Optional mapping of Jira issue keys to Confluence page IDs
    """
    global _confluence_sync_enabled, _confluence_space_key, _confluence_page_mapping
    _confluence_sync_enabled = True
    _confluence_space_key = space_key
    _confluence_page_mapping = page_mapping or {}


def disable_confluence_sync() -> None:
    """Disable automatic Confluence sync."""
    global _confluence_sync_enabled
    _confluence_sync_enabled = False


def set_confluence_page_mapping(issue_key: str, page_id: str) -> None:
    """Set mapping between a Jira issue and its Confluence documentation page."""
    global _confluence_page_mapping
    _confluence_page_mapping[issue_key] = page_id


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

    # Enable Confluence Sync
    registry.register(Tool(
        name="jira_enable_confluence_sync",
        description="Enable automatic sync of Jira work item status changes to Confluence. When enabled, all Jira transitions and updates will automatically update Confluence documentation.",
        input_schema={
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "The Confluence space key to sync status updates to"
                },
                "page_mappings": {
                    "type": "object",
                    "description": "Optional mapping of Jira issue keys to specific Confluence page IDs (e.g., {'PROJ-1': '12345'})"
                }
            },
            "required": ["space_key"]
        },
        handler=_handle_enable_confluence_sync,
        category="jira"
    ))

    # Disable Confluence Sync
    registry.register(Tool(
        name="jira_disable_confluence_sync",
        description="Disable automatic sync of Jira work item status changes to Confluence",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=_handle_disable_confluence_sync,
        category="jira"
    ))

    # Manual Sync to Confluence
    registry.register(Tool(
        name="jira_sync_to_confluence",
        description="Manually sync a Jira issue's current status to Confluence documentation",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key to sync (e.g., PROJ-123)"
                },
                "confluence_page_id": {
                    "type": "string",
                    "description": "Optional specific Confluence page ID to update. If not provided, uses configured space."
                }
            },
            "required": ["issue_key"]
        },
        handler=_handle_manual_sync_to_confluence,
        requires_approval=True,
        category="jira"
    ))

    # Set Page Mapping
    registry.register(Tool(
        name="jira_set_confluence_page_mapping",
        description="Map a Jira issue to a specific Confluence documentation page for status sync",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key (e.g., PROJ-123)"
                },
                "page_id": {
                    "type": "string",
                    "description": "The Confluence page ID to map to"
                }
            },
            "required": ["issue_key", "page_id"]
        },
        handler=_handle_set_page_mapping,
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

        # Get current issue details for Confluence sync
        issue = client.get_issue(issue_key, fields="summary,status")
        current_summary = summary or issue.get("fields", {}).get("summary", "")
        current_status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")

        result = {
            "success": True,
            "key": issue_key,
            "updated_fields": list(fields.keys())
        }

        # Auto-sync to Confluence if enabled
        confluence_sync = _sync_issue_to_confluence(
            issue_key=issue_key,
            status=current_status,
            summary=current_summary,
            update_type="field_update",
        )
        if confluence_sync:
            result["confluence_sync"] = confluence_sync

        return json.dumps(result)
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
        target_status = None
        for t in transitions.get("transitions", []):
            if t["name"].lower() == transition_name.lower():
                transition_id = t["id"]
                target_status = t.get("to", {}).get("name", transition_name)
                break

        if not transition_id:
            available = [t["name"] for t in transitions.get("transitions", [])]
            return json.dumps({
                "error": f"Transition '{transition_name}' not found",
                "available_transitions": available
            })

        client.transition_issue(issue_key, transition_id)

        # Get issue details for Confluence sync
        issue = client.get_issue(issue_key, fields="summary,status")
        summary = issue.get("fields", {}).get("summary", "")
        new_status = issue.get("fields", {}).get("status", {}).get("name", target_status)

        result = {
            "success": True,
            "key": issue_key,
            "transition": transition_name,
            "new_status": new_status,
        }

        # Auto-sync to Confluence if enabled
        confluence_sync = _sync_issue_to_confluence(
            issue_key=issue_key,
            status=new_status,
            summary=summary,
            update_type="transition",
        )
        if confluence_sync:
            result["confluence_sync"] = confluence_sync

        return json.dumps(result)
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


def _sync_issue_to_confluence(
    issue_key: str,
    status: str,
    summary: str,
    update_type: str = "status_change",
    additional_info: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Sync Jira issue status to Confluence documentation.

    This is called automatically when Confluence sync is enabled and a Jira
    issue is updated or transitioned.

    Args:
        issue_key: The Jira issue key (e.g., PROJ-123)
        status: The current status of the issue
        summary: The issue summary/title
        update_type: Type of update (status_change, field_update, transition)
        additional_info: Additional information to include in the sync

    Returns:
        Dict with sync result or None if sync is disabled/failed
    """
    if not _confluence_sync_enabled:
        return None

    try:
        from .confluence_tools import get_confluence_client

        confluence = get_confluence_client()
        if not confluence.is_configured:
            return {"error": "Confluence not configured for sync"}

        # Check if there's a specific page mapping for this issue
        page_id = _confluence_page_mapping.get(issue_key)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if page_id:
            # Update existing page with status change
            try:
                current_page = confluence.get_page(page_id)
                current_content = current_page.get("body", {}).get("storage", {}).get("value", "")
                version = current_page["version"]["number"]

                # Add status update section
                status_update = f"""
<h3>Status Update - {timestamp}</h3>
<table>
<tr><th>Issue</th><td>{issue_key}</td></tr>
<tr><th>Summary</th><td>{summary}</td></tr>
<tr><th>Status</th><td><strong>{status}</strong></td></tr>
<tr><th>Update Type</th><td>{update_type}</td></tr>
</table>
<hr/>
"""
                # Prepend the status update after the first heading or at the beginning
                if "<h1>" in current_content:
                    # Insert after the first h1 closing tag
                    h1_end = current_content.find("</h1>") + 5
                    updated_content = current_content[:h1_end] + status_update + current_content[h1_end:]
                else:
                    updated_content = status_update + current_content

                confluence.update_page(
                    page_id=page_id,
                    title=current_page["title"],
                    content=updated_content,
                    version_number=version + 1,
                )

                return {
                    "success": True,
                    "action": "page_updated",
                    "page_id": page_id,
                    "issue_key": issue_key,
                    "status": status,
                }
            except Exception as e:
                return {"error": f"Failed to update Confluence page: {str(e)}"}

        elif _confluence_space_key:
            # Search for existing page or create a work item status page
            try:
                # Search for a project status page
                search_result = confluence.search(
                    f'space="{_confluence_space_key}" AND title~"Work Item Status"',
                    limit=1
                )

                if search_result.get("results"):
                    # Update existing status page
                    existing_page = search_result["results"][0]
                    page_id = existing_page["id"]
                    current_page = confluence.get_page(page_id)
                    current_content = current_page.get("body", {}).get("storage", {}).get("value", "")
                    version = current_page["version"]["number"]

                    # Add new status entry to the table
                    new_row = f"""<tr>
<td>{timestamp}</td>
<td>{issue_key}</td>
<td>{summary}</td>
<td><strong>{status}</strong></td>
<td>{update_type}</td>
</tr>"""

                    # Insert row after table header
                    if "</thead>" in current_content:
                        insert_pos = current_content.find("</thead>") + 8
                        if "<tbody>" in current_content:
                            insert_pos = current_content.find("<tbody>") + 7
                        updated_content = current_content[:insert_pos] + new_row + current_content[insert_pos:]
                    else:
                        # Add to end of content
                        updated_content = current_content + new_row

                    confluence.update_page(
                        page_id=page_id,
                        title=current_page["title"],
                        content=updated_content,
                        version_number=version + 1,
                    )

                    return {
                        "success": True,
                        "action": "status_page_updated",
                        "page_id": page_id,
                        "issue_key": issue_key,
                        "status": status,
                    }
                else:
                    # Create new Work Item Status page
                    status_page_content = f"""<h1>Work Item Status Log</h1>
<p><strong>Space:</strong> {_confluence_space_key}</p>
<p><strong>Last Updated:</strong> {timestamp}</p>
<p>This page tracks status changes for Jira work items automatically synced from the DSDM workflow.</p>
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
<tr>
<td>{timestamp}</td>
<td>{issue_key}</td>
<td>{summary}</td>
<td><strong>{status}</strong></td>
<td>{update_type}</td>
</tr>
</tbody>
</table>
"""
                    new_page = confluence.create_page(
                        space_key=_confluence_space_key,
                        title="Work Item Status Log",
                        content=status_page_content,
                    )

                    return {
                        "success": True,
                        "action": "status_page_created",
                        "page_id": new_page["id"],
                        "issue_key": issue_key,
                        "status": status,
                    }

            except Exception as e:
                return {"error": f"Failed to sync to Confluence: {str(e)}"}

        return {"success": False, "reason": "No page mapping or space key configured"}

    except ImportError:
        return {"error": "Confluence tools not available"}
    except Exception as e:
        return {"error": str(e)}


def _handle_enable_confluence_sync(
    space_key: str,
    page_mappings: Optional[Dict[str, str]] = None
) -> str:
    """Handle enable Confluence sync request."""
    try:
        enable_confluence_sync(space_key, page_mappings)
        return json.dumps({
            "success": True,
            "message": "Confluence sync enabled",
            "space_key": space_key,
            "page_mappings_count": len(page_mappings) if page_mappings else 0,
            "info": "All Jira transitions and updates will now automatically sync to Confluence"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_disable_confluence_sync() -> str:
    """Handle disable Confluence sync request."""
    try:
        disable_confluence_sync()
        return json.dumps({
            "success": True,
            "message": "Confluence sync disabled",
            "info": "Jira updates will no longer automatically sync to Confluence"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_manual_sync_to_confluence(
    issue_key: str,
    confluence_page_id: Optional[str] = None
) -> str:
    """Handle manual sync to Confluence request."""
    global _confluence_sync_enabled

    client = get_jira_client()
    if not client.is_configured:
        return json.dumps({"error": "Jira not configured"})

    try:
        # Get issue details
        issue = client.get_issue(issue_key)
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        status = fields.get("status", {}).get("name", "Unknown")

        # If specific page ID provided, temporarily add to mapping
        if confluence_page_id:
            set_confluence_page_mapping(issue_key, confluence_page_id)

        # Ensure sync is enabled for this operation
        was_enabled = _confluence_sync_enabled
        if not was_enabled:
            if not _confluence_space_key and not confluence_page_id:
                return json.dumps({
                    "error": "Confluence sync not configured. Either enable sync with a space key or provide a confluence_page_id"
                })
            # Temporarily enable if we have a page ID
            if confluence_page_id:
                _confluence_sync_enabled = True

        # Perform sync
        result = _sync_issue_to_confluence(
            issue_key=issue_key,
            status=status,
            summary=summary,
            update_type="manual_sync",
        )

        # Restore previous state if we temporarily enabled
        if not was_enabled and confluence_page_id:
            _confluence_sync_enabled = was_enabled

        if result:
            return json.dumps({
                "success": result.get("success", False),
                "issue_key": issue_key,
                "status": status,
                "summary": summary,
                "confluence_result": result
            })
        else:
            return json.dumps({
                "error": "Sync failed - Confluence sync may not be properly configured"
            })

    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_set_page_mapping(issue_key: str, page_id: str) -> str:
    """Handle set page mapping request."""
    try:
        set_confluence_page_mapping(issue_key, page_id)
        return json.dumps({
            "success": True,
            "issue_key": issue_key,
            "page_id": page_id,
            "message": f"Mapped {issue_key} to Confluence page {page_id}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
