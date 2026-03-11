# 🏗️ Genesis Engine: AI-Native System Specifications (SPEC)

**版本:** v1.0 (Occam's Razor Edition)
**前置文档:** PRD_Genesis.md, Architecture_Design.md
**目标受众:** AI 编程辅助平台 (Cursor, Claude, Local LLMs)、核心人类研发
**设计原则:** 强类型(Strongly Typed)、零歧义(Unambiguous)、程序化控制(Programmatic Control)

---

## 1. 全局数据字典 (Data Dictionary & Schemas)
*(参见: Architecture_Design.md §2.4, PRD_Genesis.md §5.3)*

_⚠️ AI 编码守则: 在编写 FastAPI 路由与数据库模型时，必须严格遵守以下 Pydantic v2 兼容的 JSON Schema。绝不允许凭空捏造字段。_

### 1.1 实体重定义 (Entity - The Grimoire)
系统设定的核心载体，存储于单体 SQLite 中。

```json
// Schema: Entity
{
  "entity_id": "string (UUID)",
  "type": "string (Enum: CHARACTER, FACTION, LOCATION, ITEM)",
  "name": "string",
  "base_attributes": { // 绝对静止的初始设定 (System Prompt 来源)
    "aliases": ["string"],
    "personality": "string",
    "core_motive": "string",
    "background": "string"
  },
  "current_status": { // 由 Scribe 动态改写的快照状态 (Scene Prompt 来源)
    "health": "string",
    "inventory": ["string"],
    "recent_memory_summary": ["string (滑动窗口：后端仅保留最近 N 条，超限自动淘汰最旧条目)"],
    "relationships": {
      "[target_entity_id]": "string (e.g. '仇恨', '暗恋')"
    }
  },
  "is_deleted": "boolean (默认 false，仅做软删除以保证历史快照的外键引用安全)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 1.2 脱水剧本块 (Story IR Block)
推演循环的最终产物。**推演逻辑层面不可变 (`action_sequence` 等结构化字段一旦生成即锁死)**；仅 `content_html` 可被 Camera 渲染/用户精修覆写。

```json
// Schema: StoryIRBlock
{
  "block_id": "string (UUID)",
  "chapter_id": "string (UUID)",
  "lexorank": "string (Lexorank for manual sorting)", 
  "summary": "string (Maestro 提炼的该段落大意)",
  "involved_entities": ["string (UUID)"], 
  "scene_context": {
    "location_id": "string (UUID)",
    "time_of_day": "string"
  },
  "action_sequence": [ // Camera Agent 渲染的基础原料
    {
      "actor_id": "string (UUID 或 'SYSTEM' 表示客观环境/旁白/突发事件)",
      "intent": "string (内心的真实意图)",
      "action": "string (物理动作与微表情。如果是 SYSTEM 则直接描写客观发生的事)",
      "dialogue": "string (说出口的台词，无对白则留空)"
    }
  ],
  "content_html": "string | null (最初为空。Camera 渲染完毕或经用户手工精修最后 Commit 时，承载该大纲块最终落盘的正文内容)",
  "created_at": "datetime"
}
```

### 1.3 推演输入源 (The Spark)
启动并控制一次编排循环 (Orchestration Loop) 的全局参数。

```json
// Schema: TheSpark
{
  "spark_id": "string (UUID)",
  "chapter_id": "string (UUID)",
  "user_prompt": "string (如：'主角被嘲笑，愤而反击')",
  "overrides": { 
    // 上帝模式：在此次推演中强制让某个角色带着特定态度 (Director Note)
    "[entity_id]": "string (如: '必须表现得极其贪婪')" 
  }
}
```

### 1.4 世界观快照与分支 (Snapshot & Branch)
支撑时间倒流和多线剧情的底层数据结构。

```json
// Schema: GrimoireSnapshot
{
  "snapshot_id": "string (UUID)",
  "branch_id": "string (UUID)",
  "parent_snapshot_id": "string (UUID) | null", // null 代表这是世界的起源点
  "triggering_block_id": "string (UUID)",       // 是哪个剧情块的 Commit 触发了这次快照
  "grimoire_state_json": {                      // 当前时刻全量 Entity 的序列化集合
    "entities": ["<List of Schema: Entity>"]
  },
  "created_at": "datetime"
}

// Schema: Branch
{
  "branch_id": "string (UUID)",
  "name": "string (如：'主线', 'IF线：宁毅黑化')",
  "origin_snapshot_id": "string (UUID) | null",
  "is_active": "boolean"
}
```

### 1.5 大纲树节点 (StoryNode)
左侧导航栏的骨架。

```json
// Schema: StoryNode
{
  "node_id": "string (UUID)",
  "branch_id": "string (UUID)",
  "type": "string (Enum: VOLUME, CHAPTER)",
  "title": "string",
  "summary": "string | null",
  "lexorank": "string (Lexorank 保证树状绝对顺序)",
  "parent_node_id": "string (UUID) | null"
}
```

### 1.6 渲染管线请求 (RenderRequest)
Camera Agent 将 IR 转化为文字的请求载体。

```json
// Schema: RenderRequest
{
  "ir_block_id": "string (UUID)",
  "pov_type": "string (Enum: OMNISCIENT, FIRST_PERSON, CHARACTER_LIMITED)",
  "pov_character_id": "string (UUID) | null", 
  "style_template": "string (如：'古风/肃杀/白描')",
  "subtext_ratio": "float (0.0 - 1.0, 决定内心情感渲染比重)"
}
```

### 1.7 Maestro 决策输出 (Maestro Output Definitions)
_⚠️ AI 编码守则: 这是 Maestro LLM API 必须无条件输出的严格格式，需配置 Pydantic 兜底重试。_

```json
// Schema: MaestroDecision (在 REASONING 态输出)
{
  "next_actor_id": "string (UUID) | null",
  "is_beat_complete": "boolean",
  "reasoning": "string (Maestro 的内心独白，通过 WebSocket 下发给开发者看板)"
}

// Schema: MaestroEvaluation (在 EVALUATING 态输出)
{
  "is_valid": "boolean",
  "reject_reason": "string | null",
  "tension_score": "integer (0-100)"
}
```

### 1.8 角色动作输出 (Character Output Definition)
_⚠️ AI 编码守则: Character LLM 必须无条件输出以下格式，同时也是 `StoryIRBlock.action_sequence` 中单条记录的数据源。_

```json
// Schema: CharacterAction (Character LLM 的强制输出格式)
{
  "intent": "string (内心的真实意图)",
  "action": "string (物理动作与微表情)",
  "dialogue": "string (说出口的台词，无对白则留空)"
}
```

### 1.9 史官提炼输出 (Scribe Output Definitions)
_⚠️ AI 编码守则: 绝对禁止让 Scribe 输出完整的 Entity 对象，极易引发幻觉丢字段。必须强制输出以下增量更新 (Delta) 格式，由后台 Python 代码执行精确的 `UPDATE`。一个推演段落通常涉及多个角色，Scribe 必须为每个参与角色分别输出一条 Delta。_

```json
// Schema: ScribeExtractionResult (Scribe 的顶层输出)
{
  "updates": [
    {
      "entity_id": "string (UUID, 标明这条 Delta 是给谁的)",
      "delta": {
        // Schema: ScribeMemoryDelta (嵌套)
        "inventory_changes": { 
          "added": ["string"], 
          "removed": ["string"] 
        },
        "health_delta": "string | null (为空代表未受伤或未变更)",
        "memory_to_append": "string | null (用一两句话总结刚发生的重大事件，后端将自动 Push 到实体 recent_memory_summary 数组中)",
        "relationship_changes": { 
          "[target_entity_id]": "string (描述新的羁绊或仇恨状态)"
        }
      }
    }
  ]
}
```

### 1.9 全局配置 (ProjectSettings)
独立于世界观之外，用于存储单机运行时用户设定的偏好与大模型秘钥的持久化表。

```json
// Schema: ProjectSettings
{
  "id": "single_row_lock",
  "llm_api_keys": {
    "openai": "string | null",
    "anthropic": "string | null",
    "deepseek": "string | null"
  },
  "llm_api_base": "string | null (自定义 API 端点 URL，如阿里云 DashScope 的 OpenAI 兼容地址。留空则使用模型供应商默认端点)",
  "default_render_mixer": {
    "pov_type": "string",
    "style_template": "string",
    "subtext_ratio": "float (0.0 - 1.0, 默认 0.5, 决定内心情感渲染比重)"
  }
}
```

---

## 2. 核心状态机 (State Machine & Concurrency)
*(参见: Architecture_Design.md §3.3)*

_⚠️ AI 编码守则: 必须在 Python 后端实现对以下状态的强检查。在 `REASONING` 或 `CALLING_AGENT` 态，拒绝任何修改设定的外部请求（只读锁）。_

### 2.1 Sandbox State Enum
```python
class SandboxState(str, Enum):
    IDLE = "IDLE"                               # 空闲，等待 Spark
    SPARK_RECEIVED = "SPARK_RECEIVED"           # 收到 Spark，初始化内存 Scratchpad
    REASONING = "REASONING"                     # Maestro 思考该由谁发言或是否结束
    CALLING_CHARACTER = "CALLING_CHARACTER"     # 等待 Character LLM 回复
    EVALUATING = "EVALUATING"                   # Maestro 评估上一轮发言的张力与合法性
    EMITTING_IR = "EMITTING_IR"                 # 提取结构化 Block
    RENDERING = "RENDERING"                     # Camera 正在生成散文
    COMMITTED = "COMMITTED"                     # 用户确认，状态已固化至 SQLite 快照
    INTERRUPTED = "INTERRUPTED"                 # 用户 Cut 或 Override
```

---

## 3. 程序化编排算法 (Programmatic Orchestration Logic)
*(参见: Architecture_Design.md §3.2)*

_⚠️ AI 编码守则: 坚决摒弃让 Maestro Agent（大模型）自主通过 Function Calling 决定流程的思想。必须用以下 Python 伪代码确立的 `for / while` 控制流。 Maestro 只配输出 JSON 结构作为 `if/else` 的判断条件。_

### 3.1 The Maestro Loop (Python Pseudo-code)

```python
async def run_maestro_orchestration(spark: TheSpark, grimoire_snapshot: Grimoire):
    # 1. 挂载内存上下文 (In-Memory Scratchpad) 和 覆盖消息队列
    scratchpad = Scratchpad(turn_logs=[], pending_facts=[], max_turns=10)
    override_queue = get_ws_override_queue(spark.spark_id)

    # 0. 广播推演启动信号
    current_state = SandboxState.SPARK_RECEIVED
    await emit_ws_event("STATE_CHANGE", {"state": current_state})
    current_state = SandboxState.REASONING

    try:
        for turn in range(scratchpad.max_turns):
            # 状态广播
            await emit_ws_event("STATE_CHANGE", {"state": current_state})
            await emit_ws_event("TURN_STARTED", {"turn": turn})

            # 2. 编排决策 (Schema: MaestroDecision)
            decision = await evaluate_scene_progression(spark, grimoire_snapshot, scratchpad)
            await emit_ws_event("SYS_DEV_LOG", {"reasoning": decision.reasoning})
            
            if decision.is_beat_complete:
                current_state = SandboxState.EMITTING_IR
                break

            current_state = SandboxState.CALLING_CHARACTER
            await emit_ws_event("STATE_CHANGE", {"state": current_state})
            
            # 3. 组装 3-Layer Prompt 并调用 Character
            await emit_ws_event("DISPATCH", {"actor_id": decision.next_actor_id})
            char_response = await generate_character_action(
                actor_id=decision.next_actor_id,
                grimoire=grimoire_snapshot, 
                history=scratchpad.turn_logs,
                director_note=spark.overrides.get(decision.next_actor_id, "")
            ) # 此处内部应包含 emit_ws_event("CHAR_STREAM")
            
            # 4. 暂存记忆并进入评估态
            scratchpad.turn_logs.append(char_response)
            current_state = SandboxState.EVALUATING
            await emit_ws_event("STATE_CHANGE", {"state": current_state})

            # 5. 处理排队的上帝指令 (Override) 
            # (确保在 LLM 吐字完成后的安全间隙注入，不污染当前生成流)
            if override_queue.has_pending():
                latest_override = override_queue.pop_all()[-1]
                spark.overrides[latest_override.entity_id] = latest_override.new_directive
                # 触发了 override，下一轮强制重新评估
                continue 

            # 6. 后置张力打分审查 (Schema: MaestroEvaluation)
            evaluation = await score_character_output(char_response, scratchpad)
            if not evaluation.is_valid:
                scratchpad.turn_logs.pop() # 非法动作直接回滚
                await emit_ws_event("SYS_DEV_LOG", {"reject": evaluation.reject_reason})
                current_state = SandboxState.REASONING
        
        # 7. 兜底与收束场景 (LLM Call: IR Extraction)
        # 如果超出 max_turns 还没收束，强制收束
        if current_state != SandboxState.EMITTING_IR:
            await emit_ws_event("SYS_DEV_LOG", {"warning": "Max turns reached, forcing IR extraction."})
            
        current_state = SandboxState.EMITTING_IR
        await emit_ws_event("STATE_CHANGE", {"state": current_state})
        ir_block = await extract_story_ir(scratchpad.turn_logs)
        await persist_to_sqlite(ir_block)
        # ⚠️ 注意: 此处不进入 IDLE！保持 EMITTING_IR 等待态。
        # 真正的 COMMITTED → IDLE 跃迁由 POST /sandbox/commit 路由负责触发。
        await emit_ws_event("SCENE_COMPLETE", {"ir_block": ir_block})

    except asyncio.CancelledError:
        # 用户点击了 [Cut] 强制打断，任务被取消
        current_state = SandboxState.INTERRUPTED
        scratchpad.clear()
        await emit_ws_event("STATE_CHANGE", {"state": current_state})
        await emit_ws_event("ERROR", {"message": "推演已被造物主强行切断 (Cut)。"})
        raise # 将异常抛出给上层 FastAPI 背景任务管理器
        
    except Exception as e:
        # 处理诸如 JSON 解析彻底崩溃、网络断开等
        await emit_ws_event("ERROR", {"message": f"系统崩溃: {str(e)}"})
        raise
```

---

## 4. 前后端通信契约 (IPC Protocols)
*(参见: Architecture_Design.md §7, PRD_Genesis.md §3.3)*

_⚠️ AI 编码守则: 此项目不采用微服务。所有 Agent 在单机 FastAPI 进程内运行。前端与后端的互动仅限于以下信道。_

### 4.1 REST API (统一前缀 `/api/v1/`)

**The Muse 代理网关 (The Muse Gateway)**
*   **POST** `/api/v1/muse/chat`
    *   *Payload*: `{ "messages": [ { "role": "user", "content": "我想写一段..." } ] }`
    *   *Response*: `Content-Type: text/event-stream` (返回 SSE 流，吐出 Muse 的聊天回复以及等待人类确认的 Markdown Tool Call 指令预览)。
    *   *⚠️ 架构执行红线*: The Muse 返回的 Tool Call（如修改角色设定）**仅作为前端渲染确认卡片的凭证**。用户点击确认后，**由前端程序负责发起**原生的 `PATCH /api/v1/grimoire/entities` API 请求。绝不允许后端 `/muse/chat` 接口在未经确认时偷偷落库。

**大纲树与时光机 (Storyboard & History)**
*   **GET** `/api/v1/storyboard/nodes` (拉取左侧边栏的章节大纲树)
*   **POST** `/api/v1/storyboard/nodes` (创建或移动节点)
    *   *Payload*: `{ "title": "第一章：风起", "type": "CHAPTER", "branch_id": "uuid", "parent_node_id": "uuid | null", "after_id": "uuid | null" }` (⚠️ 由后端负责计算并分配最终落库的 `lexorank` 字符串，前端禁算)。
*   **GET** `/api/v1/storyboard/chapters/{chapter_id}/blocks` (🔥 画布主干线：拉取该章节下属的所有 `StoryIRBlock`，前端拼接 `content_html` 进行大屏渲染)。
*   **PATCH** `/api/v1/storyboard/blocks/{block_id}` (用户在脱离推演态的手工精修错别字与文本。*Payload: `{ "content_html": "..." }`*)
*   **POST** `/api/v1/history/checkout` (时光倒流：切回指定的 `snapshot_id` 状态)
*   **POST** `/api/v1/history/branch` (创建平行分支并设为 Active)
*   **GET** `/api/v1/history/branches` (拉取所有分支的历史线)

**推演沙盒控制流 (Sandbox Controls)**
*   **GET** `/api/v1/sandbox/state` (获取当前沙盒状态枚举与暂存的 `turn_logs`。用于前端刷新页面/断线重连后的**状态恢复 (State Recovery)**)
*   **POST** `/api/v1/sandbox/spark` 
    *   *Payload*: `Schema: TheSpark`
    *   *Response*: `202 Accepted` (触发后台 `run_maestro_orchestration` 异步任务)
*   **POST** `/api/v1/sandbox/override`
    *   *Payload*: `{ "entity_id": "uuid", "new_directive": "string" }`
    *   *Behavior*: 放入该次 Spark 的 Override 消息队列，等待 EVALUATING 间隙消费。
*   **POST** `/api/v1/sandbox/commit`
    *   *Payload*: `{ "ir_block_id": "uuid", "final_content_html": "string" }` (⚠️ 用户可带着直接在打字机下发后人工修改热修过的正文结果发起 Commit，覆盖 Camera 生成的内容)。
    *   *Behavior*: 触发 Scribe 后台基于 IR 的增量抽象 Snapshot；落盘 `content_html`；关闭当前推演沙盒。

**全局系统设置 (Project Settings)**
*   **GET** `/api/v1/settings` (拉取大模型 Key 等配置，供右侧面板渲染)
*   **PATCH** `/api/v1/settings` (修改配置)

**世界观 CRUD (The Grimoire Management)**
*   **POST** `/api/v1/grimoire/entities` (创建实体)
*   **PATCH** `/api/v1/grimoire/entities/{entity_id}` (修改实体属性)
*   **DELETE** `/api/v1/grimoire/entities/{entity_id}` (⚠️ **软删除**：物理行为是 `SET is_deleted = true`，绝非 SQL `DELETE FROM`。历史快照仍可安全引用该实体)
*   **GET** `/api/v1/grimoire/entities/{entity_id}` (查询单个实体详情，供 Muse 拔用卡片渲染)
*   **GET** `/api/v1/grimoire/entities`
    *   *Query Parameters*: `?type=CHARACTER` (可选过滤，V1.0 直接拉取全量用于本地缓存，不设 Limit/Offset 分页)

**渲染管线 (Render Pipeline)**
*   **POST** `/api/v1/render/block`
    *   *Payload*: `Schema: RenderRequest`
    *   *Response*: `Content-Type: text/event-stream` (返回 SSE 流供 Web 端原生打字机渲染，流速建议限制 ~30 tokens/s 以平滑视觉)。
    *   *⚠️ 信道说明*: 此接口与 The Muse 聊天一样，属于单次且不可被打断的长文本下发，故采用极简的 **SSE (Server-Sent Events)**。
    *   *⚠️ 状态约定*: 调用此接口时，后端应先将状态设为 `RENDERING`，渲染完毕后回到 `EMITTING_IR` 等待用户 Commit。`RENDERING` 态的进出由渲染接口独立负责，与 Maestro Loop 解耦。

### 4.2 WebSocket 信道 (推演状态流与面板监控)
**连接端点**: `ws://{host}/ws/sandbox` (单连接，复用于推演全程的双向通信)

作为双向通信的高频信道，**仅用于整个后台沙盒推演期间的中控广播**，通过单个 `ws://` 维持长连以接收打断和下发推演碎步。

向前端吐出 `Event Stream`。
*   `EventType: STATE_CHANGE` -> `{ "state": "SandboxState" }` (驱动前端按钮起效或变灰，禁止并发锁)。
*   `EventType: TURN_STARTED` -> `{ "turn": int }` (回合计数器更新)。
*   `EventType: DISPATCH` -> `{ "actor_id": "uuid" }` (告诉前端当前轮到哪个角色说话，点亮头像)。
*   `EventType: CHAR_STREAM` -> `{ "delta": "string" }` (Character LLM 的打字机片段，直接灌入 UI 的 Monitor 面板)。
*   `EventType: SYS_DEV_LOG` -> `{ "reasoning": "...", "reject": "...", "warning": "..." }` (仅在开发者模式生效。下发 Maestro 的原始 JSON 判断，用于 debug)。
*   `EventType: ERROR` -> `{ "code": "string", "message": "string" }` 
    *   *Enum Code*: `ERR_TIMEOUT`, `ERR_JSON_PARSE`, `ERR_SAFETY_BLOCK`, `ERR_CUT`
    *   *Behavior*: 前端需依据短路码做对应的退火处理 (如 `ERR_CUT` 直接清空面板)。
*   `EventType: SCENE_COMPLETE` -> `{ "ir_block": StoryIRBlock }` (脱水完毕，渲染脱水结构框并弹出 Commit 按钮)。

**前端上行消息 (Client → Server)**
*   `Action: CUT` -> `{}` (前端用户点击 [✈️ Cut] 按钮时，通过此 WebSocket 信道上发打断信号。后端收到后调用 `asyncio.Task.cancel()` 斩断推演。)
*   `Action: OVERRIDE` -> `{ "entity_id": "uuid", "new_directive": "string" }` (可选替代 REST `POST /sandbox/override` 的 WS 上行版本，保持单信道干净)。

---

## 5. 组装契约与架构隔离 (Prompt & Isolation Contracts)

_⚠️ AI 编码守则: 绝对禁止将“文学修饰”写进 Character 或 Maestro 的 Prompt 中。_

### 5.1 隔离红线 (The Iron Wall)

| Agent 类型 | 输入源 | 输出结构 | 绝对禁止的行为 |
| :--- | :--- | :--- | :--- |
| **Character** | 3-Layer Prompt (核心设定+近期动向+导演提示) | 仅输出 JSON: 当前内心的 `intent` 加上要物理作出的 `action` / `dialogue`。 | 绝不允许使用第三人称散文体描写自己（如“夕阳下，他的身影拉得很长”）。 |
| **Maestro** | 整体局势快照 + Turn Logs 堆栈 | 仅输出 JSON: 流程流转的 Boolean 与张力打分。 | 绝不允许替 Character 代写台词。 |
| **Camera** | Story IR Block JSON + POV / 风格参数 | Markdown / HTML 散文流。 | 绝不允许创造 IR 中不存在的物理事件、角色或对话。它只能润饰，不能虚构。 |
| **Scribe** | 锁定的 Story IR Block JSON | SQLite 实体表的 `current_status` Update JSON。 | 绝不允许基于 Camera 渲染出的“散文正文”进行总结。模型极易被文学修饰引发过度解读幻觉。只能针对结构化的 IR 提取事实。 |

### 5.2 3-Layer Prompt 强制组装公式 (Jinja2 伪语法)
在向基础模型发起 Character 生成请求时，后端必须以此公式精确合成：

```jinja2
# [Layer 1: System - 绝对静止层]
你扮演实体: {{ character.name }}
你的基本人设: {{ character.base_attributes.personality }}
你的核心动机: {{ character.base_attributes.core_motive }}
目前的客观状态: {{ character.current_status }}

# [Layer 2: Scene & History - 动态滑动层]
当前场景: {{ last_ir_block.scene_context }}
最近发生的事情:
{% for turn in scratchpad.last_5_turns %}
- {{ turn.actor_name }}: {{ turn.action }} "{{ turn.dialogue }}"
{% endfor %}

# [Layer 3: Director Note - 最高权重干预层]
{% if director_note %}
<Director_Note>
⚠️ 极高权重：导演对你当前回合的表现做出了硬性指示：
{{ director_note }}
请在不违背核心人物设定的情况下，顺应并表现出上述指导。
</Director_Note>
{% endif %}

请以 JSON 格式输出你在当前局势下的 `intent`, `action`, 和 `dialogue`。
```

---

## 6. 物理工程落地拓扑 (Physical Implementation Topology)

_⚠️ AI 编码守则: 为了保证架构的纯粹性，未来的实际物理代码目录必须严格遵照以下结构与阶段进行落地，严禁随意创建冗余的抽象层或微服务模块。_

### 6.1 阶段一：基础设施与领域模型 (Infrastructure & Domains)
*   **`backend/requirements.txt`** (或 `uv` 配置): 锁定 `fastapi, aiosqlite, pydantic, loguru, litellm`。
*   **`backend/database.py`**: 单体异步 SQLite 的建表与连接池逻辑。*(⚠️ AI 编码守则: 必须在 AIOSQLite 建立连接时立刻执行 `PRAGMA journal_mode=WAL;` 以实现无阻塞的读写并发，防范沙盒长连时的 Database Locked 崩溃。)*
*   **`backend/models.py`**: 物理落地全量 Pydantic V2 实体类（严格遵循本 SPEC 第 1 章与第 2 章的所有 Schema 与 Enum）。

### 6.2 阶段二：中枢控制器与管线 (The Maestro Pipeline)
*   **`backend/services/maestro_loop.py`**: 翻译并物理实现本 SPEC §3.1 的 Orchestration Loop 纯异步流。
*   **`backend/services/llm_client.py`**: 剥离组装 Jinja2 Prompt，并调用 LiteLLM/OpenAI 完成带重试机制的结构化输出。
*   **`backend/services/scribe_worker.py`**: 异步任务，负责提取事实更新 SQLite `current_status`。

### 6.3 阶段三：REST API 与 WebSocket 通信 (API & IPC)
*   **`backend/routes/grimoire_api.py`**: 包含 `?type=CHARACTER` 过滤的实体 CRUD 接口。
*   **`backend/routes/sandbox_api.py`**: 处理 Spark 入口、Override 注入、Commit 落库以及 Render 的 SSE 推流。
*   **`backend/websocket_manager.py`**: 统筹 `STATE_CHANGE`, `ERROR`, `CHAR_STREAM` 等全部 7 种 Event Stream 的下发。
*   **`backend/main.py`**: FastAPI App 挂载入口。

### 6.4 阶段四：前端 React 画布 (The Canvas)
*   **构建栈**: `Vite + React 18+ + TypeScript`
*   **`frontend/src/store/sandboxStore.ts`**: 用 Zustand 全面接管底层的沙盒流转状态与对话历史缓存。
*   **`frontend/src/components/TheManuscript.tsx`**: 彻底无状态化渲染 Tiptap 正文与不可变历史。
*   **`frontend/src/components/TheMonitor.tsx`**: 接收并流式打印 Maestro 与 Character 内心独白的开发者看板。

*(注：在后续实际 AI 结令落地时，必须严格按以上四大阶段顺次打通并进行 API 连通验证，严禁在后端模型未就绪时跳跃至前端开发。)*

---

## 7. 核心测试与验收基准 (Testing & Validation Criteria)

_⚠️ AI 编码守则: 为了保证架构层面的防爆性，在完成阶段一与阶段二（后端领域模型与管线）的编码后，必须使用 `pytest` (或相近框架) 通过以下**强制测试用例**的验证，才能宣布后端完工。_

### 7.1 Pydantic 强类型抗压测试 (Validation Tests)
*   **断言目标**: 当 LLM 返回残缺的 JSON 或字段超界时，系统必须在最外围被 Pydantic 拦截。
*   **测试用例要求**:
    *   构造必填字段缺失的 `MaestroDecision` JSON payload，断言触发 `ValidationError`。
    *   构造含有多余 Markdown 格式符（如 ` ```json `）的包裹文本，测试 JSON 解析器能否具备基础洗数据容错能力。

### 7.2 状态机与并发断言测试 (State Machine TDD)
*   **断言目标**: 推演过程中的状态跃迁必须绝对遵守转移矩阵。
*   **测试用例要求**:
    *   **The Cut Test (强制打断测试)**: 模拟沙盒处于 `CALLING_CHARACTER` 态时，抛入 `asyncio.CancelledError`，断言 `SandboxState` 成功重置为 `INTERRUPTED`，且 `Scratchpad` 被安全清空。
    *   **The Lock Test (只读锁测试)**: 模拟沙盒处于 `EVALUATING` 态时，测试向 `PATCH /api/v1/grimoire/entities/{id}` 接口发请求。系统必须返回 `409 Conflict` (或受限提示)，断言防脏写锁生效。

### 7.3 管线兜底测试 (Pipeline Fallback Tests)
*   **断言目标**: 编排系统不能因为大模型的智障而死循环。
*   **测试用例要求**:
    *   **Max Turns Test**: 挂载一个模拟始终返回 `is_beat_complete: false` 的 Dummy Maestro 模型，要求测试验证系统在运行到等于 `max_turns` 时，能够强制退出 `for` 循环并无缝执行 `EMITTING_IR` 收束操作。