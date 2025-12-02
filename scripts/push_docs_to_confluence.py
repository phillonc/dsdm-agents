#!/usr/bin/env python3
"""
Push DSDM Agents documentation updates to Confluence.

This script pushes the README and Technical Requirements Document to Confluence,
demonstrating the new Jira-Confluence sync feature.

Usage:
    python scripts/push_docs_to_confluence.py

Requires environment variables:
    CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.tools.integrations.confluence_tools import get_confluence_client


# Configuration - update these for your Confluence space
CONFLUENCE_SPACE = os.environ.get("CONFLUENCE_DEFAULT_SPACE", "dhdemoconf")
PROJECT_NAME = "DSDM Agents"


def markdown_to_confluence(md_content: str) -> str:
    """Convert Markdown to Confluence storage format."""
    html = md_content

    # Headers
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Code blocks
    html = re.sub(r'```(\w+)?\n(.*?)```', r'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">\1</ac:parameter><ac:plain-text-body><![CDATA[\2]]></ac:plain-text-body></ac:structured-macro>', html, flags=re.DOTALL)

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Lists
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Paragraphs (simple conversion)
    lines = html.split('\n')
    result = []
    for line in lines:
        if line.strip() and not line.strip().startswith('<'):
            result.append(f'<p>{line}</p>')
        else:
            result.append(line)

    return '\n'.join(result)


def create_or_update_page(client, title: str, content: str, parent_id: str = None) -> dict:
    """Create or update a Confluence page."""
    try:
        # Check if page exists
        search_results = client.search(f'space="{CONFLUENCE_SPACE}" AND title="{title}"')

        if search_results.get("results"):
            # Update existing page
            page_id = search_results["results"][0]["id"]
            current = client.get_page(page_id)
            version = current["version"]["number"] + 1

            page = client.update_page(
                page_id=page_id,
                title=title,
                content=content,
                version_number=version
            )
            print(f"  Updated: {client.base_url}/wiki{page.get('_links', {}).get('webui', '')}")
            return page
        else:
            # Create new page
            page = client.create_page(
                space_key=CONFLUENCE_SPACE,
                title=title,
                content=content,
                parent_id=parent_id
            )
            print(f"  Created: {client.base_url}/wiki{page.get('_links', {}).get('webui', '')}")
            return page

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def push_readme():
    """Push README.md to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        print("ERROR: Confluence not configured. Set environment variables:")
        print("  CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN")
        return None

    # Read README
    readme_path = project_root / "README.md"
    if not readme_path.exists():
        print(f"ERROR: README not found at {readme_path}")
        return None

    readme_content = readme_path.read_text()
    html_content = markdown_to_confluence(readme_content)

    # Add update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - Documentation"
    print(f"\nPushing README to Confluence...")
    return create_or_update_page(client, title, html_content)


def push_trd():
    """Push Technical Requirements Document to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    # Read TRD
    trd_path = project_root / "docs" / "TECHNICAL_REQUIREMENTS.md"
    if not trd_path.exists():
        print(f"ERROR: TRD not found at {trd_path}")
        return None

    trd_content = trd_path.read_text()
    html_content = markdown_to_confluence(trd_content)

    # Add update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - Technical Requirements Document"
    print(f"\nPushing TRD to Confluence...")
    return create_or_update_page(client, title, html_content)


def push_devops_tools_docs():
    """Push DevOps Tools documentation to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    # Read DevOps Tools documentation
    devops_doc_path = project_root / "docs" / "DEVOPS_TOOLS.md"
    if not devops_doc_path.exists():
        print(f"ERROR: DevOps Tools doc not found at {devops_doc_path}")
        return None

    devops_content = devops_doc_path.read_text()
    html_content = markdown_to_confluence(devops_content)

    # Add update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - DevOps Tools Documentation"
    print(f"\nPushing DevOps Tools documentation to Confluence...")
    return create_or_update_page(client, title, html_content)


