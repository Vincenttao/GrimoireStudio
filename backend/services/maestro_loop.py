import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

from loguru import logger

from backend.database import get_db_connection
from backend.models import (
    CharacterAction,
    GrimoireSnapshot,
    SandboxState,
    StoryIRBlock,
    TheSpark,
)
from backend.services.llm_client import llm_client
from backend.services.websocket_manager import manager

# ==========================================
# V1.1: JSONL Scratchpad — crash-resilient Turn Log
# ==========================================

SCRATCHPAD_JSONL_PATH = Path(os.getenv("SCRATCHPAD_JSONL_PATH", "scratchpad.jsonl"))


def _scratchpad_append(record: dict) -> None:
    """Append a single record to scratchpad.jsonl. Never throws."""
    try:
        record.setdefault("ts", datetime.utcnow().isoformat())
        SCRATCHPAD_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SCRATCHPAD_JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:  # never block inference on disk errors
        logger.warning(f"[Scratchpad] Append failed (non-fatal): {e}")


def scratchpad_scan_unfinished() -> List[dict]:
    """
    Scan scratchpad.jsonl at startup. Return a list of unfinished traces.
    Each dict: {trace_id, spark_id, last_state, last_turn, events: [...]}
    A trace is "unfinished" if no COMMITTED/INTERRUPTED terminal event is found.
    """
    if not SCRATCHPAD_JSONL_PATH.exists():
        return []

    traces: dict[str, dict] = {}
    try:
        with open(SCRATCHPAD_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = row.get("trace_id") or row.get("spark_id")
                if not tid:
                    continue
                entry = traces.setdefault(
                    tid,
                    {
                        "trace_id": tid,
                        "spark_id": row.get("spark_id"),
                        "events": [],
                        "terminal": False,
                    },
                )
                entry["events"].append(row)
                event_name = row.get("event") or row.get("state")
                if event_name in ("COMMITTED", "INTERRUPTED"):
                    entry["terminal"] = True
    except Exception as e:
        logger.error(f"[Scratchpad] Scan failed: {e}")
        return []

    return [
        {
            "trace_id": t["trace_id"],
            "spark_id": t["spark_id"],
            "last_state": (t["events"][-1].get("state") if t["events"] else None),
            "last_turn": (t["events"][-1].get("turn") if t["events"] else None),
            "events_count": len(t["events"]),
        }
        for t in traces.values()
        if not t["terminal"]
    ]


def scratchpad_compact(keep_terminal_recent: int = 100) -> None:
    """
    Compact scratchpad.jsonl: keep only unfinished + recent-N terminal traces.
    Safe to run at startup.
    """
    if not SCRATCHPAD_JSONL_PATH.exists():
        return
    try:
        traces: dict[str, list[dict]] = {}
        terminal_order: list[str] = []
        with open(SCRATCHPAD_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = row.get("trace_id") or row.get("spark_id")
                if not tid:
                    continue
                traces.setdefault(tid, []).append(row)
                if row.get("event") in ("COMMITTED", "INTERRUPTED") and tid not in terminal_order:
                    terminal_order.append(tid)

        keep_terminal = set(terminal_order[-keep_terminal_recent:])
        kept_lines: list[str] = []
        for tid, rows in traces.items():
            has_terminal = any(r.get("event") in ("COMMITTED", "INTERRUPTED") for r in rows)
            if not has_terminal or tid in keep_terminal:
                for row in rows:
                    kept_lines.append(json.dumps(row, ensure_ascii=False))

        with open(SCRATCHPAD_JSONL_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(kept_lines))
            if kept_lines:
                f.write("\n")
    except Exception as e:
        logger.warning(f"[Scratchpad] Compact failed (non-fatal): {e}")


# ==========================================
# In-memory scratchpad (unchanged) + sqlite checkpoint
# ==========================================


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
    logger.info(f"[Checkpoint] Saved scratchpad state for spark {spark_id} at turn {current_turn}")


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
        await conn.execute("DELETE FROM scratchpad_checkpoints WHERE spark_id = ?", (spark_id,))
        await conn.commit()
    logger.info(f"[Checkpoint] Cleared checkpoint for spark {spark_id}")


async def persist_to_sqlite(ir_block: StoryIRBlock):
    """Mock saving block for Phase 3. Real integration happens in Phase 4."""
    logger.info(f"Persisted IR Block: {ir_block.block_id}")


# ==========================================
# Orchestration Loop
# ==========================================


async def run_maestro_orchestration(spark: TheSpark, grimoire_snapshot: GrimoireSnapshot):
    """
    The Maestro Loop — V1.1 edition.
    - beat_type 驱动的完成判据
    - JSONL scratchpad 落盘
    """
    logger.info(
        f"Starting Maestro Orchestration for Spark: {spark.spark_id} (beat_type={spark.beat_type})"
    )
    trace_id = spark.spark_id
    scratchpad = Scratchpad(max_turns=10)
    override_queue = manager.get_ws_override_queue(spark.spark_id)

    _scratchpad_append(
        {
            "trace_id": trace_id,
            "spark_id": spark.spark_id,
            "event": "STARTED",
            "beat_type": spark.beat_type.value,
            "target_char_count": spark.target_char_count,
        }
    )

    current_state = SandboxState.SPARK_RECEIVED
    await manager.broadcast("STATE_CHANGE", {"state": current_state})
    _scratchpad_append(
        {"trace_id": trace_id, "spark_id": spark.spark_id, "state": current_state.value}
    )
    logger.info(f"State transition: -> {current_state}")

    current_state = SandboxState.REASONING
    turn = 0

    try:
        for turn in range(scratchpad.max_turns):
            logger.info(f"--- Starting Turn {turn} ---")
            await manager.broadcast("STATE_CHANGE", {"state": current_state})
            await manager.broadcast("TURN_STARTED", {"turn": turn})

            entities_json = grimoire_snapshot.grimoire_state_json.model_dump_json()
            history_json = "\n".join([t.action for t in scratchpad.turn_logs])

            logger.info("Calling Maestro to evaluate scene progression...")
            decision = await llm_client.evaluate_scene_progression(
                prompt=spark.user_prompt,
                entities_json=entities_json,
                history_json=history_json,
                beat_type=spark.beat_type,
            )
            logger.info(f"Maestro Decision: {decision.model_dump_json()}")
            await manager.broadcast("SYS_DEV_LOG", {"reasoning": decision.reasoning})
            _scratchpad_append(
                {
                    "trace_id": trace_id,
                    "spark_id": spark.spark_id,
                    "turn": turn,
                    "event": "MAESTRO_DECISION",
                    "payload": decision.model_dump(),
                }
            )

            if decision.is_beat_complete:
                current_state = SandboxState.EMITTING_IR
                break

            current_state = SandboxState.CALLING_CHARACTER
            await manager.broadcast("STATE_CHANGE", {"state": current_state})
            _scratchpad_append(
                {
                    "trace_id": trace_id,
                    "spark_id": spark.spark_id,
                    "turn": turn,
                    "state": current_state.value,
                }
            )

            if decision.next_actor_id is None:
                logger.warning("Maestro returned null next_actor_id but sequence is not complete.")
                break

            await manager.broadcast("DISPATCH", {"actor_id": decision.next_actor_id})

            actor = next(
                (
                    e
                    for e in grimoire_snapshot.grimoire_state_json.entities
                    if e.entity_id == decision.next_actor_id
                ),
                None,
            )
            if not actor:
                raise ValueError(f"Actor {decision.next_actor_id} not found in Grimoire Snapshot.")

            director_note = spark.overrides.get(decision.next_actor_id, "")

            char_response = await llm_client.generate_character_action(
                actor=actor,
                history=scratchpad.turn_logs,
                director_note=director_note,
                scene_context="MVP Room",
            )

            scratchpad.turn_logs.append(char_response)
            current_state = SandboxState.EVALUATING
            await manager.broadcast("STATE_CHANGE", {"state": current_state})
            _scratchpad_append(
                {
                    "trace_id": trace_id,
                    "spark_id": spark.spark_id,
                    "turn": turn,
                    "state": current_state.value,
                    "actor_id": decision.next_actor_id,
                    "payload": char_response.model_dump(),
                }
            )

            CHECKPOINT_INTERVAL = 3
            if turn > 0 and turn % CHECKPOINT_INTERVAL == 0:
                await save_checkpoint(spark.spark_id, scratchpad, turn)

            if override_queue.has_pending():
                latest_override = override_queue.pop_all()[-1]
                spark.overrides[latest_override.entity_id] = latest_override.new_directive
                continue

            evaluation = await llm_client.score_character_output(
                char_response=char_response, history_json=history_json
            )

            if not evaluation.is_valid:
                scratchpad.turn_logs.pop()
                await manager.broadcast("SYS_DEV_LOG", {"reject": evaluation.reject_reason})
                current_state = SandboxState.REASONING
                continue

            current_state = SandboxState.REASONING

        if current_state != SandboxState.EMITTING_IR:
            logger.info("Max turns reached or loop interrupted, forcing EMITTING_IR")
            await manager.broadcast(
                "SYS_DEV_LOG", {"warning": "Max turns reached, forcing IR extraction."}
            )

        current_state = SandboxState.EMITTING_IR
        logger.info(f"Final State transition: -> {current_state}")
        await manager.broadcast("STATE_CHANGE", {"state": current_state})

        await clear_checkpoint(spark.spark_id)

        logger.info("Orchestration loop finished. Waiting for user commit.")
        await manager.broadcast("SCENE_COMPLETE", {"ir_block": "MOCK_IR_BLOCK_FOR_NOW"})

        _scratchpad_append({"trace_id": trace_id, "spark_id": spark.spark_id, "event": "COMMITTED"})

    except asyncio.CancelledError:
        current_state = SandboxState.INTERRUPTED
        scratchpad.clear()
        await clear_checkpoint(spark.spark_id)
        await manager.broadcast("STATE_CHANGE", {"state": current_state})
        await manager.broadcast(
            "ERROR", {"message": "推演已被造物主强行切断 (Cut)。", "code": "ERR_CUT"}
        )
        _scratchpad_append(
            {"trace_id": trace_id, "spark_id": spark.spark_id, "event": "INTERRUPTED"}
        )
        raise

    except Exception as e:
        current_turn = turn if "turn" in dir() and isinstance(turn, int) else 0
        await save_checkpoint(spark.spark_id, scratchpad, current_turn)
        await manager.broadcast("ERROR", {"message": f"系统崩溃: {str(e)}", "code": "ERR_SYS"})
        _scratchpad_append(
            {
                "trace_id": trace_id,
                "spark_id": spark.spark_id,
                "event": "ERROR",
                "message": str(e),
            }
        )
        raise
