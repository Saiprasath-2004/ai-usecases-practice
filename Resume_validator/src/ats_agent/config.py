"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set")
if not OPENROUTER_MODEL:
    raise ValueError("OPENROUTER_MODEL is not set")
