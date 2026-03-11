# 🏗️ Genesis Engine: 技术架构设计文档 (Technical Architecture Design)

**版本:** v1.0 Draft
**目标读者:** 系统架构师、后端研发、前端研发
**前置文档:** PRD_Genesis.md
**后续文档:** SPEC.md (将包含具体的 JSON Schema 和 API 契约)

本说明书作为 PRD 向 SPEC 过渡的中间文档，旨在从全局视角拉齐研发团队对 Genesis Engine 核心技术栈、逻辑分层、关键数据流转及并发控制的理解。

---

## 1. 系统设计哲学 (Design Philosophy)

1.  **管线绝对解耦 (Ultimate Pipeline Decoupling):** 逻辑推演（产生剧情）与文学渲染（润色文字）必须在物理进程和依赖链条上完全分离。
2.  **拟人化的超级中枢 (The Orchestrated Maestro Loop):** 借鉴 Pi Agent 和 MemGPT 的架构，放弃过去机械的流水线 Agent，The Maestro 作为一个拥有独立暂存记忆的心智中枢，通过一个确定的**程序化编排循环 (Programmatic Orchestration Loop)** 来感知世界、驱动 Character，仅让大模型输出简单的结构化决策，极大降低错误率并避免过度设计的完全自主 Agent。
3.  **不可变基础设施 (Immutable Narrative Data):** 产生的主线剧情点（Story IR Block）永远是追加写入的 (Append-Only)。如果用户修改了历史，只会产生新的 Revision 分支，绝不 `UPDATE` 覆盖原历史记录。
4.  **大模型 Token 经济学 (Token Economics):** 将高频的合法性判定与张力打分交给高速低成本模型（如 DeepSeek-Chat），仅在最后的终端文学渲染（Camera Agent）接入昂贵的顶级模型（如 Claude-3.5-Sonnet 或 GPT-4o）。

---

## 2. 逻辑分层与拓扑结构 (Logical Layer & Topology)

Genesis Engine 采用经典的三层物理隔离架构：

### 2.1 表现层 (Presentation Layer: React + Vite + Tailwind)
*   **职责:** 提供极致的“唯一稿纸”沉浸式体验，处理复杂状态的客户端驻留。
*   **核心布局:** 三栏界面 (Left: The Grimoire, Center: Editor & Monitor, Right: Render Mixer)。
*   **四大全局视图 (Global Views)** 采用前端路由无缝切换：
    *   `Compass (主罗盘)`: 包含上方的核心写作区 (Tiptap) 与下方的推演控制台 (Monitor Sandbox)。
    *   `Network (关系网)`: 可视化渲染当前 Active Grimoire 中所有实体（角色、地点、势力）的连线与爱恨羁绊。
    *   `Archive (档案馆)`: 系统级的长篇大纲树与 RAG 文本溯源检索库。
    *   `Settings (控制台)`: Token 花费看板、大模型 API Key 配置与渲染混合器 (Render Mixer) 默认项。
*   **交互枢纽:** `The Muse Chat`，作为悬浮无状态的天然客服拦截一切意图，调用工具操作这四大视图。

### 2.2 核心调度层 (Orchestration Layer: FastAPI / Python)
*   **职责:** 它是真正的系统大脑，统筹所有的状态流转并管理大模型的网络开销。
*   **核心枢纽:** **The Maestro (大黑板/主控器)**
    *   这是一个基于 MemGPT 理念构建的 **Stateful Orchestration Loop (状态化编排循环)**。
    *   它维护一个内部的 Scratchpad（暂存黑板），记录当前场景的张力和进度。
    *   **放弃纯自主 Tool Calling**：为兼顾模型稳定性和工程可落地性，Maestro 不再自主决定调用哪个工具，而是由 Python 后端程序进行确定的 `for` 循环编排。Maestro （作为 LLM API）仅负责基于当前 Context 输出“是否继续推进”、“场景是否收束”的结构化 JSON 决策。

### 2.3 四大智力阶级 (The Intelligence Hierarchy)
为坚持“如非必要，勿增实体”的极简原则，同时保证系统稳定与 Token 消耗可控，架构对不同节点的大模型赋予了绝对不同的权限与形态：

