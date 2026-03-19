import asyncio
from typing import List
from loguru import logger
from datetime import datetime
import json

from backend.models import (
    SandboxState,
    TheSpark,
    GrimoireSnapshot,
    StoryIRBlock,
    CharacterAction,
)
from backend.services.websocket_manager import manager
from backend.services.llm_client import llm_client
from backend.database import get_db_connection


class Scratchpad:
    """In-Memory cache for the current orchestration turn."""

    def __init__(self, max_turns: int = 10):
        self.turn_logs: List[CharacterAction] = []
        self.pending_facts: List[str] = []
        self.max_turns = max_turns

    def clear(self):
        self.turn_logs.clear()
        self.pending_facts.clear()

    def to_checkpoint_json(self, current_turn: int) -> dict:
        return {
            "turn_logs": [t.model_dump() for t in self.turn_logs],
            "pending_facts": self.pending_facts,
            "current_turn": current_turn,
        }


async def save_checkpoint(spark_id: str, scratchpad: "Scratchpad", current_turn: int):
    checkpoint = scratchpad.to_checkpoint_json(current_turn)
    async with get_db_connection() as conn:
        await conn.execute(
            """INSERT OR REPLACE INTO scratchpad_checkpoints 
               (spark_id, turn_logs_json, pending_facts_json, current_turn, created_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                spark_id,
                json.dumps(checkpoint["turn_logs"]),
                json.dumps(checkpoint["pending_facts"]),
                checkpoint["current_turn"],
                datetime.utcnow().isoformat(),
            ),
        )
        await conn.commit()
    logger.info(
        f"[Checkpoint] Saved scratchpad state for spark {spark_id} at turn {current_turn}"
    )


async def load_checkpoint(spark_id: str) -> tuple["Scratchpad", int] | None:
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM scratchpad_checkpoints WHERE spark_id = ?", (spark_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                scratchpad = Scratchpad()
                scratchpad.turn_logs = [
                    CharacterAction(**t) for t in json.loads(row["turn_logs_json"])
                ]
                scratchpad.pending_facts = json.loads(row["pending_facts_json"])
                return scratchpad, row["current_turn"]
    return None


async def clear_checkpoint(spark_id: str):
    async with get_db_connection() as conn:
        await conn.execute(
            "DELETE FROM scratchpad_checkpoints WHERE spark_id = ?", (spark_id,)
        )
        await conn.commit()
    logger.info(f"[Checkpoint] Cleared checkpoint for spark {spark_id}")


async def persist_to_sqlite(ir_block: StoryIRBlock):
    """
    Mock saving block for Phase 3. Real integration happens in Phase 4.
    """
    logger.info(f"Persisted IR Block: {ir_block.block_id}")


async def run_maestro_orchestration(
    spark: TheSpark, grimoire_snapshot: GrimoireSnapshot
):
    """
    The Maestro Loop logic strictly mirroring SPEC.md §3.1
    """
    logger.info(f"Starting Maestro Orchestration for Spark: {spark.spark_id}")
    scratchpad = Scratchpad(max_turns=10)
    override_queue = manager.get_ws_override_queue(spark.spark_id)

    # 0. Broadcast launch
    current_state = SandboxState.SPARK_RECEIVED
    await manager.broadcast("STATE_CHANGE", {"state": current_state})
    logger.info(f"State transition: -> {current_state}")

    current_state = SandboxState.REASONING
    turn = 0

    try:
        for turn in range(scratchpad.max_turns):
            logger.info(f"--- Starting Turn {turn} ---")
            # Broadcast state
            await manager.broadcast("STATE_CHANGE", {"state": current_state})
            await manager.broadcast("TURN_STARTED", {"turn": turn})

            # 2. Orchestration Decision
            entities_json = grimoire_snapshot.grimoire_state_json.model_dump_json()
            history_json = "\n".join([t.action for t in scratchpad.turn_logs])

            logger.info("Calling Maestro to evaluate scene progression...")
            decision = await llm_client.evaluate_scene_progression(
                prompt=spark.user_prompt,
                entities_json=entities_json,
                history_json=history_json,
            )
            logger.info(f"Maestro Decision: {decision.model_dump_json()}")
            await manager.broadcast("SYS_DEV_LOG", {"reasoning": decision.reasoning})

            if decision.is_beat_complete:
                current_state = SandboxState.EMITTING_IR
                break

            current_state = SandboxState.CALLING_CHARACTER
            await manager.broadcast("STATE_CHANGE", {"state": current_state})

            # 3. 3-Layer Prompting
            if decision.next_actor_id is None:
                logger.warning(
                    "Maestro returned null next_actor_id but sequence is not complete."
                )
                break

            await manager.broadcast("DISPATCH", {"actor_id": decision.next_actor_id})

            # Find actor entity
            actor = next(
                (
                    e
                    for e in grimoire_snapshot.grimoire_state_json.entities
                    if e.entity_id == decision.next_actor_id
                ),
                None,
            )
            if not actor:
                raise ValueError(
                    f"Actor {decision.next_actor_id} not found in Grimoire Snapshot."
                )

            director_note = spark.overrides.get(decision.next_actor_id, "")

            char_response = await llm_client.generate_character_action(
                actor=actor,
                history=scratchpad.turn_logs,
                director_note=director_note,
                scene_context="MVP Room",  # Hardcoded for now
            )

            # 4. Save and Evaluate
            scratchpad.turn_logs.append(char_response)
            current_state = SandboxState.EVALUATING
            await manager.broadcast("STATE_CHANGE", {"state": current_state})

            # Checkpoint: Save state every 3 turns for crash recovery
            CHECKPOINT_INTERVAL = 3
            if turn > 0 and turn % CHECKPOINT_INTERVAL == 0:
                await save_checkpoint(spark.spark_id, scratchpad, turn)

            # 5. Process Pending Overrides (Injecting God Interventions between LLM generations)
            if override_queue.has_pending():
                latest_override = override_queue.pop_all()[-1]
                spark.overrides[latest_override.entity_id] = (
                    latest_override.new_directive
                )
                # Forced evaluation re-try for next loop
                continue

            # 6. Tension Score
            evaluation = await llm_client.score_character_output(
                char_response=char_response, history_json=history_json
            )

            if not evaluation.is_valid:
                scratchpad.turn_logs.pop()  # Rollback illegal move
                await manager.broadcast(
                    "SYS_DEV_LOG", {"reject": evaluation.reject_reason}
                )
                current_state = SandboxState.REASONING
                # Continue loop to force Maestro to reason again
                continue

            # If valid, go back to reasoning for next actor
            current_state = SandboxState.REASONING

        # 7. Fallback Block
        if current_state != SandboxState.EMITTING_IR:
            logger.info("Max turns reached or loop interrupted, forcing EMITTING_IR")
            await manager.broadcast(
                "SYS_DEV_LOG", {"warning": "Max turns reached, forcing IR extraction."}
            )

        current_state = SandboxState.EMITTING_IR
        logger.info(f"Final State transition: -> {current_state}")
        await manager.broadcast("STATE_CHANGE", {"state": current_state})

        # Real extraction happens later
        # ir_block = await llm_client.extract_story_ir(scratchpad.turn_logs, spark.chapter_id)
        # await persist_to_sqlite(ir_block)

        # Clear checkpoint on successful completion
        await clear_checkpoint(spark.spark_id)

        # NOTE: Do NOT jump to IDLE immediately, wait for user COMMIT (per SPEC edge cases)
        logger.info("Orchestration loop finished. Waiting for user commit.")
        await manager.broadcast("SCENE_COMPLETE", {"ir_block": "MOCK_IR_BLOCK_FOR_NOW"})

    except asyncio.CancelledError:
        # User CUT
        current_state = SandboxState.INTERRUPTED
        scratchpad.clear()
        await clear_checkpoint(spark.spark_id)
        await manager.broadcast("STATE_CHANGE", {"state": current_state})
        await manager.broadcast(
            "ERROR", {"message": "推演已被造物主强行切断 (Cut)。", "code": "ERR_CUT"}
        )
        raise

    except Exception as e:
        # Save checkpoint on error for potential recovery
        current_turn = turn if "turn" in dir() and isinstance(turn, int) else 0
        await save_checkpoint(spark.spark_id, scratchpad, current_turn)
        await manager.broadcast(
            "ERROR", {"message": f"系统崩溃: {str(e)}", "code": "ERR_SYS"}
        )
        raise
