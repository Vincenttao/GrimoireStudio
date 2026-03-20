from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import asyncio
import os
from pathlib import Path
from loguru import logger
import litellm
from dotenv import load_dotenv

from backend.database import get_db_connection, get_project_settings

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


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

        messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + entities_summary}]
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
