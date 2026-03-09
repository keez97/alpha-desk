from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import (
    AVAILABLE_MODELS,
    get_current_model,
    set_current_model,
    get_openrouter_model_id,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ModelSelection(BaseModel):
    model: str


@router.get("/models")
async def list_models():
    """List available LLM models and the currently selected one."""
    current = get_current_model()
    return {
        "current": current,
        "current_id": get_openrouter_model_id(),
        "available": [
            {"key": key, "openrouter_id": oid}
            for key, oid in AVAILABLE_MODELS.items()
        ],
    }


@router.post("/models")
async def switch_model(selection: ModelSelection):
    """Switch the active LLM model."""
    try:
        new_id = set_current_model(selection.model)
        return {
            "current": selection.model,
            "current_id": new_id,
            "message": f"Switched to {selection.model}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
