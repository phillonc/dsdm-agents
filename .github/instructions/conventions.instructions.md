---
applyTo: "**"
description: Repo-wide coding and documentation conventions every agent must follow.
---

# Repository Conventions

## Python (`src/`, `tests/`, `main.py`)

### Style
- Python 3.10+
- 4-space indent, no tabs
- Type hints on all public functions
- Docstrings: short, one-line for simple functions; sectioned for complex
- Prefer `dataclasses` / `pydantic` over plain dicts for structured data
- Async-first for I/O; never block the event loop

### Linting
- `ruff 0.1.7` is the source of truth
- `pylint 2.16.2` and `flake8 7.0.0` available for deeper checks
- `pre-commit` hooks expected on contributors' machines

### Testing
- `pytest 9.0.1` with `pytest-asyncio 0.21.1` and `pytest-cov 4.1.0`
- Tests under `tests/`, mirror the `src/` layout
- ≥80% coverage on new code
- No flaky tests — quarantine and fix

## Markdown

- ATX headings (`#`, `##`, …)
- Tables for structured data
- Fenced code blocks with language hints
- Wrap long lines naturally; do not hard-wrap at 80 cols

## Generated artefacts

- Live exclusively under `generated/<project-slug>/`
- Each phase writes to the same project slug
- Standard subfolders: `src/`, `tests/`, `config/`, `docs/`, `prototypes/`, `infra/`

## Secrets

- Never commit `.env`, credentials, tokens, or keys
- Use `.env.example` as the template and document new vars there
- For runtime secrets in CI, use repository / organisation secrets

## Commits

- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`, `perf:`, `ci:`)
- Subject ≤ 72 chars, imperative mood
- Body explains *why*, not *what*

## Documentation

- Source-of-truth requirements live in `docs/`
- Per-project artefacts live in `generated/<project>/docs/`
- API docs as OpenAPI/Swagger (`generated/<project>/docs/api/openapi.yaml`)
- ADRs numbered sequentially under `generated/<project>/docs/architecture/decisions/`
