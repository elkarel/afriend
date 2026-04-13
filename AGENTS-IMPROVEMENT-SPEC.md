# AGENTS Improvement Spec

Audit date: 2026-04-13  
Auditor: Ona

---

## Current State

### What exists

| File | Purpose | Quality |
|---|---|---|
| `.devcontainer/devcontainer.json` | Dev container config | Minimal but functional |
| `.ona/review/comments.json` | Ona review state | Auto-generated, empty |
| `AGENTS.md` | Agent guidance | Created this session — skeleton only |

### What is missing

1. **No source code** — the repository has zero commits and no application files.
2. **No skill files** — no `.ona/skills/`, no `.cursor/rules/`, no agent-specific prompt files.
3. **No automations** — no `automations.yaml` or equivalent task/service definitions.
4. **No `.gitignore`** — nothing to prevent accidental commits of build artifacts or secrets.
5. **No CI/CD** — no GitHub Actions, no test pipeline.
6. **No README** — no project description, setup instructions, or usage docs.
7. **AGENTS.md is a skeleton** — language, stack, test commands, and style rules are all TBD placeholders.

### What is wrong

1. **`devcontainer.json` uses the universal image** (`universal:4.0.1-noble`, ~10 GB). This is appropriate for exploration but should be replaced with a language-specific image once the stack is known, to reduce startup time.
2. **No `postCreateCommand`** in `devcontainer.json` — dependencies are not installed automatically on environment creation.
3. **No `forwardPorts`** — developers must manually expose ports.
4. **AGENTS.md has no actionable rules** — it is all placeholders. Agents reading it gain no real guidance.

---

## Improvement Spec

### Priority 1 — Immediate (before any code is written)

#### 1.1 Add `.gitignore`

Create a `.gitignore` appropriate for the chosen stack. At minimum include:

```
# OS
.DS_Store
Thumbs.db

# Editor
.vscode/
.idea/
*.swp

# Secrets
.env
.env.*
!.env.example

# Ona platform state (auto-generated)
# .ona/ — keep tracked so review state persists across environments
```

Extend with language-specific patterns once the stack is decided.

#### 1.2 Decide and document the stack

Update `AGENTS.md` with:
- Primary language(s) and runtime versions
- Framework(s) in use
- Package manager (npm/yarn/pnpm, pip/poetry, go mod, etc.)
- Test runner and command (`npm test`, `pytest`, `go test ./...`, etc.)
- Lint/format command

#### 1.3 Replace the universal dev container image

Once the stack is known, switch to a smaller base image:

| Stack | Recommended image |
|---|---|
| Node.js | `mcr.microsoft.com/devcontainers/javascript-node:22` |
| Python | `mcr.microsoft.com/devcontainers/python:3.13` |
| Go | `mcr.microsoft.com/devcontainers/go:1.24` |
| Java | `mcr.microsoft.com/devcontainers/java:21` |

Add `postCreateCommand` to install dependencies automatically, e.g.:
```json
"postCreateCommand": "npm ci"
```

Add `forwardPorts` for the application's default port.

---

### Priority 2 — Once source code exists

#### 2.1 Flesh out AGENTS.md

Replace all placeholder sections with concrete rules:

- **Code style**: indentation, naming conventions, import order, file naming.
- **Commit messages**: confirm conventional commits format; add scope examples specific to this repo's module structure.
- **Testing**: exact command to run tests, how to run a single test, coverage threshold if any.
- **PR conventions**: branch naming pattern, required reviewers, label usage.
- **Off-limits paths**: files agents must not modify (generated files, lock files, etc.).

#### 2.2 Add Ona automations

Create `.ona/automations.yaml` (or equivalent) with at minimum:

- **`install` task**: runs dependency installation on environment start.
- **`dev` service**: starts the development server and forwards the port.
- **`test` task**: runs the test suite.
- **`lint` task**: runs the linter/formatter check.

Example skeleton:
```yaml
tasks:
  - id: install
    name: Install dependencies
    command: npm ci

  - id: test
    name: Run tests
    command: npm test

services:
  - id: dev
    name: Dev server
    command: npm run dev
```

#### 2.3 Add agent skill files

Create `.ona/skills/` with project-specific skills for recurring agent workflows, e.g.:

- `add-feature.md` — workflow for adding a new feature (branch, implement, test, PR).
- `fix-bug.md` — workflow for triaging and fixing a bug.
- `review-pr.md` — checklist for reviewing a pull request.

#### 2.4 Add a README

Minimum sections:
- What the project does (one paragraph)
- Prerequisites
- Setup (`git clone` → dev container → run)
- How to run tests
- How to contribute

---

### Priority 3 — Ongoing hygiene

#### 3.1 CI pipeline

Add a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every PR:
- Install dependencies
- Run linter
- Run tests
- Report coverage

#### 3.2 Keep AGENTS.md current

After any significant architectural change, update AGENTS.md. Treat it as living documentation, not a one-time artifact.

#### 3.3 Pin dev container image versions

The current `universal:4.0.1-noble` is already pinned — maintain this practice for the replacement image to ensure reproducible environments.

---

## Summary Table

| Item | Status | Priority |
|---|---|---|
| `.gitignore` | Missing | P1 |
| Stack decision documented in AGENTS.md | Missing | P1 |
| Language-specific dev container image | Not done | P1 |
| `postCreateCommand` in devcontainer | Missing | P1 |
| `forwardPorts` in devcontainer | Missing | P1 |
| Concrete code style rules in AGENTS.md | Placeholder | P2 |
| Concrete test command in AGENTS.md | Placeholder | P2 |
| Ona automations (`automations.yaml`) | Missing | P2 |
| Agent skill files (`.ona/skills/`) | Missing | P2 |
| README | Missing | P2 |
| CI pipeline | Missing | P3 |
| AGENTS.md maintenance process | Not established | P3 |
