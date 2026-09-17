"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
FALLBACK_OPENROUTER_MODEL = os.getenv("FALLBACK_OPENROUTER_MODEL")

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Active Free/Developer Tier Groq Models
GROQ_PRIMARY_MODEL = os.getenv("GROQ_PRIMARY_MODEL", "openai/gpt-oss-20b")
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "llama3-8b-8192")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set")
if not OPENROUTER_MODEL:
    raise ValueError("OPENROUTER_MODEL is not set")
if not FALLBACK_OPENROUTER_MODEL:
    raise ValueError("FALLBACK_OPENROUTER_MODEL is not set")
