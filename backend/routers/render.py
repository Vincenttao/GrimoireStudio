from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from backend.models import RenderRequest, POVType, DefaultRenderMixer
from backend.crud.storyboard import get_story_ir_block, update_ir_block_html
from backend.crud.entities import get_entity
from backend.services.camera_client import CameraClient, CameraError
from backend.database import get_db_connection, get_project_settings

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


# Dependency injection for testing
_camera_client: Optional[CameraClient] = None


def get_camera_client() -> CameraClient:
    """Get or create Camera client singleton."""
    global _camera_client
    if _camera_client is None:
        _camera_client = CameraClient()
    return _camera_client


@router.post("", response_model=RenderResponse)
async def render_block(request: RenderRequestInput):
    """
    POST /api/v1/render
    Submit a render request for a Story IR Block.

    Camera Agent will generate literary prose based on the IR and render parameters.
    """
    logger.info(f"Render request received for block: {request.ir_block_id}")

    # 1. Fetch the IR block
    ir_block = await get_story_ir_block(request.ir_block_id)
    if not ir_block:
        raise HTTPException(status_code=404, detail=f"IR Block not found: {request.ir_block_id}")

    # 2. Fetch POV character if needed
    pov_character = None
    if request.pov_character_id:
        pov_character = await get_entity(request.pov_character_id)
        if not pov_character:
            raise HTTPException(
                status_code=404,
                detail=f"POV Character not found: {request.pov_character_id}",
            )

    # 3. Call Camera to render
    camera = get_camera_client()
    try:
        content_html = await camera.render(
            ir_block=ir_block,
            pov_type=request.pov_type,
            style_template=request.style_template,
            subtext_ratio=request.subtext_ratio,
            pov_character=pov_character,
        )

        # 4. Update IR block with rendered content
        await update_ir_block_html(request.ir_block_id, content_html)

        return RenderResponse(
            block_id=request.ir_block_id,
            status="completed",
            content_html=content_html,
            message="Render completed successfully.",
        )

    except CameraError as e:
        logger.error(f"Camera render failed: {e}")
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected render error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during render: {str(e)}")


@router.post("/{block_id}/retry", response_model=RenderResponse)
async def retry_render(block_id: str, request: RenderRetryRequest):
    """
    POST /api/v1/render/{block_id}/retry
    Retry rendering with optionally modified parameters.

    The IR Block remains unchanged - only the rendering parameters are updated.
    """
    logger.info(f"Render retry requested for block: {block_id}")

    # Fetch the IR block
    ir_block = await get_story_ir_block(block_id)
    if not ir_block:
        raise HTTPException(status_code=404, detail=f"IR Block not found: {block_id}")

    # Use defaults or override with new parameters
    pov_type = request.pov_type or POVType.OMNISCIENT
    style_template = request.style_template or "Standard"
    subtext_ratio = request.subtext_ratio if request.subtext_ratio is not None else 0.5

    # Call Camera
    camera = get_camera_client()
    try:
        content_html = await camera.render(
            ir_block=ir_block,
            pov_type=pov_type,
            style_template=style_template,
            subtext_ratio=subtext_ratio,
            pov_character=None,  # Retry doesn't support POV character change yet
        )

        # Update IR block with new rendered content
        await update_ir_block_html(block_id, content_html)

        return RenderResponse(
            block_id=block_id,
            status="completed",
            content_html=content_html,
            message="Render retry completed successfully.",
        )

    except CameraError as e:
        logger.error(f"Camera retry render failed: {e}")
        raise HTTPException(status_code=500, detail=f"Render retry failed: {str(e)}")


@router.get("/{block_id}/status")
async def get_render_status(block_id: str):
    """
    GET /api/v1/render/{block_id}/status
    Check the status of a render job.

    Since rendering is synchronous, this checks if the block has content_html.
    """
    ir_block = await get_story_ir_block(block_id)
    if not ir_block:
        raise HTTPException(status_code=404, detail=f"IR Block not found: {block_id}")

    if ir_block.content_html:
        return {
            "block_id": block_id,
            "status": "completed",
            "content_html": ir_block.content_html,
            "message": "Block has been rendered.",
        }
    else:
        return {
            "block_id": block_id,
            "status": "pending",
            "content_html": None,
            "message": "Block has not been rendered yet.",
        }


class AdjustRenderRequest(BaseModel):
    """Request to adjust default render mixer parameters."""

    subtext_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    style_template: Optional[str] = None
    pov_type: Optional[POVType] = None


class AdjustRenderResponse(BaseModel):
    """Response after adjusting render parameters."""

    default_render_mixer: dict
    message: str


@router.post("/adjust", response_model=AdjustRenderResponse)
async def adjust_render_params(request: AdjustRenderRequest):
    """
    POST /api/v1/render/adjust
    Adjust the default render mixer parameters.

    These parameters will be used for subsequent render operations.
    """
    async with get_db_connection() as conn:
        settings = await get_project_settings(conn)

        updates = {}
        if request.subtext_ratio is not None:
            updates["subtext_ratio"] = request.subtext_ratio
        if request.style_template is not None:
            updates["style_template"] = request.style_template
        if request.pov_type is not None:
            updates["pov_type"] = request.pov_type.value

        if updates:
            # Merge with existing defaults
            current = settings.default_render_mixer.model_dump()
            current.update(updates)
            settings.default_render_mixer = DefaultRenderMixer(**current)

            await conn.execute(
                "UPDATE settings SET default_render_mixer_json = ? WHERE id = ?",
                [settings.default_render_mixer.model_dump_json(), "single_row_lock"],
            )
            await conn.commit()

        return AdjustRenderResponse(
            default_render_mixer=settings.default_render_mixer.model_dump(),
            message="Render parameters updated.",
        )
