"""Confluence integration tools for DSDM agents."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from ..tool_registry import Tool, ToolRegistry


class ConfluenceClient:
    """Client for Confluence API interactions."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.base_url = base_url or os.environ.get("CONFLUENCE_BASE_URL", "").rstrip("/")
        self.username = username or os.environ.get("CONFLUENCE_USERNAME", "")
        self.api_token = api_token or os.environ.get("CONFLUENCE_API_TOKEN", "")
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
        """Check if Confluence is properly configured."""
        return bool(self.base_url and self.username and self.api_token)

    def _api_url(self, endpoint: str) -> str:
        """Build API URL."""
        return f"{self.base_url}/wiki/rest/api/{endpoint.lstrip('/')}"

    def get_space(self, space_key: str) -> Dict[str, Any]:
        """Get space information."""
        response = self.session.get(self._api_url(f"space/{space_key}"))
        response.raise_for_status()
        return response.json()

    def get_page(self, page_id: str, expand: str = "body.storage,version") -> Dict[str, Any]:
        """Get page content."""
        response = self.session.get(
            self._api_url(f"content/{page_id}"),
            params={"expand": expand}
        )
        response.raise_for_status()
        return response.json()

    def create_page(
        self,
        space_key: str,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new page."""
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        response = self.session.post(self._api_url("content"), json=payload)
        response.raise_for_status()
        return response.json()

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version_number: int,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing page."""
        payload = {
            "type": "page",
            "title": title,
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            },
            "version": {"number": version_number}
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        response = self.session.put(self._api_url(f"content/{page_id}"), json=payload)
        response.raise_for_status()
        return response.json()

    def search(self, cql: str, limit: int = 25) -> Dict[str, Any]:
        """Search Confluence using CQL."""
        response = self.session.get(
            self._api_url("content/search"),
            params={"cql": cql, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    def get_page_children(self, page_id: str) -> Dict[str, Any]:
        """Get child pages."""
        response = self.session.get(
            self._api_url(f"content/{page_id}/child/page")
        )
        response.raise_for_status()
        return response.json()

    def add_comment(self, page_id: str, comment: str) -> Dict[str, Any]:
        """Add a comment to a page."""
        payload = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {
                "storage": {
                    "value": comment,
                    "representation": "storage"
                }
            }
        }
        response = self.session.post(self._api_url("content"), json=payload)
        response.raise_for_status()
        return response.json()


# Global client instance
_confluence_client: Optional[ConfluenceClient] = None


def get_confluence_client() -> ConfluenceClient:
    """Get or create global Confluence client."""
    global _confluence_client
    if _confluence_client is None:
        _confluence_client = ConfluenceClient()
    return _confluence_client


def register_confluence_tools(registry: ToolRegistry) -> None:
    """Register Confluence tools with the registry."""

    # Get Page Content
    registry.register(Tool(
        name="confluence_get_page",
        description="Get the content of a Confluence page by its ID",
        input_schema={
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The Confluence page ID"
                }
            },
            "required": ["page_id"]
        },
        handler=_handle_get_page,
        category="confluence"
    ))

    # Create Page
    registry.register(Tool(
        name="confluence_create_page",
        description="Create a new Confluence page in a space",
        input_schema={
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "The Confluence space key (e.g., 'PROJ')"
                },
                "title": {
                    "type": "string",
                    "description": "Page title"
                },
                "content": {
                    "type": "string",
                    "description": "Page content in Confluence storage format (HTML-like)"
                },
                "parent_id": {
                    "type": "string",
                    "description": "Optional parent page ID to nest under"
                }
            },
            "required": ["space_key", "title", "content"]
        },
        handler=_handle_create_page,
        requires_approval=True,
        category="confluence"
    ))

    # Update Page
    registry.register(Tool(
        name="confluence_update_page",
        description="Update an existing Confluence page",
        input_schema={
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The Confluence page ID to update"
                },
                "title": {
                    "type": "string",
                    "description": "New page title"
                },
                "content": {
                    "type": "string",
                    "description": "New page content in Confluence storage format"
                }
            },
            "required": ["page_id", "title", "content"]
        },
        handler=_handle_update_page,
        requires_approval=True,
        category="confluence"
    ))

    # Search Pages
    registry.register(Tool(
        name="confluence_search",
        description="Search Confluence pages using CQL (Confluence Query Language)",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "CQL query string (e.g., 'space=PROJ and type=page')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 25)"
                }
            },
            "required": ["query"]
        },
        handler=_handle_search,
        category="confluence"
    ))

    # Get Space Info
    registry.register(Tool(
        name="confluence_get_space",
        description="Get information about a Confluence space",
        input_schema={
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "The Confluence space key"
                }
            },
            "required": ["space_key"]
        },
        handler=_handle_get_space,
        category="confluence"
    ))

    # Add Comment
    registry.register(Tool(
        name="confluence_add_comment",
        description="Add a comment to a Confluence page",
        input_schema={
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "The page ID to comment on"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment content (can include HTML)"
                }
            },
            "required": ["page_id", "comment"]
        },
        handler=_handle_add_comment,
        category="confluence"
    ))

    # Create Documentation Page (DSDM-specific)
    registry.register(Tool(
        name="confluence_create_dsdm_doc",
        description="Create a DSDM methodology documentation page with standard structure",
        input_schema={
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "The Confluence space key"
                },
                "doc_type": {
                    "type": "string",
                    "enum": [
                        "feasibility_report",
                        "business_requirements",
                        "functional_spec",
                        "technical_design",
                        "deployment_plan",
                        "risk_log",
                        "timebox_plan"
                    ],
                    "description": "Type of DSDM document"
                },
                "project_name": {
                    "type": "string",
                    "description": "Name of the project"
                },
                "content_sections": {
                    "type": "object",
                    "description": "Key-value pairs of section names and content"
                },
                "parent_id": {
                    "type": "string",
                    "description": "Optional parent page ID"
                }
            },
            "required": ["space_key", "doc_type", "project_name", "content_sections"]
        },
        handler=_handle_create_dsdm_doc,
        requires_approval=True,
        category="confluence"
    ))


