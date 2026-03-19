from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import asyncio
from loguru import logger
import litellm

from backend.database import get_db_connection, get_project_settings

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

SYSTEM_PROMPT = """
你是 The Muse，Genesis Engine 的创世编辑与首席助理。你的任务是协助作者构思小说世界、设定角色，并在时机成熟时启动推演沙盒。

如果用户想要创建一个新角色或实体，你必须除了回复文字外，附带一段用特定 Markdown 格式包裹的 JSON 代码块（即 Tool Call 预览），前端会解析它并展现给用户确认。
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

2. 启动推演 (Start Spark):
当用户给出了明确的动作或冲突指令时，使用这个：
```tool_call
{
  "action": "start_spark",
  "payload": {
    "user_prompt": "提炼后的具体动作指令，例如：Artemis 在酒馆里被刺客包围，他决定反击。"
  }
}
```

请在你的回复末尾附带这个代码块（如果需要触发动作的话）。不要直接修改数据库，你只负责生成指令等待人类确认。
"""

@router.post("/chat")
async def muse_chat(request: ChatRequest):
    async def generate():
        async with get_db_connection() as conn:
            settings = await get_project_settings(conn)
            
        api_key = None
        if "gpt" in settings.llm_model:
            api_key = settings.llm_api_keys.openai
        elif "claude" in settings.llm_model:
            api_key = settings.llm_api_keys.anthropic
        elif "deepseek" in settings.llm_model:
            api_key = settings.llm_api_keys.deepseek
            
        if not api_key and settings.llm_api_base:
            api_key = settings.llm_api_keys.openai

        actual_model = settings.llm_model
        if settings.llm_api_base and "/" not in actual_model:
            actual_model = f"openai/{actual_model}"

        # 组装上下文，带上现有的实体信息
        entities_summary = "当前世界没有任何实体。"
        async with get_db_connection() as conn:
            async with conn.execute("SELECT name, type FROM entities WHERE is_deleted = 0") as cursor:
                rows = await cursor.fetchall()
                if rows:
                    entities_summary = "当前的实体有: " + ", ".join([f"{r['name']}({r['type']})" for r in rows])

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
                api_key=api_key,
                base_url=settings.llm_api_base,
                custom_llm_provider="openai" if settings.llm_api_base else None
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                    
        except Exception as e:
            logger.error(f"Muse chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")