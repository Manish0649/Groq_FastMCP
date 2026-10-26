import os
from dotenv import load_dotenv

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MCP_PUBLIC_URL = os.getenv("MCP_PUBLIC_URL", "")

# Langfuse Observability
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


def is_groq_configured() -> bool:
    return bool(GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_your_") and not GROQ_API_KEY.startswith("gsk_demo_"))


def is_langfuse_configured() -> bool:
    return bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY and not LANGFUSE_PUBLIC_KEY.startswith("pk-lf-your_"))
