import json
import os
from pathlib import Path
from typing import List, Literal, Optional

import litellm
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from backend.database import get_db_connection, get_project_settings
from backend.models import BeatType

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


MuseMode = Literal["write", "setting"]


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    # V1.1: Muse dual-mode
    mode: MuseMode = Field(default="write", description="V1.1: 'write'=写稿档, 'setting'=设定档")


WRITE_MODE_PROMPT = """
你是 The Muse（写稿档），中文网文作者的贴身责编。你的任务：
  1. 帮作者构思下一章 / 下一场戏（生成 Spark）
  2. 在作者卡文时给出 3 个不同方向的 Spark 候选（unblock_writer）
  3. 微操推演（override_turn）
  4. 调渲染参数（adjust_render / switch_platform_profile）
  5. 查询 Grimoire（query_memory）

专注"怎么写下一章"。不要主动提议改角色设定/世界观，那属于"设定档"。
用户明确要改设定时，提醒他"切到设定档（发送 /设定 或切换按钮）"。

回复语言必须**中文**、**网文作者口吻**（兄弟 / 道友 / 老哥随便选一个，亲切但不油腻）。
不要喊 "prompt engineering" 之类英文术语。

Tool Call 格式（包裹在 ```tool_call 和 ``` 之间）：

1. 生成 Spark（启动推演）：
```tool_call
{
  "action": "start_spark",
  "payload": {
    "user_prompt": "具体冲突描述",
    "beat_type": "SHOW_OFF_FACE_SLAP",
    "target_char_count": 3000
  }
}
```
beat_type 可选值：SHOW_OFF_FACE_SLAP(装逼打脸) / PAYOFF(爽点兑现) / SUSPENSE_SETUP(悬念铺垫) /
EMOTIONAL_CLIMAX(情感升华) / POWER_REVEAL(金手指展示) / REVERSAL(反转) /
WORLDBUILDING(世界观补完) / DAILY_SLICE(日常流)

2. 卡文救急（一键生成 3 个 Spark 候选）：
```tool_call
{
  "action": "unblock_writer",
  "payload": {}
}
```

3. 微操推演：
```tool_call
{
  "action": "override_turn",
  "payload": {
    "spark_id": "当前推演ID",
    "entity_id": "角色ID",
    "directive": "新指令"
  }
}
```

4. 调整渲染：
```tool_call
{
  "action": "adjust_render",
  "payload": {
    "subtext_ratio": 0.3,
    "style_template": "热血爽文",
    "target_char_count": 3000
  }
}
```

5. 切换平台预设：
```tool_call
{
  "action": "switch_platform_profile",
  "payload": {"platform": "QIDIAN"}
}
```
平台可选：QIDIAN / FANQIE / JINJIANG / ZONGHENG / QIMAO / CUSTOM

6. 查询记忆：
```tool_call
{
  "action": "query_memory",
  "payload": {"query": "宁毅现在身上有多少钱"}
}
```

请在回复末尾附带这个代码块（若需要触发动作）。不要直接改库，只生成指令等确认。
"""


