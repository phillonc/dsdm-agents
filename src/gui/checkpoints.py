"""Restore points: undoing a stage's effect on `generated/`.

Stopping a run halts the agents but leaves whatever they already wrote on disk.
To step back through the process a user needs the *documents* to move back too,
so the console takes a restore point immediately before each stage runs and can
put the workspace back the way it was.

Three rules keep a destructive operation safe:

1. **Only what the console touched.** A restore point records the project
   folders the console has written to (its "owned" folders). Restoring replaces
   exactly those and deletes any created after the restore point. Every other
   project under `generated/` is left alone, even if something else changed it
   in the meantime.
2. **Nothing outside `generated/`.** Every path is resolved and checked against
   the workspace root before it is written to or deleted.
3. **Never silently partial.** Anything that changed but cannot be put back -
   because it was outside those folders when the restore point was taken - is
   reported as unrecoverable rather than quietly skipped.

The owned set is session-wide rather than per-run (see `RunManager.session_scope`):
run 2 routinely builds on run 1's documents, so a point taken during run 1 has
to be able to undo run 2 as well.

Restore points live under `.dsdm-console/checkpoints/`, outside `generated/`,
so they never appear in the document browser. They are per-process: runs live
in memory, so the store is purged when the console starts.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .workspace import generated_root

CHECKPOINT_ROOT = Path(".dsdm-console") / "checkpoints"

# A restore point copies files. Design & Build can emit a whole application, so
# there is a ceiling: past it the restore point records what changed but keeps
# no content, and says so instead of pretending it can undo the stage.
MAX_CHECKPOINT_BYTES = 250 * 1024 * 1024

# Paths listed in a preview before it starts summarising rather than listing.
MAX_LISTED_PATHS = 40


class CheckpointError(Exception):
    """Raised when a restore point cannot be created or applied."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def checkpoint_root() -> Path:
    """Absolute root of the restore-point store."""
    return CHECKPOINT_ROOT.resolve()


def purge_all() -> None:
    """Delete every stored restore point. Called when the console starts."""
    shutil.rmtree(checkpoint_root(), ignore_errors=True)


def discard_run(run_id: str) -> None:
    """Delete the restore points belonging to one run."""
    shutil.rmtree(checkpoint_root() / run_id, ignore_errors=True)


def _manifest(root: Path) -> Dict[str, Tuple[float, int]]:
    """Map every file under `root` to (mtime, size), relative to `root`."""
    manifest: Dict[str, Tuple[float, int]] = {}
    if not root.exists():
        return manifest
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        manifest[item.relative_to(root).as_posix()] = (stat.st_mtime, stat.st_size)
    return manifest


def _tree_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _is_owned(relative: str, owned: Iterable[str]) -> bool:
    return any(relative == name or relative.startswith(f"{name}/") for name in owned)


def _safe_target(name: str) -> Path:
    """Resolve `generated/<name>`, refusing anything that escapes the root."""
    root = generated_root()
    target = (root / name).resolve()
    if target == root or root not in target.parents:
        raise CheckpointError(f"Refusing to touch a path outside the workspace: {name}")
    return target


@dataclass
class Checkpoint:
    """One saved state of the run's own folders under `generated/`."""

    id: str
    run_id: str
    index: int  # position in the run's stage list; -1 for the pre-rollback safety copy
    label: str
    stage_id: Optional[str]
    created_at: str = field(default_factory=_now)
    owned: List[str] = field(default_factory=list)  # project folders saved here
    top_level: List[str] = field(default_factory=list)  # everything in generated/ at the time
    manifest: Dict[str, Tuple[float, int]] = field(default_factory=dict)
    file_count: int = 0
    size_bytes: int = 0
    skipped: bool = False
    reason: str = ""

    @property
    def content_dir(self) -> Path:
        return checkpoint_root() / self.run_id / self.id / "content"

    def to_dict(self, steps_back: Optional[int] = None) -> Dict[str, Any]:
        payload = {
            "id": self.id,
            "index": self.index,
            "label": self.label,
            "stageId": self.stage_id,
            "createdAt": self.created_at,
            "fileCount": self.file_count,
            "sizeBytes": self.size_bytes,
            "skipped": self.skipped,
            "reason": self.reason,
            "projects": list(self.owned),
        }
        if steps_back is not None:
            payload["stepsBack"] = steps_back
        return payload


