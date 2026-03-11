# 🤖 Project Genesis: AI 编程与架构纪律 (AGENT.md)

**用途:** 规范所有参与本项目的 AI 编程助手（Agent/Cursor/Claude 等）在撰写、修改底层代码与系统架构时的行为边界。
**状态:** 强制执行 (Strict Enforcement - 违背此文档的生成的代码将被视为破坏架构)

---

## 1. 核心架构与编排纪律 (Architecture & Orchestration)

### 1.1 拒绝纯自主大模型路由 (No Autonomous LLM Routing)
*   **动作准则:** 系统核心中枢 The Maestro 必须采用**程序化编排 (Programmatic Orchestration)**。在 FastAPI 后端，必须用显式的 `async for / while` 循环控制推演进度。
*   **禁止操作:** 严禁将控制权全部交给大模型的 Function Calling（即不准让模型自己决定现在该调 API 还是该结束）。LLM 在这里只作为一个纯函数，输出特定的 JSON 决策，然后交回给 Python 代码。

### 1.2 绝不再造分布式 (Zero Microservices)
*   **动作准则:** V1.0 必须贯彻单体应用 (Single-User Monolith) 理念。
*   **禁止操作:** 严禁在 Agent 之间设计 REST API 相互调用！The Muse, Character, Maestro 必须是同一 FastAPI 进程中的类或者函数，流转数据必须走极其底层的 `await internal_function_call(context)`。

### 1.3 严格的锁机制 (Strict Mutex & Locks)
*   **动作准则:** 必须严格实现“回合制互斥锁”与“剧本防脏写锁”。
*   **禁止操作:** 绝对不允许并发执行多个推演回合；在推演未 `Commit` 前，绝对不允许外部请求修改（UPDATE）当前的 Grimoire 实体库状态。

### 1.4 拒绝外部监控依赖 (No External SaaS Observability)
*   **动作准则:** 系统内部流转的透明度靠本地的 `loguru` 和 WebSocket `SYS_DEV_LOG` 实现。
*   **禁止操作:** 严禁在代码中引入 Langfuse, LangSmith 或 OpenTelemetry 等重型外部监控 SaaS SDK。

---

## 2. 数据与持久化纪律 (Data & Persistence)

### 2.1 极简持久化选型 (The SQLite Monolith)
*   **动作准则:** 一切归于单体 SQLite 文件。
*   **禁止操作:** 严禁引入 Redis 缓存。严禁在 V1.0 代码中引入 ChromaDB, Milvus 或是 `sqlite-vec` 向量引擎扩展。禁止实现大海捞针式的超长 RAG，仅依赖滑动窗口加载近期 `Turn Logs` 和 `Story IR Block`。

### 2.2 快照链与不可变原则 (Snapshot Chain & Immutability)
*   **动作准则:** 世界观状态采用**快照链 (Snapshot Chain)** 存储模式。当场景提交时，对当前整个 `Grimoire` State 拍个可追溯的快照。
*   **禁止操作:** 禁止盲目构造复杂的 DAG 事件溯源图计算法则，或随意使用 SQL 的 `UPDATE` 覆写并抹除历史剧情片段。

---

## 3. Agent IO 与 LLM 交互守则 (LLM Integration Standards)

### 3.1 强制 JSON 与防破损 (Strict JSON & Fallbacks)
*   **动作准则:** 调用 Character 和 Maestro 时，强制要求其输出 `SPEC.md` 中定义的 JSON Schema。并在代码中用 Pydantic V2 构建带有自动重试与兜底逻辑的解析器。
*   **禁止操作:** 严禁使用正则去大段散文里抠取业务字段。更不能信任大模型没有格式包裹的输出。

### 3.2 零硬编码与 Prompt 隔离 (Prompt & Logic Separation)
*   **动作准则:** 所有 AI 角色的指令（尤其是 `3-Layer Prompt`）必须彻底从后端 `routers` 或 `services` 控制流中抽离，可作为独立的模版（如 Jinja2 或单独配置常量）管理。
*   **禁止操作:** 严禁将大段中文 Prompt 字符字面量 (String Literals) 直接写在 FastAPI 控制器函数的内部。

