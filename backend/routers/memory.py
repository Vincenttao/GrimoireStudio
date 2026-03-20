from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from backend.crud.memory import insert_memory, search_memories, delete_memories_by_entity

router = APIRouter()


class CreateMemoryRequest(BaseModel):
    entity_id: str = Field(..., description="Entity ID this memory belongs to")
    text: str = Field(..., description="Memory text to embed and store")


class CreateMemoryResponse(BaseModel):
    status: str
    id: int


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., description="Query text for semantic search")
    entity_id: Optional[str] = Field(None, description="Filter by entity ID")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")


class MemoryResult(BaseModel):
    id: int
    entity_id: str
    memory_text: str
    distance: float


class SearchMemoryResponse(BaseModel):
    results: List[MemoryResult]


class DeleteMemoryResponse(BaseModel):
    status: str
    deleted_count: int


@router.post("", response_model=CreateMemoryResponse)
async def create_memory(request: CreateMemoryRequest):
    """
    POST /api/v1/memory
    Create a new memory with embedding for semantic search.
    """
    logger.info(f"Creating memory for entity: {request.entity_id}")

    try:
        memory_id = await insert_memory(request.entity_id, request.text)
        return CreateMemoryResponse(status="created", id=memory_id)
    except ImportError as e:
        logger.error(f"Embedding model not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="Memory embedding service unavailable. Install sentence-transformers.",
        )
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory_endpoint(request: SearchMemoryRequest):
    """
    POST /api/v1/memory/search
    Semantic search across entity memories.
    """
    logger.info(f"Searching memories: '{request.query[:50]}...'")

    try:
        results = await search_memories(
            query=request.query,
            entity_id=request.entity_id,
            top_k=request.top_k,
        )

        return SearchMemoryResponse(results=[MemoryResult(**r) for r in results])
    except ImportError as e:
        logger.error(f"Embedding model not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="Memory embedding service unavailable. Install sentence-transformers.",
        )
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.delete("/entity/{entity_id}", response_model=DeleteMemoryResponse)
async def delete_entity_memories(entity_id: str):
    """
    DELETE /api/v1/memory/entity/{entity_id}
    Delete all memories for a specific entity.
    """
    logger.info(f"Deleting memories for entity: {entity_id}")

    try:
        count = await delete_memories_by_entity(entity_id)
        return DeleteMemoryResponse(status="deleted", deleted_count=count)
    except Exception as e:
        logger.error(f"Failed to delete memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete memories: {str(e)}")
