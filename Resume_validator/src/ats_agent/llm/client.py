"""Factory for the configured ChatGroq models with JSON response formatting."""

import json
import logging
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

from ats_agent.config import (
    GROQ_API_KEY,
    GROQ_FALLBACK_MODEL,
    GROQ_PRIMARY_MODEL,
)

logger = logging.getLogger(__name__)


def get_chat_model(json_mode: bool = True) -> BaseChatModel:
    """Create primary chat model with Groq fallback and explicit JSON formatting."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

    model_kwargs = {}
    if json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}

    # Primary Model
    primary_llm = ChatGroq(
        model=GROQ_PRIMARY_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=0.0,
        max_tokens=4096,
        model_kwargs=model_kwargs,
    )

    # Fallback Model
    fallback_llm = ChatGroq(
        model=GROQ_FALLBACK_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=0.0,
        max_tokens=4096,
        model_kwargs=model_kwargs,
    )

    return primary_llm.with_fallbacks(
        fallbacks=[fallback_llm],
        exceptions_to_handle=(Exception,),
    )


def parse_llm_json(content: str) -> dict[str, Any]:
    """Extract and parse a JSON object from an LLM response string."""
    if not content or not content.strip():
        raise RuntimeError("LLM returned an empty response string.")

    text = content.strip()

    # Clean potential reasoning tags or code blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

    # Locate outermost JSON braces
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx : end_idx + 1].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to decode JSON from LLM content:\n{content}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("Parsed LLM JSON output must be a valid dictionary object.")

    return data


def extract_text_from_response(response: Any) -> str:
    """Extract text content from various LLM response formats."""
    if not response or not hasattr(response, "content") or not response.content:
        return ""

    content = response.content

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        ).strip()

    return str(content).strip()
