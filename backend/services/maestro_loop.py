import asyncio
from typing import List
from loguru import logger

from backend.models import (
    SandboxState, TheSpark, GrimoireSnapshot, 
    StoryIRBlock, CharacterAction
)
from backend.services.websocket_manager import manager
from backend.services.llm_client import llm_client

class Scratchpad:
    """In-Memory cache for the current orchestration turn."""
    def __init__(self, max_turns: int = 10):
        self.turn_logs: List[CharacterAction] = []
        self.pending_facts: List[str] = []
        self.max_turns = max_turns

    def clear(self):
        self.turn_logs.clear()
        self.pending_facts.clear()

async def persist_to_sqlite(ir_block: StoryIRBlock):
    """
    Mock saving block for Phase 3. Real integration happens in Phase 4.
    """
    logger.info(f"Persisted IR Block: {ir_block.block_id}")

async def run_maestro_orchestration(spark: TheSpark, grimoire_snapshot: GrimoireSnapshot):
    """
    The Maestro Loop logic strictly mirroring SPEC.md §3.1
    """
    scratchpad = Scratchpad(max_turns=10)
    override_queue = manager.get_ws_override_queue(spark.spark_id)
    
    # 0. Broadcast launch
    current_state = SandboxState.SPARK_RECEIVED
    await manager.broadcast("STATE_CHANGE", {"state": current_state})
    
    current_state = SandboxState.REASONING

    try:
        for turn in range(scratchpad.max_turns):
            # Broadcast state
            await manager.broadcast("STATE_CHANGE", {"state": current_state})
            await manager.broadcast("TURN_STARTED", {"turn": turn})

            # 2. Orchestration Decision
            # Mocking standard inputs for now
            entities_json = grimoire_snapshot.grimoire_state_json.model_dump_json()
            history_json = "\n".join([t.action for t in scratchpad.turn_logs])
            
            decision = await llm_client.evaluate_scene_progression(
                prompt=spark.user_prompt,
                entities_json=entities_json,
                history_json=history_json
            )
            await manager.broadcast("SYS_DEV_LOG", {"reasoning": decision.reasoning})
            
            if decision.is_beat_complete:
                current_state = SandboxState.EMITTING_IR
                break

            current_state = SandboxState.CALLING_CHARACTER
            await manager.broadcast("STATE_CHANGE", {"state": current_state})
            
            # 3. 3-Layer Prompting
            if decision.next_actor_id is None:
                logger.warning("Maestro returned null next_actor_id but sequence is not complete.")
                break
                
            await manager.broadcast("DISPATCH", {"actor_id": decision.next_actor_id})
            
            # Find actor entity
            actor = next((e for e in grimoire_snapshot.grimoire_state_json.entities if e.entity_id == decision.next_actor_id), None)
            if not actor:
                raise ValueError(f"Actor {decision.next_actor_id} not found in Grimoire Snapshot.")

            director_note = spark.overrides.get(decision.next_actor_id, "")
            
            char_response = await llm_client.generate_character_action(
                actor=actor,
                history=scratchpad.turn_logs,
                director_note=director_note,
                scene_context="MVP Room" # Hardcoded for now
            )
            
            # 4. Save and Evaluate
            scratchpad.turn_logs.append(char_response)
            current_state = SandboxState.EVALUATING
            await manager.broadcast("STATE_CHANGE", {"state": current_state})

            # 5. Process Pending Overrides (Injecting God Interventions between LLM generations)
            if override_queue.has_pending():
                latest_override = override_queue.pop_all()[-1]
                spark.overrides[latest_override.entity_id] = latest_override.new_directive
                # Forced evaluation re-try for next loop
                continue 

            # 6. Tension Score
            evaluation = await llm_client.score_character_output(
                char_response=char_response, 
                history_json=history_json
            )
            
            if not evaluation.is_valid:
                scratchpad.turn_logs.pop() # Rollback illegal move
                await manager.broadcast("SYS_DEV_LOG", {"reject": evaluation.reject_reason})
                current_state = SandboxState.REASONING
                # Continue loop to force Maestro to reason again
                continue
                
            # If valid, go back to reasoning for next actor
            current_state = SandboxState.REASONING
        
        # 7. Fallback Block
        if current_state != SandboxState.EMITTING_IR:
            await manager.broadcast("SYS_DEV_LOG", {"warning": "Max turns reached, forcing IR extraction."})
            
        current_state = SandboxState.EMITTING_IR
        await manager.broadcast("STATE_CHANGE", {"state": current_state})
        
        # Real extraction happens later
        # ir_block = await llm_client.extract_story_ir(scratchpad.turn_logs, spark.chapter_id)
        # await persist_to_sqlite(ir_block)
        
        # NOTE: Do NOT jump to IDLE immediately, wait for user COMMIT (per SPEC edge cases)
        await manager.broadcast("SCENE_COMPLETE", {"ir_block": "MOCK_IR_BLOCK_FOR_NOW"})

    except asyncio.CancelledError:
        # User CUT
        current_state = SandboxState.INTERRUPTED
        scratchpad.clear()
        await manager.broadcast("STATE_CHANGE", {"state": current_state})
        await manager.broadcast("ERROR", {"message": "推演已被造物主强行切断 (Cut)。", "code": "ERR_CUT"})
        raise 
        
    except Exception as e:
        await manager.broadcast("ERROR", {"message": f"系统崩溃: {str(e)}", "code": "ERR_SYS"})
        raise
