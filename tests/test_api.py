"""
Integration tests for the Flask REST API.
Ollama calls are mocked — no running Ollama instance required.
"""
import importlib
import json
import pytest


@pytest.fixture()
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATS_DIR", str(tmp_path / "chats"))

    # Reload config so CHATS_DIR is picked up
    import app.config as cfg
    importlib.reload(cfg)
    import app.history as hist
    importlib.reload(hist)

    # Patch the module-level registry in routes to use a fresh one
    import app.routes as routes
    importlib.reload(routes)

    import app.factory as factory
    importlib.reload(factory)

    flask_app = factory.create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_deepseek(monkeypatch):
    """Replace ds.chat with a deterministic stub."""
    import app.deepseek_client as ds

    def fake_chat(messages, model=None, stream=False):
        last = messages[-1]["content"]
        reply = f"Echo: {last}"
        if stream:
            return iter([reply])
        return reply

    monkeypatch.setattr(ds, "chat", fake_chat)
    monkeypatch.setattr(ds, "list_local_models", lambda: ["deepseek-r1:1.5b"])


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["ollama"]["reachable"] is True


# ---------------------------------------------------------------------------
# POST /chat/<phone>
# ---------------------------------------------------------------------------

def test_send_message_returns_reply(client):
    r = client.post("/chat/+1234567890", json={"message": "Hello"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["reply"] == "Echo: Hello"
    assert data["turn"] == 1


def test_send_message_missing_body(client):
    r = client.post("/chat/+1234567890", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_send_message_empty_message(client):
    r = client.post("/chat/+1234567890", json={"message": "   "})
    assert r.status_code == 400


def test_multiple_turns_increment(client):
    client.post("/chat/+1111111111", json={"message": "Turn 1"})
    r = client.post("/chat/+1111111111", json={"message": "Turn 2"})
    assert r.get_json()["turn"] == 2


def test_independent_sessions(client):
    client.post("/chat/+AAA", json={"message": "msg A"})
    client.post("/chat/+BBB", json={"message": "msg B"})

    ha = client.get("/chat/+AAA/history").get_json()
    hb = client.get("/chat/+BBB/history").get_json()

    assert ha["turns"] == 1
    assert hb["turns"] == 1
    assert ha["messages"][0]["content"] == "msg A"
    assert hb["messages"][0]["content"] == "msg B"


# ---------------------------------------------------------------------------
# GET /chat/<phone>/history
# ---------------------------------------------------------------------------

def test_get_history_empty(client):
    r = client.get("/chat/+9999999999/history")
    assert r.status_code == 200
    data = r.get_json()
    assert data["turns"] == 0
    assert data["messages"] == []


def test_get_history_after_chat(client):
    client.post("/chat/+2222222222", json={"message": "Hi"})
    r = client.get("/chat/+2222222222/history")
    data = r.get_json()
    assert data["turns"] == 1
    assert data["messages"][0] == {"role": "user", "content": "Hi"}
    assert data["messages"][1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# GET /chat/<phone>/markdown
# ---------------------------------------------------------------------------

def test_get_markdown_not_found(client):
    r = client.get("/chat/+0000000000/markdown")
    assert r.status_code == 404


def test_get_markdown_returns_content(client):
    client.post("/chat/+3333333333", json={"message": "Test"})
    r = client.get("/chat/+3333333333/markdown")
    assert r.status_code == 200
    assert "Test" in r.data.decode()
    assert "**User**" in r.data.decode()


# ---------------------------------------------------------------------------
# DELETE /chat/<phone>
# ---------------------------------------------------------------------------

def test_delete_clears_history(client):
    client.post("/chat/+4444444444", json={"message": "Delete me"})
    r = client.delete("/chat/+4444444444")
    assert r.status_code == 200
    assert r.get_json()["deleted"] is True

    # History should be gone
    r2 = client.get("/chat/+4444444444/history")
    assert r2.get_json()["turns"] == 0


def test_delete_nonexistent(client):
    r = client.delete("/chat/+nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /chats
# ---------------------------------------------------------------------------

def test_list_chats(client):
    client.post("/chat/+5555555555", json={"message": "x"})
    client.post("/chat/+6666666666", json={"message": "y"})
    r = client.get("/chats")
    data = r.get_json()
    assert "+5555555555" in data["chats"]
    assert "+6666666666" in data["chats"]
    assert data["count"] >= 2
