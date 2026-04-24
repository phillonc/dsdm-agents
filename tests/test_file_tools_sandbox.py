"""Path-sandbox tests for src.tools.file_tools.

These tests cover the security fix that prevents an LLM-controlled tool call
from reading or writing outside the generated/ sandbox root.
"""

import json
from pathlib import Path

import pytest

from src.tools import file_tools
from src.tools.file_tools import (
    PathSandboxError,
    append_file_handler,
    copy_file_handler,
    create_directory_handler,
    delete_file_handler,
    get_output_path,
    read_file_handler,
    write_file_handler,
)


@pytest.fixture(autouse=True)
def _sandbox_root(tmp_path, monkeypatch):
    """Point every test's sandbox at a fresh tmp directory."""
    root = tmp_path / "generated"
    root.mkdir()
    monkeypatch.setattr(file_tools, "DEFAULT_OUTPUT_DIR", str(root))
    return root


def _result(handler_output: str) -> dict:
    return json.loads(handler_output)


# --- get_output_path ------------------------------------------------------


def test_get_output_path_rejects_absolute():
    with pytest.raises(PathSandboxError):
        get_output_path("/etc/passwd")


def test_get_output_path_rejects_traversal():
    with pytest.raises(PathSandboxError):
        get_output_path("../../etc/passwd")


def test_get_output_path_rejects_empty():
    with pytest.raises(PathSandboxError):
        get_output_path("")


def test_get_output_path_stays_inside_root(_sandbox_root):
    resolved = get_output_path("foo/bar.txt")
    assert str(resolved).startswith(str(_sandbox_root.resolve()))


# --- write_file_handler ---------------------------------------------------


def test_write_file_ok(_sandbox_root):
    result = _result(write_file_handler("src/a.txt", "hello"))
    assert result["success"] is True
    assert (_sandbox_root / "src" / "a.txt").read_text() == "hello"


def test_write_file_blocks_traversal(_sandbox_root):
    result = _result(write_file_handler("../escape.txt", "pwned"))
    assert result["success"] is False
    assert "sandbox" in result["error"].lower()
    assert not (_sandbox_root.parent / "escape.txt").exists()


def test_write_file_blocks_absolute(_sandbox_root, tmp_path):
    target = tmp_path / "abs.txt"
    result = _result(write_file_handler(str(target), "pwned"))
    assert result["success"] is False
    assert not target.exists()


def test_write_file_respects_overwrite_false(_sandbox_root):
    write_file_handler("a.txt", "v1")
    result = _result(write_file_handler("a.txt", "v2", overwrite=False))
    assert result["success"] is False
    assert (_sandbox_root / "a.txt").read_text() == "v1"


# --- read_file_handler ---------------------------------------------------


def test_read_file_ok(_sandbox_root):
    (_sandbox_root / "note.txt").write_text("payload")
    result = _result(read_file_handler("note.txt"))
    assert result["success"] is True
    assert result["content"] == "payload"


def test_read_file_blocks_traversal(_sandbox_root, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("topsecret")
    # ../secret.txt should not escape the sandbox
    result = _result(read_file_handler("../secret.txt"))
    assert result["success"] is False
    assert "sandbox" in result["error"].lower() or "escape" in result["error"].lower()


def test_read_file_blocks_absolute(_sandbox_root):
    result = _result(read_file_handler("/etc/passwd"))
    assert result["success"] is False


# --- delete / append / copy / directory ----------------------------------


def test_delete_blocks_traversal(_sandbox_root, tmp_path):
    target = tmp_path / "do_not_delete.txt"
    target.write_text("keep")
    result = _result(delete_file_handler("../do_not_delete.txt"))
    assert result["success"] is False
    assert target.exists()


def test_append_blocks_traversal():
    result = _result(append_file_handler("../evil.txt", "pwn"))
    assert result["success"] is False


def test_copy_blocks_traversal(_sandbox_root, tmp_path):
    (_sandbox_root / "ok.txt").write_text("ok")
    result = _result(copy_file_handler("ok.txt", "../leaked.txt"))
    assert result["success"] is False
    assert not (tmp_path / "leaked.txt").exists()


def test_create_directory_blocks_traversal(_sandbox_root, tmp_path):
    result = _result(create_directory_handler("../evil_dir"))
    assert result["success"] is False
    assert not (tmp_path / "evil_dir").exists()