1.  **交互层 Agent (The Muse)**：
    *   **形态**: `Router / Proxy Agent`。
    *   **职责**: 唯一的面向用户客服。它能理解自然语言，并通过 **Tool Calling** 发出修改 UI、调整配置或发起推演的指令。它管理着前台多轮对话的状态 (Session State)。
    *   **核心 Tool 清单 (能力边界)**:
        *   `create_entity` / `update_entity` / `delete_entity`: 实体 CRUD (调用 Grimoire API)。
        *   `start_spark`: 启动推演 (`POST /api/orchestration/spark`)。
        *   `override_turn`: 微操覆盖 (`POST /api/orchestration/override`)。
        *   `query_grimoire`: 从活动物化视图检索世界状态。
        *   `switch_branch`: 切换/创建平行分支。
2.  **主控层 Agent (The Maestro)**：
    *   **形态**: `Stateful Cognitive Loop Agent` (依赖内存缓存)。
    *   **职责**: 推演大板管家。负责评理、算分，调度底层驱动演员。
    *   **状态维护**: 采用无状态 API 应对并发扩展，但在单次推演循环 (Cognitive Loop) 内，其临时推演状态 (Scratchpad、Turn Logs) 将直接挂载在 **FastAPI 进程内存 (In-Memory)** 中，防止同一会话内每次都要将几千 Token 完整来回吞吐，解决上下文雪崩。
3.  **表演层生成器 (The Character)**：
    *   **形态**: `Stateless LLM API Call`。
    *   **职责**: 一个完美的黑盒函数。**没有工具调用权限，不持久化状态**，仅根据传入的极简 Prompt 输出意图和台词。
4.  **渲染层生成器 (The Camera)**：
    *   **形态**: `Stateless LLM API Call`。
    *   **职责**: 一次性流式吐出散体文字。

*(注：原设计的史官 Scribe 降维为普通的 `Async Background Task` 异步提取函数，不再作为具备独立心智的 Agent 存在，进一步减少系统并发实体。)*

### 2.4 记忆与持久化层 (Snapshot Chain + 单体 SQLite)
为践行极简 MVP 架构，兼具“时光倒流（Time Travel）”与避免过度设计的“事件图谱计算”，系统采用极其优雅的**单一文件架构**：
*   **关系型主库 (SQLite 独尊):** 整个项目的所有大纲、设定、正文全部封装为**单个 `.sqlite` 文件**，支持如同 `.psd` 般的本地项目文件级管理与分享。(注：未来可引入 `Litestream` 或 `cr-sqlite(CRDT)` 以天然支持多设备/云盘无缝同步，V1.0 暂不实现)。
*   **不可变快照链 (Snapshot Chain):** 放弃复杂的 Event Sourcing 及 DAG 实时物化视图，采用 Git 式的线性快照回退模型。
    *   **日常推演**: 在内存级的 Scratchpad (FastAPI 进程) 里暂存 `Pending Facts`。
    *   **固化落盘**: 用户点击 `Commit` 时，系统直接对当前完整的 Grimoire 状态拍一个 JSON 快照存入 SQLite，指向前一个快照。
    *   **分支与回退**: 回退就是读取上一条 `Snapshot JSON`：分支就是在某条 `Snapshot` 上横生一条新 `branch_id` 数据流。彻底免去从零回放重算的计算风暴。
*   *(注：向量 RAG 及 `sqlite-vec` 插件在 V1.0 的短篇场景中为无效冗余，已下放至 V2.0/V3.0 中长篇处理阶段。V1.0 的记忆检索引擎纯粹靠结构化查询与滑动黑板。)*

---

## 3. 关键业务数据流转 (Key Data Flows)

我们通过重塑传统的网文码字流，定义了 Genesis Engine 最核心的三条高速管线：

### 3.1 零基础开局流 (The Cold Start Boilerplate Flow)
`用户自然语言输入` ➡️ `The Muse 解析意图` ➡️ `后端提取实体 JSON` ➡️ `前端弹出 Diff 确认` ➡️ `用户确认` ➡️ `写入 RDBMS (Grimoire)` ➡️ `初始化首章 Storyboard` ➡️ `准备 The Spark`。

