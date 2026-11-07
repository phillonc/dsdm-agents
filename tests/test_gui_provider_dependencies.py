"""Provider-specific Python dependency readiness checks."""

from src.gui import diagnostics


def test_openai_does_not_require_anthropic(monkeypatch):
    original_import = diagnostics.importlib.import_module

    def import_without_anthropic(name):
        if name == "anthropic":
            raise ImportError("Anthropic SDK is not installed")
        return original_import(name)

    monkeypatch.setattr(diagnostics.importlib, "import_module", import_without_anthropic)
    check = diagnostics._dependency_check({"id": "openai"}, "legacy")
    assert check["status"] == "ok"


def test_ollama_does_not_require_anthropic(monkeypatch):
    original_import = diagnostics.importlib.import_module

    def import_without_anthropic(name):
        if name == "anthropic":
            raise ImportError("Anthropic SDK is not installed")
        return original_import(name)

    monkeypatch.setattr(diagnostics.importlib, "import_module", import_without_anthropic)
    assert diagnostics._dependency_check({"id": "ollama"}, "legacy")["status"] == "ok"


def test_anthropic_requires_its_sdk_for_builtin_runtime(monkeypatch):
    original_import = diagnostics.importlib.import_module

    def import_without_anthropic(name):
        if name == "anthropic":
            raise ImportError("Anthropic SDK is not installed")
        return original_import(name)

    monkeypatch.setattr(diagnostics.importlib, "import_module", import_without_anthropic)
    check = diagnostics._dependency_check({"id": "anthropic"}, "legacy")
    assert check["status"] == "error"
    assert "anthropic" in check["detail"]


def test_pi_runtime_does_not_require_python_anthropic_sdk(monkeypatch):
    original_import = diagnostics.importlib.import_module

    def import_without_anthropic(name):
        if name == "anthropic":
            raise ImportError("Anthropic SDK is not installed")
        return original_import(name)

    monkeypatch.setattr(diagnostics.importlib, "import_module", import_without_anthropic)
    assert diagnostics._dependency_check({"id": "anthropic"}, "pi")["status"] == "ok"