SETTING_MODE_PROMPT = """
你是 The Muse（设定档），中文网文作者的设定管理员。你的任务：
  1. 实体 CRUD（角色/势力/地点/物品）
  2. 事实修订（apply_soft_patch —— 作者在正文里改了事实，要同步到 Grimoire）
  3. 分支管理（create_branch）
  4. 回档（rollback）
  5. 查询（query_memory —— 两档都有）

操作前必须用 Markdown 展示 diff 摘要，再请用户"确认"才生成 tool_call。危险操作（删除 / 回档）**二次确认**。

回复语言必须**中文**、专业但不生硬。

Tool Call 格式：

1. 创建实体：
```tool_call
{
  "action": "create_entity",
  "payload": {
    "type": "CHARACTER",
    "name": "角色名",
    "base_attributes": {
      "aliases": ["别名"],
      "personality": "性格",
      "core_motive": "核心动机",
      "background": "背景"
    },
    "voice_signature": {
      "catchphrases": ["口头禅"],
      "honorifics": {"长辈": "您"},
      "forbidden_words": ["宝宝"],
      "sample_utterances": ["范本台词"]
    }
  }
}
```

2. 修改实体：
```tool_call
{
  "action": "update_entity",
  "payload": {
    "entity_id": "角色ID",
    "updates": { "name": "新名", "base_attributes": {"personality": "新性格"} }
  }
}
```

3. 删除实体（二次确认）：
```tool_call
{
  "action": "delete_entity",
  "payload": {"entity_id": "角色ID"}
}
```

4. 事实修订（软层 patch）：
```tool_call
{
  "action": "apply_soft_patch",
  "payload": {
    "target_entity_id": "角色ID",
    "target_path": "current_status.inventory",
    "new_value": ["新物品列表"],
    "author_note": "原文 3000 两错了，应该 300 两"
  }
}
```

5. 创建分支：
```tool_call
{"action": "create_branch", "payload": {"name": "暗黑线", "origin_snapshot_id": null, "parent_branch_id": null}}
```

6. 回档（二次确认）：
```tool_call
{"action": "rollback", "payload": {"snapshot_id": "快照ID"}}
```

7. 查询：同写稿档。
"""


SYSTEM_PROMPT = """
你是 The Muse，Genesis Engine 的创世编辑与首席助理。你的任务是协助作者构思小说世界、设定角色，并在时机成熟时启动推演沙盒。

如果用户想要创建、修改、删除实体，或者查询世界状态，你必须除了回复文字外，附带一段用特定 Markdown 格式包裹的 JSON 代码块（即 Tool Call 预览），前端会解析它并展现给用户确认。
如果用户描述了一段剧情冲突，并且你认为可以开始推演了，你也需要输出启动推演的 Tool Call。

支持的 Tool Call 格式（必须严格遵循，包裹在 ```tool_call 和 ``` 之间）：

1. 创建角色 (Create Entity):
```tool_call
{
  "action": "create_entity",
  "payload": {
    "type": "CHARACTER",
    "name": "角色名称",
    "base_attributes": {
      "aliases": ["别名"],
      "personality": "性格描述",
      "core_motive": "核心动机",
      "background": "背景故事"
    }
  }
}
```

2. 修改角色 (Update Entity):
当用户想要修改已有角色的属性时使用：
```tool_call
{
  "action": "update_entity",
  "payload": {
    "entity_id": "角色的entity_id",
    "updates": {
      "name": "新名字",
      "base_attributes": {
        "personality": "新性格"
      },
      "current_status": {
        "health": "受伤"
      }
    }
  }
}
```

3. 删除角色 (Delete Entity):
当用户想要删除某个角色时使用（软删除，可恢复）：
```tool_call
{
  "action": "delete_entity",
  "payload": {
    "entity_id": "要删除的角色ID"
  }
}
```

4. 查询世界状态 (Query Memory):
当用户想要了解当前世界的角色和他们的记忆时使用：
```tool_call
{
  "action": "query_memory",
  "payload": {
    "query": "所有角色的记忆"
  }
}
```

5. 启动推演 (Start Spark):
当用户给出了明确的动作或冲突指令时，使用这个：
```tool_call
{
  "action": "start_spark",
  "payload": {
    "user_prompt": "提炼后的具体动作指令，例如：Artemis 在酒馆里被刺客包围，他决定反击。"
  }
}
```

6. 微操推演 (Override Turn):
当用户想要在推演进行中修改某个角色的意图时使用（上帝之手）：
```tool_call
{
  "action": "override_turn",
  "payload": {
    "spark_id": "当前推演的spark_id",
    "entity_id": "要修改的角色ID",
    "directive": "新的意图或行为指令"
  }
}
```

7. 调整渲染 (Adjust Render):
当用户想要调整文学渲染的参数时使用：
```tool_call
{
  "action": "adjust_render",
  "payload": {
    "subtext_ratio": 0.7,
    "style_template": "武侠飘逸风",
    "pov_type": "FIRST_PERSON"
  }
}
```

8. 创建分支 (Create Branch):
当用户想要创建平行宇宙分支时使用：
```tool_call
{
  "action": "create_branch",
  "payload": {
    "from_chapter_id": "源章节ID",
    "branch_name": "分支名称"
  }
}
```

9. 回档 (Rollback):
当用户想要回退到某个快照状态时使用：
```tool_call
{
  "action": "rollback",
  "payload": {
    "snapshot_id": "要回退的快照ID"
  }
}
```

请在你的回复末尾附带这个代码块（如果需要触发动作的话）。不要直接修改数据库，你只负责生成指令等待人类确认。
"""