### 3.3 隔离红线与反幻觉纪律 (The Iron Wall)
*   **动作准则:** 各个 Agent 必须严格坚守自己的数据出入边界。
*   **禁止操作:** 
    1. 严禁 Character 使用第三人称散文体描写自己。
    2. 严禁 Camera 在渲染时虚构 `StoryIRBlock` 中不存在的物理事件、角色或对话。
    3. 严禁 Scribe 读取 Camera 生成的最终散文进行总结（必须读结构化的 `StoryIRBlock` 防幻觉）。

---

## 4. UI 与前后端交互边界 (UI & IPC Strictness)

### 4.1 沉浸式唯一稿纸 (Minimalist UI Rendering)
*   **动作准则:** 前端必须保持 Tiptap 富文本为界面的绝对核心。系统级别的通知与对话框必须收敛到右侧的 `The Muse` 聊天面板中。
*   **禁止操作:** 绝对不允许在前端编写遮挡主正文编辑区的全屏 Modals 弹窗进行状态确认。

### 4.2 WebSocket 实时性优先 (Real-time Feedback)
*   **动作准则:** 后端在沙盒推演进行期间，必须通过 WebSocket (或 SSE) 实时向前端发射 `Event Stream` (如 `CHAR_STREAM` 和 `SYS_DEV_LOG`)，确保用户和开发者能随时监视推演状态。
*   **禁止操作:** 禁止使用 Ajax 轮询来获知推演进度。

---

## 5. 防患未然的契约底线 (The Golden Rule)

**在撰写或修改每一行代码前，必须查阅并严格遵循 `docs/SPEC.md` 中定义的 JSON Schema，绝不允许 AI 凭空捏造和扩展未登记在案的字段或接口。如果在代码实现中发现 SPEC 不合理，必须先向人类开发者报告，优先修改 SPEC 文档再动代码！**

---

## 6. 测试驱动强制纪律 (Test-Driven Development Mandate)

### 6.1 逢功能必测试 (Tests Before Trust)
*   **动作准则:** 每当我们（AI 助手）完成一个具体的后端函数、路由或数据模型的构建后，**必须**主动同步产出对应的单元测试 (`pytest` 用例)。在尚未书写测试并证明其跑通前，严禁宣称“该功能已开发完毕”。
*   **验收标准:** 必须覆盖 `docs/SPEC.md` 第 7 章中规定的所有“核心测试与验收基准”（包含 Pydantic 强类型抗压、状态机打断与锁机制、以及管线兜底退出）。

---

## 7. AI 执行与验证命门 (AI Execution Commands)

*   **动作准则:** AI 在被要求“实现某个功能”或“修复某个 Bug”时，必须在同一轮对话内**主动执行**以下代码格式化与测试验证流程。严禁在未经本地验证通过的情况下直接回复人类“已修复”。
*   **核心终端命令栈 (The Commands):**
    *   执行后端单元测试: `pytest backend/tests/ -v` 或 `uv run pytest backend/tests/`
    *   静默格式化后台代码 (Black/Ruff): `ruff format backend/` & `ruff check backend/ --fix`
    *   检查前端类型错误: `cd frontend && npm run typecheck`

---

## 8. 提交与 PR 审查清单 (Review & Checklist)

*   **动作准则:** 任何一次大的代码重构或新 API 落地后，AI 必须对照以下清单进行自我审查并向造物主报告：
    1.  [ ] 我的实现是否严格遵守了 `SPEC.md` 的 Pydantic JSON Schema，没有任何私自增加的非标字段？
    2.  [ ] 我的路由代码里是否存在破坏“隔离红线”的直接中文 Prompt 拼接？
    3.  [ ] 我是否为这次新增的逻辑编写对应了 `backend/tests/` 下的 `pytest` 函数？
    4.  [ ] 是否引发了 SQLite 并发下的 `Database is locked` 危险行为？

---

## 9. 记忆沉淀与避坑墓地 (Memory Accumulation / Bug Graveyard)

*   **动作准则:** 每当 AI 犯下低级错误或遇到复杂的架构死锁被造物主纠正后，必须主动将“流血教训”以 `/learned` 的形式补充到下方，防止后续的 Agent 踩入相同的坑。
*   *(当前暂无新增教训，在此期待您的第一次挫折)*

> `<EOF>`
