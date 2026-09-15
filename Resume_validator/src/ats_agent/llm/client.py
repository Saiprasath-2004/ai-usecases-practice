"""Factory for the configured chat model."""

from langchain_openrouter import ChatOpenRouter

from ats_agent.config import OPENROUTER_API_KEY, OPENROUTER_MODEL


def get_chat_model() -> ChatOpenRouter:
    """Create a deterministic OpenRouter chat model from environment config."""
    return ChatOpenRouter(
        model=OPENROUTER_MODEL,
        api_key=OPENROUTER_API_KEY,
        temperature=0,
    )
