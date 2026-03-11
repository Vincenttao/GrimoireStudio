from fastapi import APIRouter
from typing import Optional
from backend.models import Entity
from backend.crud import entities

router = APIRouter()

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
