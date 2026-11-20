import os

from dotenv import load_dotenv

load_dotenv()

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

# PostgreSQL configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Langfuse observability configuration
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_BASE_URL = os.getenv(
    "LANGFUSE_BASE_URL",
    "https://cloud.langfuse.com",
)

# Validate required configuration
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing from .env")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

# Langfuse is optional
LANGFUSE_ENABLED = bool(
    LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
)