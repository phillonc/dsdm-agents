#!/usr/bin/env python3
"""
Push Shopping List TRD to Confluence and create Jira tickets.

Usage:
    python push_to_atlassian.py

Requires environment variables:
    CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN
    JIRA_BASE_URL, JIRA_USERNAME, JIRA_API_TOKEN
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.tools.integrations.confluence_tools import get_confluence_client
from src.tools.integrations.jira_tools import get_jira_client

# Configuration
CONFLUENCE_SPACE = "dhdemoconf"
JIRA_PROJECT = "DD"
PROJECT_NAME = "Shopping List Application"


def create_confluence_page():
    """Create TRD page in Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        print("ERROR: Confluence not configured. Set environment variables:")
        print("  CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN")
        return None

    # Read TRD content
    trd_path = Path(__file__).parent.parent / "docs" / "TECHNICAL_REQUIREMENTS.md"
    if not trd_path.exists():
        print(f"ERROR: TRD not found at {trd_path}")
        return None

    trd_content = trd_path.read_text()

    # Convert Markdown to Confluence storage format (simplified)
    html_content = markdown_to_confluence(trd_content)

    try:
        # Check if page already exists
        search_results = client.search(f'space={CONFLUENCE_SPACE} AND title="{PROJECT_NAME} - Technical Requirements Document"')

        if search_results.get("results"):
            # Update existing page
            page_id = search_results["results"][0]["id"]
            current = client.get_page(page_id)
            version = current["version"]["number"] + 1

            page = client.update_page(
                page_id=page_id,
                title=f"{PROJECT_NAME} - Technical Requirements Document",
                content=html_content,
                version_number=version
            )
            print(f"Updated Confluence page: {client.base_url}/wiki{page.get('_links', {}).get('webui', '')}")
        else:
            # Create new page
            page = client.create_page(
                space_key=CONFLUENCE_SPACE,
                title=f"{PROJECT_NAME} - Technical Requirements Document",
                content=html_content
            )
            print(f"Created Confluence page: {client.base_url}/wiki{page.get('_links', {}).get('webui', '')}")

        return page

    except Exception as e:
        print(f"ERROR creating Confluence page: {e}")
        return None


