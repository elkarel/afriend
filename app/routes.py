"""
Flask REST API routes.

Endpoints
---------
POST   /chat/<phone>          Send a message; get a reply.
GET    /chat/<phone>/history  Return the full message history as JSON.
GET    /chat/<phone>/markdown Return the raw markdown file content.
DELETE /chat/<phone>          Clear history for a phone number.
GET    /chats                 List all phone numbers that have history.
GET    /health                Liveness check + Ollama reachability.

Phone number format
-------------------
Any string is accepted as <phone>. Characters unsafe for filenames are
replaced with underscores when writing to disk (see history._safe_filename).
Callers should use E.164 format (e.g. +12025551234) for consistency.

Error responses
---------------
All errors return JSON: {"error": "<message>"} with an appropriate HTTP status.
"""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context

from app import deepseek_client as ds
from app.config import Config
from app.history import _chat_path, registry

bp = Blueprint("chat", __name__)


# ---------------------------------------------------------------------------
# POST /chat/<phone>
# ---------------------------------------------------------------------------

@bp.post("/chat/<phone>")
def send_message(phone: str):
    """
    Body (JSON):
        {
            "message": "Hello!",          # required
            "system":  "You are helpful", # optional system prompt
            "stream":  false              # optional, default false
        }

    Response (stream=false):
        {"reply": "...", "turn": 3}

    Response (stream=true):
        text/event-stream — each chunk is a raw text fragment.
    """
    body = request.get_json(silent=True) or {}
    user_msg = body.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Field 'message' is required and must not be empty."}), 400

    system_prompt = body.get("system", "").strip()
    do_stream = bool(body.get("stream", False))

    session = registry.get(phone)
    history = session.messages  # snapshot before this turn

    # Build the message list to send to Ollama
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": user_msg})

    if do_stream:
        def generate():
            chunks: list[str] = []
            try:
                for chunk in ds.chat(messages, stream=True):
                    chunks.append(chunk)
                    yield chunk
            finally:
                # Persist only after the stream is fully consumed
                full_reply = "".join(chunks)
                if full_reply:
                    session.add_exchange(user_msg, full_reply)

        return Response(
            stream_with_context(generate()),
            content_type="text/plain; charset=utf-8",
        )

    # Non-streaming path
    try:
        reply = ds.chat(messages, stream=False)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    session.add_exchange(user_msg, reply)
    return jsonify({"reply": reply, "turn": session.turn_count()})


# ---------------------------------------------------------------------------
# GET /chat/<phone>/history
# ---------------------------------------------------------------------------

@bp.get("/chat/<phone>/history")
def get_history(phone: str):
    """
    Returns the full conversation as a JSON array of message objects.

    Response:
        {
            "phone": "+12025551234",
            "turns": 3,
            "messages": [
                {"role": "user",      "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                ...
            ]
        }
    """
    session = registry.get(phone)
    msgs = session.messages
    return jsonify({
        "phone": phone,
        "turns": session.turn_count(),
        "messages": msgs,
    })


# ---------------------------------------------------------------------------
# GET /chat/<phone>/markdown
# ---------------------------------------------------------------------------

@bp.get("/chat/<phone>/markdown")
def get_markdown(phone: str):
    """Return the raw markdown file for a phone number."""
    path = _chat_path(phone)
    if not path.exists():
        return jsonify({"error": "No chat history found for this number."}), 404
    return Response(path.read_text(encoding="utf-8"), content_type="text/markdown; charset=utf-8")


# ---------------------------------------------------------------------------
# DELETE /chat/<phone>
# ---------------------------------------------------------------------------

@bp.delete("/chat/<phone>")
def clear_history(phone: str):
    """Erase all history for a phone number (memory + markdown file)."""
    deleted = registry.delete(phone)
    if not deleted:
        return jsonify({"error": "No chat history found for this number."}), 404
    return jsonify({"deleted": True, "phone": phone})


# ---------------------------------------------------------------------------
# GET /chats
# ---------------------------------------------------------------------------

@bp.get("/chats")
def list_chats():
    """List all phone numbers that have a chat file on disk."""
    phones = registry.list_phones()
    return jsonify({"chats": phones, "count": len(phones)})


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@bp.get("/health")
def health():
    """Liveness check. Also reports whether Ollama is reachable."""
    try:
        models = ds.list_local_models()
        ollama_ok = True
        ollama_models = models
    except Exception as exc:
        ollama_ok = False
        ollama_models = []
        ollama_error = str(exc)

    status = {
        "status": "ok",
        "ollama": {
            "reachable": ollama_ok,
            "host": Config.OLLAMA_HOST,
            "model": Config.DEEPSEEK_MODEL,
            "available_models": ollama_models,
        },
    }
    if not ollama_ok:
        status["ollama"]["error"] = ollama_error  # type: ignore[index]

    http_status = 200 if ollama_ok else 503
    return jsonify(status), http_status
