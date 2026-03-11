"""
FinBERT Sentiment Analysis Service.

Provides GPU/CPU-accelerated financial sentiment scoring using ProsusAI/finbert.
The model is loaded once at import time and reused for all subsequent requests.

Output per headline:
  - sentiment: float in [-1, +1]  (positive → +1, negative → -1)
  - label:     'positive' | 'negative' | 'neutral'
  - confidence: float in [0, 1]  (softmax probability of winning class)
  - probabilities: {positive, negative, neutral}

Batch scoring is supported for efficiency (multiple headlines in one forward pass).
"""

import logging
from typing import Dict, Any, List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model singleton – loaded once on first import
# ---------------------------------------------------------------------------
_MODEL_NAME = "ProsusAI/finbert"
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForSequenceClassification] = None
_device: Optional[torch.device] = None
_LABEL_MAP = {0: "positive", 1: "negative", 2: "neutral"}


def _ensure_model_loaded():
    """Lazy-load the FinBERT model on first use."""
    global _tokenizer, _model, _device
    if _model is not None:
        return

    logger.info("Loading FinBERT model (%s)...", _MODEL_NAME)
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    _model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
    _model.to(_device)
    _model.eval()
    logger.info("FinBERT loaded on %s", _device)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_headline(text: str) -> Dict[str, Any]:
    """
    Score a single headline.

    Returns:
        {
            "sentiment": float,       # -1 to +1
            "label": str,             # 'positive'|'negative'|'neutral'
            "confidence": float,      # 0 to 1
            "probabilities": {
                "positive": float,
                "negative": float,
                "neutral": float,
            }
        }
    """
    results = score_batch([text])
    return results[0]


def score_batch(texts: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
    """
    Score a batch of headlines efficiently.

    Args:
        texts: List of headline strings.
        batch_size: Max texts per forward pass (default 32).

    Returns:
        List of score dicts (same order as input).
    """
    _ensure_model_loaded()

    all_results: List[Dict[str, Any]] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]

        inputs = _tokenizer(
            chunk,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512,
        ).to(_device)

        with torch.no_grad():
            outputs = _model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1).cpu().numpy()

        for i, text in enumerate(chunk):
            p_pos = float(probs[i][0])
            p_neg = float(probs[i][1])
            p_neu = float(probs[i][2])

            # Winning class
            label_idx = int(probs[i].argmax())
            label = _LABEL_MAP[label_idx]
            confidence = float(probs[i][label_idx])

            # Continuous score: positive contributes +1, negative -1, neutral 0
            sentiment = p_pos - p_neg  # range [-1, +1]

            all_results.append({
                "text": text,
                "sentiment": round(sentiment, 4),
                "label": label,
                "confidence": round(confidence, 4),
                "probabilities": {
                    "positive": round(p_pos, 4),
                    "negative": round(p_neg, 4),
                    "neutral": round(p_neu, 4),
                },
            })

    return all_results


def is_available() -> bool:
    """Check if FinBERT can be loaded (dependencies present)."""
    try:
        _ensure_model_loaded()
        return _model is not None
    except Exception:
        return False
