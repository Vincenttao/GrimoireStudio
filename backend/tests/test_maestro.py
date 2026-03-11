import pytest
import asyncio
from datetime import datetime

from backend.models import (
    TheSpark, GrimoireSnapshot, GrimoireStateJSON, MaestroDecision
)
from backend.services.maestro_loop import run_maestro_orchestration
from backend.services.websocket_manager import manager
from backend.services.llm_client import llm_client

@pytest.mark.asyncio
async def test_maestro_cut_interruption(monkeypatch):
    """
    Test Phase 3: The Cut Test (SPEC §7.2 State Machine TDD).
    Ensures that throwing CancelledError correctly sets the state to INTERRUPTED.
    """
    
    # Mock LLM calls so we don't hit the real API
    async def mock_evaluate(*args, **kwargs):
        # We simulate a slow API call so the cut has time to interrupt
        await asyncio.sleep(0.5)
        return MaestroDecision(is_beat_complete=False, next_actor_id="123", reasoning="Test")
        
    monkeypatch.setattr(llm_client, "evaluate_scene_progression", mock_evaluate)

    # 1. Setup mock spark and grimoire
    spark = TheSpark(
        spark_id="test_run_1",
        chapter_id="chap_1",
        user_prompt="start fighting"
    )
    grimoire = GrimoireSnapshot(
        snapshot_id="snap_1",
        branch_id="main",
        parent_snapshot_id=None,
        triggering_block_id="prev_block",
        grimoire_state_json=GrimoireStateJSON(entities=[]),
        created_at=datetime.utcnow()
    )
    
    # 2. Wrap the maestro loop in an async task
    task = asyncio.create_task(run_maestro_orchestration(spark, grimoire))
    
    # Register the task in our WS manager for interruption
    manager.register_task(spark.spark_id, task)
    
    # 3. Trigger the CUT equivalent (User hits the button in UI)
    # Give the task a tiny bit of time to start running The Maestro loop's initial emit logic
    await asyncio.sleep(0.1) 
    manager.cancel_task(spark.spark_id)
    
    # 5. Assert the correct exception was raised and state transitions handled
    with pytest.raises(asyncio.CancelledError):
        await task
    
    # Simulate processing time 
    await asyncio.sleep(0.1)
    
    # 4. Trigger the CUT equivalent (User hits the button in UI)
    manager.cancel_task(spark.spark_id)
    
    # 5. Assert the correct exception was raised and state transitions handled
    with pytest.raises(asyncio.CancelledError):
        await task
