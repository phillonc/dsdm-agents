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


def push_optix_service_endpoints():
    """Push OPTIX Service Endpoints documentation to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    # Read OPTIX Service Endpoints documentation
    optix_doc_path = project_root / "docs" / "OPTIX_Service_Endpoints.md"
    if not optix_doc_path.exists():
        print(f"ERROR: OPTIX Service Endpoints doc not found at {optix_doc_path}")
        return None

    optix_content = optix_doc_path.read_text()
    html_content = markdown_to_confluence(optix_content)

    # Add update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - OPTIX Service Endpoints"
    print(f"\nPushing OPTIX Service Endpoints documentation to Confluence...")
    return create_or_update_page(client, title, html_content)


def push_optix_frontend_readme():
    """Push OPTIX Frontend README to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    # Read OPTIX Frontend README
    frontend_doc_path = project_root / "generated" / "optix" / "frontend" / "README.md"
    if not frontend_doc_path.exists():
        print(f"ERROR: OPTIX Frontend README not found at {frontend_doc_path}")
        return None

    frontend_content = frontend_doc_path.read_text()
    html_content = markdown_to_confluence(frontend_content)

    # Add update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - OPTIX Frontend Documentation"
    print(f"\nPushing OPTIX Frontend documentation to Confluence...")
    return create_or_update_page(client, title, html_content)


