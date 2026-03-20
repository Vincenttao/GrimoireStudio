from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
import asyncio
from typing import Optional, List
from loguru import logger
from datetime import datetime
import uuid as uuid_module

from backend.models import (
    TheSpark,
    GrimoireSnapshot,
    GrimoireStateJSON,
    SandboxState,
    StoryIRBlock,
    Branch,
    Entity,
)
from backend.services.websocket_manager import manager, OverrideMessage
from backend.services.maestro_loop import run_maestro_orchestration
from backend.crud.branches import create_branch, get_branch, list_branches
from backend.crud.snapshots import (
    create_snapshot,
    get_snapshot,
    get_latest_snapshot,
    list_snapshots_by_branch,
)

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


class CreateBranchRequest(BaseModel):
    """Request to create a new branch."""

    name: str = Field(..., description="Human-readable branch name")
    origin_snapshot_id: Optional[str] = Field(None, description="Snapshot to branch from")
    parent_branch_id: Optional[str] = Field(None, description="Parent branch ID")


class CreateBranchResponse(BaseModel):
    """Response after creating a branch."""

    branch: Branch
    message: str


class RollbackRequest(BaseModel):
    """Request to rollback to a snapshot."""

    snapshot_id: str = Field(..., description="Snapshot ID to rollback to")


class RollbackResponse(BaseModel):
    """Response after rollback."""

    snapshot_id: str
    branch_id: str
    entities_count: int
    message: str


class BranchListResponse(BaseModel):
    """Response for listing branches."""

    branches: List[Branch]


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
                entities.append(
                    Entity(
                        entity_id=row["entity_id"],
                        type=row["type"],
                        name=row["name"],
                        base_attributes=BaseAttributes.model_validate_json(
                            row["base_attributes_json"]
                        ),
                        current_status=CurrentStatus.model_validate_json(
                            row["current_status_json"]
                        ),
                        is_deleted=bool(row["is_deleted"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )

    # PRE-FLIGHT CHECK: Maestro cannot orchestrate an empty world.
    if not entities:
        logger.warning("Attempted to start spark with zero entities.")
        raise HTTPException(
            status_code=400,
            detail="格里莫 (Grimoire) 为空。请先通过 Muse 或设定页面创建一个角色。没有演员，创世引擎无法开场。",
        )

    # 2. Build the Snapshot for Maestro
    grimoire_snapshot = GrimoireSnapshot(
        snapshot_id="active_snapshot",
        branch_id="main",
        parent_snapshot_id=None,
        triggering_block_id="genesis",
        grimoire_state_json=GrimoireStateJSON(entities=entities),
        created_at=datetime.utcnow(),
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
# Branch Endpoints (V2.0)
# --------------------------
@router.post("/branch", response_model=CreateBranchResponse)
async def create_new_branch(request: CreateBranchRequest):
    """
    POST /api/v1/sandbox/branch
    Create a new story branch.

    Per PRD §3.3: Branching Tree UI with lazy snapshot.
    Creates a metadata-only branch reference.
    """
    logger.info(f"Creating branch: {request.name}")

    # Generate a unique branch ID
    branch_id = f"branch_{uuid_module.uuid4().hex[:8]}"

    # Create the branch
    branch = await create_branch(
        branch_id=branch_id,
        name=request.name,
        origin_snapshot_id=request.origin_snapshot_id,
        parent_branch_id=request.parent_branch_id,
    )

    return CreateBranchResponse(
        branch=branch,
        message=f"Branch '{request.name}' created successfully.",
    )


@router.get("/branches", response_model=BranchListResponse)
async def get_all_branches():
    """
    GET /api/v1/sandbox/branches
    List all branches.
    """
    branches = await list_branches(active_only=False)
    return BranchListResponse(branches=branches)


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_to_snapshot(request: RollbackRequest):
    """
    POST /api/v1/sandbox/rollback
    Rollback the world state to a specific snapshot.

    Per PRD §3.3: Rollback to snapshot.
    Restores all entities from the snapshot's grimoire_state_json.
    """
    logger.info(f"Rolling back to snapshot: {request.snapshot_id}")

    # 1. Fetch the snapshot
    snapshot = await get_snapshot(request.snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot not found: {request.snapshot_id}",
        )

    # 2. Restore entities from snapshot
    from backend.database import get_db_connection
    from backend.models import Entity, BaseAttributes, CurrentStatus

    entities = snapshot.grimoire_state_json.entities
    entities_count = len(entities)

    async with get_db_connection() as conn:
        # Clear current entities (soft delete all)
        await conn.execute("UPDATE entities SET is_deleted = 1")

        # Restore entities from snapshot
        for entity in entities:
            # Check if entity already exists
            cursor = await conn.execute(
                "SELECT entity_id FROM entities WHERE entity_id = ?",
                (entity.entity_id,),
            )
            existing = await cursor.fetchone()

            if existing:
                # Update existing entity
                await conn.execute(
                    """
                    UPDATE entities SET
                        type = ?,
                        name = ?,
                        base_attributes_json = ?,
                        current_status_json = ?,
                        is_deleted = 0,
                        updated_at = ?
                    WHERE entity_id = ?
                    """,
                    (
                        entity.type.value,
                        entity.name,
                        entity.base_attributes.model_dump_json(),
                        entity.current_status.model_dump_json(),
                        datetime.utcnow().isoformat(),
                        entity.entity_id,
                    ),
                )
            else:
                # Insert new entity
                await conn.execute(
                    """
                    INSERT INTO entities (
                        entity_id, type, name, base_attributes_json,
                        current_status_json, is_deleted, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.entity_id,
                        entity.type.value,
                        entity.name,
                        entity.base_attributes.model_dump_json(),
                        entity.current_status.model_dump_json(),
                        0,
                        entity.created_at.isoformat(),
                        datetime.utcnow().isoformat(),
                    ),
                )

        await conn.commit()

    # 3. Broadcast state change
    await manager.broadcast(
        "ROLLBACK_COMPLETE",
        {
            "snapshot_id": request.snapshot_id,
            "entities_count": entities_count,
        },
    )

    return RollbackResponse(
        snapshot_id=request.snapshot_id,
        branch_id=snapshot.branch_id,
        entities_count=entities_count,
        message=f"Rolled back to snapshot. Restored {entities_count} entities.",
    )


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
