from typing import List, Dict, TypeVar, Type, Optional
import json
import os
import time
from pathlib import Path
from pydantic import BaseModel
import litellm
from loguru import logger
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

litellm.set_verbose = True

from backend.models import (
    Entity,
    StoryIRBlock,
    MaestroDecision,
    MaestroEvaluation,
    CharacterAction,
    ProjectSettings,
    ActionItem,
    SceneContext,
)
from backend.services.websocket_manager import manager
from backend.database import get_db_connection, get_project_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


def get_env_config() -> Dict[str, Optional[str]]:
    """
    Get LLM configuration from environment variables.
    Returns dict with: model, api_key, api_base
    """
    return {
        "model": os.getenv("LLM_MODEL"),
        "openai_key": os.getenv("OPENAI_API_KEY"),
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY"),
        "deepseek_key": os.getenv("DEEPSEEK_API_KEY"),
        "api_base": os.getenv("LLM_API_BASE"),
    }


def resolve_api_key(model: str, env_config: Dict, settings_api_keys) -> Optional[str]:
    """
    Resolve API key with precedence: env var > db settings.
    """
    # First check environment variables
    if "gpt" in model.lower() or "openai" in model.lower():
        if env_config["openai_key"]:
            return env_config["openai_key"]
        return settings_api_keys.openai
    elif "claude" in model.lower() or "anthropic" in model.lower():
        if env_config["anthropic_key"]:
            return env_config["anthropic_key"]
        return settings_api_keys.anthropic
    elif "deepseek" in model.lower():
        if env_config["deepseek_key"]:
            return env_config["deepseek_key"]
        return settings_api_keys.deepseek

    # For custom endpoints, use OpenAI key
    if env_config["openai_key"]:
        return env_config["openai_key"]
    return settings_api_keys.openai