def push_optix_platform_readme():
    """Push OPTIX Platform README to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    # Read OPTIX Platform README
    optix_readme_path = project_root / "generated" / "optix" / "README.md"
    if not optix_readme_path.exists():
        print(f"ERROR: OPTIX Platform README not found at {optix_readme_path}")
        return None

    optix_content = optix_readme_path.read_text()
    html_content = markdown_to_confluence(optix_content)

    # Add update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - OPTIX Platform Overview"
    print(f"\nPushing OPTIX Platform README to Confluence...")
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


def push_generic_doc(file_path: str, title_suffix: str) -> dict:
    """Push a generic markdown document to Confluence."""
    client = get_confluence_client()

    if not client.is_configured:
        return None

    doc_path = project_root / file_path
    if not doc_path.exists():
        print(f"  SKIP: {file_path} not found")
        return None

    doc_content = doc_path.read_text()
    html_content = markdown_to_confluence(doc_content)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f'<p><em>Last synced from repository: {timestamp}</em></p><hr/>' + html_content

    title = f"{PROJECT_NAME} - {title_suffix}"
    print(f"\nPushing {title_suffix}...")
    return create_or_update_page(client, title, html_content)


# Document configuration: (file_path, title_suffix, display_name)
DOCUMENTS = [
    # Core documentation
    ("README.md", "Documentation", "README"),
    ("GETTING_STARTED.md", "Getting Started Guide", "Getting Started"),
    ("docs/TECHNICAL_REQUIREMENTS.md", "Technical Requirements Document", "TRD"),
    ("docs/DEVOPS_TOOLS.md", "DevOps Tools Documentation", "DevOps Tools"),
    ("docs/WORKFLOW_DIAGRAM.md", "Workflow Diagram", "Workflow Diagram"),

    # OPTIX Requirements
    ("docs/requirements/OPTIX_PRD.md", "OPTIX PRD", "OPTIX PRD"),
    ("docs/requirements/OPTIX_TRD_DSDM.md", "OPTIX TRD DSDM", "OPTIX TRD DSDM"),
    ("docs/requirements/OPTIX_PRD_Generative_UI.md", "OPTIX PRD Generative UI", "OPTIX PRD GenUI"),
    ("docs/requirements/OPTIX_TRD_Generative_UI.md", "OPTIX TRD Generative UI", "OPTIX TRD GenUI"),
    ("docs/requirements/OPTIX_TRD_Generative_UI_API.md", "OPTIX TRD Generative UI API", "OPTIX TRD GenUI API"),
    ("docs/requirements/OPTIX_TRD_Vertical_Slices.md", "OPTIX TRD Vertical Slices", "OPTIX TRD Vertical Slices"),

    # OPTIX Service Documentation
    ("docs/OPTIX_Service_Endpoints.md", "OPTIX Service Endpoints", "OPTIX Service Endpoints"),

    # OPTIX Platform
    ("generated/optix/README.md", "OPTIX Platform Overview", "OPTIX Platform"),
    ("generated/optix/REMAINING_UI_UX_TASKS.md", "OPTIX Remaining UI/UX Tasks", "OPTIX UI/UX Tasks"),
    ("generated/optix/frontend/README.md", "OPTIX Frontend Documentation", "OPTIX Frontend"),
    ("generated/optix/genui_service/README.md", "OPTIX GenUI Service", "OPTIX GenUI Service"),

    # Vertical Slices - Trading Platform
    ("generated/optix/optix-trading-platform/README.md", "OPTIX Trading Platform", "Trading Platform"),
    ("generated/optix/optix-trading-platform/docs/API_REFERENCE.md", "OPTIX Trading Platform API", "Trading Platform API"),
    ("generated/optix/optix-trading-platform/docs/DEPLOYMENT.md", "OPTIX Trading Platform Deployment", "Trading Platform Deployment"),

    # Vertical Slices - Backtester
    ("generated/optix/optix_backtester/README.md", "OPTIX Backtester", "Backtester"),
    ("generated/optix/optix_backtester/docs/ARCHITECTURE.md", "OPTIX Backtester Architecture", "Backtester Architecture"),

    # Vertical Slices - GEX Visualizer
    ("generated/optix/gex_visualizer/README.md", "OPTIX GEX Visualizer", "GEX Visualizer"),
    ("generated/optix/gex_visualizer/docs/ARCHITECTURE.md", "OPTIX GEX Visualizer Architecture", "GEX Visualizer Architecture"),
    ("generated/optix/gex_visualizer/docs/API.md", "OPTIX GEX Visualizer API", "GEX Visualizer API"),

    # Vertical Slices - Volatility Compass
    ("generated/optix/optix_volatility_compass/README.md", "OPTIX Volatility Compass", "Volatility Compass"),
    ("generated/optix/optix_volatility_compass/docs/ARCHITECTURE.md", "OPTIX Volatility Compass Architecture", "Volatility Compass Architecture"),
    ("generated/optix/optix_volatility_compass/docs/USER_GUIDE.md", "OPTIX Volatility Compass User Guide", "Volatility Compass Guide"),

    # Vertical Slices - Smart Alerts (VS9)
    ("generated/optix/vs9_smart_alerts/README.md", "OPTIX Smart Alerts", "Smart Alerts"),
    ("generated/optix/vs9_smart_alerts/docs/ARCHITECTURE.md", "OPTIX Smart Alerts Architecture", "Smart Alerts Architecture"),
    ("generated/optix/vs9_smart_alerts/docs/API_GUIDE.md", "OPTIX Smart Alerts API", "Smart Alerts API"),

    # Vertical Slices - Trading Journal AI (VS10)
    ("generated/optix/vs10_trading_journal_ai/README.md", "OPTIX Trading Journal AI", "Trading Journal AI"),
    ("generated/optix/vs10_trading_journal_ai/docs/USER_GUIDE.md", "OPTIX Trading Journal AI User Guide", "Trading Journal Guide"),
    ("generated/optix/vs10_trading_journal_ai/docs/DEPLOYMENT.md", "OPTIX Trading Journal AI Deployment", "Trading Journal Deployment"),

    # Vertical Slices - Visual Strategy Builder
    ("generated/optix/optix_visual_strategy_builder/README.md", "OPTIX Visual Strategy Builder", "Visual Strategy Builder"),
    ("generated/optix/optix_visual_strategy_builder/docs/ARCHITECTURE.md", "OPTIX Visual Strategy Builder Architecture", "VSB Architecture"),

    # Vertical Slices - Collective Intelligence
    ("generated/optix/optix_collective_intelligence/README.md", "OPTIX Collective Intelligence", "Collective Intelligence"),
    ("generated/optix/optix_collective_intelligence/docs/ARCHITECTURE.md", "OPTIX Collective Intelligence Architecture", "CI Architecture"),

    # Vertical Slices - Adaptive Intelligence
    ("generated/optix/optix_adaptive_intelligence/README.md", "OPTIX Adaptive Intelligence", "Adaptive Intelligence"),
    ("generated/optix/optix_adaptive_intelligence/docs/architecture/ARCHITECTURE.md", "OPTIX Adaptive Intelligence Architecture", "AI Architecture"),
]


def main():
    """Main function to push all documentation."""
    print("=" * 60)
    print("DSDM Agents - Push Documentation to Confluence")
    print("=" * 60)
    print(f"Space: {CONFLUENCE_SPACE}")
    print(f"Project: {PROJECT_NAME}")
    print(f"Documents to push: {len(DOCUMENTS) + 1}")

    # Push all documentation from config
    results = []
    for file_path, title_suffix, display_name in DOCUMENTS:
        result = push_generic_doc(file_path, title_suffix)
        results.append((display_name, result))

    # Push the sync feature announcement (static content)
    results.append(("Sync Feature", push_sync_feature_announcement()))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, result in results:
        status = "OK" if result else "FAILED/SKIP"
        print(f"  {name}: {status}")

    success_count = sum(1 for _, r in results if r)
    print(f"\nCompleted: {success_count}/{len(results)} pages updated")


if __name__ == "__main__":
    main()
