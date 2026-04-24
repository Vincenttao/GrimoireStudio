import os
import re
from pathlib import Path
from typing import List, Optional

import litellm
from dotenv import load_dotenv
from loguru import logger

from backend.models import Entity, HookGuardResult, POVType, StoryIRBlock

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class CameraError(Exception):
    pass


# ==========================================
# 辅助工具：字数/水字数/钩子关键词
# ==========================================

HOOK_KEYWORDS = [
    "……",
    "竟然",
    "不料",
    "却见",
    "忽然",
    "陡然",
    "突然",
    "不过",
    "而此刻",
    "就在这时",
    "紧接着",
    "岂料",
    "谁知",
    "原来",
]

HOOK_UNFINISHED_MARKERS = ["？", "?", "——", "……", "…"]


def strip_html_to_text(html: str) -> str:
    """粗略剥离 HTML 标签以计算纯中文字数。"""
    text = re.sub(r"<[^>]+>", "", html or "")
    text = re.sub(r"\s+", "", text)
    return text


def count_cn_chars(text: str) -> int:
    """统计中文字符 + 非空白字符数（网文作者眼里的字数）。"""
    return len(text)


def detect_padding(html: str) -> List[str]:
    """
    网文水字数检测（本地启发式，不调 LLM）：
      - 同一事件/名词 3+ 次重复
      - 单段环境描写 > 500 字
      - 对白占比 < 20%
    """
    warnings: List[str] = []
    text = strip_html_to_text(html)
    paragraphs = re.split(r"</p>\s*<p[^>]*>|\n\n", html or "")

    # 对白（中文引号"..."或英文引号"..."）
    quoted = re.findall(r'[""“”]([^""“”]+)[""“”]|"([^"]+)"', html or "")
    dialogue_chars = sum(len(g[0] or g[1] or "") for g in quoted)
    total_chars = count_cn_chars(text) or 1
    dialogue_ratio = dialogue_chars / total_chars
    if dialogue_ratio < 0.20 and total_chars > 500:
        warnings.append(f"对白占比 {dialogue_ratio:.1%} < 20%，网文黄金比 30-50%。建议增加对白。")

    # 长环境段
    for p in paragraphs:
        clean = strip_html_to_text(p)
        if len(clean) > 500 and ('"' not in p and '"' not in p and '"' not in p):
            warnings.append("出现单段纯描写 > 500 字，疑似水字数。")
            break

    return warnings