### 3.2 异步沙盒推演流 (The Sandbox Debate Flow & State Machine)
推演核心是一个严格定义的**全局状态机 (State Machine)**：
`IDLE` ➡️ `SPARK_RECEIVED` ➡️ `REASONING` ➡️ `CALLING_CHARACTER` ➡️ `EVALUATING` ➡️ (Loop Back) ➡️ `EMITTING_IR` ➡️ `RENDERING` ➡️ `COMMITTED`。

这不再是僵硬的 A 说话 B 裁判，而是一个由 Maestro 驱动的认知循环：
1. **唤醒 (Awaken/SPARK_RECEIVED)**: 全局进入推演态。The Muse 通过 `POST /api/orchestration/spark` 下发核心剧情意图。Maestro 初始化当前场景的 Scratchpad。
2. **观察与思考 (REASONING)**: Maestro 拉取基于 `Snapshot` 和滑动窗口组装好的 Context。Maestro（LLM）在此不负责自主调用外部 Tool，仅作为一个纯函数输出本次思考的**结构化判定**（例：张力是否合格？下一步应该继续叫人说话，还是直接收束吐出 IR？）。
3. **程序化分发 (PROGRAMMATIC DISPATCH)**: 后端 Python 程序解析 Maestro 的 JSON 决策。
    *   如果决定继续，后端代码**显式组装**对应 Character 的上下文并发起调用。
    *   *⚠️ 架构铁律 (Microphone Pass 递话筒模型 & 3-Layer Prompt)*: Maestro 绝不代写角色台词。为响应 "导演指令"，Character 的 Prompt 被硬编码分为严格的三层：
        *   ① **System (不可变层)**: 核心性格/世界观设定。
        *   ② **Scene (场景层)**: 物理空间与近期 Turn Logs。
        *   ③ **Director Note (导演备注，极高权重)**: 如果 Spark 要求某态度，此处将以 `[导演备注要求你此刻表现出愤怒]` 强行注入。模型在保持自身设定的同时，将努力完成导演下发的课题要求。
4. **结算与记忆暂存 (EVALUATING)**: 收到 Character 输出后，记录到暂存的 Turn Logs 发回 REASONING 循环。
5. **场景收束 (EMITTING_IR)**: 当 Maestro 判定张力达标主动输出 `beat_complete: true`，Python 编排程序会立即将其提炼为结构化的脱水剧本块，结束整个循环。

### 3.3 状态转移矩阵与异常中断 (State Machine Transition)

| 当前状态 | 用户触发的交互事件 | 系统动作 (副作用 Hook) | 下游目标状态 |
| :--- | :--- | :--- | :--- |
| **`IDLE`** (空闲) | 用户确认 Spark | 创建新推演回合，初始化 FastAPI 内存 Scratchpad | ➡ **`REASONING`** |
| **`CALLING_CHARACTER`** (等大模型) | 用户猛击 `[Cut ✋]` (强制中断) | 触发 `asyncio.Task.cancel()` 强行斩断当前 LLM HTTP 长连接流。**丢弃且回滚** 本回合积累的 Pending Facts。 | ➡ **`IDLE`** (归零等待) |
| **`EVALUATING`** (回合结算间隙) | The Muse 发送 Override 指令 | 将用户的上帝强行指令注入 Maestro 内存的 `Scratchpad.director_note`。 | ➡ **`REASONING`** (重新思考下半场) |
| **`RENDERING`** (文学渲染中) | 用户对文字不满意，点击 `[Retry]` | 清除上一版前端渲染文字。不污染任何推演逻辑，以相同的 IR 重新向 Camera Agent 发起 API 调用。 | ➡ 自身 **`RENDERING`** 回环 |
| **`EMITTING_IR/RENDERING`** | 全都写得太烂，用户点击 `[Discard]` (废弃) | 清空 FastApi 内存（废弃该段 Pending Events）。底层 SQLite 不新增任何提交。 | ➡ **`IDLE`** (彻底重来) |
| 任何状态 | 网络断开 `ERR_TIMEOUT` | 保留 Scratchpad 当前态，向前端下发异常。需用户手工点击 `Retry`。 | ➡ 原状态卡死 |

