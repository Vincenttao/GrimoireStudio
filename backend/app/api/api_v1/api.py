from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, projects, generation, entities, blocks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(blocks.router, prefix="/blocks", tags=["blocks"])