@router.post("/chat")
async def muse_chat(request: ChatRequest):
    async def generate():
        # Get config from environment (priority) or database
        env_model = os.getenv("LLM_MODEL")
        env_api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        )
        env_api_base = os.getenv("LLM_API_BASE")

        if not env_api_key:
            # Fallback to database settings
            async with get_db_connection() as conn:
                settings = await get_project_settings(conn)

            if "gpt" in settings.llm_model or env_model:
                env_api_key = settings.llm_api_keys.openai
            elif "claude" in settings.llm_model:
                env_api_key = settings.llm_api_keys.anthropic
            elif "deepseek" in settings.llm_model:
                env_api_key = settings.llm_api_keys.deepseek

            if not env_api_key and settings.llm_api_base:
                env_api_key = settings.llm_api_keys.openai

            env_model = env_model or settings.llm_model
            env_api_base = env_api_base or settings.llm_api_base

        actual_model = env_model or "gpt-4"
        if env_api_base and "/" not in str(actual_model):
            actual_model = f"openai/{actual_model}"

        # 组装上下文，带上现有的实体信息
        entities_summary = "当前世界没有任何实体。"
        async with get_db_connection() as conn:
            async with conn.execute(
                "SELECT name, type, entity_id FROM entities WHERE is_deleted = 0"
            ) as cursor:
                rows = await cursor.fetchall()
                if rows:
                    entities_summary = "当前的实体有: " + ", ".join(
                        [f"{r['name']}({r['type']}, ID: {r['entity_id'][:8]}...)" for r in rows]
                    )

        # V1.1: dual-mode system prompt
        if request.mode == "write":
            base_prompt = WRITE_MODE_PROMPT
        elif request.mode == "setting":
            base_prompt = SETTING_MODE_PROMPT
        else:
            base_prompt = SYSTEM_PROMPT  # V1.0 legacy fallback

        messages = [{"role": "system", "content": base_prompt + "\n\n" + entities_summary}]
        for msg in request.messages:
            # Map 'muse' to 'assistant' for LLM compatibility
            role = "assistant" if msg.role == "muse" else msg.role
            messages.append({"role": role, "content": msg.content})

        try:
            response = await litellm.acompletion(
                model=actual_model,
                messages=messages,
                stream=True,
                api_key=env_api_key,
                base_url=env_api_base,
                custom_llm_provider="openai" if env_api_base else None,
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"

        except Exception as e:
            logger.error(f"Muse chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ==========================================
# V1.1: [卡文救急] — 一键生成 3 个 Spark 候选
# ==========================================


class UnblockWriterRequest(BaseModel):
    chapter_id: Optional[str] = Field(default=None, description="当前章节 ID，用于拉取上下文")
    recent_chapters: int = Field(default=5, ge=1, le=20)


class SparkCandidate(BaseModel):
    direction: str  # "激烈冲突" / "情感转折" / "日常过渡"
    beat_type: BeatType
    user_prompt: str
    target_char_count: int = 3000
    why: str  # 给作者看的推荐理由


class UnblockWriterResponse(BaseModel):
    candidates: List[SparkCandidate]
    message: str


@router.post("/unblock_writer", response_model=UnblockWriterResponse)
async def unblock_writer(request: UnblockWriterRequest):
    """
    POST /api/v1/muse/unblock_writer
    [卡文救急] — 基于最近章节 + Grimoire 当前态，生成 3 个不同方向的 Spark 候选。

    网文作者断更 70% 是因为"今天不知道写啥"。此端点每月保一票作者不断更。
    """
    # 拉取当前实体列表做简短摘要
    entities_summary = "世界目前为空。"
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT name, type FROM entities WHERE is_deleted = 0 LIMIT 20"
        ) as cursor:
            rows = await cursor.fetchall()
            if rows:
                entities_summary = "；".join([f"{r['name']}({r['type']})" for r in rows])

    # V1.1 默认候选（不依赖 LLM 的本地硬编码回退）。
    # 如果 LLM 可用，稍后可升级到动态生成；此处保证即便离线也能给出建议。
    default_candidates = [
        SparkCandidate(
            direction="激烈冲突（装逼打脸）",
            beat_type=BeatType.SHOW_OFF_FACE_SLAP,
            user_prompt=(
                "反派登门挑衅主角，主角用金手指一招把对方挫得灰头土脸，让在场所有旁观者集体震惊。"
            ),
            target_char_count=3000,
            why="连续推日常后来一场打脸，读者订阅稳住。",
        ),
        SparkCandidate(
            direction="情感转折（情感升华）",
            beat_type=BeatType.EMOTIONAL_CLIMAX,
            user_prompt=("主角和重要女性角色在安静场合对话，揭示一段过往真相，关系升级到新阶段。"),
            target_char_count=3500,
            why="紧张推演后换一个抒情节拍，避免读者审美疲劳。",
        ),
        SparkCandidate(
            direction="日常过渡（世界观补完）",
            beat_type=BeatType.WORLDBUILDING,
            user_prompt=("主角拜访一个新地点或势力，通过日常互动曝光 2-3 条可抽取的世界观设定。"),
            target_char_count=2500,
            why="为后续大剧情铺设定，字数压一点省 token。",
        ),
    ]

    # 尝试用 LLM 基于当前实体状态改写 user_prompt。失败则用默认。
    try:
        env_model = os.getenv("LLM_MODEL")
        env_api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        )
        env_api_base = os.getenv("LLM_API_BASE")

        if env_api_key and env_model:
            actual_model = env_model
            if env_api_base and "/" not in actual_model:
                actual_model = f"openai/{actual_model}"

            prompt = f"""你是网文责编。作者卡文了，需要 3 个不同方向的冲突建议。

当前世界角色：{entities_summary}

要求：严格输出 JSON 数组（不要包 markdown），每个元素包含 {{"direction","beat_type","user_prompt","target_char_count","why"}}。
生成 3 条，分别对应：激烈冲突(SHOW_OFF_FACE_SLAP)、情感转折(EMOTIONAL_CLIMAX)、日常过渡(WORLDBUILDING)。user_prompt 要用作者的角色名、要具体、有画面感、一句话以内。"""
            response = await litellm.acompletion(
                model=actual_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=800,
                api_key=env_api_key,
                base_url=env_api_base,
                custom_llm_provider="openai" if env_api_base else None,
            )
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            if isinstance(parsed, list) and len(parsed) >= 3:
                llm_candidates = []
                for item in parsed[:3]:
                    try:
                        llm_candidates.append(SparkCandidate(**item))
                    except Exception:
                        continue
                if len(llm_candidates) == 3:
                    return UnblockWriterResponse(
                        candidates=llm_candidates,
                        message="已基于当前 Grimoire 生成 3 个方向，选一个开推吧。",
                    )
    except Exception as e:
        logger.warning(f"[unblock_writer] LLM fallback: {e}")

    return UnblockWriterResponse(
        candidates=default_candidates,
        message="LLM 不可用或离线，已返回通用候选。",
    )