class LLMClient:
    async def _generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.5,
    ) -> T:
        """
        Generic wrapper for LiteLLM structured output with robust parsing.
        Config precedence: env vars > db settings.
        """
        start_time = time.time()

        # Get config from env vars
        env_config = get_env_config()

        # Get settings from DB as fallback
        async with get_db_connection() as conn:
            settings = await get_project_settings(conn)

        # Resolve model (env var takes precedence)
        actual_model = env_config["model"] or settings.llm_model

        # Resolve API base (env var takes precedence)
        api_base = env_config["api_base"] or settings.llm_api_base

        # Resolve API key (env var takes precedence)
        api_key = resolve_api_key(actual_model, env_config, settings.llm_api_keys)

        if not api_key:
            raise LLMError(
                f"No API key found for model '{actual_model}'. "
                "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or DEEPSEEK_API_KEY in .env"
            )

        # Force JSON instructions in system prompt
        if messages[0]["role"] == "system":
            messages[0]["content"] += (
                "\nIMPORTANT: You MUST output ONLY valid JSON. Do not wrap in markdown blocks. Do not add any text before or after the JSON."
            )

        if api_base and "/" not in actual_model:
            actual_model = f"openai/{actual_model}"

        logger.info(f"[LLM] Calling {actual_model} via {api_base or 'default'} (timeout=60s)...")
        try:
            response = await litellm.acompletion(
                model=actual_model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                api_key=api_key,
                base_url=api_base,
                custom_llm_provider="openai" if api_base else None,
                request_timeout=60.0,
            )
            duration = time.time() - start_time
            logger.info(f"[LLM] Response received in {duration:.2f}s")
            content = response.choices[0].message.content

            # --- Robust Parsing ---
            # 1. Strip markdown blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # 2. Try to parse JSON to handle potential wrapping
            data = json.loads(content)

            # 3. If model wrapped the response in a key named after the model or generic key
            # e.g., {"maestro_decision": {...}}
            model_key = response_model.__name__.lower()
            snake_model_key = "".join(
                ["_" + c.lower() if c.isupper() else c for c in response_model.__name__]
            ).lstrip("_")

            if isinstance(data, dict):
                # Unpack if wrapped
                if model_key in data and len(data) == 1:
                    data = data[model_key]
                elif snake_model_key in data and len(data) == 1:
                    data = data[snake_model_key]

                # Field Mapping (LLM field name hallucination fix)
                # Map common character output variations
                if response_model.__name__ == "CharacterAction":
                    if "inner_monologue" in data and "intent" not in data:
                        data["intent"] = data.pop("inner_monologue")
                    if "thought" in data and "intent" not in data:
                        data["intent"] = data.pop("thought")
                    if "action_description" in data and "action" not in data:
                        data["action"] = data.pop("action_description")

                # Map common evaluation variations
                if response_model.__name__ == "MaestroEvaluation":
                    if "score" in data and "tension_score" not in data:
                        data["tension_score"] = data.pop("score")
                    if "status" in data and "is_valid" not in data:
                        data["is_valid"] = data["status"] in [
                            "approved",
                            "pass",
                            "success",
                            "valid",
                        ]
                    if "consistency" in data and "is_valid" not in data:
                        data["is_valid"] = data["consistency"]

            return response_model.model_validate(data)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[LLM] Failed after {duration:.2f}s: {e}")
            logger.error(f"Raw LLM Output: {content if 'content' in locals() else 'No Content'}")
            raise

    async def evaluate_scene_progression(
        self, prompt: str, entities_json: str, history_json: str
    ) -> MaestroDecision:
        """
        Maestro deciding who speaks next.
        """
        messages = [
            {
                "role": "system",
                "content": """You are The Maestro, a high-level scene orchestrator. 
Your ONLY job is to decide which entity acts next or if the scene is complete.

REQUIRED JSON SCHEMA:
{
  "next_actor_id": "string (UUID of the character) or null",
  "is_beat_complete": boolean,
  "reasoning": "short explanation"
}

DO NOT output any other fields. DO NOT output 'maestro_state' or 'response_message'.
Example: {"next_actor_id": "char-001", "is_beat_complete": false, "reasoning": "The protagonist needs to react to the explosion."}""",
            },
            {
                "role": "user",
                "content": f"User Spark/Prompt: {prompt}\nAvailable Entities (Grimoire): {entities_json}\nRecent History: {history_json}",
            },
        ]
        return await self._generate_structured(messages, MaestroDecision, temperature=0.2)

    async def generate_character_action(
        self,
        actor: Entity,
        history: List[CharacterAction],
        director_note: str,
        scene_context: str,
    ) -> CharacterAction:
        """
        Character Agent utilizing the 3-Layer Prompt (SPEC §5.2).
        """
        sys_prompt = f"""
# [Layer 1: System]
你扮演实体: {actor.name}
基本人设: {actor.base_attributes.personality}
核心动机: {actor.base_attributes.core_motive}
客观状态: {actor.current_status.model_dump_json()}

# [Constraint]
你必须仅输出 JSON 格式。严禁使用第三人称散文体描写。
JSON 必须严格符合以下结构：
{{
  "intent": "你的内心真实意图",
  "action": "你的物理动作与微表情",
  "dialogue": "你说出口的台词"
}}
"""

        history_text = "\n".join(
            [f"- {h.intent} -> Action: {h.action} Dialogue: {h.dialogue}" for h in history]
        )
        scene_prompt = f"""
# [Layer 2: Scene & History]
当前场景: {scene_context}
最近发生的事情:
{history_text}
"""
        note_prompt = ""
        if director_note:
            note_prompt = f"""
# [Layer 3: Director Note]
<Director_Note>
⚠️ 重点指导: {director_note}
</Director_Note>
"""

        messages = [
            {"role": "system", "content": sys_prompt},
            {
                "role": "user",
                "content": f"{scene_prompt}\n{note_prompt}\n请输出 JSON CharacterAction。",
            },
        ]

        result = await self._generate_structured(messages, CharacterAction, temperature=0.7)
        await manager.broadcast(
            "CHAR_STREAM",
            {"delta": f"\n[{actor.name}]: {result.dialogue} (Action: {result.action})\n"},
        )
        return result

    async def score_character_output(
        self, char_response: CharacterAction, history_json: str
    ) -> MaestroEvaluation:
        """
        Maestro evaluating tension (SPEC §1.7).
        """
        messages = [
            {
                "role": "system",
                "content": """You are The Maestro, a narrative tension evaluator. 
Your ONLY job is to score the character's last action and decide if it is valid.

REQUIRED JSON SCHEMA:
{
  "is_valid": boolean,
  "reject_reason": "string (if invalid) or null",
  "tension_score": integer (0-100)
}

DO NOT output fields like 'score', 'status', or 'feedback'.""",
            },
            {
                "role": "user",
                "content": f"Last Action:\n{char_response.model_dump_json()}\nHistory:\n{history_json}",
            },
        ]
        return await self._generate_structured(messages, MaestroEvaluation, temperature=0.1)

    async def extract_story_ir(
        self,
        history: List[CharacterAction],
        previous_block_id: Optional[str],
        chapter_id: str,
    ) -> StoryIRBlock:
        """
        Extract Story IR Block from turn logs.

        Args:
            history: List of CharacterAction from the orchestration loop
            previous_block_id: ID of previous block (for lexorank calculation)
            chapter_id: Chapter this block belongs to

        Returns:
            StoryIRBlock with structured action sequence
        """
        if not history:
            raise LLMError("Cannot extract IR from empty history")

        import uuid
        from datetime import datetime

        block_id = f"block_{uuid.uuid4().hex[:8]}"

        lexorank = "a0"
        if previous_block_id:
            lexorank = "a0i"

        action_sequence = []
        for i, action in enumerate(history):
            action_sequence.append(
                ActionItem(
                    actor_id=f"actor_{i}",
                    intent=action.intent,
                    action=action.action,
                    dialogue=action.dialogue,
                )
            )

        summary = self._generate_summary(history)

        return StoryIRBlock(
            block_id=block_id,
            chapter_id=chapter_id,
            lexorank=lexorank,
            summary=summary,
            involved_entities=[f"actor_{i}" for i in range(len(history))],
            scene_context=SceneContext(location_id="default_location", time_of_day="未知"),
            action_sequence=action_sequence,
            created_at=datetime.utcnow(),
        )

    def _generate_summary(self, history: List[CharacterAction]) -> str:
        """Generate a summary from action history."""
        if not history:
            return "空场景"

        actions = [h.action for h in history if h.action]
        if actions:
            return actions[0][:50] + "..." if len(actions[0]) > 50 else actions[0]

        return "场景描述"


llm_client = LLMClient()
