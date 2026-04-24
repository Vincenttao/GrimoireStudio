from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.crud import entities, soft_patches
from backend.models import Entity, SoftPatch

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = "all"


@router.get("/entities")
async def get_entities(type: Optional[str] = None):
    res = await entities.list_entities(type)
    return {"entities": res}


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    res = await entities.get_entity(entity_id)
    return {"entity": res}


@router.post("/entities")
async def create_entity(entity: Entity):
    res = await entities.create_entity(entity)
    return {"status": "created", "entity": res}


@router.patch("/entities/{entity_id}")
async def patch_entity(entity_id: str, payload: dict):
    res = await entities.update_entity(entity_id, payload)
    return {"status": "patched", "entity": res}


@router.delete("/entities/{entity_id}")
async def soft_delete_entity(entity_id: str):
    success = await entities.soft_delete_entity(entity_id)
    return {"status": "soft_deleted" if success else "not_found"}


# ==========================================
# V1.1: SoftPatch (事实修订软层 delta)
# ==========================================


class CreateSoftPatchRequest(BaseModel):
    target_entity_id: str = Field(..., description="要修订的实体 ID")
    target_path: str = Field(
        ...,
        description="JSONPath，如 'current_status.inventory' 或 'base_attributes.personality'",
    )
    new_value: Any = Field(..., description="修订后的新值")
    author_note: str = Field(..., description="作者改动原因")


class SoftPatchResponse(BaseModel):
    patch: SoftPatch
    message: str


@router.post("/soft_patches", response_model=SoftPatchResponse)
async def create_soft_patch_endpoint(request: CreateSoftPatchRequest):
    """
    POST /api/v1/grimoire/soft_patches
    创建一条软层事实修订 patch。不影响历史快照，只在当前状态上 overlay。
    下次 Commit 时合并。
    """
    entity = await entities.get_entity(request.target_entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {request.target_entity_id}")

    # 提取 old_value 用于记录
    data = entity.model_dump()
    old_value: Any = None
    cursor = data
    for part in request.target_path.split("."):
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            cursor = None
            break
    old_value = cursor

    patch = await soft_patches.create_soft_patch(
        target_entity_id=request.target_entity_id,
        target_path=request.target_path,
        old_value=old_value,
        new_value=request.new_value,
        author_note=request.author_note,
    )
    return SoftPatchResponse(patch=patch, message="软层事实修订已登记，下次 Commit 时合并入快照。")


@router.get("/soft_patches", response_model=dict)
async def list_pending_soft_patches(entity_id: Optional[str] = None):
    """GET /api/v1/grimoire/soft_patches?entity_id=... — 列出 PENDING patches"""
    patches = await soft_patches.list_pending_patches(entity_id)
    return {"patches": [p.model_dump() for p in patches], "count": len(patches)}


@router.delete("/soft_patches/{patch_id}")
async def discard_soft_patch(patch_id: str):
    """DELETE /api/v1/grimoire/soft_patches/{id} — 撤销一条 pending patch"""
    ok = await soft_patches.discard_patch(patch_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Patch not found or already merged")
    return {"status": "discarded"}


@router.get("/entities/{entity_id}/effective")
async def get_entity_with_patches(entity_id: str):
    """
    GET /api/v1/grimoire/entities/{id}/effective
    返回实体当前状态 overlay 所有 PENDING SoftPatch 之后的"有效值"。
    """
    entity = await entities.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

    pending = await soft_patches.list_pending_patches(entity_id)
    data = entity.model_dump()
    for p in pending:
        data = soft_patches.apply_patch_to_dict(data, p.target_path, p.new_value)

    return {"entity": data, "applied_patch_count": len(pending)}


@router.post("/entities/query")
async def query_entities(request: QueryRequest):
    """
    POST /api/v1/grimoire/entities/query

    Query endpoint for query_memory tool call.
    Returns all entities with their memories for world state queries.

    Args:
        request: QueryRequest with query field (currently only "all" supported)

    Returns:
        {"entities": [...]} - List of entities with full data including memories
    """
    all_entities = await entities.list_entities()

    # Return entities with their memories
    # For now, we return all entities (query="all")
    # Future: could implement filtering by memory content
    return {
        "entities": [e.model_dump() for e in all_entities],
        "query": request.query,
        "count": len(all_entities),
    }
