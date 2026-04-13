"""
Thin wrapper around the Ollama Python client for DeepSeek models.

Ollama must be running locally (or at OLLAMA_HOST) with the target model
already pulled:
    ollama pull deepseek-r1:1.5b

The client is stateless — it receives the full message history on each call
so the caller (ChatSession) owns conversation state.
"""
from __future__ import annotations

from typing import Generator

import ollama

from app.config import Config


def _make_client() -> ollama.Client:
    return ollama.Client(host=Config.OLLAMA_HOST)


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    stream: bool = False,
) -> str | Generator[str, None, None]:
    """
    Send a conversation to the local DeepSeek model and return the reply.

    Args:
        messages: Full conversation history in OpenAI-style format:
                  [{"role": "user"|"assistant"|"system", "content": "..."}]
        model:    Override the model from Config. Defaults to Config.DEEPSEEK_MODEL.
        stream:   If True, returns a generator that yields text chunks.

    Returns:
        The assistant's reply as a string (stream=False) or a generator of
        string chunks (stream=True).

    Raises:
        ollama.ResponseError: If Ollama returns an error (e.g. model not found).
        httpx.ConnectError:   If Ollama is not reachable at OLLAMA_HOST.
    """
    client = _make_client()
    target_model = model or Config.DEEPSEEK_MODEL

    if stream:
        return _stream_reply(client, target_model, messages)

    response = client.chat(model=target_model, messages=messages)
    return response.message.content


def _stream_reply(
    client: ollama.Client,
    model: str,
    messages: list[dict[str, str]],
) -> Generator[str, None, None]:
    for chunk in client.chat(model=model, messages=messages, stream=True):
        content = chunk.message.content
        if content:
            yield content


def list_local_models() -> list[str]:
    """Return names of models currently available in the local Ollama instance."""
    client = _make_client()
    return [m.model for m in client.list().models]
