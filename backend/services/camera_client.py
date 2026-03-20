from typing import Optional, List
import os
from pathlib import Path
from loguru import logger
import litellm
from dotenv import load_dotenv

from backend.models import StoryIRBlock, POVType, Entity, RenderRequest

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class CameraError(Exception):
    pass


class CameraClient:
    """
    Camera Agent: The sole responsible for literary rendering.
    Converts Story IR Blocks into styled prose HTML.

    Per SPEC §5.3:
    - Only reads IR, never reads rendered HTML
    - Supports POV, Style, Subtext parameters
    - Stateless LLM API call
    """

    async def render(
        self,
        ir_block: StoryIRBlock,
        pov_type: POVType,
        style_template: str,
        subtext_ratio: float,
        pov_character: Optional[Entity] = None,
    ) -> str:
        """
        Main entry point for rendering.

        Args:
            ir_block: The Story IR Block to render
            pov_type: Point of view (OMNISCIENT, FIRST_PERSON, CHARACTER_LIMITED)
            style_template: Style name or anchor text
            subtext_ratio: 0.0 = pure action, 1.0 = pure internal monologue
            pov_character: Required if POV is FIRST_PERSON or CHARACTER_LIMITED

        Returns:
            HTML string of rendered prose

        Raises:
            CameraError: If validation fails
        """
        self._validate_render_request(ir_block, pov_type, pov_character)

        prompt = self._build_prompt(
            ir_block=ir_block,
            pov_type=pov_type,
            style_template=style_template,
            subtext_ratio=subtext_ratio,
            pov_character=pov_character,
        )

        html_content = await self._generate_prose(prompt)
        return html_content

    def _validate_render_request(
        self, ir_block: StoryIRBlock, pov_type: POVType, pov_character: Optional[Entity]
    ):
        """Validate render parameters before calling LLM."""
        if not ir_block.action_sequence:
            raise CameraError("Cannot render IR block with empty action_sequence")

        if pov_type == POVType.CHARACTER_LIMITED and pov_character is None:
            raise CameraError("CHARACTER_LIMITED POV requires pov_character")

        if pov_type == POVType.FIRST_PERSON and pov_character is None:
            raise CameraError("FIRST_PERSON POV requires pov_character")

    def _build_prompt(
        self,
        ir_block: StoryIRBlock,
        pov_type: POVType,
        style_template: str,
        subtext_ratio: float,
        pov_character: Optional[Entity],
    ) -> str:
        """
        Build the LLM prompt from IR block and render parameters.
        """
        ir_json = ir_block.model_dump_json(indent=2)

        pov_instruction = self._get_pov_instruction(pov_type, pov_character)
        style_instruction = self._get_style_instruction(style_template)
        subtext_instruction = self._get_subtext_instruction(subtext_ratio)

        prompt = f"""你是专业的文学渲染引擎 Camera。你的任务是将结构化的故事骨架（Story IR）渲染为优美的文学正文。

[视角要求]
{pov_instruction}

[文风锚点]
{style_instruction}

[潜台词密度]
{subtext_instruction}

[故事骨架]
以下是本次需要渲染的场景骨架（JSON 格式）：
{ir_json}

[输出要求]
1. 将 action_sequence 中的每个动作渲染为连贯的文学段落
2. dialogue 字段保持原样，嵌入正文中
3. 输出 HTML 格式，使用 <p> 标签分段
4. 严禁添加 action_sequence 中不存在的动作或对话
5. 严禁第三人称描述角色的心理活动（除非 POV 允许）

现在请渲染："""

        return prompt

    def _get_pov_instruction(self, pov_type: POVType, pov_character: Optional[Entity]) -> str:
        if pov_type == POVType.OMNISCIENT:
            return "采用全知视角（上帝视角）。你可以描述所有角色的外在行为和对话，但内心活动只能通过暗示和潜台词表现。"

        elif pov_type == POVType.FIRST_PERSON:
            char_name = pov_character.name if pov_character else "主角"
            return f"采用第一人称视角。以「我」（{char_name}）的口吻叙述。只能描述「我」看到的、听到的、想到的。"

        elif pov_type == POVType.CHARACTER_LIMITED:
            char_name = pov_character.name if pov_character else "主角"
            return f"采用角色限制视角。第三人称叙述，但视角绑定在 {char_name} 身上。只能描述该角色所感知的内容。"

        return "采用全知视角。"

    def _get_style_instruction(self, style_template: str) -> str:
        return f"文风参考：{style_template}。请保持统一的叙事节奏和语言质感。"

    def _get_subtext_instruction(self, subtext_ratio: float) -> str:
        if subtext_ratio <= 0.3:
            return f"潜台词密度：{subtext_ratio:.1%}（低）。侧重白描动作和对话，减少心理描写。"
        elif subtext_ratio <= 0.7:
            return f"潜台词密度：{subtext_ratio:.1%}（中）。适度穿插暗示和心理活动。"
        else:
            return (
                f"潜台词密度：{subtext_ratio:.1%}（高）。大量使用意识流和内心独白，心理描写丰富。"
            )

    async def _generate_prose(self, prompt: str) -> str:
        """
        Call LLM to generate prose using env config or settings.
        """
        logger.info("[Camera] Generating prose...")

        # Get config from environment
        model = os.getenv("LLM_MODEL", "gpt-4")
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        )
        api_base = os.getenv("LLM_API_BASE")

        if not api_key:
            raise CameraError(
                "No API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or DEEPSEEK_API_KEY in .env"
            )

        actual_model = model
        if api_base and "/" not in model:
            actual_model = f"openai/{model}"

        try:
            response = await litellm.acompletion(
                model=actual_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
                api_key=api_key,
                base_url=api_base,
                custom_llm_provider="openai" if api_base else None,
            )

            content = response.choices[0].message.content
            logger.info(f"[Camera] Generated {len(content)} characters")
            return content

        except Exception as e:
            logger.error(f"[Camera] Generation failed: {e}")
            raise CameraError(f"Prose generation failed: {str(e)}")


camera_client = CameraClient()
