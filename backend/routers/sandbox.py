from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio
from typing import Optional
from loguru import logger
from datetime import datetime

from backend.models import (
    TheSpark, GrimoireSnapshot, GrimoireStateJSON, 
    SandboxState, StoryIRBlock
)
from backend.services.websocket_manager import manager, OverrideMessage
from backend.services.maestro_loop import run_maestro_orchestration

router = APIRouter()

# --------------------------
# Models
# --------------------------
class OverrideRequest(BaseModel):
    entity_id: str
    new_directive: str

class CommitRequest(BaseModel):
    ir_block_id: str
    final_content_html: str

# --------------------------
# State Endpoints
# --------------------------
@router.get("/state")
async def get_sandbox_state():
    """Returns the current state of the global Sandbox (Simplified for MVP single-user)."""
    # For a real multi-user app we would fetch this from Redis.
    # MVP Monolith: Query the manager or a global var. 
    return {"state": SandboxState.IDLE}

# --------------------------
# Action Endpoints
# --------------------------
@router.post("/spark", status_code=202)
async def trigger_spark(spark: TheSpark, background_tasks: BackgroundTasks):
    """
    POST /api/v1/sandbox/spark
    Ingests the prompt and fires the background Orchestration Loop.
    """
    logger.info(f"Received Spark: {spark.spark_id} for Chapter {spark.chapter_id}")
    
    from backend.database import get_db_connection
    from backend.models import Entity, BaseAttributes, CurrentStatus
    import json

    # 1. Fetch active entities from DB to populate the snapshot
    entities = []
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM entities WHERE is_deleted = 0") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                entities.append(Entity(
                    entity_id=row["entity_id"],
                    type=row["type"],
                    name=row["name"],
                    base_attributes=BaseAttributes.model_validate_json(row["base_attributes_json"]),
                    current_status=CurrentStatus.model_validate_json(row["current_status_json"]),
                    is_deleted=bool(row["is_deleted"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"])
                ))

    # PRE-FLIGHT CHECK: Maestro cannot orchestrate an empty world.
    if not entities:
        logger.warning("Attempted to start spark with zero entities.")
        raise HTTPException(
            status_code=400, 
            detail="格里莫 (Grimoire) 为空。请先通过 Muse 或设定页面创建一个角色。没有演员，创世引擎无法开场。"
        )

    # 2. Build the Snapshot for Maestro
    grimoire_snapshot = GrimoireSnapshot(
        snapshot_id="active_snapshot",
        branch_id="main",
        parent_snapshot_id=None,
        triggering_block_id="genesis",
        grimoire_state_json=GrimoireStateJSON(entities=entities),
        created_at=datetime.utcnow()
    )
    
    # 3. Fire the Async Task
    task = asyncio.create_task(run_maestro_orchestration(spark, grimoire_snapshot))
    
    # 4. Register for possible Cut tracking
    manager.register_task(spark.spark_id, task)
    
    return {"message": "Accepted", "spark_id": spark.spark_id}

@router.post("/override")
async def inject_override(spark_id: str, request: OverrideRequest):
    """
    POST /api/v1/sandbox/override
    Adds a God Directive to the override MQ for the next Maestro Evaluation beat.
    """
    q = manager.get_ws_override_queue(spark_id)
    q.push(OverrideMessage(entity_id=request.entity_id, new_directive=request.new_directive))
    return {"status": "Override Queued"}

@router.post("/commit")
async def commit_ir_block(request: CommitRequest):
    """
    POST /api/v1/sandbox/commit
    Finalizes the IR block, saves the final HTML, and triggers Scribe delta updates.
    """
    logger.info(f"Committing IR Block {request.ir_block_id} with final HTML.")
    
    # Mock transition to IDLE per SPEC §3.1 End State
    await manager.broadcast("STATE_CHANGE", {"state": SandboxState.IDLE})
    return {"status": "Committed"}

# --------------------------
# WebSocket Endpoint
# --------------------------
@router.websocket("")
async def sandbox_websocket(websocket: WebSocket):
    """
    ws://{host}/ws/sandbox Route handler.
    Dual-channel IPC for state streams (down) and cut commands (up).
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Client → Server Handle
            if "Action" in data:
                if data["Action"] == "CUT":
                    spark_id = data.get("spark_id")
                    if spark_id:
                        manager.cancel_task(spark_id)
                
                elif data["Action"] == "OVERRIDE":
                    spark_id = data.get("spark_id")
                    entity_id = data.get("entity_id")
                    new_directive = data.get("new_directive")
                    if spark_id and entity_id and new_directive:
                        q = manager.get_ws_override_queue(spark_id)
                        q.push(OverrideMessage(entity_id, new_directive))
                        
    except WebSocketDisconnect:
        manager.disconnect()
