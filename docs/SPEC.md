# 🏗️ Genesis Engine: 系统架构与技术规格说明书 (SPEC)

**版本:** v1.0 Draft
**对应的产品文档:** PRD_Genesis.md
**目标读者:** 系统架构师、后端研发（Python/FastAPI）、前端研发（React/Vite）、Prompt 工程师

---

## 1. 架构总览 (System Architecture Overview)
### 1.1 逻辑分层架构图 (Logical Architecture)
系统采用严格的三层物理隔离架构：
1.  **表现层 (Presentation Layer)**: React + Vite + Tailwind 4。负责无状态的 UI 渲染。Tiptap 处理最终正文的展示，Monitor 面板通过 WebSockets/SSE 实时流式渲染推演日志。
2.  **引擎层 (Narrative Engine Layer)**: FastAPI (Python)。核心业务中枢，调度五大核心 Agent。它是整个系统的“大导演”，管理所有的状态流转并拼接 Prompt。
3.  **记忆层 (Memory & Persistence Layer)**: 
    *   关系型数据库 (PostgreSQL / SQLite via SQLModel) 存储大纲树、实体元信息、和不可变的 IR 日志库。
    *   向量数据库 (ChromaDB / Qdrant) 存储用于 RAG 召回的切片记忆 (StoryBlock Embeddings)。

### 1.2 核心设计模式 (Design Patterns)
*   **事件溯源 (Event Sourcing) & 不可变性 (Immutability)**: `Story IR Block` 是追加不可变日志 (Append-only)。任何对历史剧情的修改都会生成新的修订版 (Revision) 节点，保证时间线可随时一键回档。
*   **逻辑与渲染解耦 (Logic-Render Decoupling)**: 业务逻辑推演绝不产出最终修饰文字，仅产出结构化标签。文字渲染（生花妙笔）仅能在最后一公里发生。
*   **无状态客户端 (Stateless Session)**: 所有的 UI 会话状态（如 Muse 的多轮确认表单）存于原地的 React 组件中。向后端发起的请求始终携带有执行动作的闭环 payload。

---

## 2. 核心域模型与数据契约 (Domain Entities & Data Contracts)

### 2.1 The Grimoire Entity (世界观属性树)
每个实体（角色、势力、地点）的持久化数据结构。由于需支持动态生长，属性详情采用 JSON 存储。
```json
{
  "entity_id": "char_123",
  "type": "character",      // enum: character, faction, location, item
  "name": "宁毅",
  "base_attributes": {
    "aliases": ["血手人屠", "宁立恒"],
    "personality": "表散漫，内果决",
    "core_motive": "保护苏檀儿，苟全性命于乱世"
  },
  "current_status": {       // Scribe 动态更新的可变状态区
    "health": "healthy",
    "inventory": ["转轮手枪", "匕首"],
    "recent_memory_summary": "得知乌家截断蚕丝，准备反击。"
  }
}
```

### 2.2 Story IR Block (剧本中间件)
这是整个 Genesis Engine 最核心的血液，是脱水后的情节切片。**不可变 (Immutable)**。
```json
{
  "block_id": "blk_8899",
  "chapter_id": "chap_45",
  "lexorank": "0|100000:",   // 决定其在全局章节中的绝对线性顺序
  "revision_of": null,       // 若修改历史段落，则指向原 block_id
  "summary": "宁毅给出毒计，决定做空乌家岁布。",
  "involved_entities": ["char_123", "char_456"],
  "scene_context": {
    "location": "loc_789 (苏家布行)",
    "time": "傍晚"
  },
  "action_sequence": [       // 结构化的动作序列，Camera 的渲染基座
    {"actor": "苏檀儿", "intent": "焦急求助", "dialogue": "立恒，蚕丝断了，怎么办？"},
    {"actor": "宁毅", "intent": "抛出毒计", "action": "把玩茶杯，眼神变冷", "dialogue": "让他买，我们做空他。"}
  ]
}
```

### 2.3 The Spark (推演输入指令)
用户启动一轮沙盒推演的输入结构体。
```json
{
  "spark_id": "spk_101",
  "chapter_id": "chap_45",
  "user_prompt": "乌家截断了蚕丝，苏檀儿急疯了向宁毅求助，我要宁毅用极度散漫的态度随口给出一条毒计。",
  "overrides": {} // 允许用户在当次推演临时覆写 Grimoire 设定
}
```

---

## 3. Agent 交互协议与管线 (Agent Protocols & Pipelines)