def push_sync_feature_announcement():
    """Push a page announcing the new Jira-Confluence sync feature."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""<h1>New Feature: Jira-Confluence Sync</h1>
<p><strong>Released:</strong> {timestamp}</p>
<hr/>

<h2>Overview</h2>
<p>DSDM Agents now supports automatic synchronization of Jira work item status changes to Confluence documentation.</p>

<h2>Key Features</h2>
<ul>
<li><strong>Automatic Sync:</strong> When you transition or update a Jira issue, the status is automatically logged to Confluence</li>
<li><strong>Work Item Status Log:</strong> A dedicated page tracks all status changes with timestamps</li>
<li><strong>Page Mapping:</strong> Map specific Jira issues to dedicated Confluence documentation pages</li>
<li><strong>DSDM Phase Context:</strong> Sync includes DSDM phase information for better traceability</li>
</ul>

<h2>New Tools</h2>
<table>
<thead>
<tr><th>Tool</th><th>Description</th></tr>
</thead>
<tbody>
<tr><td><code>setup_jira_confluence_sync</code></td><td>Enable sync and create status page</td></tr>
<tr><td><code>sync_work_item_status</code></td><td>Sync with DSDM phase context</td></tr>
<tr><td><code>get_sync_status</code></td><td>Check current sync configuration</td></tr>
<tr><td><code>jira_enable_confluence_sync</code></td><td>Enable automatic sync</td></tr>
<tr><td><code>jira_disable_confluence_sync</code></td><td>Disable automatic sync</td></tr>
<tr><td><code>jira_sync_to_confluence</code></td><td>Manual sync for specific issue</td></tr>
<tr><td><code>jira_set_confluence_page_mapping</code></td><td>Map issue to specific page</td></tr>
</tbody>
</table>

<h2>Quick Start</h2>
<ac:structured-macro ac:name="code">
<ac:parameter ac:name="language">python</ac:parameter>
<ac:plain-text-body><![CDATA[
from src.orchestrator import DSDMOrchestrator

# Create orchestrator with both integrations
orchestrator = DSDMOrchestrator(include_jira=True, include_confluence=True)

# Setup sync - this enables automatic sync and creates a status page
orchestrator.tool_registry.execute(
    "setup_jira_confluence_sync",
    confluence_space_key="PROJ"
)

# Now any Jira transition will auto-sync to Confluence
# Example: transitioning an issue
orchestrator.tool_registry.execute(
    "jira_transition_issue",
    issue_key="PROJ-123",
    transition_name="In Progress"
)
# ^ This automatically updates Confluence with the status change!
]]></ac:plain-text-body>
</ac:structured-macro>

<h2>Benefits</h2>
<ul>
<li>Keep documentation in sync with actual work item status</li>
<li>Automatic audit trail of status changes</li>
<li>Reduce manual documentation updates</li>
<li>Better traceability across DSDM phases</li>
</ul>

<p><em>For more details, see the updated README and Technical Requirements Document.</em></p>
"""

    title = f"{PROJECT_NAME} - Jira-Confluence Sync Feature"
    print(f"\nPushing feature announcement to Confluence...")
    return create_or_update_page(client, title, content)


def main():
    """Main function to push all documentation."""
    print("=" * 60)
    print("DSDM Agents - Push Documentation to Confluence")
    print("=" * 60)
    print(f"Space: {CONFLUENCE_SPACE}")
    print(f"Project: {PROJECT_NAME}")

    # Push all documentation
    results = []
    results.append(("README", push_readme()))
    results.append(("TRD", push_trd()))
    results.append(("DevOps Tools", push_devops_tools_docs()))
    results.append(("Sync Feature", push_sync_feature_announcement()))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, result in results:
        status = "OK" if result else "FAILED"
        print(f"  {name}: {status}")

    success_count = sum(1 for _, r in results if r)
    print(f"\nCompleted: {success_count}/{len(results)} pages updated")


if __name__ == "__main__":
    main()
