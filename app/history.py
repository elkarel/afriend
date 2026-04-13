"""
Per-phone-number chat history, persisted as Markdown files.

Layout on disk:
    chats/
        +1234567890.md
        +0987654321.md
        ...

Markdown format per file:
    # Chat: +1234567890
    _Started: 2026-04-13 20:00:00 UTC_

    ---

    ## Turn 1 — 2026-04-13 20:00:05 UTC

    **User**

    Hello, who are you?

    **Assistant**

    I'm DeepSeek, a local AI assistant...

    ---

    ## Turn 2 — ...

The in-memory message list (OpenAI-style dicts) is the source of truth during a
session. The markdown file is append-only and written after every assistant reply.
On startup (or when a new request arrives for a known number) the history is
re-parsed from the markdown file so sessions survive server restarts.
"""
from __future__ import annotations

import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe_filename(phone: str) -> str:
    """Strip characters that are unsafe in filenames, keep digits, +, -."""
    return re.sub(r"[^\w+\-]", "_", phone)


def _chats_dir() -> Path:
    path = Path(Config.CHATS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _chat_path(phone: str) -> Path:
    return _chats_dir() / f"{_safe_filename(phone)}.md"


# ---------------------------------------------------------------------------
# Markdown serialisation
# ---------------------------------------------------------------------------

_TURN_HEADER_RE = re.compile(r"^## Turn \d+")


def _parse_markdown(text: str) -> list[dict[str, str]]:
    """
    Reconstruct the OpenAI-style message list from a markdown chat file.
    Returns [] if the file is empty or unparseable.
    """
    messages: list[dict[str, str]] = []
    current_role: Optional[str] = None
    current_lines: list[str] = []

    def flush():
        if current_role and current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                messages.append({"role": current_role, "content": content})

    for line in text.splitlines():
        if _TURN_HEADER_RE.match(line):
            flush()
            current_role = None
            current_lines = []
            continue

        if line == "**User**":
            flush()
            current_role = "user"
            current_lines = []
            continue

        if line == "**Assistant**":
            flush()
            current_role = "assistant"
            current_lines = []
            continue

        # Skip decorative lines
        if line.startswith("# Chat:") or line.startswith("_Started:") or line == "---":
            continue

        if current_role is not None:
            current_lines.append(line)

    flush()
    return messages


def _append_turn(path: Path, turn_number: int, user_msg: str, assistant_msg: str) -> None:
    """Append one user/assistant exchange to the markdown file."""
    timestamp = _now_utc()
    block = (
        f"\n## Turn {turn_number} — {timestamp}\n"
        f"\n**User**\n\n{user_msg}\n"
        f"\n**Assistant**\n\n{assistant_msg}\n"
        f"\n---\n"
    )
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(block)


def _init_file(path: Path, phone: str) -> None:
    """Write the file header if the file does not exist yet."""
    if not path.exists():
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Chat: {phone}\n")
            fh.write(f"_Started: {_now_utc()}_\n\n---\n")


# ---------------------------------------------------------------------------
# ChatSession
# ---------------------------------------------------------------------------

class ChatSession:
    """
    Represents one ongoing conversation for a phone number.

    Thread-safe: a per-session lock serialises concurrent requests for the
    same phone number (the Flask API may receive them from different threads).
    """

    def __init__(self, phone: str) -> None:
        self.phone = phone
        self._path = _chat_path(phone)
        self._lock = threading.Lock()
        self._messages: list[dict[str, str]] = []
        self._load()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def messages(self) -> list[dict[str, str]]:
        """Read-only snapshot of the current message history."""
        with self._lock:
            return list(self._messages)

    def add_exchange(self, user_content: str, assistant_content: str) -> None:
        """
        Record a completed user/assistant exchange in memory and on disk.
        Call this after the assistant reply is fully available.
        """
        with self._lock:
            self._messages.append({"role": "user", "content": user_content})
            self._messages.append({"role": "assistant", "content": assistant_content})
            turn_number = len(self._messages) // 2
            _append_turn(self._path, turn_number, user_content, assistant_content)

    def clear(self) -> None:
        """Erase history in memory and delete the markdown file."""
        with self._lock:
            self._messages = []
            if self._path.exists():
                self._path.unlink()

    def turn_count(self) -> int:
        with self._lock:
            return len(self._messages) // 2

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Restore message history from the markdown file if it exists."""
        _init_file(self._path, self.phone)
        text = self._path.read_text(encoding="utf-8")
        self._messages = _parse_markdown(text)


# ---------------------------------------------------------------------------
# Session registry
# ---------------------------------------------------------------------------

class SessionRegistry:
    """
    Process-wide store of active ChatSession objects, keyed by phone number.

    Sessions are created on first access and kept alive for the process
    lifetime. This is intentional: the markdown file is the durable store;
    the in-memory session is just a cache of it.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._lock = threading.Lock()

    def get(self, phone: str) -> ChatSession:
        """Return the session for *phone*, creating it if necessary."""
        with self._lock:
            if phone not in self._sessions:
                self._sessions[phone] = ChatSession(phone)
            return self._sessions[phone]

    def delete(self, phone: str) -> bool:
        """
        Clear and remove the session for *phone*.
        Returns True if a session existed, False otherwise.
        """
        with self._lock:
            session = self._sessions.pop(phone, None)
        if session:
            session.clear()
            return True
        # Phone had a file but no in-memory session — delete the file directly.
        path = _chat_path(phone)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_phones(self) -> list[str]:
        """Return phone numbers that have a chat file on disk."""
        return [
            p.stem
            for p in _chats_dir().glob("*.md")
        ]


# Module-level singleton used by the Flask app.
registry = SessionRegistry()
