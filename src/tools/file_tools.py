"""File operation tools for DSDM Agents.

Provides actual file writing capabilities so agents can persist generated code to disk.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .tool_registry import Tool, ToolRegistry


# Default output directory for generated code
DEFAULT_OUTPUT_DIR = "generated"


def get_output_path(base_path: str, output_dir: Optional[str] = None) -> Path:
    """Get the full output path, creating directories if needed."""
    output_base = output_dir or DEFAULT_OUTPUT_DIR
    full_path = Path(output_base) / base_path
    return full_path


def write_file_handler(
    file_path: str,
    content: str,
    output_dir: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """Write content to a file in the output directory."""
    try:
        full_path = get_output_path(file_path, output_dir)

        # Check if file exists and overwrite is not allowed
        if full_path.exists() and not overwrite:
            return json.dumps({
                "success": False,
                "error": f"File already exists: {full_path}. Set overwrite=True to replace.",
                "file_path": str(full_path),
            })

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        full_path.write_text(content, encoding="utf-8")

        return json.dumps({
            "success": True,
            "file_path": str(full_path),
            "absolute_path": str(full_path.absolute()),
            "size_bytes": len(content.encode("utf-8")),
            "lines": len(content.splitlines()),
            "created_at": datetime.now().isoformat(),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "file_path": file_path,
        })


def read_file_handler(file_path: str, output_dir: Optional[str] = None) -> str:
    """Read content from a file."""
    try:
        # First check if it's an absolute path or exists as-is
        path = Path(file_path)
        if not path.exists():
            # Try in output directory
            path = get_output_path(file_path, output_dir)

        if not path.exists():
            return json.dumps({
                "success": False,
                "error": f"File not found: {file_path}",
            })

        content = path.read_text(encoding="utf-8")

        return json.dumps({
            "success": True,
            "file_path": str(path),
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
            "lines": len(content.splitlines()),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "file_path": file_path,
        })


def create_directory_handler(
    dir_path: str,
    output_dir: Optional[str] = None,
) -> str:
    """Create a directory in the output directory."""
    try:
        full_path = get_output_path(dir_path, output_dir)
        full_path.mkdir(parents=True, exist_ok=True)

        return json.dumps({
            "success": True,
            "dir_path": str(full_path),
            "absolute_path": str(full_path.absolute()),
            "created_at": datetime.now().isoformat(),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "dir_path": dir_path,
        })


def list_directory_handler(
    dir_path: str = "",
    output_dir: Optional[str] = None,
    recursive: bool = False,
) -> str:
    """List contents of a directory."""
    try:
        full_path = get_output_path(dir_path, output_dir) if dir_path else Path(output_dir or DEFAULT_OUTPUT_DIR)

        if not full_path.exists():
            return json.dumps({
                "success": False,
                "error": f"Directory not found: {full_path}",
            })

        if not full_path.is_dir():
            return json.dumps({
                "success": False,
                "error": f"Not a directory: {full_path}",
            })

        if recursive:
            items = []
            for item in full_path.rglob("*"):
                rel_path = item.relative_to(full_path)
                items.append({
                    "path": str(rel_path),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
        else:
            items = []
            for item in full_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })

        return json.dumps({
            "success": True,
            "dir_path": str(full_path),
            "items": items,
            "count": len(items),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "dir_path": dir_path,
        })


def delete_file_handler(file_path: str, output_dir: Optional[str] = None) -> str:
    """Delete a file from the output directory."""
    try:
        full_path = get_output_path(file_path, output_dir)

        if not full_path.exists():
            return json.dumps({
                "success": False,
                "error": f"File not found: {full_path}",
            })

        if full_path.is_dir():
            return json.dumps({
                "success": False,
                "error": f"Path is a directory, use delete_directory instead: {full_path}",
            })

        full_path.unlink()

        return json.dumps({
            "success": True,
            "file_path": str(full_path),
            "deleted_at": datetime.now().isoformat(),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "file_path": file_path,
        })


def append_file_handler(
    file_path: str,
    content: str,
    output_dir: Optional[str] = None,
) -> str:
    """Append content to a file."""
    try:
        full_path = get_output_path(file_path, output_dir)

        # Create parent directories if file doesn't exist
        if not full_path.exists():
            full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "a", encoding="utf-8") as f:
            f.write(content)

        # Get updated file info
        file_content = full_path.read_text(encoding="utf-8")

        return json.dumps({
            "success": True,
            "file_path": str(full_path),
            "appended_bytes": len(content.encode("utf-8")),
            "total_size_bytes": len(file_content.encode("utf-8")),
            "total_lines": len(file_content.splitlines()),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "file_path": file_path,
        })


def copy_file_handler(
    source_path: str,
    dest_path: str,
    output_dir: Optional[str] = None,
) -> str:
    """Copy a file within the output directory."""
    try:
        source = get_output_path(source_path, output_dir)
        dest = get_output_path(dest_path, output_dir)

        if not source.exists():
            return json.dumps({
                "success": False,
                "error": f"Source file not found: {source}",
            })

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

        return json.dumps({
            "success": True,
            "source_path": str(source),
            "dest_path": str(dest),
            "size_bytes": dest.stat().st_size,
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


def register_file_tools(registry: ToolRegistry) -> None:
    """Register file operation tools with the registry."""

    registry.register(Tool(
        name="file_write",
        description="Write content to a file in the generated code directory. Creates parent directories automatically.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path for the file (e.g., 'src/components/Button.tsx')"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether to overwrite existing files (default: false)"
                }
            },
            "required": ["file_path", "content"]
        },
        handler=write_file_handler,
        requires_approval=True,
        category="file_operations"
    ))

    registry.register(Tool(
        name="file_read",
        description="Read content from a file in the generated code directory or any accessible path.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory to search in (default: 'generated')"
                }
            },
            "required": ["file_path"]
        },
        handler=read_file_handler,
        category="file_operations"
    ))

    registry.register(Tool(
        name="directory_create",
        description="Create a directory in the generated code directory.",
        input_schema={
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "Relative path for the directory (e.g., 'src/components')"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                }
            },
            "required": ["dir_path"]
        },
        handler=create_directory_handler,
        requires_approval=True,
        category="file_operations"
    ))

    registry.register(Tool(
        name="directory_list",
        description="List contents of a directory in the generated code directory.",
        input_schema={
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "Relative path to the directory (empty for root)"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively (default: false)"
                }
            },
            "required": []
        },
        handler=list_directory_handler,
        category="file_operations"
    ))

    registry.register(Tool(
        name="file_delete",
        description="Delete a file from the generated code directory.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file to delete"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                }
            },
            "required": ["file_path"]
        },
        handler=delete_file_handler,
        requires_approval=True,
        category="file_operations"
    ))

    registry.register(Tool(
        name="file_append",
        description="Append content to a file in the generated code directory.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to append"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                }
            },
            "required": ["file_path", "content"]
        },
        handler=append_file_handler,
        requires_approval=True,
        category="file_operations"
    ))

    registry.register(Tool(
        name="file_copy",
        description="Copy a file within the generated code directory.",
        input_schema={
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Source file path"
                },
                "dest_path": {
                    "type": "string",
                    "description": "Destination file path"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                }
            },
            "required": ["source_path", "dest_path"]
        },
        handler=copy_file_handler,
        requires_approval=True,
        category="file_operations"
    ))
