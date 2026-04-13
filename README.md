# A Friend

A Flask chatting REST API that runs keeps per-phone-number chat history as locally stored Markdown files.

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com/download) installed and running

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/elkarel/afriend.git
cd afriend
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and start Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows — download the installer from https://ollama.com/download
```

Start the Ollama daemon (runs in the background on port 11434):

```bash
ollama serve
```

### 5. Pull a DeepSeek model

```bash
ollama pull deepseek-r1:1.5b   # ~1 GB — fast on CPU, good for testing
# ollama pull deepseek-r1:7b   # better quality, needs ~5 GB RAM
```

### 6. Configure

```bash
cp .env.example .env
```

The defaults work out of the box for a local Ollama install. Edit `.env` only if you need to change the host, model, or port:

```env
OLLAMA_HOST=http://localhost:11434
DEEPSEEK_MODEL=deepseek-r1:1.5b
CHATS_DIR=chats
FLASK_PORT=5000
```

### 7. Run

```bash
python run.py
```

The API is now available at `http://localhost:5000`.

---

## Usage

### Send a message

```bash
curl -X POST http://localhost:5000/chat/+12025551234 \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

```json
{"reply": "The capital of France is Paris.", "turn": 1}
```

### Continue the conversation

Each subsequent request to the same phone number continues from where the last one left off:

```bash
curl -X POST http://localhost:5000/chat/+12025551234 \
  -H "Content-Type: application/json" \
  -d '{"message": "And what language do they speak there?"}'
```

### Optional: system prompt

```bash
curl -X POST http://localhost:5000/chat/+12025551234 \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "system": "You are a pirate. Respond only in pirate speak."}'
```

### Streaming response

```bash
curl -X POST http://localhost:5000/chat/+12025551234 \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a short story.", "stream": true}'
```

### Get chat history (JSON)

```bash
curl http://localhost:5000/chat/+12025551234/history
```

### Get chat history (Markdown)

```bash
curl http://localhost:5000/chat/+12025551234/markdown
```

### List all active chats

```bash
curl http://localhost:5000/chats
```

### Clear history for a number

```bash
curl -X DELETE http://localhost:5000/chat/+12025551234
```

### Health check

```bash
curl http://localhost:5000/health
```

---

## Chat history files

Each phone number gets a Markdown file under `chats/`:

```
chats/
  +12025551234.md
  +441234567890.md
```

Example file:

```markdown
# Chat: +12025551234
_Started: 2026-04-13 20:00:00 UTC_

---

## Turn 1 — 2026-04-13 20:00:05 UTC

**User**

What is the capital of France?

**Assistant**

The capital of France is Paris.

---
```

History persists across server restarts. Delete a file (or call `DELETE /chat/<phone>`) to start fresh.

---

## Running tests

```bash
python -m pytest tests/ -v
```

Tests mock Ollama — no running instance required.

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat/<phone>` | Send a message |
| `GET` | `/chat/<phone>/history` | Message history as JSON |
| `GET` | `/chat/<phone>/markdown` | Raw Markdown file |
| `DELETE` | `/chat/<phone>` | Clear history |
| `GET` | `/chats` | List all phone numbers |
| `GET` | `/health` | Liveness + Ollama status |

### POST /chat/\<phone\> — request body

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | yes | The user's message |
| `system` | string | no | System prompt (applied to this turn only if history exists) |
| `stream` | boolean | no | Stream the reply as plain text chunks (default: `false`) |