### 3.1 核心主控协议：The Maestro Pipeline
在沙盒推演态，每一回合 (Turn) 的完整单向链路：
1. **Character (演员)** 思考并输出粗糙的意图和台词。
2. 引擎拦截该输出，连同世界状态打包发给 **The Maestro**。
3. **The Maestro** 返回统一下达的 JSON 裁决：
```json
{
  "is_action_valid": true,
  "reject_reason": "",
  "tension_score": 85,
  "plot_twist_injection": "",
  "is_beat_complete": true,  // 张力达标，通知前端推演结束
  "extracted_ir_block": { ... } // 自动构建上述 2.2 的结构
}
```

### 3.2 最终渲染协议：Camera Engine
当用户点击【Render】时，前端将已脱水的 `Story IR Block` 发给后端 Camera 节点，并附带渲染参数：
*   **Payload**: `{ "ir_block_id": "blk_8899", "pov": "char_123", "style": "肃杀", "subtext_ratio": 0.8 }`
*   **Output**: 纯字符串。通过流式传输 (Streaming) 返回 Tiptap 编辑器。

### 3.3 记忆提取协议：Scribe Agent
用户确认正文段落后触发。
*   **Trigger**: 用户点击 UI 上的 [Commit] 按钮。
*   **Input**: 刚刚锁定的 `Story IR Block`（JSON），系统*严格屏蔽*最终生成的散文串。
*   **Output**: 对涉及到的实体，生成更新指令（Diff），经代码校验后写入数据库的 `current_status` 字段。

---

## 4. 状态机与并发锁定 (State Machines & Concurrency Locks)

### 4.1 Monitor 异步回合单线程流转
*   **锁机制 (Round-Robin Lock)**: 推演沙盒是严格的串行打断。系统在任意时刻只允许当前拿到 Token 的 Character 发言或 Maestro 结算。若后端正在等待 LLM 响应，前端的 `[Action ▶]` 按钮置灰。
*   **上帝之手 (God's Hand Interrupt)**: 用户点击某条推演记录时，后端引擎立即终止当前进行中的 LLM 协程，清空当前 Turn 缓存，等待用户下发覆写指令后，按新设定重启当前回合。

### 4.2 剧本互斥锁 (Manuscript & Grimoire Mutex)
防脏写机制 (Race Condition Prevention)：
*   当系统处于【沙盒推演态】（生成 Spark 到 Commit IR Block 期间）。
*   后端数据库对对应实体的 `Grimoire` 设置为**“Read-Only (只读锁)”**。
*   若用户试图通过 The Muse 强制修改正在参演角色的属性，Muse 将返回拦截信息：“造物主，世界正在推演中 (Locked)，请在当前回合封板 (Commit) 后再修改设定。”

---

## 5. 记忆与上下文组装策略 (RAG & Context Windows)

### 5.1 滑动窗口与动态召回 (Sliding Memory Strategy)
为防推演时 Token 爆炸，Character 的 Prompt 上下文组装需遵循极严权重的 RAG 策略：
1. **绝对免疫区 (Tier 0)**: 角色自身的 `Grimoire Entity` 属性（硬加载，不可省略）。
2. **近期滑动窗口 (Tier 1)**: 绝对加载本章节内发生的前 3 个 `Story IR Block`。
3. **模糊向量召回 (Tier 2)**: 将当前用户的 `Spark` 指令转为 Embedding 向量，向历史库进行 KNN 检索，召回 Top-K=3 个最高相似度的历史 `Story IR Block`，作为“记忆闪回”补充入 Prompt。

---

## 6. 异常流与降级策略 (Edge Cases & Fallbacks)

### 6.1 LLM 无法输出合规 JSON (Parsing Failures)
*   **重试闭环**: 当 The Maestro 等输出 JSON 解析失败（如被大模型用 Markdown 语法包裹 ` ```json `，或缺少花括号），后端代码必须自动进行二次剥离尝试（Regex fallback）。若彻底损坏，向该 LLM 发起最多 2 次静默重试。
*   **熔断**: 2次重试失败后，阻断流程，通过 SSE 向前端报错。

### 6.2 违禁词风控拦截 (Safety Blocks)
*   如 Camera 渲染文字中途被 API 风控拦截流式输出断开，后端抛出 `ERR_SAFETY_BLOCK`。
*   前端展示红色下划线，The Muse 弹出异常应对模板（提供更换提示词入口）。

### 6.3 网络超时与前端重连 (SSE Timeouts)
*   后端的异步推演与渲染走 Server-Sent Events (SSE)。前端需处理 `onclose` 事件。若突发心跳断联，必须携带最后的 `Turn ID` 请求后端接口以恢复挂起的沙盒流转状态，杜绝死锁死循环。