def markdown_to_confluence(md_content: str) -> str:
    """Convert Markdown to Confluence storage format."""
    import re

    html = md_content

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Code blocks
    html = re.sub(r'```(\w+)?\n(.*?)```', r'<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[\2]]></ac:plain-text-body></ac:structured-macro>', html, flags=re.DOTALL)

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Horizontal rules
    html = re.sub(r'^---+$', r'<hr/>', html, flags=re.MULTILINE)

    # Tables (simplified - Confluence tables)
    lines = html.split('\n')
    in_table = False
    table_lines = []
    result_lines = []

    for line in lines:
        if '|' in line and not line.strip().startswith('```'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
        else:
            if in_table:
                result_lines.append(convert_table(table_lines))
                in_table = False
                table_lines = []
            result_lines.append(line)

    if in_table:
        result_lines.append(convert_table(table_lines))

    html = '\n'.join(result_lines)

    # Paragraphs (wrap non-HTML lines)
    lines = html.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<') and not stripped.startswith('|'):
            result.append(f'<p>{line}</p>')
        else:
            result.append(line)

    return '\n'.join(result)


def convert_table(table_lines: list) -> str:
    """Convert Markdown table to Confluence table."""
    if len(table_lines) < 2:
        return '\n'.join(table_lines)

    rows = []
    for i, line in enumerate(table_lines):
        if '---' in line:
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if i == 0:
            # Header row
            rows.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
        else:
            rows.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')

    return '<table>' + ''.join(rows) + '</table>'


def create_jira_tickets():
    """Create Jira tickets for all requirements."""
    client = get_jira_client()

    if not client.is_configured:
        print("ERROR: Jira not configured. Set environment variables:")
        print("  JIRA_BASE_URL, JIRA_USERNAME, JIRA_API_TOKEN")
        return []

    created_tickets = []

    # Define all requirements from TRD
    requirements = [
        # Authentication Requirements (Must Have)
        {
            "summary": "[MUST] FR-AUTH-001: Google OAuth Login",
            "description": "Users can authenticate using Google accounts. Implement Google OAuth 2.0 flow with passport-google-oauth20.\n\nPriority: Must Have\nCategory: Authentication",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "authentication", "dsdm"]
        },
        {
            "summary": "[MUST] FR-AUTH-002: Session Persistence",
            "description": "Sessions persist for 24 hours using express-session with secure cookie configuration.\n\nPriority: Must Have\nCategory: Authentication",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "authentication", "dsdm"]
        },
        {
            "summary": "[MUST] FR-AUTH-003: Logout Functionality",
            "description": "Users can securely log out, clearing session data and redirecting to login page.\n\nPriority: Must Have\nCategory: Authentication",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "authentication", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-AUTH-004: Development Mode Login",
            "description": "Mock login available when OAuth not configured for local development testing.\n\nPriority: Should Have\nCategory: Authentication",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "authentication", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-AUTH-005: Auto-redirect on Auth",
            "description": "Authenticated users automatically redirected to main app, unauthenticated to login.\n\nPriority: Should Have\nCategory: Authentication",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "authentication", "dsdm"]
        },

        # Shopping List Requirements (Must Have)
        {
            "summary": "[MUST] FR-LIST-001: Add Item",
            "description": "Users can add text items to their shopping list via input field and Add button.\n\nPriority: Must Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "shopping-list", "dsdm"]
        },
        {
            "summary": "[MUST] FR-LIST-002: View Items",
            "description": "All shopping list items displayed in ordered list with checkboxes and delete buttons.\n\nPriority: Must Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "shopping-list", "dsdm"]
        },
        {
            "summary": "[MUST] FR-LIST-003: Toggle Complete",
            "description": "Users can mark items as completed/uncompleted by clicking checkbox or item row.\n\nPriority: Must Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "shopping-list", "dsdm"]
        },
        {
            "summary": "[MUST] FR-LIST-004: Delete Item",
            "description": "Users can remove individual items from the list via delete button.\n\nPriority: Must Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "shopping-list", "dsdm"]
        },
        {
            "summary": "[COULD] FR-LIST-005: Clear All",
            "description": "Users can clear entire shopping list with single action (DELETE /api/shopping-list).\n\nPriority: Could Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "Medium",
            "labels": ["could-have", "shopping-list", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-LIST-006: Statistics Display",
            "description": "Display count of total items, completed items, and remaining items below the list.\n\nPriority: Should Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "shopping-list", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-LIST-007: Empty State",
            "description": "Show friendly message 'Your shopping list is empty' when list has no items.\n\nPriority: Should Have\nCategory: Shopping List",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "shopping-list", "dsdm"]
        },

        # UI Requirements
        {
            "summary": "[MUST] FR-UI-001: Responsive Design",
            "description": "Application works on desktop and mobile browsers with responsive CSS layout.\n\nPriority: Must Have\nCategory: UI",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["must-have", "ui", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-UI-002: User Profile Display",
            "description": "Show logged-in user name and profile picture in header area.\n\nPriority: Should Have\nCategory: UI",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "ui", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-UI-003: Visual Feedback",
            "description": "CSS animations for add/delete actions (slideIn animation, hover effects).\n\nPriority: Should Have\nCategory: UI",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "ui", "dsdm"]
        },
        {
            "summary": "[SHOULD] FR-UI-004: Keyboard Support",
            "description": "Enter key adds items from input field for improved usability.\n\nPriority: Should Have\nCategory: UI",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["should-have", "ui", "dsdm"]
        },

        # Non-Functional Requirements
        {
            "summary": "[NFR] PERF-001: API Response Time < 200ms",
            "description": "All API endpoints should respond within 200ms under normal load.\n\nCategory: Performance",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["non-functional", "performance", "dsdm"]
        },
        {
            "summary": "[NFR] SEC-001: OAuth 2.0 Implementation",
            "description": "Implement industry-standard OAuth 2.0 authentication with Google provider.\n\nCategory: Security",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["non-functional", "security", "dsdm"]
        },
        {
            "summary": "[NFR] SEC-002: Session Security",
            "description": "Use HTTP-only session cookies with proper expiry and secure flag in production.\n\nCategory: Security",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["non-functional", "security", "dsdm"]
        },

        # Technical Stories
        {
            "summary": "[TECH] Set up Express.js server",
            "description": "Initialize Node.js project with Express.js, configure middleware (cors, json, static files).\n\nCategory: Backend",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["technical", "backend", "dsdm"]
        },
        {
            "summary": "[TECH] Implement Passport.js authentication",
            "description": "Configure Passport.js with Google OAuth 2.0 strategy, serialize/deserialize user sessions.\n\nCategory: Backend",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["technical", "backend", "dsdm"]
        },
        {
            "summary": "[TECH] Create REST API endpoints",
            "description": "Implement GET/POST/DELETE /api/shopping-list endpoints with authentication middleware.\n\nCategory: Backend",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["technical", "backend", "dsdm"]
        },
        {
            "summary": "[TECH] Build frontend SPA",
            "description": "Create shopping-list.html with vanilla JS for item management, auth state handling.\n\nCategory: Frontend",
            "issue_type": "Story",
            "priority": "Highest",
            "labels": ["technical", "frontend", "dsdm"]
        },
        {
            "summary": "[FUTURE] Replace in-memory storage with database",
            "description": "Future: Replace Map-based storage with MongoDB or PostgreSQL for persistence.\n\nCategory: Backend Enhancement",
            "issue_type": "Story",
            "priority": "Low",
            "labels": ["future", "backend", "dsdm"]
        },
    ]

    print(f"\nCreating {len(requirements)} Jira tickets in project {JIRA_PROJECT}...")
    print("-" * 60)

    for req in requirements:
        try:
            issue = client.create_issue(
                project_key=JIRA_PROJECT,
                summary=req["summary"],
                description=req["description"],
                issue_type=req["issue_type"],
                priority=req.get("priority"),
                labels=req.get("labels")
            )
            ticket_url = f"{client.base_url}/browse/{issue['key']}"
            print(f"  Created: {issue['key']} - {req['summary'][:50]}...")
            created_tickets.append({
                "key": issue["key"],
                "summary": req["summary"],
                "url": ticket_url
            })
        except Exception as e:
            print(f"  ERROR creating '{req['summary']}': {e}")

    print("-" * 60)
    print(f"Created {len(created_tickets)} tickets successfully")

    return created_tickets


def main():
    """Main entry point."""
    print("=" * 60)
    print("Shopping List - Push to Atlassian")
    print("=" * 60)

    # Push to Confluence
    print("\n[1/2] Creating Confluence TRD page...")
    confluence_page = create_confluence_page()

    # Create Jira tickets
    print("\n[2/2] Creating Jira tickets...")
    jira_tickets = create_jira_tickets()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if confluence_page:
        print(f"Confluence: Page created/updated successfully")
    else:
        print(f"Confluence: FAILED - Check credentials")

    if jira_tickets:
        print(f"Jira: Created {len(jira_tickets)} tickets")
        print(f"\nJira tickets created:")
        for ticket in jira_tickets[:5]:
            print(f"  - {ticket['key']}: {ticket['summary'][:40]}...")
        if len(jira_tickets) > 5:
            print(f"  ... and {len(jira_tickets) - 5} more")
    else:
        print(f"Jira: FAILED - Check credentials")

    print("\nDone!")


if __name__ == "__main__":
    main()
