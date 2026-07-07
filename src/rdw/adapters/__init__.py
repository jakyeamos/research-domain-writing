from __future__ import annotations

from rdw.adapters.base import TaskAdapter
from rdw.adapters.stubs import AnthropicAdapter, LocalAdapter, OpenAIAdapter

ADAPTERS: dict[str, TaskAdapter] = {
    "local": LocalAdapter(),
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
}


def list_adapters() -> list[str]:
    return sorted(ADAPTERS)


def get_adapter(name: str) -> TaskAdapter:
    normalized = name.strip().lower()
    adapter = ADAPTERS.get(normalized)
    if adapter is None:
        known = ", ".join(list_adapters())
        raise ValueError(f"unknown adapter: {name} (known: {known})")
    return adapter
