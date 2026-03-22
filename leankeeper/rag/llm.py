"""
LeanKeeper — Pluggable LLM backends.

Supports Claude (default), OpenAI, and Ollama (local).
"""

import logging

from leankeeper.config import (
    ANTHROPIC_API_KEY,
    LLM_BACKEND,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)


class LLMBackend:
    def generate(self, system: str, user: str) -> str:
        raise NotImplementedError


class ClaudeBackend(LLMBackend):
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text


class OpenAIBackend(LLMBackend):
    def __init__(self):
        import openai
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def generate(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content


class OllamaBackend(LLMBackend):
    def __init__(self):
        import requests
        self._requests = requests
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    def generate(self, system: str, user: str) -> str:
        response = self._requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


_BACKENDS = {
    "claude": ClaudeBackend,
    "openai": OpenAIBackend,
    "ollama": OllamaBackend,
}


def get_llm(backend: str = None) -> LLMBackend:
    """Get the configured LLM backend."""
    name = backend or LLM_BACKEND
    if name not in _BACKENDS:
        raise ValueError(f"Unknown LLM backend: {name}. Available: {list(_BACKENDS.keys())}")
    return _BACKENDS[name]()