def _handle_get_page(page_id: str) -> str:
    """Handle get page request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured. Set CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_API_TOKEN"})

    try:
        page = client.get_page(page_id)
        return json.dumps({
            "id": page["id"],
            "title": page["title"],
            "version": page["version"]["number"],
            "content": page.get("body", {}).get("storage", {}).get("value", ""),
            "url": f"{client.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_create_page(
    space_key: str,
    title: str,
    content: str,
    parent_id: Optional[str] = None
) -> str:
    """Handle create page request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured"})

    try:
        page = client.create_page(space_key, title, content, parent_id)
        return json.dumps({
            "success": True,
            "id": page["id"],
            "title": page["title"],
            "url": f"{client.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_update_page(page_id: str, title: str, content: str) -> str:
    """Handle update page request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured"})

    try:
        # Get current version
        current = client.get_page(page_id)
        version = current["version"]["number"] + 1

        page = client.update_page(page_id, title, content, version)
        return json.dumps({
            "success": True,
            "id": page["id"],
            "title": page["title"],
            "version": page["version"]["number"]
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_search(query: str, limit: int = 25) -> str:
    """Handle search request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured"})

    try:
        results = client.search(query, limit)
        pages = []
        for result in results.get("results", []):
            pages.append({
                "id": result["id"],
                "title": result["title"],
                "type": result["type"],
                "url": f"{client.base_url}/wiki{result.get('_links', {}).get('webui', '')}"
            })
        return json.dumps({
            "total": results.get("totalSize", len(pages)),
            "pages": pages
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_get_space(space_key: str) -> str:
    """Handle get space request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured"})

    try:
        space = client.get_space(space_key)
        return json.dumps({
            "key": space["key"],
            "name": space["name"],
            "type": space["type"],
            "url": f"{client.base_url}/wiki{space.get('_links', {}).get('webui', '')}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_add_comment(page_id: str, comment: str) -> str:
    """Handle add comment request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured"})

    try:
        result = client.add_comment(page_id, comment)
        return json.dumps({
            "success": True,
            "comment_id": result["id"],
            "page_id": page_id
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})


def _handle_create_dsdm_doc(
    space_key: str,
    doc_type: str,
    project_name: str,
    content_sections: Dict[str, str],
    parent_id: Optional[str] = None
) -> str:
    """Handle create DSDM document request."""
    client = get_confluence_client()
    if not client.is_configured:
        return json.dumps({"error": "Confluence not configured"})

    # Document templates
    templates = {
        "feasibility_report": {
            "title": f"{project_name} - Feasibility Report",
            "sections": ["Executive Summary", "Technical Feasibility", "Business Feasibility", "Resource Assessment", "Risk Assessment", "Recommendation"]
        },
        "business_requirements": {
            "title": f"{project_name} - Business Requirements Document",
            "sections": ["Business Context", "Stakeholders", "Requirements (Must Have)", "Requirements (Should Have)", "Requirements (Could Have)", "Requirements (Won't Have)", "Acceptance Criteria"]
        },
        "functional_spec": {
            "title": f"{project_name} - Functional Specification",
            "sections": ["Overview", "User Stories", "Functional Requirements", "Non-Functional Requirements", "Prototype Notes", "User Feedback"]
        },
        "technical_design": {
            "title": f"{project_name} - Technical Design Document",
            "sections": ["Architecture Overview", "Component Design", "Data Model", "API Design", "Security Considerations", "Performance Requirements"]
        },
        "deployment_plan": {
            "title": f"{project_name} - Deployment Plan",
            "sections": ["Deployment Overview", "Prerequisites", "Deployment Steps", "Rollback Plan", "Verification Steps", "Communication Plan"]
        },
        "risk_log": {
            "title": f"{project_name} - Risk Log",
            "sections": ["Active Risks", "Mitigated Risks", "Risk Matrix", "Mitigation Actions"]
        },
        "timebox_plan": {
            "title": f"{project_name} - Timebox Plan",
            "sections": ["Timeline Overview", "Timebox 1", "Timebox 2", "Timebox 3", "Dependencies", "Milestones"]
        }
    }

    template = templates.get(doc_type, {"title": f"{project_name} - {doc_type}", "sections": []})

    # Build content
    content_parts = [f"<h1>{template['title']}</h1>"]
    content_parts.append(f"<p><strong>Project:</strong> {project_name}</p>")
    content_parts.append(f"<p><strong>Created:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>")
    content_parts.append("<hr/>")

    for section in template["sections"]:
        section_content = content_sections.get(section, content_sections.get(section.lower().replace(" ", "_"), ""))
        content_parts.append(f"<h2>{section}</h2>")
        if section_content:
            content_parts.append(f"<p>{section_content}</p>")
        else:
            content_parts.append("<p><em>To be completed</em></p>")

    content = "\n".join(content_parts)

    try:
        page = client.create_page(space_key, template["title"], content, parent_id)
        return json.dumps({
            "success": True,
            "id": page["id"],
            "title": page["title"],
            "doc_type": doc_type,
            "url": f"{client.base_url}/wiki{page.get('_links', {}).get('webui', '')}"
        })
    except requests.RequestException as e:
        return json.dumps({"error": str(e)})
