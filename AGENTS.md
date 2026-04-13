# AGENTS.md

Agent and AI assistant guidance for this repository.

## Project Overview

**afriend** is a Flask REST API that wraps a locally-running DeepSeek model
(via Ollama) and maintains per-phone-number chat history as Markdown files.

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | Flask 3.1.3 |
| LLM backend | Ollama (local) + DeepSeek model |
| Ollama Python client | `ollama` 0.6.1 |
| Config | `python-dotenv` 1.2.2 |
| Tests | `pytest` 9.0.3 |

## Project Structure

```
app/
  __init__.py          # empty package marker
  config.py            # env-var config (OLLAMA_HOST, DEEPSEEK_MODEL, etc.)
  deepseek_client.py   # thin Ollama wrapper (stateless)
  history.py           # ChatSession + SessionRegistry + markdown persistence
  factory.py           # Flask app factory
  routes.py            # all REST endpoints
chats/                 # runtime-generated markdown files (one per phone number)
tests/
  test_history.py      # unit tests for history store
  test_api.py          # integration tests for REST API (Ollama mocked)
run.py                 # dev server entry point
requirements.txt
.env.example           # copy to .env and edit before running
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install and start Ollama  (https://ollama.com)
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &

# 3. Pull a DeepSeek model
ollama pull deepseek-r1:1.5b   # ~1 GB, fast on CPU

# 4. Configure
cp .env.example .env
# Edit .env if needed (defaults work for local Ollama)

# 5. Run
python run.py
```

## Commands

| Task | Command |
|---|---|
| Run dev server | `python run.py` |
| Run tests | `python -m pytest tests/ -v` |
| Run single test file | `python -m pytest tests/test_history.py -v` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat/<phone>` | Send a message; get a reply |
| `GET` | `/chat/<phone>/history` | Full message history as JSON |
| `GET` | `/chat/<phone>/markdown` | Raw markdown file |
| `DELETE` | `/chat/<phone>` | Clear history for a number |
| `GET` | `/chats` | List all numbers with history |
| `GET` | `/health` | Liveness + Ollama reachability |

### Example

```bash
curl -X POST http://localhost:5000/chat/+12025551234 \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

## Code Conventions

- **Style**: PEP 8. 4-space indentation. Max line length 100.
- **Imports**: stdlib → third-party → local, separated by blank lines.
- **Type hints**: use `from __future__ import annotations` + standard hints.
- **Docstrings**: module-level and public functions only. Explain *why*, not *what*.
- **No global state** except `app/history.py::registry` (intentional singleton).

## Commit Messages

Conventional commits:
```
feat(api): add streaming endpoint
fix(history): handle concurrent writes with per-session lock
chore: bump ollama to 0.7.0
```

## Agent Rules

- Read this file at the start of every session.
- Do not commit or push unless explicitly asked.
- Do not modify `.ona/` files directly.
- Do not add dependencies without updating `requirements.txt`.
- Do not expose `.env` contents or secrets.
- The `chats/` directory is runtime data — do not commit it.
- When adding a new endpoint, add corresponding tests in `tests/test_api.py`.
