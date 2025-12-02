# DevOps Tools Documentation

## Overview

The DevOps Tools module provides automated code quality validation, security scanning, and development lifecycle management for the DSDM Agents framework. All tools execute real commands on your local machine and provide actionable remediation recommendations.

**Version:** 1.0.0
**Last Updated:** December 2024
**Aligned With:** 14 Development Principles

---

## Table of Contents

1. [Installation](#installation)
2. [Tool Categories](#tool-categories)
3. [Available Tools](#available-tools)
4. [Remediation System](#remediation-system)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

The DevOps tools require the following packages to be installed:

```bash
# Install via pip
pip install -r requirements.txt
```

### Installed Tool Versions

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| **Testing** | pytest | 9.0.1 | Test framework |
| **Testing** | pytest-cov | 4.1.0 | Coverage reporting |
| **Testing** | pytest-asyncio | 0.21.1 | Async test support |
| **Linting** | ruff | 0.1.7 | Fast Python linter |
| **Linting** | pylint | 2.16.2 | Static code analyzer |
| **Linting** | flake8 | 7.0.0 | Style guide enforcement |
| **Security** | bandit | 1.9.2 | SAST scanner |
| **Security** | safety | 3.7.0 | Dependency checker |
| **Security** | pip-audit | 2.10.0 | CVE scanner |
| **Performance** | locust | 2.42.6 | Load testing |
| **Infrastructure** | Terraform | 1.5.7 | IaC provisioning |
| **Infrastructure** | Docker | 28.5.1 | Container management |
| **Accessibility** | pa11y | 9.0.1 | Accessibility testing |
| **Cryptography** | pyjwt[crypto] | 2.10.1 | JWT with cryptography |
| **Cryptography** | cryptography | 46.0.3 | Secure crypto operations |

### External Tools

Some tools require separate installation:

```bash
# Terraform (macOS)
brew install terraform

# Terraform (Linux)
sudo apt install terraform

# Docker
# Download from https://www.docker.com/products/docker-desktop/

# pa11y (requires Node.js)
npm install -g pa11y pa11y-ci
```

---

## Tool Categories

### Principle 2 & 3: Testing & Quality

- **run_tests** - Execute pytest with coverage
- **check_coverage** - Verify coverage meets threshold
- **run_linter** - Run ruff, pylint, or flake8
- **check_code_quality** - Analyze complexity, maintainability

### Principle 5 & 10: CI/CD & Automation

- **run_ci_pipeline** - Trigger CI pipeline
- **deploy_to_environment** - Deploy with strategy
- **rollback_deployment** - Rollback on failure
- **automate_task** - Create automation workflows

### Principle 6 & 8: Infrastructure

- **provision_infrastructure** - Provision cloud resources
- **validate_terraform** - Validate IaC configuration
- **manage_containers** - Docker operations
- **scale_service** - Scale service replicas

### Principle 4 & 11: Monitoring & Health

- **health_check** - Service health verification
- **setup_monitoring** - Configure alerting
- **check_service_status** - Status dashboard
- **run_chaos_test** - Chaos engineering

### Principle 7 & 12: NFRs & Dependencies

- **analyze_dependencies** - Dependency analysis
- **run_performance_test** - Load testing with locust
- **check_accessibility** - Accessibility audit
- **validate_nfr** - NFR validation

### Principle 1 & 3: Documentation

- **create_adr** - Architecture Decision Records
- **generate_docs** - Auto-generate documentation
- **track_decision** - Decision tracking

### Principle 14: Task Management

- **check_incomplete_tasks** - Find TODOs/FIXMEs
- **track_toil** - Track manual activities

### Principle 9: Backup & Recovery

- **backup_database** - Create backups
- **test_restore** - Test restore capability

---

## Available Tools

### run_tests

Execute the test suite with optional coverage reporting.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| test_type | string | Yes | "unit", "integration", "e2e", or "all" |
| coverage | boolean | No | Enable coverage collection (default: true) |
| path | string | No | Path to test files (default: ".") |

**Example:**
```python
result = tool_registry.execute(
    "run_tests",
    test_type="unit",
    coverage=True,
    path="src"
)
```

**Remediation Provided:**
- Failed test debugging commands
- Coverage improvement steps
- Test discovery troubleshooting

---

### run_linter

Run code linting with ruff, pylint, or flake8.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| linter | string | Yes | "ruff", "pylint", "flake8", or "eslint" |
| fix | boolean | No | Auto-fix issues (default: false) |
| path | string | No | Path to lint (default: ".") |

**Example:**
```python
result = tool_registry.execute(
    "run_linter",
    linter="ruff",
    fix=True,
    path="src"
)
```

**Remediation Provided:**
- Issue-specific fixes (E501, F401, F841, E302, W503, C901)
- Auto-fix commands for each error type
- Configuration recommendations

---

### run_security_scan

Run security vulnerability scanning.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scan_type | string | Yes | "dependency", "sast", "secrets", "container", or "all" |
| severity_threshold | string | No | "critical", "high", "medium", "low" |

**Example:**
```python
result = tool_registry.execute(
    "run_security_scan",
    scan_type="all",
    severity_threshold="high"
)
```

**Scans Performed:**
- **sast**: Bandit static analysis
- **dependency**: pip-audit CVE scanning
- **secrets**: Pattern-based secret detection

**Remediation Provided:**
- SAST fix patterns (B101, B105, B301, B602, B608)
- Vulnerable package upgrade commands
- Secret rotation and removal steps

---

### check_code_quality

Analyze code quality metrics.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| metrics | array | No | ["complexity", "duplication", "maintainability"] |
| path | string | No | Path to analyze (default: ".") |

**Example:**
```python
result = tool_registry.execute(
    "check_code_quality",
    metrics=["complexity", "maintainability"],
    path="src"
)
```

**Metrics Analyzed:**
- **Complexity**: Cyclomatic complexity via ruff C901
- **Duplication**: Basic detection (recommends jscpd)
- **Maintainability**: Pylint score analysis

**Remediation Provided:**
- Function refactoring strategies
- Pylint issue-specific fixes (R0913, R0914, R0912, etc.)
- Duplication analysis tool recommendations

---

### analyze_dependencies

Analyze project dependencies for issues.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| analysis_type | string | Yes | "outdated", "vulnerabilities", "unused", "licenses", or "all" |
| package_manager | string | No | "pip" or "npm" (default: "pip") |

**Example:**
```python
result = tool_registry.execute(
    "analyze_dependencies",
    analysis_type="all",
    package_manager="pip"
)
```

**Analysis Performed:**
- Package count and dependency tree
- Outdated package detection
- CVE vulnerability scanning
- License compatibility checking

**Remediation Provided:**
- Specific upgrade commands for each vulnerable package
- Major vs minor update categorization
- Dependency cleanup recommendations
- License audit commands

---

### validate_terraform

Validate Terraform configuration.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | No | Path to Terraform files (default: ".") |
| plan | boolean | No | Run terraform plan (default: false) |

**Example:**
```python
result = tool_registry.execute(
    "validate_terraform",
    path="infrastructure/terraform",
    plan=True
)
```

**Operations:**
- `terraform init -backend=false`
- `terraform validate -json`
- `terraform plan -no-color` (if plan=True)

---

### manage_containers

Manage Docker container operations.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | "build", "push", "pull", "run", "stop", "list" |
| image | string | No | Container image name |
| tag | string | No | Image tag (default: "latest") |

**Example:**
```python
result = tool_registry.execute(
    "manage_containers",
    action="build",
    image="myapp",
    tag="v1.0.0"
)
```

---

### check_accessibility

Run accessibility audit using pa11y.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | URL to audit |
| standard | string | No | "WCAG2A", "WCAG2AA", "WCAG2AAA" |

**Example:**
```python
result = tool_registry.execute(
    "check_accessibility",
    url="http://localhost:3000",
    standard="WCAG2AA"
)
```

---

## Remediation System

All major DevOps tools now include intelligent remediation recommendations. Each tool result contains a `remediation` object with:

```json
{
  "remediation": {
    "actions": [
      {
        "issue": "Description of the issue found",
        "severity": "critical|high|medium|low|info",
        "steps": [
          "Step 1 to resolve",
          "Step 2 to resolve",
          "..."
        ],
        "command": "Quick fix command if available"
      }
    ],
    "priority": "critical|high|medium|low",
    "estimated_effort": "minimal|moderate|significant"
  }
}
```

### Severity Levels

| Level | Description | Action Required |
|-------|-------------|-----------------|
| **critical** | Security vulnerabilities, data exposure | Immediate fix required |
| **high** | Failed tests, major quality issues | Fix before merge |
| **medium** | Code quality, complexity issues | Fix in current sprint |
| **low** | Style issues, minor improvements | Fix when convenient |
| **info** | Recommendations, best practices | Consider implementing |

### Example Remediation Output

```json
{
  "remediation": {
    "actions": [
      {
        "issue": "Security vulnerabilities: 3 CVEs found",
        "severity": "critical",
        "steps": [
          "Found 3 vulnerabilities in dependencies",
          "Run `pip-audit --fix` to automatically upgrade vulnerable packages",
          "If auto-fix fails for a package, manually upgrade:",
          "  - requests: `pip install --upgrade \"requests>=2.32.0\"`",
          "Run tests after upgrading to ensure compatibility",
          "Update requirements.txt with fixed versions"
        ],
        "command": "pip-audit --fix"
      }
    ],
    "priority": "critical",
    "estimated_effort": "moderate"
  }
}
```

---

## Usage Examples

### Full Quality Check Workflow

```python
from src.tools.tool_registry import ToolRegistry
from src.tools.integrations.devops_tools import register_devops_tools

