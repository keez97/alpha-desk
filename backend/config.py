import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API (replaces Anthropic direct)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

if not OPENROUTER_API_KEY:
    import warnings
    warnings.warn("OPENROUTER_API_KEY not set. AI features will be unavailable.")

# Available models on OpenRouter
AVAILABLE_MODELS = {
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
    if model_key in AVAILABLE_MODELS:
        _current_model = model_key
        return AVAILABLE_MODELS[model_key]
    raise ValueError(f"Unknown model: {model_key}. Available: {list(AVAILABLE_MODELS.keys())}")


def get_openrouter_model_id() -> str:
    return AVAILABLE_MODELS.get(_current_model, AVAILABLE_MODELS["claude-sonnet-4"])


FDS_API_KEY = os.getenv("FDS_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/alphadesk")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "4"))
