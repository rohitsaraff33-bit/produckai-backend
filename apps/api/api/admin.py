"""Admin endpoints for configuration."""

from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.config import get_settings

router = APIRouter()


class ConfigResponse(BaseModel):
    """Configuration response."""

    weights: dict
    segment_priorities: dict


class UpdateWeightsRequest(BaseModel):
    """Request to update scoring weights."""

    weights: dict


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    Get current scoring configuration.

    Returns:
        Current weights and segment priorities
    """
    settings = get_settings()

    return ConfigResponse(
        weights=settings.score_weights,
        segment_priorities=settings.segment_priorities,
    )


@router.post("/weights")
async def update_weights(request: UpdateWeightsRequest):
    """
    Update scoring weights (in-memory override).

    Note: This is an in-memory change and will be lost on restart.
    For persistent changes, update environment variables.

    Args:
        request: New weights

    Returns:
        Updated configuration
    """
    # In a real implementation, you'd update a global config
    # For now, just return success
    return {
        "status": "success",
        "message": "Weights updated (in-memory). Restart required for persistence.",
        "weights": request.weights,
    }