# Initialize registry
registry = ToolRegistry()
register_devops_tools(registry)

# Run tests
test_result = registry.execute("run_tests", test_type="all", coverage=True)
print(f"Tests: {test_result}")

# Run linter
lint_result = registry.execute("run_linter", linter="ruff", path="src")
print(f"Linting: {lint_result}")

# Security scan
security_result = registry.execute("run_security_scan", scan_type="all")
print(f"Security: {security_result}")

# Code quality
quality_result = registry.execute("check_code_quality", path="src")
print(f"Quality: {quality_result}")

# Dependency analysis
deps_result = registry.execute("analyze_dependencies", analysis_type="all")
print(f"Dependencies: {deps_result}")
```

### Using with DevOps Agent

```python
from src.agents.devops_agent import DevOpsAgent
from src.tools.tool_registry import ToolRegistry
from src.tools.integrations.devops_tools import register_devops_tools

# Setup
registry = ToolRegistry()
register_devops_tools(registry)

# Create agent
agent = DevOpsAgent(tool_registry=registry)

# Run agent
result = await agent.run(
    "Please run a full security scan and provide remediation steps for any issues found."
)

print(result.output)
```

---

## Configuration

### Environment Variables

```env
# DevOps tool settings (optional)
DEVOPS_TEST_TIMEOUT=300
DEVOPS_LINT_TIMEOUT=120
DEVOPS_SECURITY_TIMEOUT=120

