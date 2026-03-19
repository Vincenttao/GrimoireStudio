from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from backend.models import RenderRequest, POVType

router = APIRouter()


class RenderRequestInput(BaseModel):
    ir_block_id: str
    pov_type: POVType
    pov_character_id: Optional[str] = None
    style_template: str = "Standard"
    subtext_ratio: float = 0.5


class RenderResponse(BaseModel):
    block_id: str
    status: str
    content_html: Optional[str] = None
    message: str


class RenderRetryRequest(BaseModel):
    pov_type: Optional[POVType] = None
    style_template: Optional[str] = None
    subtext_ratio: Optional[float] = None


@router.post("", response_model=RenderResponse)
async def render_block(request: RenderRequestInput):
    """
    POST /api/v1/render
    Submit a render request for a Story IR Block.

    Camera Agent will generate literary prose based on the IR and render parameters.
    """
    logger.info(f"Render request received for block: {request.ir_block_id}")

    return RenderResponse(
        block_id=request.ir_block_id,
        status="queued",
        content_html=None,
        message="Render request accepted. Camera Agent processing... (V2.0 implementation pending)",
    )


@router.post("/{block_id}/retry", response_model=RenderResponse)
async def retry_render(block_id: str, request: RenderRetryRequest):
    """
    POST /api/v1/render/{block_id}/retry
    Retry rendering with optionally modified parameters.

    The IR Block remains unchanged - only the rendering parameters are updated.
    """
    logger.info(f"Render retry requested for block: {block_id}")

    return RenderResponse(
        block_id=block_id,
        status="queued",
        content_html=None,
        message="Render retry accepted. Camera Agent re-processing... (V2.0 implementation pending)",
    )


@router.get("/{block_id}/status")
async def get_render_status(block_id: str):
    """
    GET /api/v1/render/{block_id}/status
    Check the status of a render job.
    """
    return {
        "block_id": block_id,
        "status": "pending",
        "message": "Render status endpoint - V2.0 implementation pending",
    }
