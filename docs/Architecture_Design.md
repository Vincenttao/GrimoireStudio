# 🏗️ Genesis Engine: 技术架构设计文档 (Technical Architecture Design)

**版本:** v1.0 Draft
**目标读者:** 系统架构师、后端研发、前端研发
**前置文档:** PRD_Genesis.md
**后续文档:** SPEC.md (将包含具体的 JSON Schema 和 API 契约)

本说明书作为 PRD 向 SPEC 过渡的中间文档，旨在从全局视角拉齐研发团队对 Genesis Engine 核心技术栈、逻辑分层、关键数据流转及并发控制的理解。

---

## 1. 系统设计哲学 (Design Philosophy)

1.  **管线绝对解耦 (Ultimate Pipeline Decoupling):** 逻辑推演（产生剧情）与文学渲染（润色文字）必须在物理进程和依赖链条上完全分离。
2.  **拟人化的超级中枢 (The Omniscient Maestro Loop):** 借鉴 Pi Agent 和 MemGPT 的架构，放弃过去机械的流水线 Agent，The Maestro 作为一个拥有独立长期记忆的心智模型，通过一个连续的 Event Loop 来感知世界、驱动 Character 和调用外部工具（Tools），而不是仅仅充当一个僵硬的过滤节点。
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
    *   这是一个基于 MemGPT/Pi 理念构建的 **Stateful Loop (状态化循环)**。
    *   它维护一个内部的 Scratchpad（暂存黑板），记录当前场景的张力和进度。
    *   通过暴露显式的 **Tool Calling (函数调用)** 能力给大模型，Maestro 可以自主决定何时发起推演 (`call_character`)、何时总结提炼事实 (`update_grimoire_memory`)，以及何时收束当前场景 (`emit_ir_block`)。
    *   过去的 Scribe（记忆提取）和 Director（IR脱水）不再是独立的 LLM API 调用，而是 Maestro 心智模型在思考后主动调用的底层 Tool。

### 2.3 四大智力阶级 (The Intelligence Hierarchy)
为坚持“如非必要，勿增实体”的极简原则，同时保证系统稳定与 Token 消耗可控，架构对不同节点的大模型赋予了绝对不同的权限与形态：

1.  **交互层 Agent (The Muse)**：
    *   **形态**: `Router / Proxy Agent`。
    *   **职责**: 唯一的面向用户客服。它能理解自然语言，并通过 **Tool Calling** 发出修改 UI、调整配置或发起推演的指令。它管理着前台多轮对话的状态 (Session State)。
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

### 2.4 记忆与持久化层 (Event Sourcing + 单一 SQLite 向量引擎)
为践行极简 MVP 架构，兼具“时光倒流（Time Travel）”与“大海捞针”能力，系统彻底**摒弃了多库并行的复杂架构（放弃 Redis 与独立 Chroma/Milvus）**，采用极其优雅的**单一文件架构**：
*   **关系型主库 (SQLite 独尊):** 整个项目的所有大纲、设定、正文全部封装为**单个 `.sqlite` 文件**，支持如同 `.psd` 般的本地项目文件级管理与分享。
*   **事件溯源模型 (Event Sourcing):** 放弃复杂的 Active/Snapshot 双表设计，The Grimoire 仅保存“发生过的事实变更事件 (Fact Events)”。
    *   `Pending Events`: 推演过程产生，一旦 `Cut` 或异常即抛弃。
    *   `Committed Events`: 用户确认后，将事件状态固化。所有世界状态通过天然的事件回溯动态计算得出，天然支持撤销与多重平行分支。
*   **原生向量检索 (SQLite-Vec):** 借助 `sqlite-vec` 或 `sqlite-vss` 插件，将文本的 Embedding 向量直接作为 SQLite 的列数据存储。实现结构化数据与向量数据的绝对 ACID 一致性，彻底避免回档时产生的“幽灵记忆”或脏数据。

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
2. **观察与思考 (REASONING)**: Maestro 拉取上下文（注意：Maestro 本身是**无连接状态的 Stateless API**。它每经历一轮循环，都是重新挂载 Core Context + 历史 Scratchpad 记录。为防止 Token 雪崩，架构将强制执行滑动窗口或摘要压缩策略，设定单次会话历史记录的 Budget 阈值）。
3. **调用演员 (CALLING_CHARACTER)**: Maestro 构造该角色的上下文，发起一次对 Character 大模型的**完全独立的 API 子调用**。
    *   *⚠️ 架构铁律 (Microphone Pass 递话筒模型 & 3-Layer Prompt)*: Maestro 绝不代写角色台词。为响应 "导演指令"，Character 的 Prompt 被硬编码分为严格的三层：
        *   ① **System (不可变层)**: 核心性格/世界观设定。
        *   ② **Scene (场景层)**: 物理空间与近期 Turn Logs。
        *   ③ **Director Note (导演备注，极高权重)**: 如果 Spark 要求某态度，此处将以 `[导演备注要求你此刻表现出愤怒]` 强行注入。模型在保持自身设定的同时，将努力完成导演下发的课题要求。
