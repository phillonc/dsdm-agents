"""DSDM Agents Console - a browser GUI for people who would rather not use the CLI.

The console is intentionally dependency-free: it is built on Python's standard
library `http.server` plus plain HTML/CSS/JS, so `python main.py --gui` works
with nothing installed beyond `requirements.txt`. Everything it does maps onto
an existing CLI capability - it drives the same `DSDMOrchestrator`, the same
delivery rooms, and the same `generated/` artefacts.
"""

from .server import ConsoleServer, create_server, serve

__all__ = ["ConsoleServer", "create_server", "serve"]
