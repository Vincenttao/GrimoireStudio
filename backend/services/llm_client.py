from typing import List, Dict, TypeVar, Type
from pydantic import BaseModel
import litellm
from loguru import logger

from backend.models import (
    Entity, StoryIRBlock, MaestroDecision, 
    MaestroEvaluation, CharacterAction
)
from backend.services.websocket_manager import manager

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name

    async def _generate_structured(
        self, 
        messages: List[Dict[str, str]], 
        response_model: Type[T],
        temperature: float = 0.5
    ) -> T:
        """
        Generic wrapper for LiteLLM structured output.
        Enforces AGENT.md Strict JSON extraction.
        """
        try:
            # Note: We use LiteLLM's response_format parameter to ensure valid JSON schema matching the Pydantic type
            response = await litellm.acompletion(
                model=self.model_name,
                messages=messages,
                response_format=response_model,
                temperature=temperature
            )
            content = response.choices[0].message.content
            return response_model.model_validate_json(content)
        except Exception as e:
            logger.error(f"LLM Generation failed for {response_model.__name__}: {e}")
            raise

    async def evaluate_scene_progression(
        self, 
        prompt: str, 
        entities_json: str, 
        history_json: str
    ) -> MaestroDecision:
        """
        Maestro deciding who speaks next.
        """
        messages = [
            {"role": "system", "content": "You are The Maestro. Analyze the Grimoire context and Turn Logs. Output JSON matching MaestroDecision."},
            {"role": "user", "content": f"Prompt: {prompt}\nEntities: {entities_json}\nLogs:\n{history_json}"}
        ]
        return await self._generate_structured(messages, MaestroDecision, temperature=0.2)

    async def generate_character_action(
        self,
        actor: Entity,
        history: List[CharacterAction],
        director_note: str,
        scene_context: str
    ) -> CharacterAction:
        """
        Character Agent utilizing the 3-Layer Prompt (SPEC §5.2). 
        Includes WS streaming for the developer monitor.
        """
        sys_prompt = f"""
# [Layer 1: System]
你扮演实体: {actor.name}
基本人设: {actor.base_attributes.personality}
核心动机: {actor.base_attributes.core_motive}
客观状态: {actor.current_status.model_dump_json()}
"""
        
        history_text = "\n".join([f"- {h.intent} -> Action: {h.action} Dialogue: {h.dialogue}" for h in history])
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
请在不违背人设情况下顺应上述指导。
</Director_Note>
"""

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"{scene_prompt}\n{note_prompt}\n请输出 JSON CharacterAction。"}
        ]
        
        # We need a custom streaming loop if we want per-char updates via WebSocket.
        # But for MVP, let's keep structured extraction rock-solid and emit the final string to Monitor.
        result = await self._generate_structured(messages, CharacterAction, temperature=0.7)
        await manager.broadcast("CHAR_STREAM", {"delta": f"\n[{actor.name}]: {result.dialogue} (Action: {result.action})\n"})
        return result

    async def score_character_output(
        self,
        char_response: CharacterAction,
        history_json: str
    ) -> MaestroEvaluation:
        """
        Maestro evaluating tension (SPEC §1.7).
        """
        messages = [
            {"role": "system", "content": "You are The Maestro evaluator. Return JSON MaestroEvaluation."},
            {"role": "user", "content": f"Action:\n{char_response.model_dump_json()}\nHistory:\n{history_json}"}
        ]
        return await self._generate_structured(messages, MaestroEvaluation, temperature=0.1)

    async def extract_story_ir(self, history: List[CharacterAction], previous_block_id: str) -> StoryIRBlock:
        """
        Mock for MVP to satisfy type checker. 
        A real extraction merges CharacterActions into the ActionSequence list and assigns lexorank.
        """
        raise NotImplementedError("IR extraction needs concrete chapter ID context.")

llm_client = LLMClient()
