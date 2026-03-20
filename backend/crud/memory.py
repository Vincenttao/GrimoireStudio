from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from backend.database import get_db_connection

# Singleton embedding model instance
_embedding_model = None


def get_embedding_model():
    """
    Get or create a singleton SentenceTransformer model.
    Uses 'all-MiniLM-L6-v2' which generates 384-dimension embeddings.
    """
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "sentence-transformers package required for embedding functionality. "
                "Install with: pip install sentence-transformers"
            )

    return _embedding_model


def serialize_embedding(vector: np.ndarray) -> bytes:
    """
    Convert numpy array to bytes for storing in sqlite-vec.
    The sqlite-vec library expects float32 format.
    """
    import sqlite_vec

    return sqlite_vec.serialize_float32(vector.astype(np.float32))


async def insert_memory(entity_id: str, text: str) -> int:
    """
    Insert a new memory with automatically generated embedding.

    Args:
        entity_id: The ID of the entity this memory belongs to
        text: The text content to be embedded and stored

    Returns:
        The ID of the inserted memory record
    """
    # Generate embedding for the text
    model = get_embedding_model()
    embedding = model.encode(text)

    # Serialize embedding for sqlite-vec
    serialized_embedding = serialize_embedding(embedding)

    async with get_db_connection() as conn:
        # Prepare the insertion statement
        cursor = await conn.execute(
            """
            INSERT INTO memory_vectors (content_embedding, entity_id, memory_text, created_at)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            (serialized_embedding, entity_id, text, datetime.now().isoformat()),
        )
        result = await cursor.fetchone()
        await conn.commit()

        if result:
            return result["id"]
        else:
            raise Exception("Failed to insert memory")


async def search_memories(
    query: str, entity_id: Optional[str] = None, top_k: int = 5
) -> List[Dict]:
    """
    Perform semantic search on memories.

    Args:
        query: The query text to find similar memories
        entity_id: Optional filter to search memories for a specific entity
        top_k: Number of top results to return

    Returns:
        List of dictionaries containing memory info and distance score
    """
    # Generate embedding for the query
    model = get_embedding_model()
    query_embedding = model.encode(query)

    # Serialize embedding for sqlite-vec
    serialized_query_embedding = serialize_embedding(query_embedding)

    async with get_db_connection() as conn:
        if entity_id:
            # Search within a specific entity with entity filter
            query_sql = """
                SELECT id, entity_id, memory_text, distance
                FROM memory_vectors
                WHERE content_embedding MATCH ? AND entity_id = ? AND k = ?
                ORDER BY distance
            """
            cursor = await conn.execute(query_sql, (serialized_query_embedding, entity_id, top_k))
        else:
            # Search across all entities
            query_sql = """
                SELECT id, entity_id, memory_text, distance
                FROM memory_vectors
                WHERE content_embedding MATCH ? AND k = ?
                ORDER BY distance
            """
            cursor = await conn.execute(query_sql, (serialized_query_embedding, top_k))

        rows = await cursor.fetchall()

        # Format results
        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "entity_id": row["entity_id"],
                    "memory_text": row["memory_text"],
                    "distance": row["distance"],
                }
            )

        return results


async def delete_memories_by_entity(entity_id: str) -> int:
    """
    Delete all memories associated with a specific entity.

    Args:
        entity_id: The entity ID whose memories should be deleted

    Returns:
        Number of deleted records
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            DELETE FROM memory_vectors
            WHERE entity_id = ?
            """,
            (entity_id,),
        )
        await conn.commit()
        return cursor.rowcount
