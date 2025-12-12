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
    overwrite: bool = True,
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
    max_items: int = 500,
) -> str:
    """List contents of a directory.

    Excludes common large directories like venv, node_modules, __pycache__ etc.
    to prevent massive outputs.
    """
    # Directories to skip when listing recursively
    SKIP_DIRS = {
        'venv', '.venv', 'env', '.env', 'virtualenv',
        'node_modules', '.npm', '.pnpm-store',
        '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
        '.git', '.svn', '.hg',
        'dist', 'build', '.tox', '.nox', '.eggs', '*.egg-info',
        '.idea', '.vscode', '.vs',
        'htmlcov', '.coverage',
    }

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

        items = []
        truncated = False

        if recursive:
            def should_skip(path: Path) -> bool:
                """Check if path should be skipped."""
                return any(
                    part in SKIP_DIRS or part.endswith('.egg-info')
                    for part in path.parts
                )

            for item in full_path.rglob("*"):
                if len(items) >= max_items:
                    truncated = True
                    break

                rel_path = item.relative_to(full_path)

                # Skip excluded directories
                if should_skip(rel_path):
                    continue

                items.append({
                    "path": str(rel_path),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
        else:
            for item in full_path.iterdir():
                if len(items) >= max_items:
                    truncated = True
                    break

                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })

        result = {
            "success": True,
            "dir_path": str(full_path),
            "items": items,
            "count": len(items),
        }

        if truncated:
            result["truncated"] = True
            result["message"] = f"Output truncated at {max_items} items. Use more specific paths to see more."
            result["excluded_dirs"] = list(SKIP_DIRS)

        return json.dumps(result)
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


