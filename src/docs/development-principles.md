# LocalHighStreet Development Principles & VS Code/Cursor Extensions

This document outlines our core development principles and the VS Code/Cursor extensions that support each principle throughout the development lifecycle.

## Table of Contents
1. [Decision Making should be distributed](#1-decision-making-should-be-distributed)
2. [If it's not tested, it's broken](#2-if-its-not-tested-its-broken)
3. [Transparency dispels myth](#3-transparency-dispels-myth)
4. [Mean Time To Innocence (MTTI)](#4-mean-time-to-innocence-mtti)
5. [No Dead Cats over the fence](#5-no-dead-cats-over-the-fence)
6. [Friends would not let friends build data centres](#6-friends-would-not-let-friends-build-data-centres)
7. [Non Functional Requirements are first class citizens](#7-non-functional-requirements-are-first-class-citizens)
8. [Cattle not Pets](#8-cattle-not-pets)
9. [Keep the Hostage](#9-keep-the-hostage)
10. [Elimination of Toil, via automation](#10-elimination-of-toil-via-automation)
11. [Failure is Normal, but customer disruption is not](#11-failure-is-normal-but-customer-disruption-is-not)
12. [Dependencies create "latency as a service"](#12-dependencies-create-latency-as-a-service)
13. [Focus our efforts on differentiating code and infrastructure](#13-focus-our-efforts-on-differentiating-code-and-infrastructure)
14. [Stop Starting and Start Stopping / Completing tasks](#14-stop-starting-and-start-stopping--completing-tasks)

---

## 1. Decision Making should be distributed

**Principle**: The best decisions are generally made by those closest to the problem. We document all technical decisions openly with rationale.

### Supporting VS Code/Cursor Extensions:

- **[Conventional Commits](https://marketplace.visualstudio.com/items?itemName=vivaxy.vscode-conventional-commits)** - Standardize commit messages with decision rationale
- **[GitLens](https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens)** - Track who made decisions and why through git history
- **[Live Share](https://marketplace.visualstudio.com/items?itemName=MS-vsliveshare.vsliveshare)** - Enable real-time collaborative decision making
- **[ADR Tools](https://marketplace.visualstudio.com/items?itemName=vincent-ledu.adr-tools)** - Architecture Decision Records management
- **[Code Review Assistant](https://marketplace.visualstudio.com/items?itemName=teamhub.vscode-code-review)** - Distributed code review and decision tracking

### Implementation:
```json
{
  "conventionalCommits.scopes": ["decision", "arch", "design"],
  "adr.directory": "docs/decisions",
  "adr.template": "MADR"
}
```

---

## 2. If it's not tested, it's broken

**Principle**: Either a module has tests or it is broken. We adopt test driven development and high degrees of test code coverage.

### Supporting VS Code/Cursor Extensions:

- **[Jest](https://marketplace.visualstudio.com/items?itemName=Orta.vscode-jest)** - Automated test runner with coverage
- **[Test Explorer UI](https://marketplace.visualstudio.com/items?itemName=hbenl.vscode-test-explorer)** - Visual test management
- **[Coverage Gutters](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters)** - Inline code coverage display
- **[Wallaby.js](https://marketplace.visualstudio.com/items?itemName=WallabyJs.wallaby-vscode)** - Real-time test execution and coverage
- **[Test & Feedback](https://marketplace.visualstudio.com/items?itemName=ms-vsts.vscode-test-feedback)** - Manual test management

### Configuration:
```json
{
  "jest.autoRun": "watch",
  "jest.showCoverageOnLoad": true,
  "coverage-gutters.showLineCoverage": true,
  "wallaby.startAutomatically": true
}
```

---

## 3. Transparency dispels myth

**Principle**: We are transparent in everything we do. We use data points to prove our hypotheses.

### Supporting VS Code/Cursor Extensions:

- **[Metrics Bar](https://marketplace.visualstudio.com/items?itemName=itisnajim.metrics-bar)** - Real-time code metrics
- **[CodeMetrics](https://marketplace.visualstudio.com/items?itemName=kisstkondoros.vscode-codemetrics)** - Complexity analysis
- **[SonarLint](https://marketplace.visualstudio.com/items?itemName=SonarSource.sonarlint-vscode)** - Code quality metrics
- **[GitHub Pull Requests](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github)** - Transparent code review
- **[Project Dashboard](https://marketplace.visualstudio.com/items?itemName=kruemelkatze.vscode-dashboard)** - Custom metrics dashboard

### Setup:
```json
{
  "codemetrics.basics.ComplexityLevelExtreme": 10,
  "codemetrics.basics.ComplexityLevelHigh": 5,
  "sonarlint.output.showAnalyzerLogs": true
}
```

---

## 4. Mean Time To Innocence (MTTI)

**Principle**: How long it takes to demonstrate that your service/system is working. We build dashboards and monitoring.

### Supporting VS Code/Cursor Extensions:

- **[Thunder Client](https://marketplace.visualstudio.com/items?itemName=rangav.vscode-thunder-client)** - API testing and health checks
- **[REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)** - Quick service verification
- **[Kubernetes](https://marketplace.visualstudio.com/items?itemName=ms-kubernetes-tools.vscode-kubernetes-tools)** - Pod health monitoring
- **[Docker](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker)** - Container health status
- **[Azure Monitor](https://marketplace.visualstudio.com/items?itemName=msazurermtools.azurerm-vscode-tools)** - Application insights

### Health Check Configuration:
```json
{
  "thunder-client.healthCheck.interval": 300,
  "kubernetes.vs-kubernetes.autoRefresh": true,
  "docker.containers.sortBy": "Status"
}
```

---

## 5. No Dead Cats over the fence

**Principle**: We do not hand over code for other people to support. If you Build It, you Operate it.

### Supporting VS Code/Cursor Extensions:

- **[GitHub Actions](https://marketplace.visualstudio.com/items?itemName=github.vscode-github-actions)** - CI/CD ownership
- **[Azure Pipelines](https://marketplace.visualstudio.com/items?itemName=ms-azure-devops.azure-pipelines)** - Build and deploy ownership
- **[YAML](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml)** - Infrastructure as code
- **[Error Lens](https://marketplace.visualstudio.com/items?itemName=usernamehw.errorlens)** - Immediate error ownership
- **[TODO Highlight](https://marketplace.visualstudio.com/items?itemName=wayou.vscode-todo-highlight)** - Track ownership tasks

### DevOps Configuration:
```json
{
  "github-actions.workflows.pinned.workflows": [".github/workflows/deploy.yml"],
  "todohighlight.keywords": ["OWNER:", "RESPONSIBLE:", "MAINTAINER:"]
}
```

---

## 6. Friends would not let friends build data centres

**Principle**: All new development shall be designed to operate on public cloud. Systems shall be elastic, fault tolerant and cost aware.

### Supporting VS Code/Cursor Extensions:

- **[AWS Toolkit](https://marketplace.visualstudio.com/items?itemName=AmazonWebServices.aws-toolkit-vscode)** - AWS cloud development
- **[Azure Tools](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-node-azure-pack)** - Azure cloud development
- **[Terraform](https://marketplace.visualstudio.com/items?itemName=HashiCorp.terraform)** - Cloud infrastructure as code
- **[Cloud Code](https://marketplace.visualstudio.com/items?itemName=GoogleCloudTools.cloudcode)** - Multi-cloud development
- **[LocalStack](https://marketplace.visualstudio.com/items?itemName=localstack.localstack-vscode)** - Local cloud testing

### Cloud-First Settings:
```json
{
  "aws.telemetry": false,
  "terraform.languageServer.enable": true,
  "cloudcode.autoDependencies": true
}
```

---

## 7. Non Functional Requirements are first class citizens

**Principle**: NFRs are equally important as Functional Requirements. We shall fix any failing NFRs before starting on new functionality.

### Supporting VS Code/Cursor Extensions:

- **[Performance Profiler](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-js-profile-flame)** - Performance analysis
- **[Lighthouse](https://marketplace.visualstudio.com/items?itemName=GoogleChromeLabs.lighthouse)** - Web performance metrics
- **[Security Scan](https://marketplace.visualstudio.com/items?itemName=ShiftLeftSecurity.shiftleft-scan)** - Security NFR validation
- **[Accessibility Insights](https://marketplace.visualstudio.com/items?itemName=deque-systems.vscode-axe-linter)** - Accessibility requirements
- **[Load Test](https://marketplace.visualstudio.com/items?itemName=k6.k6)** - Performance testing

### NFR Enforcement:
```json
{
  "lighthouse.runAuditsOnSave": true,
  "axe-linter.enable": true,
  "k6.validate.enabled": true
}
```

---

## 8. Cattle not Pets

**Principle**: Environments should be treated like "cattle" not "pets". Infrastructure as Code for all environments.

### Supporting VS Code/Cursor Extensions:

- **[Ansible](https://marketplace.visualstudio.com/items?itemName=redhat.ansible)** - Infrastructure automation
- **[Pulumi](https://marketplace.visualstudio.com/items?itemName=pulumi.pulumi-lsp-client)** - Infrastructure as code
- **[Docker Compose](https://marketplace.visualstudio.com/items?itemName=p1c2u.docker-compose)** - Container orchestration
- **[Vagrant](https://marketplace.visualstudio.com/items?itemName=bbenoist.vagrant)** - Environment provisioning
- **[Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)** - Disposable dev environments

### IaC Configuration:
```json
{
  "ansible.validation.enabled": true,
  "docker.commands.composeUp": ["up", "-d", "--remove-orphans"],
  "remote.containers.defaultExtensions": ["ms-azuretools.vscode-docker"]
}
```

---

## 9. Keep the Hostage

**Principle**: Devalue production environments through complete automation. Full backup/restore capabilities.

### Supporting VS Code/Cursor Extensions:

- **[Backup and Sync](https://marketplace.visualstudio.com/items?itemName=arnohovhannisyan.syncify)** - Configuration backup
- **[Database Client](https://marketplace.visualstudio.com/items?itemName=cweijan.vscode-database-client2)** - Database backup management
- **[Git History](https://marketplace.visualstudio.com/items?itemName=donjayamanne.githistory)** - Code history backup
- **[Azure Data Studio](https://marketplace.visualstudio.com/items?itemName=Microsoft.azuredatastudio)** - Database backup automation
- **[Vault](https://marketplace.visualstudio.com/items?itemName=owenfarrell.vscode-vault)** - Secrets backup management

### Backup Automation:
```json
{
  "database-client.autoBackup": true,
  "vault.clipboardTimeout": 15,
  "git.autofetch": true
}
```

---

## 10. Elimination of Toil, via automation

**Principle**: Any activity that adds no lasting value is Toil. We eliminate recurring Toil via automation.

### Supporting VS Code/Cursor Extensions:

- **[Task Runner](https://marketplace.visualstudio.com/items?itemName=actboy168.tasks)** - Automate repetitive tasks
- **[Auto Rename Tag](https://marketplace.visualstudio.com/items?itemName=formulahendry.auto-rename-tag)** - Reduce HTML/XML toil
- **[Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)** - Auto-format code
- **[Code Spell Checker](https://marketplace.visualstudio.com/items?itemName=streetsidesoftware.code-spell-checker)** - Automated spell checking
- **[Import Cost](https://marketplace.visualstudio.com/items?itemName=wix.vscode-import-cost)** - Automated bundle analysis

### Automation Settings:
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": true,
    "source.organizeImports": true
  },
  "task.autoDetect": "on"
}
```

---

## 11. Failure is Normal, but customer disruption is not

**Principle**: Design systems to expect and cope with failure. Deploy across regions to avoid issues.

### Supporting VS Code/Cursor Extensions:

- **[Chaos Toolkit](https://marketplace.visualstudio.com/items?itemName=chaostoolkit.vscode-chaostoolkit)** - Chaos engineering
- **[Circuit Breaker](https://marketplace.visualstudio.com/items?itemName=SawyerHood.circuit-breaker)** - Resilience patterns
- **[Multi-root Workspaces](https://code.visualstudio.com/docs/editor/multi-root-workspaces)** - Multi-region development
- **[Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)** - Cross-region debugging
- **[Retry Pattern](https://marketplace.visualstudio.com/items?itemName=retry-pattern.vscode)** - Resilience implementation

### Resilience Configuration:
```json
{
  "chaos-toolkit.experiments.path": "./chaos",
  "remote.SSH.defaultForwardedPorts": [],
  "multi-root-workspace.enabled": true
}
```

---

## 12. Dependencies create "latency as a service"

**Principle**: Teams must be enabled to go from "concept to cash" with minimal external dependencies.

### Supporting VS Code/Cursor Extensions:

- **[Dependency Analytics](https://marketplace.visualstudio.com/items?itemName=redhat.fabric8-analytics)** - Analyze dependencies
- **[NPM Dependency Links](https://marketplace.visualstudio.com/items?itemName=herrmannplatz.npm-dependency-links)** - Visualize dependencies
- **[Depcheck](https://marketplace.visualstudio.com/items?itemName=depcheck.vscode-depcheck)** - Find unused dependencies
- **[Import Map](https://marketplace.visualstudio.com/items?itemName=sporto.import-map)** - Dependency visualization
- **[License Checker](https://marketplace.visualstudio.com/items?itemName=dariofuzinato.vscode-license-checker)** - Dependency compliance

### Dependency Management:
```json
{
  "npm.enableRunFromFolder": true,
  "depcheck.autoRun": true,
  "fabric8.analytics.autoStackAnalysis": true
}
```

---

## 13. Focus our efforts on differentiating code and infrastructure

**Principle**: Engineers should focus on company IP. Adopt managed services where cost-effective.

### Supporting VS Code/Cursor Extensions:

- **[AWS CDK](https://marketplace.visualstudio.com/items?itemName=aws.aws-cdk-vscode)** - Use managed AWS services
- **[Azure Functions](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)** - Serverless computing
- **[GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)** - Focus on business logic
- **[Tabnine](https://marketplace.visualstudio.com/items?itemName=TabNine.tabnine-vscode)** - AI-assisted coding
- **[Scaffolder](https://marketplace.visualstudio.com/items?itemName=henrynguyen5.vscode-scaffolder)** - Rapid boilerplate generation

### Managed Service Configuration:
```json
{
  "aws.cdk.explorerRefreshOnSave": true,
  "azureFunctions.deploySubpath": ".",
  "github.copilot.enable": {
    "*": true,
    "yaml": true,
    "plaintext": false
  }
}
```

---

## 14. Stop Starting and Start Stopping / Completing tasks

**Principle**: Earned Value is only obtained by completed work, used by our customers.

### Supporting VS Code/Cursor Extensions:

- **[Project Manager](https://marketplace.visualstudio.com/items?itemName=alefragnani.project-manager)** - Focus on active projects
- **[Todo Tree](https://marketplace.visualstudio.com/items?itemName=Gruntfuggly.todo-tree)** - Track incomplete work
- **[Kanban](https://marketplace.visualstudio.com/items?itemName=mkloubert.vscode-kanban)** - Visual task management
- **[Time Tracker](https://marketplace.visualstudio.com/items?itemName=Compulim.vscode-clock)** - Track task completion time
- **[GitLab Workflow](https://marketplace.visualstudio.com/items?itemName=GitLab.gitlab-workflow)** - Issue tracking integration

### Task Completion Settings:
```json
{
  "todo-tree.general.tags": ["TODO", "FIXME", "INCOMPLETE", "WIP"],
  "todo-tree.highlights.enabled": true,
  "kanban.saveLocation": ".vscode/kanban.json",
  "projectManager.sortList": "Recent"
}
```

---

## Implementation Guide

### 1. Install Core Extension Pack

Create `.vscode/extensions.json`:
```json
{
  "recommendations": [
    // Decision Making
    "vivaxy.vscode-conventional-commits",
    "eamodio.gitlens",
    "vincent-ledu.adr-tools",
    
    // Testing
    "Orta.vscode-jest",
    "ryanluker.vscode-coverage-gutters",
    "hbenl.vscode-test-explorer",
    
    // Transparency
    "kisstkondoros.vscode-codemetrics",
    "SonarSource.sonarlint-vscode",
    
    // Cloud & Infrastructure
    "HashiCorp.terraform",
    "ms-azuretools.vscode-docker",
    "ms-kubernetes-tools.vscode-kubernetes-tools",
    
    // Automation
    "esbenp.prettier-vscode",
    "streetsidesoftware.code-spell-checker",
    
    // Task Management
    "Gruntfuggly.todo-tree",
    "alefragnani.project-manager"
  ]
}
```

### 2. Configure Workspace Settings

Create `.vscode/settings.json`:
```json
{
  // Testing
  "jest.autoRun": "watch",
  "coverage-gutters.showLineCoverage": true,
  
  // Code Quality
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": true,
    "source.organizeImports": true
  },
  
  // Task Management
  "todo-tree.general.tags": ["TODO", "FIXME", "WIP", "OWNER:"],
  
  // Cloud First
  "terraform.languageServer.enable": true,
  
  // Transparency
  "sonarlint.output.showAnalyzerLogs": true
}
```

### 3. Create Team Workflows

Add to `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run All Tests with Coverage",
      "type": "shell",
      "command": "npm test -- --coverage",
      "group": {
        "kind": "test",
        "isDefault": true
      }
    },
    {
      "label": "Health Check",
      "type": "shell",
      "command": "curl -f http://localhost:3000/health || exit 1",
      "problemMatcher": []
    },
    {
      "label": "Deploy to Cloud",
      "type": "shell",
      "command": "terraform apply -auto-approve",
      "dependsOn": ["Run All Tests with Coverage"]
    }
  ]
}
```

### 4. Integrate with CI/CD

Add to your pipeline:
```yaml
- name: Validate Principles
  run: |
    # Ensure tests exist
    npm test -- --coverage --ci
    
    # Check coverage threshold
    npx nyc check-coverage --lines 80
    
    # Validate infrastructure
    terraform validate
    
    # Check for incomplete tasks
    grep -r "TODO\|FIXME\|WIP" src/ && exit 1 || true
```

---

## Measuring Success

### Key Metrics:
- **Decision Distribution**: ADR count per team member
- **Test Coverage**: Minimum 80% line coverage
- **MTTI**: < 5 minutes to prove system health
- **Toil Reduction**: Automated tasks vs manual ratio
- **Task Completion**: Completed vs started ratio

### Dashboard Integration:
Configure monitoring extensions to track these metrics in real-time within VS Code.

---

## Resources

- [VS Code Extension API](https://code.visualstudio.com/api)
- [Cursor Documentation](https://cursor.sh/docs)
- [DSDM Agile Framework](https://www.agilebusiness.org/dsdm)
---