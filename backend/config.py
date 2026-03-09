import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    import warnings
    warnings.warn("ANTHROPIC_API_KEY not set. AI features will be unavailable.")

FDS_API_KEY = os.getenv("FDS_API_KEY", "7db85f55-5abb-4ee0-8253-fb5e0317e134")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./alphadesk.db")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "4"))
