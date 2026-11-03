"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
FALLBACK_OPENROUTER_MODEL = os.getenv("FALLBACK_OPENROUTER_MODEL")

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    import warnings
    warnings.warn(
        "GROQ_API_KEY is not set. The app will start, but evaluating "
        "resumes (which calls the LLM) will fail until you set it in .env.",
        stacklevel=2,
    )

# Active Free/Developer Tier Groq Models
GROQ_PRIMARY_MODEL = os.getenv("GROQ_PRIMARY_MODEL", "openai/gpt-oss-20b")
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "llama3-8b-8192")

EXTRACTION_MAX_RETRIES = int(os.getenv("EXTRACTION_MAX_RETRIES", "2"))

# Decision Thresholds
SELECT_CUTOFF = float(os.getenv("SELECT_CUTOFF", "70.0"))
REJECT_FLOOR = float(os.getenv("REJECT_FLOOR", "35.0"))

# Follow-up Configuration
FOLLOWUP_MAX_QUESTIONS = int(os.getenv("FOLLOWUP_MAX_QUESTIONS", "3"))
FOLLOWUP_TIMEOUT_DAYS = int(os.getenv("FOLLOWUP_TIMEOUT_DAYS", "7"))

# Persistence Configuration
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.sqlite")

# Actions Configuration
ACTIONS_DB_PATH = os.getenv("ACTIONS_DB_PATH", "actions_outbox.sqlite")
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "MOCK")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "mock-key-12345")
EMAIL_SENDER_ADDRESS = os.getenv("EMAIL_SENDER_ADDRESS", "recruiter@company.com")