def list_projects_handler(
    output_dir: Optional[str] = None,
    include_all: bool = False,
) -> str:
    """List all existing projects in the generated directory.

    Args:
        output_dir: Base directory to search (default: 'generated')
        include_all: If True, include all directories. If False, only include
                     directories that look like DSDM projects (have src/, tests/,
                     docs/, or project config files).
    """
    try:
        base_path = Path(output_dir or DEFAULT_OUTPUT_DIR)

        if not base_path.exists():
            return json.dumps({
                "success": True,
                "projects": [],
                "count": 0,
                "message": "Generated directory does not exist yet. No projects found."
            })

        projects = []
        for item in base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check for common project indicators
                has_pyproject = (item / "pyproject.toml").exists()
                has_package_json = (item / "package.json").exists()
                has_requirements = (item / "requirements.txt").exists()
                has_src = (item / "src").exists()
                has_tests = (item / "tests").exists()
                has_docs = (item / "docs").exists()
                has_readme = (item / "README.md").exists() or (item / "readme.md").exists()

                # Determine project type
                if has_pyproject or has_requirements:
                    project_type = "python"
                elif has_package_json:
                    project_type = "node"
                else:
                    project_type = "unknown"

                # Determine if this looks like a valid project
                # A valid project should have at least one of: project config, src dir, tests dir
                is_valid_project = any([
                    has_pyproject,
                    has_package_json,
                    has_requirements,
                    has_src and (has_tests or has_docs or has_readme),
                ])

                # Skip non-project directories unless include_all is True
                if not include_all and not is_valid_project:
                    continue

                # Get project metadata
                project_info = {
                    "name": item.name,
                    "path": str(item),
                    "absolute_path": str(item.absolute()),
                    "type": project_type,
                    "has_docs": has_docs,
                    "has_tests": has_tests,
                    "has_src": has_src,
                    "is_valid_project": is_valid_project,
                }

                # Get last modified time
                project_info["last_modified"] = datetime.fromtimestamp(
                    item.stat().st_mtime
                ).isoformat()

                projects.append(project_info)

        # Sort by last modified (most recent first)
        projects.sort(key=lambda x: x["last_modified"], reverse=True)

        return json.dumps({
            "success": True,
            "projects": projects,
            "count": len(projects),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


def get_project_handler(
    project_name: str,
    output_dir: Optional[str] = None,
) -> str:
    """Get details of a specific project if it exists."""
    try:
        base_path = Path(output_dir or DEFAULT_OUTPUT_DIR) / project_name

        if not base_path.exists():
            return json.dumps({
                "success": False,
                "exists": False,
                "project_name": project_name,
                "message": f"Project '{project_name}' does not exist in {output_dir or DEFAULT_OUTPUT_DIR}/"
            })

        if not base_path.is_dir():
            return json.dumps({
                "success": False,
                "exists": False,
                "project_name": project_name,
                "error": f"'{project_name}' exists but is not a directory"
            })

        # Gather project details
        project_info = {
            "name": project_name,
            "path": str(base_path),
            "absolute_path": str(base_path.absolute()),
            "exists": True,
        }

        # Determine project type
        if (base_path / "pyproject.toml").exists():
            project_info["type"] = "python"
        elif (base_path / "package.json").exists():
            project_info["type"] = "node"
        else:
            project_info["type"] = "unknown"

        # List top-level structure
        project_info["structure"] = {
            "has_src": (base_path / "src").exists(),
            "has_tests": (base_path / "tests").exists(),
            "has_docs": (base_path / "docs").exists(),
            "has_config": (base_path / "config").exists(),
            "has_infrastructure": (base_path / "infrastructure").exists(),
        }

        # Get file counts
        file_count = 0
        dir_count = 0
        for item in base_path.rglob("*"):
            if item.is_file():
                file_count += 1
            elif item.is_dir():
                dir_count += 1

        project_info["file_count"] = file_count
        project_info["directory_count"] = dir_count
        project_info["last_modified"] = datetime.fromtimestamp(
            base_path.stat().st_mtime
        ).isoformat()

        return json.dumps({
            "success": True,
            "exists": True,
            "project": project_info,
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "project_name": project_name,
        })


def project_exists(project_name: str, output_dir: Optional[str] = None) -> bool:
    """Check if a project already exists (helper function)."""
    base_path = Path(output_dir or DEFAULT_OUTPUT_DIR) / project_name
    return base_path.exists() and base_path.is_dir()


def init_project_handler(
    project_name: str,
    project_type: str = "python",
    include_tests: bool = True,
    include_docs: bool = True,
    include_config: bool = True,
    include_infrastructure: bool = False,
    force_recreate: bool = False,
) -> str:
    """Initialize a new project with standard directory structure.

    First checks if the project already exists in the generated directory.
    If it exists and force_recreate is False, returns the existing project info.
    """
    try:
        base_path = Path(DEFAULT_OUTPUT_DIR) / project_name

        # Check if project already exists
        if base_path.exists() and base_path.is_dir():
            if not force_recreate:
                # Return existing project info instead of recreating
                existing_info = json.loads(get_project_handler(project_name))
                return json.dumps({
                    "success": True,
                    "already_exists": True,
                    "project_name": project_name,
                    "base_path": str(base_path),
                    "absolute_path": str(base_path.absolute()),
                    "message": f"Project '{project_name}' already exists. Use force_recreate=True to reinitialize.",
                    "existing_project": existing_info.get("project", {}),
                })
            else:
                # force_recreate is True - we'll continue to recreate/update the project
                pass

        # Define directory structure based on project type
        directories = ["src"]

        if include_tests:
            directories.extend(["tests/unit", "tests/integration"])

        if include_docs:
            directories.extend(["docs/api", "docs/architecture", "docs/user-guides"])

        if include_config:
            directories.append("config")

        if include_infrastructure:
            directories.extend([
                "infrastructure/docker",
                "infrastructure/kubernetes",
                "infrastructure/terraform",
            ])

        # Create all directories
        created_dirs = []
        for dir_path in directories:
            full_path = base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(full_path.relative_to(Path(DEFAULT_OUTPUT_DIR))))

        # Create base files based on project type
        files_created = []

        # README.md
        readme_content = f"""# {project_name}

## Overview

This project was generated by DSDM Agents.

## Project Structure

```
{project_name}/
├── src/                    # Application source code
{"├── tests/                  # Test suites" if include_tests else ""}
{"│   ├── unit/              # Unit tests" if include_tests else ""}
{"│   └── integration/       # Integration tests" if include_tests else ""}
{"├── docs/                   # Documentation" if include_docs else ""}
{"├── config/                 # Configuration files" if include_config else ""}
{"└── infrastructure/        # Infrastructure as Code" if include_infrastructure else ""}
```

## Getting Started

[Add getting started instructions here]

## Development

[Add development instructions here]

## Testing

[Add testing instructions here]

## License

[Add license information here]
"""
        readme_path = base_path / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        files_created.append(f"{project_name}/README.md")

        # .gitignore
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local

# Testing
.coverage
htmlcov/
.pytest_cache/

# Build artifacts
*.log
"""
        gitignore_path = base_path / ".gitignore"
        gitignore_path.write_text(gitignore_content, encoding="utf-8")
        files_created.append(f"{project_name}/.gitignore")

        # Project-type specific files
        if project_type == "python":
            # requirements.txt
            requirements_path = base_path / "requirements.txt"
            requirements_path.write_text("# Project dependencies\n", encoding="utf-8")
            files_created.append(f"{project_name}/requirements.txt")

            # setup.py or pyproject.toml
            pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "Project generated by DSDM Agents"
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
'''
            pyproject_path = base_path / "pyproject.toml"
            pyproject_path.write_text(pyproject_content, encoding="utf-8")
            files_created.append(f"{project_name}/pyproject.toml")

            # src/__init__.py
            init_path = base_path / "src" / "__init__.py"
            init_path.write_text(f'"""{project_name} package."""\n', encoding="utf-8")
            files_created.append(f"{project_name}/src/__init__.py")

            if include_tests:
                # tests/__init__.py
                test_init_path = base_path / "tests" / "__init__.py"
                test_init_path.write_text('"""Test suite."""\n', encoding="utf-8")
                files_created.append(f"{project_name}/tests/__init__.py")

        elif project_type == "node":
            # package.json
            package_json = f'''{{
  "name": "{project_name}",
  "version": "0.1.0",
  "description": "Project generated by DSDM Agents",
  "main": "src/index.js",
  "scripts": {{
    "start": "node src/index.js",
    "test": "jest",
    "lint": "eslint src/"
  }},
  "dependencies": {{}},
  "devDependencies": {{}}
}}
'''
            package_path = base_path / "package.json"
            package_path.write_text(package_json, encoding="utf-8")
            files_created.append(f"{project_name}/package.json")

        return json.dumps({
            "success": True,
            "project_name": project_name,
            "project_type": project_type,
            "base_path": str(base_path),
            "absolute_path": str(base_path.absolute()),
            "directories_created": created_dirs,
            "files_created": files_created,
            "created_at": datetime.now().isoformat(),
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "project_name": project_name,
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
                    "description": "Whether to overwrite existing files (default: true)"
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

    # Project management tools
    registry.register(Tool(
        name="project_list",
        description="List all existing projects in the generated/ directory. Use this FIRST to check what projects already exist before creating a new one. Only shows valid projects (with src/, tests/, or project config files) by default.",
        input_schema={
            "type": "object",
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory to search (default: 'generated')"
                },
                "include_all": {
                    "type": "boolean",
                    "description": "Include all directories, not just valid projects (default: false)"
                }
            },
            "required": []
        },
        handler=list_projects_handler,
        category="file_operations"
    ))

    registry.register(Tool(
        name="project_get",
        description="Get details of a specific project if it exists in the generated/ directory. Returns project structure, file counts, and metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project to look up"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Base output directory (default: 'generated')"
                }
            },
            "required": ["project_name"]
        },
        handler=get_project_handler,
        category="file_operations"
    ))

    registry.register(Tool(
        name="project_init",
        description="Initialize a new project with standard directory structure under generated/<project_name>/. IMPORTANT: First checks if project already exists - if so, returns existing project info unless force_recreate=True. Creates src/, tests/, docs/, config/, and optional infrastructure/ directories with base files.",
        input_schema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project (will be used as directory name)"
                },
                "project_type": {
                    "type": "string",
                    "enum": ["python", "node"],
                    "description": "Type of project (default: 'python')"
                },
                "include_tests": {
                    "type": "boolean",
                    "description": "Include tests/ directory structure (default: true)"
                },
                "include_docs": {
                    "type": "boolean",
                    "description": "Include docs/ directory structure (default: true)"
                },
                "include_config": {
                    "type": "boolean",
                    "description": "Include config/ directory (default: true)"
                },
                "include_infrastructure": {
                    "type": "boolean",
                    "description": "Include infrastructure/ directory for IaC (default: false)"
                },
                "force_recreate": {
                    "type": "boolean",
                    "description": "Force reinitialize even if project exists (default: false). If false and project exists, returns existing project info."
                }
            },
            "required": ["project_name"]
        },
        handler=init_project_handler,
        requires_approval=True,
        category="file_operations"
    ))
