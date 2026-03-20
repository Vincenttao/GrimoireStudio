from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel
from backend.models import Entity
from backend.crud import entities

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
