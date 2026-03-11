import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Provider Configuration ---
# Supports both Anthropic direct and OpenRouter.
# Priority: ANTHROPIC_API_KEY (direct) > OPENROUTER_API_KEY (proxy)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Determine which provider to use
if ANTHROPIC_API_KEY:
    LLM_PROVIDER = "anthropic"
elif OPENROUTER_API_KEY:
    LLM_PROVIDER = "openrouter"
else:
    LLM_PROVIDER = "none"
    import warnings
    warnings.warn("No LLM API key set (ANTHROPIC_API_KEY or OPENROUTER_API_KEY). AI features will be unavailable.")

# Anthropic model IDs (used when LLM_PROVIDER == "anthropic")
ANTHROPIC_MODELS = {
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-haiku-3.5": "claude-3-5-haiku-20241022",
}

# OpenRouter model IDs (used when LLM_PROVIDER == "openrouter")
OPENROUTER_MODELS = {
    "claude-sonnet-4": "anthropic/claude-sonnet-4",
    "claude-haiku-3.5": "anthropic/claude-3.5-haiku",
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gemini-2.5-pro": "google/gemini-2.5-pro-preview",
    "deepseek-chat": "deepseek/deepseek-chat-v3-0324",
    "llama-4-maverick": "meta-llama/llama-4-maverick",
}

# Default model (can be overridden via env or API)
DEFAULT_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4")
_current_model = DEFAULT_MODEL


def get_current_model() -> str:
    return _current_model


def set_current_model(model_key: str) -> str:
    global _current_model
    models = ANTHROPIC_MODELS if LLM_PROVIDER == "anthropic" else OPENROUTER_MODELS
    if model_key in models:
        _current_model = model_key
        return models[model_key]
    raise ValueError(f"Unknown model: {model_key}. Available: {list(models.keys())}")


def get_model_id() -> str:
    """Get the model ID for the current provider."""
    if LLM_PROVIDER == "anthropic":
        return ANTHROPIC_MODELS.get(_current_model, ANTHROPIC_MODELS["claude-sonnet-4"])
    return OPENROUTER_MODELS.get(_current_model, OPENROUTER_MODELS["claude-sonnet-4"])


# Keep backward compat alias
def get_openrouter_model_id() -> str:
    return get_model_id()


FDS_API_KEY = os.getenv("FDS_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/alphadesk")

# Cache TTL settings (seconds)
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "4"))
CACHE_TTL_QUOTE = int(os.getenv("CACHE_TTL_QUOTE", "60"))           # 1 min for live quotes
CACHE_TTL_HISTORY = int(os.getenv("CACHE_TTL_HISTORY", "3600"))     # 1 hour for daily bars
CACHE_TTL_MACRO = int(os.getenv("CACHE_TTL_MACRO", "900"))          # 15 min for macro data
CACHE_TTL_FUNDAMENTALS = int(os.getenv("CACHE_TTL_FUNDAMENTALS", "14400"))  # 4 hours for fundamentals
CACHE_TTL_SECTOR = int(os.getenv("CACHE_TTL_SECTOR", "300"))        # 5 min for sector data