def create(
    run_id: str,
    index: int,
    label: str,
    stage_id: Optional[str],
    owned: Iterable[str],
) -> Checkpoint:
    """Save the current state of the owned folders.

    `owned` is the set of project folders the console has written to so far. A
    folder that does not exist yet is still recorded: restoring to this point
    then means deleting whatever the rolled-back stages created.
    """
    root = generated_root()
    owned_list = sorted({name for name in owned if name})
    checkpoint = Checkpoint(
        id=f"cp-{index}" if index >= 0 else "undo",
        run_id=run_id,
        index=index,
        label=label,
        stage_id=stage_id,
        owned=owned_list,
        top_level=sorted(item.name for item in root.iterdir()) if root.exists() else [],
        manifest=_manifest(root),
    )

    existing = [(name, root / name) for name in owned_list if (root / name).is_dir()]
    total = sum(_tree_size(path) for _, path in existing)
    if total > MAX_CHECKPOINT_BYTES:
        checkpoint.skipped = True
        checkpoint.reason = (
            f"The project is larger than {MAX_CHECKPOINT_BYTES // (1024 * 1024)} MB, "
            "so no copy was kept. Stepping back past this point cannot restore its documents."
        )
        return checkpoint

    destination = checkpoint.content_dir
    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)
    try:
        for name, path in existing:
            shutil.copytree(path, destination / name, dirs_exist_ok=True)
    except OSError as exc:
        checkpoint.skipped = True
        checkpoint.reason = f"The documents could not be copied: {exc}"
        shutil.rmtree(destination, ignore_errors=True)
        return checkpoint

    checkpoint.size_bytes = total
    checkpoint.file_count = sum(1 for path in checkpoint.manifest if _is_owned(path, owned_list))

    meta = checkpoint.content_dir.parent / "meta.json"
    meta.write_text(
        json.dumps(
            {
                "id": checkpoint.id,
                "runId": run_id,
                "index": index,
                "label": label,
                "stageId": stage_id,
                "createdAt": checkpoint.created_at,
                "owned": owned_list,
                "topLevel": checkpoint.top_level,
                "fileCount": checkpoint.file_count,
                "sizeBytes": checkpoint.size_bytes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return checkpoint


def _plan(checkpoint: Checkpoint, owned_now: Iterable[str]) -> Dict[str, Any]:
    """Work out what restoring `checkpoint` would change, without changing it."""
    root = generated_root()
    owned_now = sorted({name for name in owned_now if name} | set(checkpoint.owned))
    current = _manifest(root)

    saved = set(checkpoint.owned)
    # Folders the run created after this restore point: they go away entirely.
    to_delete = [name for name in owned_now if name not in checkpoint.top_level and (root / name).is_dir()]
    delete_set = set(to_delete)

    remove: List[str] = []
    add_back: List[str] = []
    unrecoverable: List[str] = []

    for path in sorted(current):
        top = path.split("/", 1)[0]
        if top in delete_set:
            remove.append(path)
        elif top in saved and path not in checkpoint.manifest:
            remove.append(path)

    for path, stamp in sorted(checkpoint.manifest.items()):
        top = path.split("/", 1)[0]
        if current.get(path) == stamp:
            continue
        if top in saved and not checkpoint.skipped:
            add_back.append(path)
        elif top in delete_set:
            continue  # the whole folder is being removed; nothing to put back
        else:
            # Changed since the restore point, but no copy was kept for it.
            unrecoverable.append(path)

    return {
        "checkpointId": checkpoint.id,
        "label": checkpoint.label,
        "folders": {"replace": sorted(saved), "delete": sorted(to_delete)},
        "remove": remove,
        "restore": add_back,
        "unrecoverable": unrecoverable,
    }


def _summarise(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Trim the path lists so a browser is never handed thousands of entries."""
    summary = dict(plan)
    for key in ("remove", "restore", "unrecoverable"):
        paths = plan[key]
        summary[f"{key}Count"] = len(paths)
        summary[key] = paths[:MAX_LISTED_PATHS]
        summary[f"{key}Truncated"] = len(paths) > MAX_LISTED_PATHS
    return summary


def preview(checkpoint: Checkpoint, owned_now: Iterable[str]) -> Dict[str, Any]:
    """Describe what stepping back to `checkpoint` would do."""
    return _summarise(_plan(checkpoint, owned_now))


def restore(checkpoint: Checkpoint, owned_now: Iterable[str]) -> Dict[str, Any]:
    """Put the run's folders back to `checkpoint`. Returns what was changed."""
    if checkpoint.skipped:
        raise CheckpointError(checkpoint.reason or "No copy was kept for this restore point.")

    plan = _plan(checkpoint, owned_now)
    root = generated_root()

    for name in plan["folders"]["delete"]:
        target = _safe_target(name)
        shutil.rmtree(target, ignore_errors=True)

    for name in plan["folders"]["replace"]:
        target = _safe_target(name)
        saved = checkpoint.content_dir / name
        shutil.rmtree(target, ignore_errors=True)
        if saved.is_dir():
            shutil.copytree(saved, target)

    root.mkdir(parents=True, exist_ok=True)
    result = _summarise(plan)
    result["restoredAt"] = _now()
    return result


def load_owned_from_files(files: Iterable[str]) -> Set[str]:
    """Top-level project folders implied by a list of `generated/`-relative paths."""
    return {path.split("/", 1)[0] for path in files if path}