*(注：**关于 Override 的严格时序约束**。为防止脏数据污染上下文，当用户在 `CALLING_CHARACTER` 阶段（屏幕正在一个字一个字吐角色台词时）敲入 Override 指令，系统**绝不立即中止**正在返回的流。系统会将 Override 请求放入挂起队列 (Queue)，直到当前这一轮对话完全吐完自然进入 `EVALUATING` 状态后，再将 Override 指令作为下一轮的最高权重 Prompt 注入 `REASONING` 环节。)*

### 3.4 异步事实提炼与渲染流 (Scribe & Render Flow)
当场景进入 `EMITTING_IR` 并被用户圈定：
1. **文笔渲染 (The Camera)**: 合并（IR + 文风参数 + POV），流式倒灌进前端 Tiptap 编辑器。
2. **后台异步提炼 (Scribe Task)**: 与渲染管线并行，FastAPI 触发轻量级的后台提炼函数接手刚出炉的 IR Block：
    *   将 Maestro 积攒的 `Pending Facts` 转化为标准的 Snapshot 快照事件存入 SQLite。
    *   *(注：此处移除向 Embedding 层转化向量的操作，V1.0 着重提取并落盘，RAG 架构延迟至 V2.0)*
3.  **封存 (COMMITTED)**: 用户对正文满意，点击 `Commit`。此时 Active 状态中的临时事实正式转正为一个 `Snapshot`。推演彻底归档。

---

## 4. 并发、锁定与状态约束 (Concurrency & Locks)

为防范大模型系统固有的不确定性与脏数据，架构层面强制实施以下两种锁：

### 4.1 回合制互斥锁 (Round-Robin Mutex for Sandbox)
推演必须是**强制串行**的。
*   不允许两个 Character 同时发言。在任何一个时刻，Token 的控制权只能在一个特定的 Character 会话，或在 Maestro 会话中。
*   前端的 `[Action ▶]` 必须受制于后端的 Loading State 排他锁。

### 4.2 剧本互斥锁 (Manuscript Read-Only Lock)
防范幻觉并发（Race Condition）。
*   当系统处于推演态时（The Spark 已抛出，但 The IR 尚未 Commit），整个左侧世界观属性面板 (`The Grimoire`) 切换为**严格的只读 (Read-Only) 模式**。
*   后端接口将拒绝此阶段任何对人物底层的属性修改（防止当前推演的 Character 上下文被中途篡改导致精神分裂）。

---

## 5. 记忆与上下文组装架构 (Structured Paging Memory)

参考 Pi Agent / MemGPT 的轻量级架构，系统采用**核心状态 + 滚动摘要 + 局部轻量 RAG**的结构化记忆分页策略，精准控制 Input Token。

每次推演唤醒 Character 时，Context 由以下结构化块拼接：
1.  **Core Memory (绝对召回):** 直接从数据库当前活动的 `Grimoire Snapshot` 表提取该角色的基础属性 (性格、动机) 和 `current_status` (当前持有物、刚经历的重大事件)。
2.  **Archival Summary (长期记忆挂载):** 获取上一大章节的 **Chapter Summary**。这由 Scribe 后台异步任务通过低廉模型压缩历史 Block 产生。
3.  **Working Memory (近期滑动窗口):** 直接从数据库中 Select 最近完成的 N 个 `Story IR Block`，外加当前未结束场景中的最后 M 个 `Turn Log`。这是毫米级的分镜感知。
4.  *(V2.0 前瞻规划)* **Vector RAG (长篇召回):** 仅在百万字长篇进入 V2 阶段才引入向量扩展引擎补充大海捞针的超长上下文回溯，V1.0 彻底禁用。

## 6. 其他核心架构考量 (Additional Architectural Considerations)

在推演沙盒之外，为了保障系统的稳定性与可维护性，必须在架构初期划定以下红线：

### 6.1 Token 经济学与 LLM 路由策略 (Model Routing)
系统必须支持多模型混用，绝不能将所有节点的 API 都死绑在一款昂贵模型上（如 GPT-4o）。架构设计需要一个**Model Router（模型路由层）**：
*   **The Maestro (决策层)**: 必须使用具备极强逻辑推理和 Function Calling 能力的顶级模型。
*   **The Character (对话层)**: 优先采用快响应、低成本模型以应对 `while` 循环的高频。
*   **The Camera (文学层)**: 提供用户自定义选项切换专攻文笔的大模型。