4. **结算与记忆整理 (EVALUATING)**: 收到 Character 输出后，Maestro 通过内部循环评估合法性和张力。
    *   如果有重大事实演变，Maestro 仅记录在暂存黑板的 `Pending Facts` 中。
5. **场景收束 (EMITTING_IR)**: 当 Maestro 判定张力达标主动调用工具吐出结构化的脱水剧本块。此时等待用户做最终审阅。并同步触发后台 Scribe Agent 工作链。

### 3.3 异步事实提炼与渲染流 (Scribe & Render Flow)
当场景进入 `EMITTING_IR` 并被用户圈定：
1. **文笔渲染 (The Camera)**: 合并（IR + 文风参数 + POV），流式倒灌进前端 Tiptap 编辑器。
2. **后台异步提炼 (Scribe Task)**: 与渲染管线并行，FastAPI 触发轻量级的后台提炼函数接手刚出炉的 IR Block：
    *   将 Maestro 积攒的 `Pending Facts` 转化为标准的 Fact Events。
    *   将 IR 的核心语义请求 Embedding 层转换为向量，作为同一条 SQLite 记录的附带列直接写入单机数据库，用于未来精准召回。
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
1.  **Core Memory (绝对召回):** 直接从数据库 `Grimoire` 表提取该角色的基础属性 (性格、动机) 和 `current_status` (当前持有物、刚经历的重大事件)。
2.  **Archival Summary (长期记忆挂载):** 获取上一大章节的 **Chapter Summary**。这由 Scribe 后台异步任务通过低廉模型压缩历史 Block 产生。
3.  **Working Memory (近期滑动窗口):** 直接从数据库中 Select 最近完成的 N 个 `Story IR Block`，外加当前未结束场景中的最后 M 个 `Turn Log`。这是毫米级的分镜感知。
4.  **Vector RAG (按需召回):** 仅当跨越章节且碰到历史关键实体时，借助 SQLite 内置的向量扩展引擎调用查询，防范大海捞针与 OOC。

## 6. 其他核心架构考量 (Additional Architectural Considerations)

在推演沙盒之外，为了保障系统的稳定性与可维护性，必须在架构初期划定以下红线：

### 6.1 Token 经济学与 LLM 路由策略 (Model Routing)
系统必须支持多模型混用，绝不能将所有节点的 API 都死绑在一款昂贵模型上（如 GPT-4o）。架构设计需要一个**Model Router（模型路由层）**：
*   **The Maestro (决策层)**: 必须使用具备极强逻辑推理和 Function Calling 能力的顶级模型。
*   **The Character (对话层)**: 优先采用快响应、低成本模型以应对 `while` 循环的高频。
*   **The Camera (文学层)**: 提供用户自定义选项切换专攻文笔的大模型。

### 6.2 可观测性与调试链路 (Observability & Tracing)
*   **分布式追踪 (Distributed Tracing)**: 为每次推演注入统一的 `Trace ID`，打穿 The Muse -> Maestro -> Character 的调用链路，借由 OpenTelemetry 让内部流转透明。
*   **开发者视图 (Developer Mode)**: 在前端 UI 预留开关，开启后，可在 Monitor 中查看被隐藏的 Maestro 内心独白、消耗 Token 看板及函数调用原始 JSON。

### 6.3 严格的数据契约与异常兜底 (Strict JSON Error Handling)
*   任何输出 JSON 的调用必须使用 Pydantic / Zod 进行严格结构校验。
*   发生破损时自动重试，失败则阻断。

## 7. 部署策略与通信协议 (Deployment & Communication - MVP)

作为面向创作者个人的 MVP 产品，V1.0 暂不考虑大规模 K8s 集群横向伸缩。
*   **通信协议边界**:
    *   The Muse ➡️ Maestro (`POST /api/orchestration/spark`) 单向触发，把控制权交给 Maestro Cognitive Loop。
    *   Maestro ➡️ FrontEnd 严格基于 HTTP SSE/WebSocket 下发进度。
    *   **中断信号 (Cut/Override)**: 前端触发紧急变更，后端结束或修正当前正在 `REASONING` 的循环，清空 FastAPI 进程内存中的暂存缓存区，State Machine 强制回落。
*   **超极简基础设施选型 (纯 SQLite Monolith):**
    *   **移除 Redis**: Maestro 运行时的 Session Context 和 Pending Facts 仅在 FastAPI 内存中管理；防丢失机制通过 SQLite 的 WAL（预写日志）模式保障。
    *   **移除独立 Vector DB**: 内置 `sqlite-vec` / `sqlite-vss`。整个用户项目最终沉淀为您本地硬盘上的单一 `.sqlite` 格式文件。
*   **本地一键起飞运行:** 甚至不再需要 `docker-compose`，只需一个 Python 环境或单个可执行文件即可秒级启动整个引擎。
