"""
Unit tests for the chat history store.
These tests do not require Ollama to be running.
"""
import os
import tempfile
import pytest

# Point CHATS_DIR at a temp directory before importing history
@pytest.fixture(autouse=True)
def tmp_chats_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATS_DIR", str(tmp_path / "chats"))
    # Re-import config so it picks up the patched env var
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    import app.history as hist
    importlib.reload(hist)
    yield tmp_path / "chats"


def _get_hist():
    import importlib
    import app.history as hist
    importlib.reload(hist)
    return hist


def test_session_creates_markdown_file(tmp_chats_dir):
    hist = _get_hist()
    session = hist.ChatSession("+1234567890")
    assert (tmp_chats_dir / "+1234567890.md").exists()


def test_add_exchange_persists(tmp_chats_dir):
    hist = _get_hist()
    session = hist.ChatSession("+1111111111")
    session.add_exchange("Hello", "Hi there!")

    content = (tmp_chats_dir / "+1111111111.md").read_text()
    assert "Hello" in content
    assert "Hi there!" in content
    assert "**User**" in content
    assert "**Assistant**" in content


def test_history_survives_reload(tmp_chats_dir):
    hist = _get_hist()
    session = hist.ChatSession("+2222222222")
    session.add_exchange("What is 2+2?", "4")
    session.add_exchange("And 3+3?", "6")

    # Simulate a new session loading from disk
    session2 = hist.ChatSession("+2222222222")
    msgs = session2.messages
    assert len(msgs) == 4
    assert msgs[0] == {"role": "user", "content": "What is 2+2?"}
    assert msgs[1] == {"role": "assistant", "content": "4"}
    assert msgs[2] == {"role": "user", "content": "And 3+3?"}
    assert msgs[3] == {"role": "assistant", "content": "6"}


def test_turn_count(tmp_chats_dir):
    hist = _get_hist()
    session = hist.ChatSession("+3333333333")
    assert session.turn_count() == 0
    session.add_exchange("msg1", "reply1")
    assert session.turn_count() == 1
    session.add_exchange("msg2", "reply2")
    assert session.turn_count() == 2


def test_clear_removes_file(tmp_chats_dir):
    hist = _get_hist()
    session = hist.ChatSession("+4444444444")
    session.add_exchange("hi", "hello")
    session.clear()
    assert not (tmp_chats_dir / "+4444444444.md").exists()
    assert session.messages == []


def test_safe_filename_sanitises_special_chars(tmp_chats_dir):
    hist = _get_hist()
    # Slash and space are unsafe — should not raise and should create a file
    session = hist.ChatSession("bad/name here")
    path = tmp_chats_dir / "bad_name_here.md"
    assert path.exists()


def test_registry_returns_same_session(tmp_chats_dir):
    hist = _get_hist()
    reg = hist.SessionRegistry()
    s1 = reg.get("+5555555555")
    s2 = reg.get("+5555555555")
    assert s1 is s2


def test_registry_list_phones(tmp_chats_dir):
    hist = _get_hist()
    reg = hist.SessionRegistry()
    reg.get("+6666666666")
    reg.get("+7777777777")
    phones = reg.list_phones()
    assert "+6666666666" in phones
    assert "+7777777777" in phones


def test_registry_delete(tmp_chats_dir):
    hist = _get_hist()
    reg = hist.SessionRegistry()
    reg.get("+8888888888").add_exchange("x", "y")
    assert reg.delete("+8888888888") is True
    assert not (tmp_chats_dir / "+8888888888.md").exists()


def test_registry_delete_nonexistent(tmp_chats_dir):
    hist = _get_hist()
    reg = hist.SessionRegistry()
    assert reg.delete("+0000000000") is False
