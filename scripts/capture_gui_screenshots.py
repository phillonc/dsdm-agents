#!/usr/bin/env python3
"""Regenerate the console screenshots used by docs/GUI.md.

    pip install playwright && playwright install chromium
    python scripts/capture_gui_screenshots.py

Playwright is a documentation-only dependency and is deliberately not in
`requirements.txt` - nothing the console itself does needs a browser driver.

The screenshots are taken against a throwaway demo workspace in a temp
directory, with a stubbed orchestrator standing in for the real agents. That
means no API key is consumed, no LLM is called, the images are reproducible,
and nobody's real project ends up in the documentation.

Run this whenever the console's layout changes, then commit docs/images/.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "images"
IMAGE_WIDTH = 1200  # documentation images are downscaled to this width
MISSION = "Give clients a self-service portal so they can track orders without calling support"

sys.path.insert(0, str(REPO_ROOT))


def build_demo_workspace() -> Path:
    """Create a temp working directory with a small, realistic project in it."""
    work = Path(tempfile.mkdtemp(prefix="dsdm-console-docs-"))
    shutil.copytree(REPO_ROOT / "src", work / "src", dirs_exist_ok=True)
    (work / "generated").mkdir(exist_ok=True)
    os.chdir(work)
    # A placeholder key so the Setup page reads "Ready" for most of the shots.
    os.environ["ANTHROPIC_API_KEY"] = "demo-key-not-real"
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["AGENT_RUNTIME"] = "legacy"

    docs = work / "generated" / "customer-portal" / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "FEASIBILITY_REPORT.md").write_text(
        "# Feasibility Report: Customer Self-Service Portal\n\n"
        "**Recommendation:** Go\n"
        "**Confidence:** High\n"
        "**DSDM fit:** Strong — the scope can be delivered incrementally\n\n"
        "## Summary\n\n"
        "Order tracking is the single highest-volume reason customers call support. A read-only "
        "portal over the existing order service delivers most of that value without changing the "
        "order system itself.\n\n"
        "## Top risks\n\n"
        "| Risk | Impact | Mitigation |\n"
        "| --- | --- | --- |\n"
        "| Order data quality varies by channel | High | Validate against a sample before build |\n"
        "| Identity/login has no existing service | Medium | Reuse the customer identity provider |\n"
        "| Support process change not yet agreed | Medium | Involve support lead from Business Study |\n\n"
        "## Recommendation\n\n"
        "Proceed to Business Study with a Must-have scope limited to order status and history.\n",
        encoding="utf-8",
    )
    (docs / "BUSINESS_STUDY.md").write_text(
        "# Business Study\n\n## Prioritised requirements\n\n"
        "| Requirement | MoSCoW |\n| --- | --- |\n"
        "| View live order status | Must |\n"
        "| View order history | Must |\n"
        "| Email notification on status change | Should |\n"
        "| Download invoices | Could |\n"
        "| Live chat with an agent | Won't (this increment) |\n",
        encoding="utf-8",
    )
    (docs / "PRD.md").write_text(
        "# Product Requirements Document\n\nScope, success metrics and user journeys.\n",
        encoding="utf-8",
    )

    # src.rooms and src.orchestrator import each other; importing the
    # orchestrator package first is what the CLI does and avoids the cycle.
    import src.orchestrator  # noqa: F401
    from src.rooms import create_delivery_room, export_delivery_room

    room = create_delivery_room(MISSION, "customer-portal", "mvp", True)
    export_delivery_room(room.project_name)
    return work


def install_stub_orchestrator() -> None:
    """Point the run manager at a stub, so the images cost nothing to produce."""
    from src.agents.base_agent import AgentResult, ProgressEvent, ProgressInfo
    from src.gui.runs import get_run_manager

    class StubAgent:
        def __init__(self) -> None:
            self.progress_callback = None
            self.approval_callback = None

        def set_progress_callback(self, callback) -> None:
            self.progress_callback = callback

    class StubToolRegistry:
        def get(self, name):
            tool = type("Tool", (), {})()
            tool.name = name
            tool.description = "Write a document into the project workspace. Creates parent folders if needed."
            return tool

    class StubOrchestrator:
        def __init__(self, project: str = "customer-portal") -> None:
            self.project = project
            self.agents = {"stage": StubAgent()}
            self.design_build_agents = {}
            self.tool_registry = StubToolRegistry()

        def run_phase(self, phase, user_input, context=None):
            agent = self.agents["stage"]
            target = Path(f"generated/{self.project}/docs")
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{phase.value.upper()}.md").write_text(f"# {phase.value}\n", encoding="utf-8")

            for index, (event, message, tool) in enumerate(
                [
                    (ProgressEvent.STARTED, f"Starting task: {user_input[:70]}", None),
                    (ProgressEvent.THINKING, "Reviewing the business context and existing constraints", None),
                    (ProgressEvent.TOOL_CALLING, "Creating the project workspace", "project_init"),
                    (ProgressEvent.TOOL_COMPLETED, "Project workspace ready", "project_init"),
                    (ProgressEvent.THINKING, "Drafting the assessment and top risks", None),
                ],
                1,
            ):
                agent.progress_callback(
                    ProgressInfo(
                        event=event,
                        message=message,
                        agent_name="Feasibility Agent",
                        iteration=index,
                        max_iterations=12,
                        tool_name=tool,
                    )
                )
                time.sleep(0.3)

            if phase.value == "business_study":
                agent.approval_callback(
                    "write_file",
                    {
                        "file_path": "customer-portal/docs/BUSINESS_STUDY.md",
                        "content": "# Business Study\n\n## Prioritised requirements\n\n"
                        "| Requirement | MoSCoW |\n| View live order status | Must |...",
                    },
                )

            return AgentResult(
                success=True,
                output="# Feasibility complete\n\n**Recommendation:** Go\n\n"
                "Order tracking is the highest-volume support call driver, and a read-only portal "
                "over the existing order service delivers most of that value.\n\n"
                "- Live order status is the Must-have\n"
                "- Email notifications are a Should-have\n",
                artifacts={"recommendation": "go", "confidence": "high"},
            )

        def shutdown_pi_bridge(self) -> None:
            pass

    get_run_manager()._create_orchestrator = lambda run: StubOrchestrator(run.project or "customer-portal")


def run_second_delivery() -> None:
    """Run a short second delivery so History spans more than one run."""
    from src.gui.runs import get_run_manager

    manager = get_run_manager()
    run = manager.start(
        kind="stage",
        brief="A mobile companion app so customers can track orders on the move",
        stage_ids=["design_build"],
        project="portal-mobile",
    )
    deadline = time.time() + 60
    while run.status not in ("completed", "failed", "stopped") and time.time() < deadline:
        time.sleep(0.1)


def find_chromium() -> str | None:
    """Return an explicit Chromium path when one is provisioned, else None."""
    browsers_root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    for candidate in sorted(browsers_root.glob("chromium-*/chrome-linux/chrome")):
        return str(candidate)
    return None


def capture(work: Path) -> list[str]:
    from playwright.sync_api import sync_playwright

    from src.gui.server import create_server

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    launch_kwargs = {"args": ["--no-sandbox"]}
    executable = find_chromium()
    if executable:
        launch_kwargs["executable_path"] = executable

    server = create_server(host="127.0.0.1", port=0).start()
    base = f"http://127.0.0.1:{server.port}"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**launch_kwargs)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

            def visit(route: str, pause: float = 1.4) -> None:
                page.goto(f"{base}/{route}", wait_until="networkidle")
                time.sleep(pause)

            def save(name: str) -> None:
                page.screenshot(path=str(OUTPUT_DIR / f"{name}.png"), full_page=True)
                print(f"captured {name}")

            # Drive a real run first, so Activity and the run page have content.
            visit("#/new")
            page.fill("#brief", MISSION)
            page.fill("#project", "customer-portal")
            page.click("[data-step-next]")
            time.sleep(0.4)
            page.click("[data-scope='stages']")
            time.sleep(0.4)
            page.click("[data-stage='business_study']")
            time.sleep(0.5)
            save("gui-start-delivery-scope")

            page.click("[data-step-next]")
            time.sleep(0.4)
            page.click("[data-oversight='hybrid']")
            time.sleep(0.4)
            save("gui-start-delivery-oversight")

            page.click("[data-step-next]")
            time.sleep(0.4)
            page.click("[data-start-run]")

            # Guided oversight pauses twice: the stage checkpoint, then the tool.
            page.wait_for_selector("[data-approve]", timeout=30_000)
            time.sleep(0.8)
            save("gui-run-approval")
            page.click("[data-approve]")
            page.wait_for_selector("[data-approve]", timeout=30_000)
            time.sleep(0.5)
            page.click("[data-approve]")
            time.sleep(7)  # let the run finish and the toast fade
            save("gui-run-complete")

            # The step-back panel, expanded on the point that undoes both stages.
            page.wait_for_selector("[data-rollback]", timeout=30_000)
            page.locator("[data-rollback]").nth(1).click()
            time.sleep(0.8)
            save("gui-step-back")

            # A second run against a different project, so the cross-run
            # timeline has something real to show.
            run_second_delivery()
            visit("#/history")
            save("gui-history")

            visit("#/overview")
            save("gui-overview")

            visit("#/documents/customer-portal?file=docs/FEASIBILITY_REPORT.md")
            save("gui-documents")

            visit("#/rooms/customer-portal")
            save("gui-delivery-room")

            visit("#/overview")
            page.click("#theme-toggle")
            time.sleep(0.6)
            save("gui-overview-dark")

            browser.close()
    finally:
        server.stop()

    # The Setup page is most useful showing a failing check next to its fix.
    os.environ.pop("ANTHROPIC_API_KEY", None)
    server = create_server(host="127.0.0.1", port=0).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**launch_kwargs)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(f"http://127.0.0.1:{server.port}/#/setup", wait_until="networkidle")
            time.sleep(1.4)
            page.screenshot(path=str(OUTPUT_DIR / "gui-setup.png"), full_page=True)
            print("captured gui-setup")
            browser.close()
    finally:
        server.stop()

    return errors


def optimise() -> None:
    """Downscale and palette-reduce the PNGs so the repo stays small."""
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed - skipping image optimisation (pip install pillow)")
        return

    for path in sorted(OUTPUT_DIR.glob("*.png")):
        image = Image.open(path).convert("RGB")
        if image.width > IMAGE_WIDTH:
            height = round(image.height * IMAGE_WIDTH / image.width)
            image = image.resize((IMAGE_WIDTH, height), Image.LANCZOS)
        # Flat UI colours survive a 256-colour palette without visible loss.
        image.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
        print(f"optimised {path.name} ({path.stat().st_size // 1024} KB)")


def main() -> int:
    work = build_demo_workspace()
    install_stub_orchestrator()
    errors = capture(work)
    optimise()
    shutil.rmtree(work, ignore_errors=True)

    if errors:
        print("\nBrowser reported errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"\nScreenshots written to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