# For container operations
DOCKER_HOST=unix:///var/run/docker.sock

# For Terraform
TF_VAR_environment=dev
```

### Customizing Tool Behavior

Tools can be customized by modifying the handler parameters or extending the tool registry:

```python
# Register custom tool
registry.register(Tool(
    name="my_custom_scan",
    description="Custom security scan",
    input_schema={...},
    handler=my_custom_handler,
    category="devops"
))
```

---

## Troubleshooting

### Common Issues

#### Tests Not Found

```
Issue: No tests found or executed
Remediation:
1. Verify test files exist with pattern test_*.py or *_test.py
2. Check pytest configuration in pyproject.toml
3. Run `pytest --collect-only` to see discovered tests
```

#### Linter Command Not Found

```
Issue: ruff/pylint/flake8 not installed
Remediation:
pip install ruff pylint flake8
```

#### Security Scan Timeout

```
Issue: pip-audit times out
Remediation:
1. Check network connectivity
2. Increase timeout: DEVOPS_SECURITY_TIMEOUT=300
3. Run manually: pip-audit --progress-spinner=off
```

#### Docker Permission Denied

```
Issue: Cannot connect to Docker daemon
Remediation:
1. Ensure Docker Desktop is running
2. Check Docker socket permissions
3. On Linux: sudo usermod -aG docker $USER
```

#### Terraform Not Found

```
Issue: Terraform CLI not installed
Remediation:
# macOS
brew install terraform

# Linux
sudo apt install terraform

# Verify
terraform --version
```

---

## Development Principles Alignment

Each tool aligns with specific development principles:

| Principle | Tools |
|-----------|-------|
| 1. Decision Making Distributed | create_adr, track_decision |
| 2. If not tested, it's broken | run_tests, check_coverage |
| 3. Transparency dispels myth | run_linter, check_code_quality |
| 4. Mean Time To Innocence | health_check, check_service_status |
| 5. No Dead Cats | run_ci_pipeline, deploy_to_environment |
| 6. Cloud-first | provision_infrastructure |
| 7. NFRs first class | run_security_scan, run_performance_test, check_accessibility |
| 8. Cattle not Pets | validate_terraform, manage_containers |
| 9. Keep the Hostage | backup_database, test_restore |
| 10. Eliminate Toil | automate_task, track_toil |
| 11. Failure is Normal | rollback_deployment, run_chaos_test |
| 12. Dependencies = Latency | analyze_dependencies |
| 14. Stop Starting | check_incomplete_tasks |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Dec 2024 | Initial release with remediation system |

---

*This documentation is auto-synced to Confluence. For the latest version, see the repository.*