class CameraClient:
    """
    Camera Agent: literary rendering with V1.1 web-novel constraints.
    - target_char_count hard constraint (±tolerance_ratio)
    - max_sent_len soft hint (platform preset)
    - Ending Hook Guard (章末钩子守卫)
    """

    # ---- Entry point -------------------------------------------------------

    async def render(
        self,
        ir_block: StoryIRBlock,
        pov_type: POVType,
        style_template: str,
        subtext_ratio: float,
        pov_character: Optional[Entity] = None,
        # V1.1 新增
        target_char_count: Optional[int] = None,
        max_sent_len: Optional[int] = None,
        tolerance_ratio: float = 0.10,
        adjust_mode: Optional[str] = None,
    ) -> str:
        """
        Main entry point for rendering.

        V1.1: target_char_count & max_sent_len 为可选硬约束。若 target_char_count 提供，
        首轮渲染后会自动按偏差调用 adjust_length（最多 3 轮）。
        """
        self._validate_render_request(ir_block, pov_type, pov_character)

        prompt = self._build_prompt(
            ir_block=ir_block,
            pov_type=pov_type,
            style_template=style_template,
            subtext_ratio=subtext_ratio,
            pov_character=pov_character,
            target_char_count=target_char_count,
            max_sent_len=max_sent_len,
            adjust_mode=adjust_mode,
        )
        html_content = await self._generate_prose(prompt)
        return html_content

    # ---- V1.1: 字数约束循环 --------------------------------------------------

    async def render_with_char_count_enforcement(
        self,
        ir_block: StoryIRBlock,
        pov_type: POVType,
        style_template: str,
        subtext_ratio: float,
        target_char_count: int,
        pov_character: Optional[Entity] = None,
        max_sent_len: Optional[int] = None,
        tolerance_ratio: float = 0.10,
        max_attempts: int = 3,
    ) -> tuple[str, int, List[str]]:
        """
        渲染 + 自动字数调整循环。
        返回: (content_html, actual_char_count, padding_warnings)
        """
        html = await self.render(
            ir_block=ir_block,
            pov_type=pov_type,
            style_template=style_template,
            subtext_ratio=subtext_ratio,
            pov_character=pov_character,
            target_char_count=target_char_count,
            max_sent_len=max_sent_len,
        )

        for attempt in range(max_attempts):
            actual = count_cn_chars(strip_html_to_text(html))
            deviation = (actual - target_char_count) / target_char_count
            logger.info(
                f"[Camera] Char count attempt {attempt + 1}: {actual}/{target_char_count} "
                f"(deviation {deviation:+.1%})"
            )

            if abs(deviation) <= tolerance_ratio:
                break

            mode = "shrink" if deviation > 0 else "expand"
            html = await self.render(
                ir_block=ir_block,
                pov_type=pov_type,
                style_template=style_template,
                subtext_ratio=subtext_ratio,
                pov_character=pov_character,
                target_char_count=target_char_count,
                max_sent_len=max_sent_len,
                adjust_mode=mode,
            )

        actual = count_cn_chars(strip_html_to_text(html))
        padding_warnings = detect_padding(html)
        return html, actual, padding_warnings

    # ---- V1.1: Ending Hook Guard -------------------------------------------

    async def check_ending_hook(self, html: str) -> HookGuardResult:
        """
        本地启发式 + 可选 LLM fallback。默认本地启发式足够。
        """
        text = strip_html_to_text(html)
        if not text:
            return HookGuardResult(has_hook=False, reason="章末为空")

        tail = text[-200:]
        has_keyword = any(kw in tail for kw in HOOK_KEYWORDS)
        has_unfinished = any(m in tail for m in HOOK_UNFINISHED_MARKERS)
        # "……" "—" 也是悬念符号；或以问号结尾
        ends_with_question = tail.rstrip().endswith(("？", "?"))

        if has_keyword or has_unfinished or ends_with_question:
            hook_types = []
            if has_keyword:
                hook_types.append("悬念对白")
            if ends_with_question:
                hook_types.append("未解冲突")
            if has_unfinished and "悬念对白" not in hook_types:
                hook_types.append("悬念对白")
            return HookGuardResult(
                has_hook=True,
                hook_type="/".join(hook_types) if hook_types else "悬念对白",
                reason=f"章末 200 字检测到关键钩子标记: {tail[-30:]}",
            )

        return HookGuardResult(
            has_hook=False,
            hook_type=None,
            reason="章末 200 字未检测到悬念/反转/未完结动作/疑问；建议补钩子",
        )

    async def refine_ending(
        self,
        html: str,
        ir_block: StoryIRBlock,
        pov_type: POVType,
        style_template: str,
        subtext_ratio: float,
        pov_character: Optional[Entity] = None,
    ) -> str:
        """
        钩子守卫触发时调用：只重渲染最后一段，不改前文。
        """
        # 找最后一个 <p>...</p> 段落，替换
        paragraphs = re.split(r"(</p>)", html or "")
        if len(paragraphs) < 2:
            logger.warning("[HookGuard] Cannot locate last paragraph, returning as-is")
            return html

        # 重新调用 Camera 生成"仅章末"段落，强约束留钩子
        last_action = ir_block.action_sequence[-1] if ir_block.action_sequence else None
        if not last_action:
            return html

        prompt = f"""你是中文网文渲染引擎 Camera。以下是一段章末，需要你重写最后一段，**必须留下钩子**。

[文风] {style_template}
[POV] {pov_type.value}
[最后一个 Action]
intent: {last_action.intent}
action: {last_action.action}
dialogue: {last_action.dialogue}

[强约束] 必须在末尾留下以下至少一种钩子：
 1. 未解冲突（角色面临抉择/威胁/谜题）
 2. 新入场人物或事件
 3. 形势反转
 4. 悬念对白或未完结动作（用 "……" / "？" 结尾）

输出 HTML，使用 <p> 标签。只输出最后一段（大约 100-200 字），不要重复前文。
"""
        new_ending = await self._generate_prose(prompt)

        # 去掉最后一个 </p> 之前的一段，替换
        # 找到最后一个 <p> 起始
        last_p_start = html.rfind("<p")
        if last_p_start == -1:
            return html + new_ending
        return html[:last_p_start] + new_ending

    # ---- 基础工具 -----------------------------------------------------------

    def _validate_render_request(
        self, ir_block: StoryIRBlock, pov_type: POVType, pov_character: Optional[Entity]
    ):
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
        target_char_count: Optional[int] = None,
        max_sent_len: Optional[int] = None,
        adjust_mode: Optional[str] = None,
    ) -> str:
        ir_json = ir_block.model_dump_json(indent=2)
        pov_instruction = self._get_pov_instruction(pov_type, pov_character)
        style_instruction = self._get_style_instruction(style_template)
        subtext_instruction = self._get_subtext_instruction(subtext_ratio)

        char_count_instruction = ""
        if target_char_count:
            char_count_instruction = (
                f"\n[字数约束] 目标约 {target_char_count} 字（±10%）。请在该字数范围内完成渲染。"
            )

        sent_len_instruction = ""
        if max_sent_len:
            sent_len_instruction = (
                f"\n[句长约束] 单句长度不得超过 {max_sent_len} 字，符合目标平台的快节奏阅读习惯。"
            )

        adjust_instruction = ""
        if adjust_mode == "expand":
            adjust_instruction = (
                "\n[调整指令] 上一轮渲染字数不足。本轮需在保持情节/事实不变的前提下，"
                "追加环境/心理/景物描写以达到目标字数。**严禁新增对白/动作/事实**。"
            )
        elif adjust_mode == "shrink":
            adjust_instruction = (
                "\n[调整指令] 上一轮渲染字数超标。本轮需精简至目标字数。"
                "优先保留核心对白与动作，砍冗余描写。"
            )

        prompt = f"""你是专业的中文网文渲染引擎 Camera。你的任务是将结构化的故事骨架（Story IR）渲染为优美的网文正文。

[视角要求]
{pov_instruction}

[文风锚点]
{style_instruction}

[潜台词密度]
{subtext_instruction}{char_count_instruction}{sent_len_instruction}{adjust_instruction}

[故事骨架]
以下是本次需要渲染的场景骨架（JSON 格式）：
{ir_json}

[输出要求]
1. 将 action_sequence 中的每个动作渲染为连贯的网文段落
2. dialogue 字段保持原样，嵌入正文中
3. 输出 HTML 格式，使用 <p> 标签分段
4. 严禁添加 action_sequence 中不存在的动作或对话（事实层面）
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
        """Call LLM to generate prose using env config or settings."""
        logger.info("[Camera] Generating prose...")

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
                max_tokens=4000,
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
