"""Output formatter for DSDM Agents terminal output.

Provides clear, structured formatting for agent outputs in the terminal.
"""

import re
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


class OutputFormatter:
    """Formats agent outputs for clear terminal display."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def format_agent_start(
        self,
        agent_name: str,
        phase_or_role: str,
        mode: str,
        description: Optional[str] = None,
    ) -> None:
        """Display agent start banner."""
        content = Text()
        content.append(f"Agent: ", style="dim")
        content.append(f"{agent_name}\n", style="bold cyan")
        content.append(f"Mode: ", style="dim")
        content.append(f"{mode}\n", style="yellow")
        if description:
            content.append(f"\n{description}", style="italic")

        self.console.print(Panel(
            content,
            title=f"[bold green]Starting {phase_or_role}[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))

    def format_agent_result(
        self,
        phase_or_role: str,
        success: bool,
        output: str,
        artifacts: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Display formatted agent result."""
        # Status header
        if success:
            status_text = Text("SUCCESS", style="bold green")
            border_style = "green"
        else:
            status_text = Text("FAILED", style="bold red")
            border_style = "red"

        self.console.print()
        self.console.print(Rule(f"[bold]{phase_or_role} Result[/bold]", style=border_style))
        self.console.print()

        # Status line
        status_line = Text()
        status_line.append("Status: ", style="dim")
        status_line.append(status_text)
        self.console.print(status_line)
        self.console.print()

        # Format and display main output
        self._format_output_content(output)

        # Display artifacts if any
        if artifacts:
            self._format_artifacts(artifacts)

        # Display tool call summary if any
        if tool_calls:
            self._format_tool_calls_summary(tool_calls)

        self.console.print()
        self.console.print(Rule(style=border_style))

    def _format_output_content(self, output: str) -> None:
        """Format the main output content with proper structure."""
        if not output:
            self.console.print("[dim]No output generated[/dim]")
            return

        # Try to detect and format different content types
        output = output.strip()

        # Check if output is markdown-like (has headers, lists, code blocks)
        has_markdown = bool(
            re.search(r'^#+\s', output, re.MULTILINE) or  # Headers
            re.search(r'^[-*]\s', output, re.MULTILINE) or  # Lists
            re.search(r'```', output) or  # Code blocks
            re.search(r'\*\*.*\*\*', output)  # Bold text
        )

        if has_markdown:
            self._format_markdown_output(output)
        else:
            self._format_plain_output(output)

    def _format_markdown_output(self, output: str) -> None:
        """Format markdown output with rich rendering."""
        # Extract and format code blocks separately for better display
        code_block_pattern = r'```(\w*)\n(.*?)```'
        parts = re.split(code_block_pattern, output, flags=re.DOTALL)

        i = 0
        while i < len(parts):
            if i + 2 < len(parts) and parts[i + 1] and parts[i + 2]:
                # This is text before a code block
                if parts[i].strip():
                    self.console.print(Markdown(parts[i].strip()))

                # Format the code block
                lang = parts[i + 1] or "text"
                code = parts[i + 2].strip()
                self.console.print()
                self.console.print(Syntax(code, lang, theme="monokai", line_numbers=True))
                self.console.print()
                i += 3
            else:
                # Regular text
                if parts[i].strip():
                    self.console.print(Markdown(parts[i].strip()))
                i += 1

    def _format_plain_output(self, output: str) -> None:
        """Format plain text output with paragraph breaks."""
        paragraphs = output.split('\n\n')
        for i, para in enumerate(paragraphs):
            if para.strip():
                # Check for section headers (lines ending with :)
                lines = para.strip().split('\n')
                for line in lines:
                    if line.strip().endswith(':') and len(line) < 60:
                        self.console.print(f"[bold cyan]{line}[/bold cyan]")
                    elif line.strip().startswith('-') or line.strip().startswith('*'):
                        self.console.print(f"  [dim]•[/dim] {line.strip()[1:].strip()}")
                    elif re.match(r'^\d+\.', line.strip()):
                        self.console.print(f"  {line.strip()}")
                    else:
                        self.console.print(line)

            if i < len(paragraphs) - 1:
                self.console.print()

    def _format_artifacts(self, artifacts: Dict[str, Any]) -> None:
        """Format and display artifacts."""
        self.console.print()
        self.console.print("[bold yellow]Artifacts:[/bold yellow]")

        for key, value in artifacts.items():
            if isinstance(value, dict):
                tree = Tree(f"[cyan]{key}[/cyan]")
                self._add_dict_to_tree(tree, value)
                self.console.print(tree)
            elif isinstance(value, list):
                self.console.print(f"  [cyan]{key}:[/cyan]")
                for item in value[:10]:  # Limit to 10 items
                    self.console.print(f"    • {item}")
                if len(value) > 10:
                    self.console.print(f"    [dim]... and {len(value) - 10} more[/dim]")
            else:
                self.console.print(f"  [cyan]{key}:[/cyan] {value}")

    def _add_dict_to_tree(self, tree: Tree, data: Dict[str, Any], max_depth: int = 3, current_depth: int = 0) -> None:
        """Recursively add dictionary items to a tree."""
        if current_depth >= max_depth:
            tree.add("[dim]...[/dim]")
            return

        for key, value in data.items():
            if isinstance(value, dict):
                branch = tree.add(f"[cyan]{key}[/cyan]")
                self._add_dict_to_tree(branch, value, max_depth, current_depth + 1)
            elif isinstance(value, list):
                branch = tree.add(f"[cyan]{key}[/cyan] ({len(value)} items)")
                for item in value[:5]:
                    branch.add(str(item))
                if len(value) > 5:
                    branch.add(f"[dim]... and {len(value) - 5} more[/dim]")
            else:
                tree.add(f"[cyan]{key}:[/cyan] {value}")

    def _format_tool_calls_summary(self, tool_calls: List[Dict[str, Any]]) -> None:
        """Format a summary of tool calls made during execution."""
        self.console.print()
        self.console.print("[bold yellow]Tool Calls:[/bold yellow]")

        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Tool", style="cyan")
        table.add_column("Result", style="green")

        for i, tc in enumerate(tool_calls[:20], 1):  # Limit to 20 calls
            tool_name = tc.get("tool", "unknown")
            result = tc.get("result", "")
            # Truncate result for display
            result_preview = str(result)[:50] + "..." if len(str(result)) > 50 else str(result)
            table.add_row(str(i), tool_name, result_preview)

        self.console.print(table)

        if len(tool_calls) > 20:
            self.console.print(f"[dim]... and {len(tool_calls) - 20} more tool calls[/dim]")

    def format_workflow_start(
        self,
        phases: List[str],
        description: Optional[str] = None,
    ) -> None:
        """Display workflow start banner."""
        content = Text()
        content.append("Phases: ", style="dim")
        content.append(" → ".join(phases), style="cyan")
        if description:
            content.append(f"\n\n{description}", style="italic")

        self.console.print(Panel(
            content,
            title="[bold blue]DSDM Workflow[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        ))

    def format_workflow_summary(
        self,
        results: Dict[str, Any],
    ) -> None:
        """Display workflow completion summary."""
        self.console.print()
        self.console.print(Rule("[bold]Workflow Summary[/bold]", style="blue"))
        self.console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Phase", style="cyan")
        table.add_column("Status")
        table.add_column("Summary")

        for phase_name, result in results.items():
            if hasattr(result, 'success'):
                status = "[green]✓ Success[/green]" if result.success else "[red]✗ Failed[/red]"
                summary = result.output[:80] + "..." if len(result.output) > 80 else result.output
                # Clean up summary for table display
                summary = summary.replace('\n', ' ').strip()
            else:
                status = "[yellow]? Unknown[/yellow]"
                summary = str(result)[:80]

            table.add_row(
                phase_name.replace("_", " ").title() if isinstance(phase_name, str) else str(phase_name),
                status,
                summary,
            )

        self.console.print(table)
        self.console.print()

    def format_team_start(
        self,
        team_name: str,
        roles: List[str],
    ) -> None:
        """Display team execution start banner."""
        content = Text()
        content.append("Roles: ", style="dim")
        content.append(" → ".join(roles), style="cyan")

        self.console.print(Panel(
            content,
            title=f"[bold magenta]{team_name}[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        ))

    def format_error(self, message: str, details: Optional[str] = None) -> None:
        """Display error message."""
        content = Text()
        content.append(message, style="bold red")
        if details:
            content.append(f"\n\n{details}", style="dim")

        self.console.print(Panel(
            content,
            title="[bold red]Error[/bold red]",
            border_style="red",
            padding=(1, 2),
        ))

    def format_warning(self, message: str) -> None:
        """Display warning message."""
        self.console.print(f"[yellow]⚠ {message}[/yellow]")

    def format_info(self, message: str) -> None:
        """Display info message."""
        self.console.print(f"[blue]ℹ {message}[/blue]")

    def format_progress(self, current: int, total: int, description: str) -> None:
        """Display progress indicator."""
        self.console.print(f"[dim][{current}/{total}][/dim] {description}")


# Global formatter instance
_formatter: Optional[OutputFormatter] = None


def get_formatter(console: Optional[Console] = None) -> OutputFormatter:
    """Get or create global output formatter."""
    global _formatter
    if _formatter is None or console is not None:
        _formatter = OutputFormatter(console)
    return _formatter