### 6.2 可观测性与调试链路 (Local-Native Observability)
为坚守单体极简部署架构，**V1.0 坚决不引入 Langfuse/LangSmith 或是 OpenTelemetry (ClickHouse) 等依赖重型 SaaS/数据库的监控平台**。我们通过以下自建方式实现系统的完全透明：
*   **内部 Trace ID**: 后端为每个 The Spark 启动的回合生成 UUID（`Trace ID`），打穿 The Muse -> Maestro -> Character 的内部 Python 内存 Context 链路。
*   **本地结构化大日志**: 所有上下游 LLM 的原始出入参（Prompt JSON 结构）、执行耗时与 Token 开销计量，统一使用 `loguru` 输出至本地 `.log` 文本文件。
*   **前端开发者连线 (Developer Monitor)**: 核心推演日志（包含 Maestro 的中间判定决策与发送给大模型的隐藏 Prompt）通过 WebSocket 特殊信道下发至前端。通过在 UI 点击开启“开发者视图 (Developer Mode)”，用户/管理员可在 Monitor 面板检视单次调用的纯算开销和底层打分，实现“白盒化”的原生系统内调试。

### 6.3 严格的数据契约与异常兜底 (Strict JSON Error Handling)
*   任何输出 JSON 的调用必须使用 Pydantic / Zod 进行严格结构校验。
*   发生破损时自动重试，失败则阻断。

## 7. 部署策略与通信协议 (Deployment & Communication - MVP)

作为面向创作者个人的 MVP 产品，V1.0 暂不考虑多用户并发安全，系统本质上是一个**以用户体验为中心的单体应用程序 (Single-User Monolith)**。

*   **部署形态 (Local-first Web App)**:
    *   **本地一键起飞**: 主推本地运行形态，提供启动脚本（或可执行包），在本地启动 FastAPI 并打开浏览器访问 `localhost`。用户自带 API Key，零服务器成本，且 `.sqlite` 文件保存在本地。
    *   **云端私有部署**: 代码无需修改即可部署在个人云端服务器上（通过绑定端口提供唯一的单人 Web 服务），供作者多地漫游使用。
*   **通信协议边界 (Network vs. Memory)**:
    *   **外部通信边界 (HTTP/WebSocket)**: Web 前端与后端 (FastAPI) 之间通过标准的 HTTP 和 SSE/WebSocket 交互数据与推演流。The Muse ➡️ Maestro (`POST /api/orchestration/spark`) 单向触发，把控制权交给 Maestro。
    *   **内部全异步通信 (Pure Async Calls/零 REST)**: **Agent 之间绝不使用微服务 REST 接口通信！** The Muse, Maestro, Character, Camera 均属于同一 FastAPI 进程内的类或方法。Maestro 唤醒 Character 或触发 Scribe，本质上是极其高效的 `await internal_function_call(context)` 同进程传参。这使得在内存中传递 Context、共享 Scratchpad 状态、甚至处理紧急中断（直接 `asyncio.Task.cancel()`）的开销降为最低。
    *   **中断信号 (Cut/Override)**: 前端触发紧急变更，后端结束或修正当前正在进行的同进程循环（详见上文 3.3 异常中断矩阵），清空 FastAPI 进程内存中的暂存缓存区，State Machine 强制回落。
*   **超极简基础设施选型 (纯 SQLite Monolith):**
    *   **极简快照链**: Maestro 运行时的 Session Context 和 Pending Facts 仅在 FastAPI 内存中管理；防丢失机制通过 SQLite 保存 `Snapshot JSON` 快照记录实现，摒弃复杂依赖。
    *   *(注：移除独立 Vector DB 与暂缓 sqlite-vec 的接入，全心关注在窗口内逻辑的闭环一致性。)*
*   **本地一键起飞运行:** 甚至不再需要 `docker-compose`，只需一个 Python 环境或单个可执行文件即可秒级启动整个引擎。
